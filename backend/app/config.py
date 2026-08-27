from __future__ import annotations

import os

from dotenv import load_dotenv


# ============================================================
# LOAD ENV
# ============================================================

load_dotenv()


# ============================================================
# JWT CONFIG
# ============================================================

SECRET_KEY = os.getenv("SECRET_KEY")

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256",
)


if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not configured. "
        "Please set SECRET_KEY in your .env file."
    )


# ============================================================
# NEWS API
# ============================================================

NEWS_API_KEY = os.getenv("NEWS_API_KEY")