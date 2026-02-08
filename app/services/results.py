from sqlalchemy import select, func, update
from app.models.models import Election, Candidate, Vote


async def calculate_election_winner(db, election_id: int):
    election = await db.get(Election, election_id)
    if not election:
        return {"error": "Election not found"}

    # 🔒 prevent duplicate calculation
    if election.result_calculated:
        return {"message": "Result already calculated"}

    vote_counts = (
        await db.execute(
            select(Vote.candidate_id, func.count(Vote.vote_id))
            .where(Vote.election_id == election_id)
            .group_by(Vote.candidate_id)
        )
    ).all()

    if not vote_counts:
        return {"error": "No votes found"}

    # reset candidate results
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

    total_votes = sum(count for _, count in vote_counts)

    # ⭐ store in election table
    election.total_votes = total_votes
    election.status = "COMPLETED"
    election.result_calculated = True
    election.winner_percentage = round((max_votes / total_votes) * 100, 2)

    await db.commit()

    return {
        "message": "Winner calculated successfully",
        "winner_candidate_ids": winners,
        "total_votes": total_votes,
        "winner_percentage": election.winner_percentage,
        "is_tie": len(winners) > 1,
    }