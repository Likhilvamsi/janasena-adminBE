from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.models import Election, ElectionEvent
from app.services.results import calculate_election_winner

scheduler = AsyncIOScheduler()


async def auto_complete_and_calculate():
    async with async_session_maker() as db:
        now = datetime.utcnow()

        elections = (
        await db.execute(
           select(Election)
           .join(ElectionEvent)
           .where(
                ElectionEvent.voting_end <= now,
                Election.result_calculated == False,
                    )
                )
           ).scalars().all()

        for election in elections:
            await calculate_election_winner(db, election.election_id)


def start_scheduler2():
    scheduler.add_job(auto_complete_and_calculate, "interval", minutes=1)
    scheduler.start()