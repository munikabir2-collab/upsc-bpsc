
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.writing_subscription import WritingSubscription
from app.schemas import SignupRequest, LoginRequest
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# ============================================================================
# SIGNUP
# ============================================================================

@router.post("/signup")
def signup(
    data: SignupRequest,
    db: Session = Depends(get_db),
):
    # ------------------------------------------------------------------------
    # CHECK EXISTING EMAIL
    # ------------------------------------------------------------------------

    existing_user = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    # ------------------------------------------------------------------------
    # CREATE USER
    # ------------------------------------------------------------------------

    new_user = User(
        name=data.name,
        email=data.email,
        password=hash_password(data.password),
    )

    db.add(new_user)

    # Get generated user.id before creating the subscription
    db.flush()

    # ------------------------------------------------------------------------
    # CREATE 1-DAY FREE WRITING TRIAL
    # ------------------------------------------------------------------------

    now = datetime.now(timezone.utc)

    free_trial = WritingSubscription(
        user_id=new_user.id,

        plan="free_trial",

        amount=0,

        duration_days=1,

        answer_limit=10,

        answers_used=0,

        is_active=True,

        starts_at=now,

        expires_at=now + timedelta(days=1),

        razorpay_order_id=None,

        razorpay_payment_id=None,

        payment_status="free",
    )

    db.add(free_trial)

    # ------------------------------------------------------------------------
    # SAVE USER + WRITING TRIAL
    # ------------------------------------------------------------------------

    try:
        db.commit()

        db.refresh(new_user)
        db.refresh(free_trial)

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to create user account.",
        ) from exc

    # ------------------------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------------------------

    return {
        "message": "User registered successfully",

        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
        },

        "writing_trial": {
            "plan": free_trial.plan,
            "amount": free_trial.amount,
            "duration_days": free_trial.duration_days,
            "answer_limit": free_trial.answer_limit,
            "answers_used": free_trial.answers_used,
            "remaining_answers": (
                free_trial.answer_limit
                - free_trial.answers_used
            ),
            "is_active": free_trial.is_active,
            "payment_status": free_trial.payment_status,
            "starts_at": free_trial.starts_at,
            "expires_at": free_trial.expires_at,
        },
    }


# ============================================================================
# LOGIN
# ============================================================================

@router.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    # ------------------------------------------------------------------------
    # FIND USER
    # ------------------------------------------------------------------------

    user = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    # ------------------------------------------------------------------------
    # VERIFY PASSWORD
    # ------------------------------------------------------------------------

    if not verify_password(
        data.password,
        user.password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    # ------------------------------------------------------------------------
    # CREATE JWT
    # ------------------------------------------------------------------------

    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
    })

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
    }

