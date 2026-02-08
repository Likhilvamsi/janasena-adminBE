# app/schemas/notification_schema.py

from pydantic import BaseModel
from app.models.models import NotificationType


class NotificationCreate(BaseModel):
    assembly_id: int
    type: NotificationType
    title: str
    message: str