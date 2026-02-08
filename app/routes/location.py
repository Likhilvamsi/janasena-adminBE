from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.location_service import get_assemblies, get_districts
from app.middleware.auth import get_current_admin

router = APIRouter(
    prefix="/locations",
    tags=["Locations"],
    dependencies=[Depends(get_current_admin)],  # 🔐 JWT protected
)



@router.get("/assemblies")
async def list_assemblies(db: AsyncSession = Depends(get_db)):
    return await get_assemblies(db)



@router.get("/districts")
async def list_districts(db: AsyncSession = Depends(get_db)):
    return await get_districts(db)
