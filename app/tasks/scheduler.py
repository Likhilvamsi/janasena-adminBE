from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.tasks.election_tasks import update_election_status
from app.core.database import async_session_maker


scheduler = AsyncIOScheduler()


async def run_status_update():
    async with async_session_maker() as db:
        await update_election_status(db)


def start_scheduler():
    scheduler.add_job(run_status_update, "interval", minutes=1)
    scheduler.start()
