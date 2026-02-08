from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import pytz
import asyncio

from app.models.models import (
    ElectionEvent, Election,
    Ward, Village, Mandal, Assembly,
    Member, Notification, NotificationType
)
from app.core.email import send_email

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.models.models import Nomination, Candidate
IST = pytz.timezone("Asia/Kolkata")



async def create_nomination_notification(
    db: AsyncSession,
    event_id: int,
    admin_id: int,
):
    """
    Send professional Telugu nomination notification
    personalized with member name & ward.
    """

    # 1️⃣ Get event
    event = await db.get(ElectionEvent, event_id)
    if not event:
        raise ValueError("Election event not found")

    assembly_id = event.assembly_id

    # 2️⃣ Get eligible members with ward name
    result = await db.execute(
        select(Member, Ward.ward_name)
        .join(Ward, Ward.ward_id == Member.ward_id)
        .join(Village, Village.village_id == Ward.village_id)
        .join(Mandal, Mandal.mandal_id == Village.mandal_id)
        .where(
            Mandal.assembly_id == assembly_id,
            Member.is_active.is_(True),
            Member.is_eligible_to_vote.is_(True),
        )
    )

    rows = result.all()
    recipients_count = len(rows)

    # 3️⃣ Format dates in readable IST
    def fmt(dt):
        if not dt:
            return "-"
        return dt.astimezone(IST).strftime("%d %B %Y, %I:%M %p")

    # 4️⃣ Save notification (template message only)
    notification = Notification(
        admin_id=admin_id,
        assembly_id=assembly_id,
        type=NotificationType.NOMINATION,
        title=f"నామినేషన్లు ప్రారంభం – {event.title}",
        message="Nomination notification sent",
        recipients_count=recipients_count,
    )

    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    # 5️⃣ Safe email sender
    async def safe_send(email, subject, body):
        try:
            await send_email(email, subject, body)
            return True
        except Exception:
            return False

    # 6️⃣ Prepare & send personalized emails
    tasks = []

    for member, ward_name in rows:

        subject = f"నామినేషన్లు ప్రారంభం – {event.title}"

        body = f"""
ప్రియమైన శ్రీ/శ్రీమతి {member.name} గారికి,

మీరు {ward_name} వార్డు సభ్యుడిగా నమోదయ్యారు.

"{event.title}" ఎన్నికలకు సంబంధించిన నామినేషన్లు అధికారికంగా ప్రారంభమయ్యాయి.

📅 నామినేషన్ ప్రారంభ తేదీ: {fmt(event.nomination_start)}
📅 నామినేషన్ చివరి తేదీ: {fmt(event.nomination_end)}

మీరు అభ్యర్థిగా పోటీ చేయాలని ఆసక్తి ఉంటే,
దయచేసి పై తేదీలలోపు మీ నామినేషన్‌ను సమర్పించండి.

ఈ సమాచారం మీకు సులభంగా అర్థమయ్యే విధంగా పంపించబడింది.
ఏమైనా సందేహాలు ఉంటే స్థానిక ఎన్నికల నిర్వాహకులను సంప్రదించండి.

ధన్యవాదాలు,
ఎన్నికల నిర్వహణ బృందం
"""

        tasks.append(safe_send(member.email, subject, body))

    results = await asyncio.gather(*tasks)
    success_count = sum(results)

    # 7️⃣ Mark email sent
    notification.email_sent = True
    notification.email_sent_at = datetime.now(IST).replace(tzinfo=None)

    await db.commit()

    # 8️⃣ Response
    return {
        "message": "నామినేషన్ నోటిఫికేషన్ విజయవంతంగా పంపబడింది",
        "total_recipients": recipients_count,
        "emails_sent_successfully": success_count,
        "event_id": event_id,
        "notification_id": notification.notification_id,
    }


from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.models import Nomination, Member, Election


async def get_all_nominations(db: AsyncSession):
    # -------------------------------
    # Total count
    # -------------------------------
    total_result = await db.execute(select(func.count(Nomination.nomination_id)))
    total = total_result.scalar_one()

    # -------------------------------
    # Fetch nominations with joins
    # -------------------------------
    result = await db.execute(
        select(Nomination)
        .options(
            joinedload(Nomination.member),
            joinedload(Nomination.election),
        )
        .order_by(Nomination.applied_at.desc())
    )

    nominations = result.scalars().all()

    # -------------------------------
    # Response formatting
    # -------------------------------
    return {
        "total": total,
        "nominations": [
            {
                "nomination_id": n.nomination_id,
                "candidate_id": n.candidate_id,

                # Member details
                "member_name": n.member.name if n.member else None,
                "member_id": n.member_id,
                "mobile": n.member.mobile if n.member else None,
                "photo_url": n.member.photo_url if n.member else None,

                # Nomination fields
                "profile_photo_url": n.profile_photo_url,
                "bio": n.bio,
                "status": n.status,
                "applied_at": n.applied_at,
                "reviewed_at": n.reviewed_at,
                "reviewed_by": n.reviewed_by,
                "rejection_reason": n.rejection_reason,
                "approval_notes": n.approval_notes,

                # Election details
                "election": {
                    "election_id": n.election.election_id,
                    "title": n.election.title,
                    "status": n.election.status,
                } if n.election else None,
            }
            for n in nominations
        ],
    }
# ==============================
# Approve nomination
# ==============================
async def approve_nomination(db: AsyncSession, nomination_id: int, admin_id: int):
    result = await db.execute(
        select(Nomination).where(Nomination.nomination_id == nomination_id)
    )
    nomination = result.scalar_one_or_none()

    if not nomination:
        return {"error": "Nomination not found"}

    if nomination.status != "PENDING":
        return {"error": "Already reviewed"}

    # create candidate
    candidate = Candidate(
        election_id=nomination.election_id,
        member_id=nomination.member_id,
        status="APPROVED",
    )

    db.add(candidate)
    await db.flush()  # get candidate_id

    # update nomination
    nomination.status = "APPROVED"
    nomination.candidate_id = candidate.candidate_id
    nomination.reviewed_by = admin_id
    nomination.reviewed_at = datetime.now(timezone.utc)

    await db.commit()

    return {"message": "Nomination approved", "candidate_id": candidate.candidate_id}


# ==============================
# Reject nomination
# ==============================
async def reject_nomination(
    db: AsyncSession,
    nomination_id: int,
    admin_id: int,
    reason: str,
):
    result = await db.execute(
        select(Nomination).where(Nomination.nomination_id == nomination_id)
    )
    nomination = result.scalar_one_or_none()

    if not nomination:
        return {"error": "Nomination not found"}

    if nomination.status != "PENDING":
        return {"error": "Already reviewed"}

    nomination.status = "REJECTED"
    nomination.rejection_reason = reason
    nomination.reviewed_by = admin_id
    nomination.reviewed_at = datetime.now(timezone.utc)

    await db.commit()

    return {"message": "Nomination rejected"}