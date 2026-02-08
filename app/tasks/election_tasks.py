from datetime import datetime
from sqlalchemy import update, select
from app.models.models import Election, ElectionEvent
import pytz


IST = pytz.timezone("Asia/Kolkata")


async def update_election_status(db):
    """
    Update election status using IST time.
    Election timing comes from ElectionEvent table.
    """

    # Current IST time (naive to match MySQL DATETIME)
    now = datetime.now(IST).replace(tzinfo=None)
    print("STATUS CRON RUN AT:", now)

    # --------------------------------------------------
    # 1️⃣ NOMINATION OPEN
    # --------------------------------------------------
    await db.execute(
        update(Election)
        .where(
            Election.event_id == ElectionEvent.event_id,
            ElectionEvent.nomination_start <= now,
            ElectionEvent.nomination_end > now,
        )
        .values(status="NOMINATION_OPEN")
    )

    # --------------------------------------------------
    # 2️⃣ READY FOR POLL (after nomination end, before voting start)
    # --------------------------------------------------
    await db.execute(
        update(Election)
        .where(
            Election.event_id == ElectionEvent.event_id,
            ElectionEvent.nomination_end <= now,
            ElectionEvent.voting_start > now,
        )
        .values(status="READY_FOR_POLL")
    )

    # --------------------------------------------------
    # 3️⃣ VOTING ACTIVE
    # --------------------------------------------------
    await db.execute(
        update(Election)
        .where(
            Election.event_id == ElectionEvent.event_id,
            ElectionEvent.voting_start <= now,
            ElectionEvent.voting_end > now,
        )
        .values(status="ACTIVE")
    )

    # --------------------------------------------------
    # 4️⃣ COMPLETED
    # --------------------------------------------------
    await db.execute(
        update(Election)
        .where(
            Election.event_id == ElectionEvent.event_id,
            ElectionEvent.voting_end <= now,
        )
        .values(status="COMPLETED")
    )

    await db.commit()