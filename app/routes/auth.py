from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.auth_service import (
    admin_register,
    admin_login,
    send_member_otp,
    member_verify_otp,
)

from app.schemas.auth import (
    AdminRegisterRequest,
    AdminLoginRequest,
    MemberSendOTPRequest,
    MemberVerifyOTPRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])



@router.post("/admin/register", response_model=TokenResponse)
async def register_admin(
    data: AdminRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await admin_register(db, data)
    if not result:
        raise HTTPException(status_code=400, detail="Admin already exists")
    return result


@router.post("/admin/login", response_model=TokenResponse)
async def login_admin(
    data: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await admin_login(db, data.email, data.password)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials or inactive admin")

    return result



@router.post("/member/send-otp")
async def member_send_otp(
    data: MemberSendOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await send_member_otp(db, data.member_number)
    if not result:
        raise HTTPException(status_code=404, detail="Member not found or inactive")
    return result


@router.post("/member/verify-otp", response_model=TokenResponse)
async def member_verify(
    data: MemberVerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await member_verify_otp(db, data.member_number, data.otp)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    return result
