from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Admin, Member, Assembly
from app.core.security import verify_password, hash_password, create_access_token
from app.core.otp import generate_otp, verify_otp
from app.core.email import send_email


async def admin_register(db: AsyncSession, data):

    # Check existing email
    result = await db.execute(select(Admin).where(Admin.email == data.email))
    existing = result.scalar_one_or_none()
    if existing:
        return None

    # Validate assembly if admin is ASSEMBLY level
    if data.admin_level == "ASSEMBLY":
        if not data.assembly_id:
            return None

        res = await db.execute(
            select(Assembly).where(Assembly.assembly_id == data.assembly_id)
        )
        if not res.scalar_one_or_none():
            return None

    admin = Admin(
        name=data.name,
        email=data.email,
        mobile=data.mobile,
        password_hash=hash_password(data.password),
        admin_level=data.admin_level,
        assembly_id=data.assembly_id if data.admin_level == "ASSEMBLY" else None,
        is_active=True,
    )

    db.add(admin)
    await db.commit()
    await db.refresh(admin)

    token = create_access_token({"sub": str(admin.admin_id), "role": "admin"})
    return {"access_token": token, "token_type": "bearer"}



async def admin_login(db: AsyncSession, email: str, password: str):
    result = await db.execute(select(Admin).where(Admin.email == email))
    admin = result.scalar_one_or_none()

    if not admin or not verify_password(password, admin.password_hash):
        return None
    if not admin.is_active:
        return None
    token = create_access_token({"admin_id": admin.admin_id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "admin_id": admin.admin_id,
    }


async def send_member_otp(db: AsyncSession, member_number: str):
    result = await db.execute(select(Member).where(Member.member_number == member_number))
    member = result.scalar_one_or_none()

    if not member or not member.is_active or not member.is_eligible_to_vote:
        return None

    otp = generate_otp(member.email)

    send_email(
        to_email=member.email,
        subject="Your OTP - Political Voting System",
        body=f"Your OTP is {otp}. Valid for 5 minutes.",
    )

    return {"message": "OTP sent to registered email"}



async def member_verify_otp(db: AsyncSession, member_number: str, otp: str):
    result = await db.execute(select(Member).where(Member.member_number == member_number))
    member = result.scalar_one_or_none()

    if not member:
        return None

    if not verify_otp(member.email, otp):
        return None

    token = create_access_token({"sub": str(member.member_id), "role": "member"})
    return {"access_token": token, "token_type": "bearer"}
