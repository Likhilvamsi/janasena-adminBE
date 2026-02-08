import random
from datetime import datetime, timedelta

OTP_STORE = {}  # Replace with Redis in production


def generate_otp(email: str):
    otp = str(random.randint(100000, 999999))
    OTP_STORE[email] = {
        "otp": otp,
        "expires": datetime.utcnow() + timedelta(minutes=5),
    }
    return otp


def verify_otp(email: str, otp: str) -> bool:
    data = OTP_STORE.get(email)
    if not data:
        return False

    if data["otp"] != otp:
        return False

    if datetime.utcnow() > data["expires"]:
        return False

    return True
