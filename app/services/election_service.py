from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from datetime import datetime
import pytz

from app.models.models import (
    Election, ElectionEvent, Ward, Village, Mandal, Assembly, District, Member
)

IST = pytz.timezone("Asia/Kolkata")


# =========================================================
# CREATE ELECTION (PURE IST)
# =========================================================
async def create_election(db: AsyncSession, data, admin_id: int):
    """
    Creates:
    1️⃣ Assembly-level ElectionEvent
    2️⃣ Ward-level Elections linked to event

    ✔ Assumes frontend sends IST time
    ✔ Stores IST directly in DB
    ✔ No timezone conversion
    """

    # -------------------------------------------------
    # 1️⃣ Find wards in assembly
    # -------------------------------------------------
    ward_query = (
        select(Ward)
        .join(Village, Ward.village_id == Village.village_id)
        .join(Mandal, Village.mandal_id == Mandal.mandal_id)
        .where(Mandal.assembly_id == data.assembly_id)
    )

    wards = (await db.execute(ward_query)).scalars().all()

    if not wards:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No wards found for this assembly"
        )

    # -------------------------------------------------
    # 2️⃣ KEEP IST AS-IS (NO CONVERSION)
    # -------------------------------------------------
    nomination_start = data.nomination_start.replace(tzinfo=None)
    nomination_end   = data.nomination_end.replace(tzinfo=None)
    voting_start     = data.voting_start.replace(tzinfo=None)
    voting_end       = data.voting_end.replace(tzinfo=None)

    # -------------------------------------------------
    # 3️⃣ VALIDATION (important in production)
    # -------------------------------------------------
    if not (nomination_start < nomination_end < voting_start < voting_end):
        raise HTTPException(
            status_code=400,
            detail="Invalid election timeline order"
        )

    # -------------------------------------------------
    # 4️⃣ Create ElectionEvent
    # -------------------------------------------------
    event = ElectionEvent(
        assembly_id=data.assembly_id,
        title=data.title,
        nomination_start=nomination_start,
        nomination_end=nomination_end,
        voting_start=voting_start,
        voting_end=voting_end,
    )

    db.add(event)
    await db.flush()

    # -------------------------------------------------
    # 5️⃣ Create ward elections
    # -------------------------------------------------
    for ward in wards:
        db.add(Election(
            event_id=event.event_id,
            title=data.title,
            ward_id=ward.ward_id,
            admin_id=admin_id,
            election_level="WARD",
            status="SCHEDULED",
        ))

    await db.commit()

    return {
        "message": "Election event and ward elections created",
        "event_id": event.event_id,
        "total_wards": len(wards),
    }


# =========================================================
# GET ELECTIONS (PURE IST RETURN)
# =========================================================
from sqlalchemy import select, func


from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Election, ElectionEvent, Ward, Village, Mandal, Assembly, District, Member
)


async def get_elections(db: AsyncSession, status: str | None = None):
    """
    Returns election list with:
    - total voters in ward
    - total votes polled
    - NO winner / NO candidate details
    """

    # ⭐ Subquery → total eligible voters per ward
    voters_subq = (
        select(
            Member.ward_id,
            func.count(Member.member_id).label("total_voters")
        )
        .where(Member.is_eligible_to_vote == True)
        .group_by(Member.ward_id)
        .subquery()
    )

    query = (
        select(
            Election,
            ElectionEvent,
            Ward,
            Village,
            Mandal,
            Assembly,
            District,
            voters_subq.c.total_voters,
        )
        .join(ElectionEvent, Election.event_id == ElectionEvent.event_id)
        .join(Ward, Election.ward_id == Ward.ward_id)
        .join(Village, Ward.village_id == Village.village_id)
        .join(Mandal, Village.mandal_id == Mandal.mandal_id)
        .join(Assembly, Mandal.assembly_id == Assembly.assembly_id)
        .join(District, Assembly.district_id == District.district_id)
        .outerjoin(voters_subq, voters_subq.c.ward_id == Ward.ward_id)
        .order_by(Election.created_at.desc())
    )

    if status:
        query = query.where(Election.status == status.upper())

    rows = (await db.execute(query)).all()

    elections = []

    for e, ev, w, v, m, a, d, total_voters in rows:

        elections.append({
            "event_id": ev.event_id,
            "election_id": e.election_id,
            "title": ev.title,
            "status": e.status,

            # 📍 Location
            "district": d.district_name,
            "assembly": a.assembly_name,
            "mandal": m.mandal_name,
            "village": v.village_name,
            "ward": w.ward_name,

            # 🗳️ ONLY TOTAL COUNTS
            "total_voters": total_voters or 0,
            "total_votes_polled": e.total_votes,

            # 🏁 Result flags (optional but useful)
            "result_calculated": e.result_calculated,
            "result_published": e.result_published,

            # ⏰ Schedule
            "nomination_start": ev.nomination_start,
            "nomination_end": ev.nomination_end,
            "voting_start": ev.voting_start,
            "voting_end": ev.voting_end,

            "created_at": e.created_at,
        })

    return elections