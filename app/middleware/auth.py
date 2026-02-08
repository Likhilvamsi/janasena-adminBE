from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import Admin

security = HTTPBearer()


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    admin_id: int | None = payload.get("admin_id")
    if not admin_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(Admin).where(Admin.admin_id == admin_id))
    admin = result.scalar_one_or_none()

    if not admin or not admin.is_active:
        raise HTTPException(status_code=403, detail="Admin not active")

    return admin
