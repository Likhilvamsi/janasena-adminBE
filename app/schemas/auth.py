from pydantic import BaseModel, EmailStr, Field
from typing import Optional


# =========================================================
# COMMON TOKEN RESPONSE
# =========================================================

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_id: int | None = None

# =========================================================
# ADMIN REGISTER
# =========================================================

class AdminRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    mobile: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=6)

    # APP or ASSEMBLY
    admin_level: str = Field(..., pattern="^(APP|ASSEMBLY)$")

    # Required only for ASSEMBLY admin
    assembly_id: Optional[int] = None


class AdminRegisterResponse(TokenResponse):
    pass


# =========================================================
# ADMIN LOGIN
# =========================================================

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminLoginResponse(TokenResponse):
    pass


# =========================================================
# MEMBER SEND OTP
# =========================================================

class MemberSendOTPRequest(BaseModel):
    member_number: str = Field(..., min_length=3, max_length=50)


class MemberSendOTPResponse(BaseModel):
    message: str




class MemberVerifyOTPRequest(BaseModel):
    member_number: str
    otp: str = Field(..., min_length=4, max_length=6)


class MemberVerifyOTPResponse(TokenResponse):
    pass
