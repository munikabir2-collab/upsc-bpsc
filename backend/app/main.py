from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine

# ============================================================
# MODELS
# ============================================================

from app.models import (
    User,
    CurrentAffair,
    MCQ,
)

from app.models.writing_subscription import (
    WritingSubscription,
)

# ============================================================
# ROUTES
# ============================================================

from app.routes.auth_routes import (
    router as auth_router,
)

from app.routes.news_routes import (
    router as news_router,
)

from app.routes.writing_routes import (
    router as writing_router,
)


# ============================================================
# DATABASE
# ============================================================

Base.metadata.create_all(
    bind=engine
)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="UPSC & BPSC Preparation SaaS Backend",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTERS
# ============================================================

app.include_router(
    auth_router
)

app.include_router(
    news_router
)

app.include_router(
    writing_router
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "status": "success",
        "message": (
            "UPSC & BPSC Preparation SaaS Backend"
        ),
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": (
            "UPSC & BPSC Preparation SaaS Backend"
        ),
        "version": "1.0.0",
    }