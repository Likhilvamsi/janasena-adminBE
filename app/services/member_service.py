from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.models import Member, Ward, Village, Mandal, Assembly, District, Vote
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Member, Ward, Village, Mandal, Assembly
from app.utils.nlp_search import rank_by_similarity


async def get_members(
    db: AsyncSession,
    district_id: int | None = None,
    status: str | None = None,
    voted: str | None = None,
):
    """
    Returns filtered members + dashboard counts
    Includes district & constituency (assembly) info
    """

    # =========================================================
    # BASE QUERY WITH RELATION LOADING (FAST)
    # =========================================================
    query = (
        select(Member)
        .options(
            joinedload(Member.ward)
            .joinedload(Ward.village)
            .joinedload(Village.mandal)
            .joinedload(Mandal.assembly)
            .joinedload(Assembly.district)
        )
    )

    # =========================================================
    # FILTER: DISTRICT
    # =========================================================
    if district_id:
        query = query.join(Member.ward).join(Ward.village).join(Village.mandal)\
                     .join(Mandal.assembly).join(Assembly.district)\
                     .where(District.district_id == district_id)

    # =========================================================
    # FILTER: STATUS
    # =========================================================
    if status == "active":
        query = query.where(Member.is_active.is_(True))
    elif status == "inactive":
        query = query.where(Member.is_active.is_(False))

    # =========================================================
    # FILTER: VOTED
    # =========================================================
    if voted == "yes":
        query = query.where(Member.member_id.in_(select(Vote.member_id)))
    elif voted == "no":
        query = query.where(Member.member_id.not_in(select(Vote.member_id)))

    # =========================================================
    # EXECUTE MEMBER QUERY
    # =========================================================
    result = await db.execute(query)
    members = result.scalars().all()

    # =========================================================
    # COUNTS
    # =========================================================
    base_count_query = select(func.count(Member.member_id))

    if district_id:
        base_count_query = (
            base_count_query
            .join(Member.ward)
            .join(Ward.village)
            .join(Village.mandal)
            .join(Mandal.assembly)
            .join(Assembly.district)
            .where(District.district_id == district_id)
        )

    total_members = (await db.execute(base_count_query)).scalar() or 0

    active_members = (
        await db.execute(base_count_query.where(Member.is_active.is_(True)))
    ).scalar() or 0

    voted_members = (
        await db.execute(
            base_count_query.where(Member.member_id.in_(select(Vote.member_id)))
        )
    ).scalar() or 0

    not_voted_members = total_members - voted_members

    # =========================================================
    # RESPONSE WITH DISTRICT + CONSTITUENCY
    # =========================================================
    return {
        "summary": {
            "total": total_members,
            "active": active_members,
            "voted": voted_members,
            "not_voted": not_voted_members,
        },
        "members": [
            {
                "member_id": m.member_id,
                "name": m.name,
                "mobile": m.mobile,
                "email": m.email,
                "is_active": m.is_active,
                "joined": m.created_at,

                # 🔹 LOCATION INFO
                "district": m.ward.village.mandal.assembly.district.district_name,
                "constituency": m.ward.village.mandal.assembly.assembly_name,  # ← Narsapuram Assembly
                "mandal": m.ward.village.mandal.mandal_name,
                "village": m.ward.village.village_name,
                "ward": m.ward.ward_number,
            }
            for m in members
        ],
    }




async def search_members_service(db: AsyncSession, query: str):
    result = await db.execute(
        select(Member)
        .options(
            joinedload(Member.ward)
            .joinedload(Ward.village)
            .joinedload(Village.mandal)
            .joinedload(Mandal.assembly)
            .joinedload(Assembly.district)
        )
    )

    members = result.scalars().all()

    # ---------- BUILD SEARCH DOCUMENTS ----------
    documents = []
    for m in members:
        text = (
            f"{m.name} "
            f"{m.ward.ward_name} "
            f"{m.ward.village.village_name} "
            f"{m.ward.village.mandal.mandal_name} "
            f"{m.ward.village.mandal.assembly.assembly_name} "
            f"{m.ward.village.mandal.assembly.district.district_name}"
        )
        documents.append(text)

    ranked_indices = rank_by_similarity(query, documents)

    # ---------- RETURN FULL MEMBER DETAILS ----------
    return {
        "total": len(ranked_indices),
        "members": [
            {
                "member_id": members[i].member_id,
                "name": members[i].name,
                "mobile": members[i].mobile,
                "email": members[i].email,
                "is_active": members[i].is_active,
                "joined": members[i].created_at,

                "district": members[i].ward.village.mandal.assembly.district.district_name,
                "constituency": members[i].ward.village.mandal.assembly.assembly_name,
                "mandal": members[i].ward.village.mandal.mandal_name,
                "village": members[i].ward.village.village_name,
                "ward": members[i].ward.ward_number,
            }
            for i in ranked_indices
        ],
    }