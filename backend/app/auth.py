from __future__ import annotations

import os

from dotenv import load_dotenv
from passlib.context import CryptContext
from jose import jwt

load_dotenv()


# ============================================================
# JWT CONFIG
# ============================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "change-this-secret-key",
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256",
)


# ============================================================
# PASSWORD HASHING
# ============================================================

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:

    if not plain_password or not hashed_password:
        return False

    try:
        return pwd_context.verify(
            plain_password,
            hashed_password,
        )

    except Exception:
        return False


# ============================================================
# JWT
# ============================================================

def create_access_token(data: dict) -> str:

    payload = data.copy()

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )