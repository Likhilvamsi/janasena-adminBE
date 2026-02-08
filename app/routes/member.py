from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_admin
from app.services.member_service import get_members
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.member_service import search_members_service


router = APIRouter(
    prefix="/members",
    tags=["Members"],
    dependencies=[Depends(get_current_admin)],  # 🔐 JWT protected
)


@router.get("/")
async def list_members(
    district_id: int | None = Query(None),
    status: str | None = Query(None, description="active | inactive"),
    voted: str | None = Query(None, description="yes | no"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns:
    - Dashboard counts
    - Filtered members list
    """
    return await get_members(db, district_id, status, voted)





from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.member_service import search_members_service




@router.get("/search/members")
async def search_members(
    q: str = Query(..., description="Search member by name or location"),
    db: AsyncSession = Depends(get_db),
):
    return await search_members_service(db, q)