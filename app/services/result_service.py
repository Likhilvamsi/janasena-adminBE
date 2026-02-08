from sqlalchemy import select, func, and_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.models import (
    Election,
    Candidate,
    Vote,
    Member,
    Notification,
    NotificationType,
    State,
    District,
    Assembly,
    Mandal,
    Village,
    Ward,
    Admin,
)


# =========================================================
# PYDANTIC SCHEMAS
# =========================================================

class AdminResultsFilterParams(BaseModel):
    """Parameters for filtering admin results"""
    page: int = 1
    limit: int = 10
    state_id: Optional[int] = None
    district_id: Optional[int] = None
    assembly_id: Optional[int] = None
    election_level: Optional[str] = None
    status: str = "COMPLETED"


# =========================================================
# PUBLIC SERVICE - LIST PUBLISHED RESULTS
# =========================================================

async def get_results(
    db: AsyncSession,
    page: int,
    limit: int,
    election_level: str | None,
    district_id: int | None,
):
    """Get published election results with pagination and basic filters"""

    base_query = (
        select(
            Election.election_id,
            Election.title,
            Member.name.label("winner_name"),
            Candidate.vote_count,
            func.count(Vote.vote_id).label("total_votes"),
            Election.result_published_at,
        )
        .join(Candidate, Candidate.election_id == Election.election_id)
        .join(Member, Member.member_id == Candidate.member_id)
        .outerjoin(
            Vote,
            and_(
                Vote.election_id == Election.election_id,
                Vote.candidate_id == Candidate.candidate_id,
            ),
        )
        .where(
            Election.status == "COMPLETED",
            Election.result_published == True,
            Candidate.is_winner == True,
        )
        .group_by(Election.election_id, Candidate.candidate_id, Member.member_id)
        .order_by(Election.created_at.desc())
    )

    # Apply filters
    if election_level:
        base_query = base_query.where(Election.election_level == election_level)
    
    if district_id:
        base_query = (
            base_query
            .join(Ward, Ward.ward_id == Election.ward_id)
            .join(Village, Village.village_id == Ward.village_id)
            .join(Mandal, Mandal.mandal_id == Village.mandal_id)
            .join(Assembly, Assembly.assembly_id == Mandal.assembly_id)
            .join(District, District.district_id == Assembly.district_id)
            .where(District.district_id == district_id)
        )

    total = (
        await db.execute(
            select(func.count(Election.election_id.distinct())).select_from(
                select(Election.election_id)
                .join(Candidate, Candidate.election_id == Election.election_id)
                .where(
                    Election.status == "COMPLETED",
                    Election.result_published == True,
                    Candidate.is_winner == True,
                )
            )
        )
    ).scalar() or 0

    rows = (
        await db.execute(base_query.offset((page - 1) * limit).limit(limit))
    ).all()

    items = []

    for election_id, title, winner_name, winner_votes, total_votes, published_at in rows:
        percentage = round((winner_votes / total_votes) * 100, 2) if total_votes else 0

        items.append(
            {
                "election_id": election_id,
                "title": title,
                "winner": winner_name,
                "votes": winner_votes,
                "total_votes": total_votes,
                "percentage": percentage,
                "result_published_at": published_at,
            }
        )

    return {
        "items": items,
        "pagination": {
            "                                                                                                                    page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


# =========================================================
# PUBLIC SERVICE - LOCATION RESULT SUMMARY
# =========================================================

async def get_location_result_summary(
    db: AsyncSession,
    state_id: int | None = None,
    district_id: int | None = None,
    assembly_id: int | None = None,
):
    """
    Returns published election result summaries filtered by
    state / district / assembly.
    """

    query = (
        select(
            Election.election_id,
            Election.title,
            Member.name.label("winner_name"),
            Candidate.vote_count,
            func.count(Vote.vote_id).label("total_votes"),
            Election.result_published_at,
            State.state_name,
            District.district_name,
            Assembly.assembly_name,
        )
        .join(Candidate, Candidate.election_id == Election.election_id)
        .join(Member, Member.member_id == Candidate.member_id)
        .join(Ward, Ward.ward_id == Election.ward_id)
        .join(Village, Village.village_id == Ward.village_id)
        .join(Mandal, Mandal.mandal_id == Village.mandal_id)
        .join(Assembly, Assembly.assembly_id == Mandal.assembly_id)
        .join(District, District.district_id == Assembly.district_id)
        .join(State, State.state_id == District.state_id)
        .outerjoin(
            Vote,
            and_(
                Vote.election_id == Election.election_id,
                Vote.candidate_id == Candidate.candidate_id,
            ),
        )
        .where(
            Election.status == "COMPLETED",
            Election.result_published == True,
            Candidate.is_winner == True,
        )
        .group_by(
            Election.election_id,
            Candidate.candidate_id,
            Member.member_id,
            State.state_id,
            District.district_id,
            Assembly.assembly_id,
        )
        .order_by(Election.result_published_at.desc())
    )

    if state_id:
        query = query.where(State.state_id == state_id)

    if district_id:
        query = query.where(District.district_id == district_id)

    if assembly_id:
        query = query.where(Assembly.assembly_id == assembly_id)

    rows = (await db.execute(query)).all()

    items = []

    for (
        election_id,
        title,
        winner_name,
        winner_votes,
        total_votes,
        published_at,
        state_name,
        district_name,
        assembly_name,
    ) in rows:

        percentage = round((winner_votes / total_votes) * 100, 2) if total_votes else 0

        items.append(
            {
                "election_id": election_id,
                "title": title,
                "winner": winner_name,
                "votes": winner_votes,
                "total_votes": total_votes,
                "percentage": percentage,
                "published_at": published_at,
                "state": state_name,
                "district": district_name,
                "assembly": assembly_name,
            }
        )

    return {
        "count": len(items),
        "items": items,
    }


# =========================================================
# PUBLIC SERVICE - GET SINGLE ELECTION SUMMARY
# =========================================================

async def get_election_result_summary(db: AsyncSession, election_id: int):
    """Get winner, votes, and percentage for one election"""

    total_votes = (
        await db.execute(
            select(func.count(Vote.vote_id)).where(Vote.election_id == election_id)
        )
    ).scalar() or 0

    winner = (
        await db.execute(
            select(Candidate, Member)
            .join(Member, Member.member_id == Candidate.member_id)
            .where(
                Candidate.election_id == election_id,
                Candidate.is_winner == True,
            )
        )
    ).first()

    if not winner:
        return {"error": "Winner not calculated yet"}

    candidate, member = winner

    percentage = round((candidate.vote_count / total_votes) * 100, 2) if total_votes else 0

    return {
        "election_id": election_id,
        "winner_candidate_id": candidate.candidate_id,
        "winner_name": member.name,
        "winner_votes": candidate.vote_count,
        "total_votes": total_votes,
        "percentage": percentage,
    }


# =========================================================
# PUBLIC SERVICE - PUBLISH RESULTS
# =========================================================

async def publish_results(db: AsyncSession, data: dict):
    """Publish completed election results"""

    elections = (
        await db.execute(
            select(Election).where(
                Election.status == "COMPLETED",
                Election.result_published == False,
            )
        )
    ).scalars().all()

    if not elections:
        return {"message": "No completed elections to publish", "count": 0}

    count = 0

    for e in elections:
        e.result_published = True
        e.result_published_at = datetime.utcnow()

        notification = Notification(
            admin_id=e.admin_id,
            election_id=e.election_id,
            assembly_id=None,
            type=NotificationType.RESULT,
            title="Election Result Published",
            message="Election results are now live.",
            recipients_count=0,
            email_sent=False,
        )

        db.add(notification)
        count += 1

    await db.commit()

    return {"message": "Results published", "count": count}


# =========================================================
# PUBLIC SERVICE - UNPUBLISH RESULTS
# =========================================================

async def unpublish_results(db: AsyncSession, data: dict):
    """Unpublish election results"""

    elections = (
        await db.execute(select(Election).where(Election.result_published == True))
    ).scalars().all()

    if not elections:
        return {"message": "No published elections", "count": 0}

    election_ids = [e.election_id for e in elections]

    for e in elections:
        e.result_published = False
        e.result_published_at = None

    await db.execute(
        delete(Notification).where(
            Notification.election_id.in_(election_ids),
            Notification.type == NotificationType.RESULT,
        )
    )

    await db.commit()

    return {"message": "Results unpublished", "count": len(elections)}


# =========================================================
# PUBLIC SERVICE - CALCULATE WINNER
# =========================================================

async def calculate_election_winner(db: AsyncSession, election_id: int):
    """Calculate and determine the winner of an election"""

    election = await db.get(Election, election_id)
    if not election:
        return {"error": "Election not found"}

    vote_counts = (
        await db.execute(
            select(Vote.candidate_id, func.count(Vote.vote_id))
            .where(Vote.election_id == election_id)
            .group_by(Vote.candidate_id)
        )
    ).all()

    if not vote_counts:
        return {"error": "No votes found"}

    await db.execute(
        update(Candidate)
        .where(Candidate.election_id == election_id)
        .values(vote_count=0, is_winner=False)
    )

    max_votes = max(count for _, count in vote_counts)
    winners = []

    for candidate_id, count in vote_counts:
        is_winner = count == max_votes

        await db.execute(
            update(Candidate)
            .where(Candidate.candidate_id == candidate_id)
            .values(vote_count=count, is_winner=is_winner)
        )

        if is_winner:
            winners.append(candidate_id)

    election.status = "COMPLETED"

    await db.commit()

    return {
        "message": "Winner calculated",
        "election_id": election_id,
        "winner_candidate_ids": winners,
        "max_votes": max_votes,
    }


# =========================================================
# ADMIN SERVICE - GET ALL RESULTS (WITH FILTERS)
# =========================================================

async def admin_get_all_results(
    db: AsyncSession,
    admin_id: int,
    filters: AdminResultsFilterParams,
):
    query = (
        select(
            Election.election_id,
            Election.title,
            Election.election_level,
            Member.name.label("winner_name"),
            Candidate.vote_count.label("winner_votes"),
            Election.total_votes,
            Election.winner_percentage,   # ⭐ use stored value
            Election.result_published,
            Election.result_published_at,
            Election.created_at,
            State.state_name,
            District.district_name,
            Assembly.assembly_name,
            Mandal.mandal_name,
            Village.village_name,
            Ward.ward_number,
        )
        .join(Candidate, Candidate.election_id == Election.election_id)
        .join(Member, Member.member_id == Candidate.member_id)
        .join(Ward, Ward.ward_id == Election.ward_id)
        .join(Village, Village.village_id == Ward.village_id)
        .join(Mandal, Mandal.mandal_id == Village.mandal_id)
        .join(Assembly, Assembly.assembly_id == Mandal.assembly_id)
        .join(District, District.district_id == Assembly.district_id)
        .join(State, State.state_id == District.state_id)
        .where(
            Election.status == filters.status,
            Election.admin_id == admin_id,
            Candidate.is_winner == True,
        )
        .order_by(Election.created_at.desc())
    )

    if filters.state_id:
        query = query.where(State.state_id == filters.state_id)
    if filters.district_id:
        query = query.where(District.district_id == filters.district_id)
    if filters.assembly_id:
        query = query.where(Assembly.assembly_id == filters.assembly_id)
    if filters.election_level:
        query = query.where(Election.election_level == filters.election_level)

    total = (
        await db.execute(
            select(func.count(Election.election_id)).where(
                Election.status == filters.status,
                Election.admin_id == admin_id,
            )
        )
    ).scalar() or 0

    rows = (await db.execute(query.offset((filters.page - 1) * filters.limit).limit(filters.limit))).all()

    items = []

    for row in rows:
        (
            election_id,
            title,
            election_level,
            winner_name,
            winner_votes,
            total_votes,
            winner_percentage,
            result_published,
            result_published_at,
            created_at,
            state_name,
            district_name,
            assembly_name,
            mandal_name,
            village_name,
            ward_number,
        ) = row

        items.append(
            {
                "election_id": election_id,
                "title": title,
                "election_level": election_level,
                "winner_name": winner_name,
                "winner_votes": winner_votes,
                "total_votes": total_votes,
                "percentage": winner_percentage,  # ⭐ correct
                "state_name": state_name,
                "district_name": district_name,
                "assembly_name": assembly_name,
                "mandal_name": mandal_name,
                "village_name": village_name,
                "ward_number": ward_number,
                "result_published": result_published,
                "result_published_at": result_published_at.isoformat() if result_published_at else None,
                "created_at": created_at.isoformat() if created_at else None,
            }
        )

    return {
        "items": items,
        "pagination": {
            "page": filters.page,
            "limit": filters.limit,
            "total": total,
            "pages": (total + filters.limit - 1) // filters.limit,
        },
    }


# =========================================================
# ADMIN SERVICE - GET RESULTS BY DISTRICT
# =========================================================

async def admin_get_results_by_district(
    db: AsyncSession,
    admin_id: int,
    district_id: int,
    page: int = 1,
    limit: int = 10,
):
    """Get all completed election results for a specific district"""

    query = (
        select(
            Election.election_id,
            Election.title,
            Election.election_level,
            Member.name.label("winner_name"),
            Candidate.vote_count.label("winner_votes"),
            func.count(Vote.vote_id).label("total_votes"),
            Election.result_published,
            Election.result_published_at,
            District.district_name,
            Assembly.assembly_name,
            Mandal.mandal_name,
            Village.village_name,
            Ward.ward_number,
        )
        .join(Candidate, Candidate.election_id == Election.election_id)
        .join(Member, Member.member_id == Candidate.member_id)
        .join(Ward, Ward.ward_id == Election.ward_id)
        .join(Village, Village.village_id == Ward.village_id)
        .join(Mandal, Mandal.mandal_id == Village.mandal_id)
        .join(Assembly, Assembly.assembly_id == Mandal.assembly_id)
        .join(District, District.district_id == Assembly.district_id)
        .outerjoin(
            Vote,
            and_(
                Vote.election_id == Election.election_id,
                Vote.candidate_id == Candidate.candidate_id,
            ),
        )
        .where(
            Election.status == "COMPLETED",
            Election.admin_id == admin_id,
            District.district_id == district_id,
            Candidate.is_winner == True,
        )
        .group_by(
            Election.election_id,
            Candidate.candidate_id,
            Member.member_id,
            District.district_id,
            Assembly.assembly_id,
            Mandal.mandal_id,
            Village.village_id,
            Ward.ward_id,
        )
        .order_by(Election.created_at.desc())
    )

    total = (
        await db.execute(
            select(func.count(Election.election_id.distinct())).select_from(
                select(Election.election_id)
                .join(Ward, Ward.ward_id == Election.ward_id)
                .join(Village, Village.village_id == Ward.village_id)
                .join(Mandal, Mandal.mandal_id == Village.mandal_id)
                .join(Assembly, Assembly.assembly_id == Mandal.assembly_id)
                .join(District, District.district_id == Assembly.district_id)
                .where(
                    Election.status == "COMPLETED",
                    Election.admin_id == admin_id,
                    District.district_id == district_id,
                )
            )
        )
    ).scalar() or 0

    rows = (
        await db.execute(query.offset((page - 1) * limit).limit(limit))
    ).all()

    items = []
    for row in rows:
        (
            election_id,
            title,
            election_level,
            winner_name,
            winner_votes,
            total_votes,
            result_published,
            result_published_at,
            district_name,
            assembly_name,
            mandal_name,
            village_name,
            ward_number,
        ) = row

        percentage = round((winner_votes / total_votes) * 100, 2) if total_votes else 0

        items.append(
            {
                "election_id": election_id,
                "title": title,
                "election_level": election_level,
                "winner_name": winner_name,
                "winner_votes": winner_votes,
                "total_votes": total_votes,
                "percentage": percentage,
                "district_name": district_name,
                "assembly_name": assembly_name,
                "mandal_name": mandal_name,
                "village_name": village_name,
                "ward_number": ward_number,
                "result_published": result_published,
                "result_published_at": result_published_at.isoformat() if result_published_at else None,
            }
        )

    return {
        "district_id": district_id,
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


# =========================================================
# ADMIN SERVICE - GET RESULTS BY ASSEMBLY
# =========================================================

async def admin_get_results_by_assembly(
    db: AsyncSession,
    admin_id: int,
    assembly_id: int,
    page: int = 1,
    limit: int = 10,
):
    """Get all completed election results for a specific assembly"""

    query = (
        select(
            Election.election_id,
            Election.title,
            Election.election_level,
            Member.name.label("winner_name"),
            Candidate.vote_count.label("winner_votes"),
            func.count(Vote.vote_id).label("total_votes"),
            Election.result_published,
            Election.result_published_at,
            District.district_name,
            Assembly.assembly_name,
            Mandal.mandal_name,
            Village.village_name,
            Ward.ward_number,
        )
        .join(Candidate, Candidate.election_id == Election.election_id)
        .join(Member, Member.member_id == Candidate.member_id)
        .join(Ward, Ward.ward_id == Election.ward_id)
        .join(Village, Village.village_id == Ward.village_id)
        .join(Mandal, Mandal.mandal_id == Village.mandal_id)
        .join(Assembly, Assembly.assembly_id == Mandal.assembly_id)
        .join(District, District.district_id == Assembly.district_id)
        .outerjoin(
            Vote,
            and_(
                Vote.election_id == Election.election_id,
                Vote.candidate_id == Candidate.candidate_id,
            ),
        )
        .where(
            Election.status == "COMPLETED",
            Election.admin_id == admin_id,
            Assembly.assembly_id == assembly_id,
            Candidate.is_winner == True,
        )
        .group_by(
            Election.election_id,
            Candidate.candidate_id,
            Member.member_id,
            District.district_id,
            Assembly.assembly_id,
            Mandal.mandal_id,
            Village.village_id,
            Ward.ward_id,
        )
        .order_by(Election.created_at.desc())
    )

    total = (
        await db.execute(
            select(func.count(Election.election_id.distinct())).select_from(
                select(Election.election_id)
                .join(Ward, Ward.ward_id == Election.ward_id)
                .join(Village, Village.village_id == Ward.village_id)
                .join(Mandal, Mandal.mandal_id == Village.mandal_id)
                .join(Assembly, Assembly.assembly_id == Mandal.assembly_id)
                .where(
                    Election.status == "COMPLETED",
                    Election.admin_id == admin_id,
                    Assembly.assembly_id == assembly_id,
                )
            )
        )
    ).scalar() or 0

    rows = (
        await db.execute(query.offset((page - 1) * limit).limit(limit))
    ).all()

    items = []
    for row in rows:
        (
            election_id,
            title,
            election_level,
            winner_name,
            winner_votes,
            total_votes,
            result_published,
            result_published_at,
            district_name,
            assembly_name,
            mandal_name,
            village_name,
            ward_number,
        ) = row

        percentage = round((winner_votes / total_votes) * 100, 2) if total_votes else 0

        items.append(
            {
                "election_id": election_id,
                "title": title,
                "election_level": election_level,
                "winner_name": winner_name,
                "winner_votes": winner_votes,
                "total_votes": total_votes,
                "percentage": percentage,
                "district_name": district_name,
                "assembly_name": assembly_name,
                "mandal_name": mandal_name,
                "village_name": village_name,
                "ward_number": ward_number,
                "result_published": result_published,
                "result_published_at": result_published_at.isoformat() if result_published_at else None,
            }
        )

    return {
        "assembly_id": assembly_id,
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
    }


# =========================================================
# ADMIN SERVICE - PUBLISH SINGLE RESULT
# =========================================================

async def admin_publish_election_result(
    db: AsyncSession,
    admin_id: int,
    election_id: int,
):
    """Admin publishes a specific completed election result"""

    election = await db.get(Election, election_id)

    if not election:
        return {"error": "Election not found", "status": 404}

    if election.admin_id != admin_id:
        return {"error": "Unauthorized: You can only publish your own elections", "status": 403}

    if election.status != "COMPLETED":
        return {
            "error": f"Election is {election.status}. Only COMPLETED elections can be published.",
            "status": 400,
        }

    if election.result_published:
        return {"error": "Election result is already published", "status": 400}

    election.result_published = True
    election.result_published_at = datetime.utcnow()

    notification = Notification(
        admin_id=election.admin_id,
        election_id=election.election_id,
        assembly_id=None,
        type=NotificationType.RESULT,
        title="Election Result Published",
        message=f"Results for '{election.title}' are now live.",
        recipients_count=0,
        email_sent=False,
    )

    db.add(notification)
    await db.commit()

    return {
        "message": "Election result published successfully",
        "election_id": election_id,
        "published_at": election.result_published_at.isoformat(),
        "status": 200,
    }


# =========================================================
# ADMIN SERVICE - UNPUBLISH SINGLE RESULT
# =========================================================

async def admin_unpublish_election_result(
    db: AsyncSession,
    admin_id: int,
    election_id: int,
):
    """Admin unpublishes a published election result"""

    election = await db.get(Election, election_id)

    if not election:
        return {"error": "Election not found", "status": 404}

    if election.admin_id != admin_id:
        return {"error": "Unauthorized: You can only unpublish your own elections", "status": 403}

    if not election.result_published:
        return {"error": "Election result is not published", "status": 400}

    election.result_published = False
    election.result_published_at = None

    await db.execute(
        delete(Notification).where(
            Notification.election_id == election_id,
            Notification.type == NotificationType.RESULT,
        )
    )

    await db.commit()

    return {
        "message": "Election result unpublished successfully",
        "election_id": election_id,
        "status": 200,
    }


# =========================================================
# ADMIN SERVICE - BULK PUBLISH
# =========================================================

async def admin_bulk_publish_results(
    db: AsyncSession,
    admin_id: int,
    election_ids: list[int],
):
    """Admin publishes multiple election results at once"""

    elections = (
        await db.execute(
            select(Election).where(
                Election.election_id.in_(election_ids),
                Election.admin_id == admin_id,
                Election.status == "COMPLETED",
                Election.result_published == False,
            )
        )
    ).scalars().all()

    if not elections:
        return {"message": "No eligible elections to publish", "count": 0, "status": 200}

    count = 0
    now = datetime.utcnow()

    for election in elections:
        election.result_published = True
        election.result_published_at = now

        notification = Notification(
            admin_id=election.admin_id,
            election_id=election.election_id,
            assembly_id=None,
            type=NotificationType.RESULT,
            title="Election Result Published",
            message=f"Results for '{election.title}' are now live.",
            recipients_count=0,
            email_sent=False,
        )

        db.add(notification)
        count += 1

    await db.commit()

    return {
        "message": "Results published successfully",
        "count": count,
        "published_ids": [e.election_id for e in elections],
        "timestamp": now.isoformat(),
        "status": 200,
    }


# =========================================================
# ADMIN SERVICE - GET UNPUBLISHED COUNT
# =========================================================

async def admin_get_unpublished_count(
    db: AsyncSession,
    admin_id: int,
):
    """Get count of completed but unpublished election results"""

    count = (
        await db.execute(
            select(func.count(Election.election_id)).where(
                Election.admin_id == admin_id,
                Election.status == "COMPLETED",
                Election.result_published == False,
            )
        )
    ).scalar() or 0

    return {
        "unpublished_count": count,
        "admin_id": admin_id,
    }


# =========================================================
# ADMIN SERVICE - GET RESULTS SUMMARY BY LOCATION
# =========================================================

async def admin_get_results_summary_by_location(
    db: AsyncSession,
    admin_id: int,
):
    """Get summary statistics of results grouped by location"""

    total_completed = (
        await db.execute(
            select(func.count(Election.election_id)).where(
                Election.admin_id == admin_id,
                Election.status == "COMPLETED",
            )
        )
    ).scalar() or 0

    total_published = (
        await db.execute(
            select(func.count(Election.election_id)).where(
                Election.admin_id == admin_id,
                Election.status == "COMPLETED",
                Election.result_published == True,
            )
        )
    ).scalar() or 0

    by_state = (
        await db.execute(
            select(
                State.state_id,
                State.state_name,
                func.count(Election.election_id).label("count"),
            )
            .join(District, District.state_id == State.state_id)
            .join(Assembly, Assembly.district_id == District.district_id)
            .join(Mandal, Mandal.assembly_id == Assembly.assembly_id)
            .join(Village, Village.mandal_id == Mandal.mandal_id)
            .join(Ward, Ward.village_id == Village.village_id)
            .join(Election, Election.ward_id == Ward.ward_id)
            .where(
                Election.admin_id == admin_id,
                Election.status == "COMPLETED",
            )
            .group_by(State.state_id, State.state_name)
        )
    ).all()

    by_district = (
        await db.execute(
            select(
                District.district_id,
                District.district_name,
                func.count(Election.election_id).label("count"),
            )
            .join(Assembly, Assembly.district_id == District.district_id)
            .join(Mandal, Mandal.assembly_id == Assembly.assembly_id)
            .join(Village, Village.mandal_id == Mandal.mandal_id)
            .join(Ward, Ward.village_id == Village.village_id)
            .join(Election, Election.ward_id == Ward.ward_id)
            .where(
                Election.admin_id == admin_id,
                Election.status == "COMPLETED",
            )
            .group_by(District.district_id, District.district_name)
        )
    ).all()

    by_assembly = (
        await db.execute(
            select(
                Assembly.assembly_id,
                Assembly.assembly_name,
                func.count(Election.election_id).label("count"),
            )
            .join(Mandal, Mandal.assembly_id == Assembly.assembly_id)
            .join(Village, Village.mandal_id == Mandal.mandal_id)
            .join(Ward, Ward.village_id == Village.village_id)
            .join(Election, Election.ward_id == Ward.ward_id)
            .where(
                Election.admin_id == admin_id,
                Election.status == "COMPLETED",
            )
            .group_by(Assembly.assembly_id, Assembly.assembly_name)
        )
    ).all()

    return {
        "summary": {
            "total_completed": total_completed,
            "total_published": total_published,
            "pending_publish": total_completed - total_published,
        },
        "by_state": [
            {"state_id": state_id, "state_name": state_name, "count": count}
            for state_id, state_name, count in by_state
        ],
        "by_district": [
            {"district_id": district_id, "district_name": district_name, "count": count}
            for district_id, district_name, count in by_district
        ],
        "by_assembly": [
            {"assembly_id": assembly_id, "assembly_name": assembly_name, "count": count}
            for assembly_id, assembly_name, count in by_assembly
        ],
    }