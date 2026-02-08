from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_admin

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.candidate_service import search_candidates_service
from app.services.candidate_service import (
    
    get_candidate_details,
    reject_candidate,
    get_nominations,
    
    approve_candidate
)




router = APIRouter(
    prefix="/candidates",
    tags=["Candidates"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("/all")
async def list_nominations(
    status: str | None = Query("ALL", description="ALL | APPROVED | REJECTED"),
    election_id: int | None = Query(None, description="Filter by election"),
    assembly_id: int | None = Query(None, description="Filter by assembly"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """
    View all nomination decisions (approval/rejection history).
    
    Shows:
    - All reviewed candidates
    - Their status (APPROVED or REJECTED)
    - Admin who reviewed
    - Rejection/approval notes
    - Timestamp
    
    Returns:
        - Total nominations
        - Nomination records with details
    
    Authorization: ADMIN only
    """
    try:
        result = await get_nominations(
            db,
            status=status,
            election_id=election_id,
            assembly_id=assembly_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))







@router.get("/search/candidates")
async def search_candidates(
    q: str = Query(..., description="Search candidate by name or election"),
    db: AsyncSession = Depends(get_db),
):
    return await search_candidates_service(db, q)
