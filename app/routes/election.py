from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.election import ElectionCreate
from app.services.election_service import create_election, get_elections
from app.middleware.auth import get_current_admin
from app.models.models import Admin
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.results import calculate_election_winner

router = APIRouter(
    prefix="/elections",
    tags=["Elections"],
    dependencies=[Depends(get_current_admin)],  # 🔐 Protect ALL election APIs
)

@router.post("/admin/calculate-result/{election_id}")
async def calculate_result(
    election_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await calculate_election_winner(db, election_id)
# ========= POST =========
@router.post("/")
async def create_new_election(
    data: ElectionCreate,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),  # 🔐 Get real admin from JWT
):
    """
    Create election using logged-in admin
    """
    return await create_election(db, data, admin.admin_id)


# ========= GET =========
@router.get("/")
async def list_elections(
    status: str | None = Query(
        default=None,
        description="DRAFT | SCHEDULED | ACTIVE | COMPLETED",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns:
    - All elections if no status
    - Filtered elections if status provided
    """
    return await get_elections(db, status)
