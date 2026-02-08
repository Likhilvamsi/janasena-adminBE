from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import (
    NotificationType, State, Assembly, Village, Mandal
)


#All Notification Types
async def get_notification_types():
    return [t.value for t in NotificationType]


# All States
async def get_states(db: AsyncSession):
    result = await db.execute(select(State.state_id, State.state_name))
    return [{"id": s.state_id, "name": s.state_name} for s in result.all()]


#  All Assemblies (no district filter)
async def get_all_assemblies(db: AsyncSession):
    result = await db.execute(select(Assembly.assembly_id, Assembly.assembly_name))
    return [{"id": a.assembly_id, "name": a.assembly_name} for a in result.all()]


#  Villages by Assembly (IMPORTANT CHANGE)
async def get_villages_by_assembly(db: AsyncSession, assembly_id: int):
    result = await db.execute(
        select(Village.village_id, Village.village_name)
        .join(Mandal, Village.mandal_id == Mandal.mandal_id)
        .where(Mandal.assembly_id == assembly_id)
    )
    return [{"id": v.village_id, "name": v.village_name} for v in result.all()]



from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.models import ElectionEvent, Election


async def get_all_events_with_elections(db: AsyncSession):
    """
    Returns:
    - event_id
    - event_title
    """

    try:
        result = await db.execute(
            select(ElectionEvent, Election)
            .join(Election, Election.event_id == ElectionEvent.event_id, isouter=True)
            .order_by(ElectionEvent.event_id.desc())
        )

        rows = result.all()
        events_map = {}

        for event, election in rows:

            if event.event_id not in events_map:
                events_map[event.event_id] = {
                    "event_id": event.event_id,
                    "event_title": event.title,
                }

        return {
            "total_events": len(events_map),
            "events": list(events_map.values()),
        }

    #  Database error
    except SQLAlchemyError as e:
        await db.rollback()
        raise Exception("Database error while fetching events")

    #  Any unexpected error
    except Exception as e:
        raise Exception("Something went wrong while fetching events")