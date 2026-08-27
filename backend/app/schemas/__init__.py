# app/schemas/__init__.py

# ============================================================
# AUTH SCHEMAS
# ============================================================

from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
)


# ============================================================
# NEWS SCHEMAS
# ============================================================

from app.schemas.news import (
    NewsArticle,
    NewsSearchResponse,
    NewsListResponse,
    NewsDetailResponse,
    NewsFilterRequest,
    NewsMCQ,
    NewsMCQOption,
    NewsMCQResponse,
    NewsMCQListResponse,
)


# ============================================================
# PUBLIC EXPORTS
# ============================================================

__all__ = [
    # Auth
    "SignupRequest",
    "LoginRequest",

    # News
    "NewsArticle",
    "NewsSearchResponse",
    "NewsListResponse",
    "NewsDetailResponse",
    "NewsFilterRequest",

    # MCQ
    "NewsMCQ",
    "NewsMCQOption",
    "NewsMCQResponse",
    "NewsMCQListResponse",
]