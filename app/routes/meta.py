from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_admin
from app.models.models import Admin
from app.services import meta_service

router = APIRouter(
    prefix="/meta",
    tags=["Meta"],
    dependencies=[Depends(get_current_admin)]  # 🔐 protect all routes
)


# 🔹 Election Levels
@router.get("/election-levels")
async def get_election_levels():
    return [
        {"code": "DISTRICT", "name": "District"},
        {"code": "ASSEMBLY", "name": "Assembly"},
        {"code": "WARD", "name": "Ward"},
    ]


# 🔹 Notification Types
@router.get("/notification-types")
async def notification_types():
    return {"types": await meta_service.get_notification_types()}


# 🔹 All States
@router.get("/states")
async def states(db: AsyncSession = Depends(get_db)):
    return await meta_service.get_states(db)


# 🔹 All Assemblies
@router.get("/assemblies")
async def assemblies(db: AsyncSession = Depends(get_db)):
    return await meta_service.get_all_assemblies(db)


# 🔹 Villages by Assembly
@router.get("/villages/by-assembly/{assembly_id}")
async def villages_by_assembly(
    assembly_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await meta_service.get_villages_by_assembly(db, assembly_id)



@router.get("/elections/events")
async def fetch_events(db: AsyncSession = Depends(get_db)):
    return await meta_service.get_all_events_with_elections(db)