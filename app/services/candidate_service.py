from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from datetime import datetime
import pytz

from app.models.models import (
    Candidate, Member, Election, ElectionEvent,
    Ward, Village, Mandal, Assembly, District
)
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from datetime import datetime
import pytz

from app.models.models import (
    Candidate, Nomination, Member, Election, ElectionEvent,
    Ward, Village, Mandal, Assembly, District, Admin
)



from app.utils.nlp_search import rank_by_similarity

IST = pytz.timezone("Asia/Kolkata")


async def approve_candidate(
    db: AsyncSession,
    candidate_id: int,
    admin_id: int,
    approval_notes: str | None = None
):
    """
    Admin approves a candidate.
    
    Steps:
    1. Get candidate (must be PENDING)
    2. Create Nomination record (status=APPROVED)
    3. Update Candidate status to APPROVED
    
    Returns:
        - nomination record with decision
    
    Raises:
        ValueError: If candidate not found, already reviewed, etc.
    """
    
    # Get candidate
    result = await db.execute(
        select(Candidate)
        .options(
            joinedload(Candidate.member),
            joinedload(Candidate.election),
            joinedload(Candidate.nomination)
        )
        .where(Candidate.candidate_id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    
    if not candidate:
        raise ValueError("Candidate not found")
    
    if candidate.status != "PENDING":
        raise ValueError(f"Cannot approve. Candidate status is {candidate.status}, not PENDING")
    
    # Check if nomination already exists
    if candidate.nomination:
        raise ValueError(f"Candidate already reviewed with status: {candidate.nomination.status}")
    
    # Create Nomination record
    nomination = Nomination(
        candidate_id=candidate_id,
        election_id=candidate.election_id,
        member_id=candidate.member_id,
        status="APPROVED",
        approval_notes=approval_notes,
        reviewed_by=admin_id,
        reviewed_at=datetime.now(IST)
    )
    
    # Update Candidate status
    candidate.status = "APPROVED"
    
    db.add(nomination)
    await db.commit()
    await db.refresh(nomination)
    
    return {
        "message": "Candidate approved successfully",
        "nomination_id": nomination.nomination_id,
        "candidate_id": candidate_id,
        "status": "APPROVED",
        "reviewed_at": nomination.reviewed_at,
        "approval_notes": approval_notes
    }

async def get_candidate_details(db: AsyncSession, candidate_id: int):
    """
    Get detailed candidate info for admin review before approve/reject.
    """
    
    result = await db.execute(
        select(Candidate)
        .options(
            joinedload(Candidate.member)
            .joinedload(Member.ward)
            .joinedload(Ward.village)
            .joinedload(Village.mandal)
            .joinedload(Mandal.assembly)
            .joinedload(Assembly.district),
            joinedload(Candidate.election).joinedload(Election.event),
            joinedload(Candidate.nomination)
        )
        .where(Candidate.candidate_id == candidate_id)
    )
    
    candidate = result.scalar_one_or_none()
    if not candidate:
        return None
    
    # Check if already reviewed
    nomination = candidate.nomination
    
    return {
        "candidate_id": candidate.candidate_id,
        "member_id": candidate.member_id,
        "name": candidate.member.name,
        "mobile": candidate.member.mobile,
        "email": candidate.member.email,
        "photo_url": candidate.member.photo_url,
        
        "status": candidate.status,
        "applied_at": candidate.nominated_at,
        
        "election": candidate.election.event.title if candidate.election and candidate.election.event else None,
        "election_id": candidate.election_id,
        
        # Location
        "district": candidate.member.ward.village.mandal.assembly.district.district_name,
        "assembly": candidate.member.ward.village.mandal.assembly.assembly_name,
        "mandal": candidate.member.ward.village.mandal.mandal_name,
        "village": candidate.member.ward.village.village_name,
        "ward": candidate.member.ward.ward_number,
        
        # Nomination record (if reviewed)
        "nomination": {
            "nomination_id": nomination.nomination_id,
            "status": nomination.status,
            "reviewed_at": nomination.reviewed_at,
            "reviewed_by": nomination.reviewed_admin.name if nomination.reviewed_admin else None,
            "rejection_reason": nomination.rejection_reason,
            "approval_notes": nomination.approval_notes,
        } if nomination else None
    }




async def reject_candidate(
    db: AsyncSession,
    candidate_id: int,
    admin_id: int,
    rejection_reason: str
):
    """
    Admin rejects a candidate with reason.
    
    Steps:
    1. Get candidate (must be PENDING)
    2. Create Nomination record (status=REJECTED) with reason
    3. Update Candidate status to REJECTED
    
    Returns:
        - nomination record with rejection reason
    
    Raises:
        ValueError: If candidate not found, already reviewed, etc.
    """
    
    if not rejection_reason or len(rejection_reason.strip()) < 5:
        raise ValueError("Rejection reason is required (minimum 5 characters)")
    
    # Get candidate
    result = await db.execute(
        select(Candidate)
        .options(
            joinedload(Candidate.member),
            joinedload(Candidate.election),
            joinedload(Candidate.nomination)
        )
        .where(Candidate.candidate_id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    
    if not candidate:
        raise ValueError("Candidate not found")
    
    if candidate.status != "PENDING":
        raise ValueError(f"Cannot reject. Candidate status is {candidate.status}, not PENDING")
    
    # Check if nomination already exists
    if candidate.nomination:
        raise ValueError(f"Candidate already reviewed with status: {candidate.nomination.status}")
    
    # Create Nomination record
    nomination = Nomination(
        candidate_id=candidate_id,
        election_id=candidate.election_id,
        member_id=candidate.member_id,
        status="REJECTED",
        rejection_reason=rejection_reason.strip(),
        reviewed_by=admin_id,
        reviewed_at=datetime.now(IST)
    )
    
    # Update Candidate status
    candidate.status = "REJECTED"
    
    db.add(nomination)
    await db.commit()
    await db.refresh(nomination)
    
    return {
        "message": "Candidate rejected successfully",
        "nomination_id": nomination.nomination_id,
        "candidate_id": candidate_id,
        "status": "REJECTED",
        "rejection_reason": rejection_reason.strip(),
        "reviewed_at": nomination.reviewed_at
    }


# =========================================================
# 5️⃣ GET ALL NOMINATIONS (Approval History)
# =========================================================
async def get_nominations(
    db: AsyncSession,
    status: str | None = "ALL",
    election_id: int | None = None,
    assembly_id: int | None = None,
):
    """
    Get all nominations (approved/rejected) - Admin history view.
    """
    
    query = (
        select(Nomination)
        .options(
            joinedload(Nomination.member),
            joinedload(Nomination.candidate),
            joinedload(Nomination.election).joinedload(Election.event),
            joinedload(Nomination.reviewed_admin)
        )
    )
    
    # Status filter
    if status and status != "ALL":
        query = query.where(Nomination.status == status.upper())
    
    # Election filter
    if election_id:
        query = query.where(Nomination.election_id == election_id)
    
    # Assembly filter
    if assembly_id:
        query = query.join(Nomination.member)\
                     .join(Member.ward)\
                     .join(Ward.village)\
                     .join(Village.mandal)\
                     .where(Mandal.assembly_id == assembly_id)
    
    result = await db.execute(query.order_by(Nomination.reviewed_at.desc()))
    nominations = result.scalars().all()
    
    return {
        "total": len(nominations),
        "nominations": [
            {
                "nomination_id": n.nomination_id,
                "candidate_id": n.candidate_id,
                "member_name": n.member.name,
                "member_id": n.member_id,
                "mobile": n.member.mobile,
                "status": n.status,
                "applied_at": n.applied_at,
                "reviewed_at": n.reviewed_at,
                "reviewed_by": n.reviewed_admin.name if n.reviewed_admin else None,
                "rejection_reason": n.rejection_reason,
                "approval_notes": n.approval_notes,
                "election": n.election.event.title if n.election and n.election.event else None,
            }
            for n in nominations
        ]
    }



async def get_nomination_stats(
    db: AsyncSession,
    election_id: int | None = None,
    event_id: int | None = None
):
    """
    Get statistics for admin dashboard.
    """
    
    query_pending = select(func.count(Candidate.candidate_id)).where(
        and_(
            Candidate.status == "PENDING",
            ~Candidate.nomination.has()
        )
    )
    
    query_approved = select(func.count(Nomination.nomination_id)).where(
        Nomination.status == "APPROVED"
    )
    
    query_rejected = select(func.count(Nomination.nomination_id)).where(
        Nomination.status == "REJECTED"
    )
    
    # Apply filters
    if election_id:
        query_pending = query_pending.where(Candidate.election_id == election_id)
        query_approved = query_approved.where(Nomination.election_id == election_id)
        query_rejected = query_rejected.where(Nomination.election_id == election_id)
    
    if event_id:
        query_pending = query_pending.join(Election).where(Election.event_id == event_id)
        query_approved = query_approved.join(Election).where(Election.event_id == event_id)
        query_rejected = query_rejected.join(Election).where(Election.event_id == event_id)
    
    pending_count = (await db.execute(query_pending)).scalar() or 0
    approved_count = (await db.execute(query_approved)).scalar() or 0
    rejected_count = (await db.execute(query_rejected)).scalar() or 0
    
    return {
        "pending": pending_count,
        "approved": approved_count,
        "rejected": rejected_count,
        "total_reviewed": approved_count + rejected_count,
        "total_applications": pending_count + approved_count + rejected_count
    }




async def search_candidates_service(db: AsyncSession, query: str):
    result = await db.execute(
        select(Candidate)
        .options(
            joinedload(Candidate.member)
            .joinedload(Member.ward)
            .joinedload(Ward.village)
            .joinedload(Village.mandal)
            .joinedload(Mandal.assembly)
            .joinedload(Assembly.district),
            joinedload(Candidate.election).joinedload(Election.event),
        )
    )

    candidates = result.scalars().all()

    # ---------- BUILD SEARCH DOCUMENTS ----------
    documents = []
    for c in candidates:
        text = f"{c.member.name} {c.election.title if c.election else ''}"
        documents.append(text)

    ranked_indices = rank_by_similarity(query, documents)

    # ---------- RETURN FULL RESPONSE ----------
    return {
        "total": len(ranked_indices),
        "candidates": [
            {
                "candidate_id": candidates[i].candidate_id,
                "name": candidates[i].member.name,
                "mobile": candidates[i].member.mobile,
                "photo_url": candidates[i].member.photo_url,
                "status": candidates[i].status,
                "vote_count": candidates[i].vote_count,

                "election": (
                    candidates[i].election.event.title
                    if candidates[i].election and candidates[i].election.event
                    else None
                ),

                "district": candidates[i].member.ward.village.mandal.assembly.district.district_name,
                "assembly": candidates[i].member.ward.village.mandal.assembly.assembly_name,
                "mandal": candidates[i].member.ward.village.mandal.mandal_name,
                "village": candidates[i].member.ward.village.village_name,
                "ward": candidates[i].member.ward.ward_number,
            }
            for i in ranked_indices
        ],
    }