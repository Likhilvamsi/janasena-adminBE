from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import Config

# ================= PASSWORD HASHING =================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash plain password"""
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify plain password against hash"""
    return pwd_context.verify(password, hashed)


# ================= JWT TOKEN =================
def create_access_token(data: Dict[str, Any]) -> str:
    """
    Create JWT access token
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=int(Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        Config.SECRET_KEY,
        algorithm=Config.ALGORITHM,
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode JWT token safely
    Returns payload if valid, otherwise None
    """
    try:
        payload = jwt.decode(
            token,
            Config.SECRET_KEY,
            algorithms=[Config.ALGORITHM],
        )
        return payload
    except JWTError:
        return None
