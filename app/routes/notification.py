from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_admin
from app.services.notification_service import get_notifications , create_notification_for_assembly

from app.schemas.notification import NotificationCreate



from app.models.models import NotificationType


router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("/")
async def list_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all notifications with pagination (20 per page).
    """
    return await get_notifications(db, page=page, limit=20)













@router.post("/create")
async def create_notification(
    data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    return await create_notification_for_assembly(
        db=db,
        admin_id=admin.admin_id,
        assembly_id=data.assembly_id,
        type=data.type,
        title=data.title,
        message=data.message,
    )