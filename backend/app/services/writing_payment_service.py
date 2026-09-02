
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import razorpay
from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.writing_subscription import (
    WritingSubscription,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger(
    "app.writing_payment_service"
)


# ============================================================
# WRITING PLAN
# ============================================================

WRITING_PLAN = {
    "plan": "weekly",
    "name": "Weekly Writing Plan",

    # Rupees
    "amount": 39,

    # Paise
    "amount_paise": 3900,

    "duration_days": 7,

    "answer_limit": 10,

    "currency": "INR",
}


# ============================================================
# RAZORPAY CONFIG
# ============================================================

RAZORPAY_KEY_ID = (
    os.getenv(
        "RAZORPAY_KEY_ID",
        "",
    )
    .strip()
)

RAZORPAY_KEY_SECRET = (
    os.getenv(
        "RAZORPAY_KEY_SECRET",
        "",
    )
    .strip()
)


# ============================================================
# RAZORPAY CLIENT
# ============================================================

def get_razorpay_client():
    """
    Return configured Razorpay client.
    """

    if not RAZORPAY_KEY_ID:
        logger.error(
            "RAZORPAY_KEY_ID is missing."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "RAZORPAY_KEY_ID is not configured."
            ),
        )

    if not RAZORPAY_KEY_SECRET:
        logger.error(
            "RAZORPAY_KEY_SECRET is missing."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "RAZORPAY_KEY_SECRET is not configured."
            ),
        )

    return razorpay.Client(
        auth=(
            RAZORPAY_KEY_ID,
            RAZORPAY_KEY_SECRET,
        )
    )


# ============================================================
# DATETIME HELPERS
# ============================================================

def _as_utc(
    value: Optional[datetime],
) -> Optional[datetime]:
    """
    Convert datetime to timezone-aware UTC.
    """

    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    )


def _now_utc() -> datetime:
    """
    Current UTC datetime.
    """

    return datetime.now(
        timezone.utc
    )


# ============================================================
# EXPIRE SUBSCRIPTION
# ============================================================

def _expire_if_needed(
    db: Session,
    subscription: Optional[
        WritingSubscription
    ],
):
    """
    Automatically expire subscription
    when expires_at is reached.
    """

    if not subscription:
        return None

    now = _now_utc()

    expires_at = _as_utc(
        subscription.expires_at
    )

    if (
        bool(subscription.is_active)
        and expires_at
        and expires_at <= now
    ):
        subscription.is_active = False

        if subscription.payment_status in {
            "paid",
            "free",
        }:
            subscription.payment_status = (
                "expired"
            )

        try:
            db.commit()
            db.refresh(subscription)

        except Exception:
            db.rollback()

            logger.exception(
                "Failed to expire Writing subscription | "
                "subscription_id=%s",
                subscription.id,
            )

    return subscription


# ============================================================
# GET LATEST SUBSCRIPTION
# ============================================================

def get_latest_subscription(
    db: Session,
    user_id: int,
):
    """
    Return user's latest Writing subscription.
    """

    subscription = (
        db.query(WritingSubscription)
        .filter(
            WritingSubscription.user_id
            == user_id
        )
        .order_by(
            WritingSubscription.id.desc()
        )
        .first()
    )

    return _expire_if_needed(
        db=db,
        subscription=subscription,
    )


# ============================================================
# ACTIVE SUBSCRIPTION CHECK
# ============================================================

def _is_subscription_active(
    subscription: Optional[
        WritingSubscription
    ],
) -> bool:
    """
    Authoritative active subscription check.
    """

    if not subscription:
        return False

    if not bool(
        subscription.is_active
    ):
        return False

    if subscription.payment_status != "paid":
        return False

    expires_at = _as_utc(
        subscription.expires_at
    )

    if not expires_at:
        return False

    return expires_at > _now_utc()


# ============================================================
# SERIALIZE SUBSCRIPTION
# ============================================================

def _serialize_subscription(
    subscription: Optional[
        WritingSubscription
    ],
):
    """
    Convert subscription into frontend JSON.
    """

    if not subscription:
        return {
            "has_subscription": False,

            "is_active": False,

            "plan": None,

            "name": WRITING_PLAN["name"],

            "amount": None,

            "currency": WRITING_PLAN[
                "currency"
            ],

            "duration_days": 0,

            "answer_limit": 0,

            "total_answers": 0,

            "answers_used": 0,

            "used_answers": 0,

            "remaining_answers": 0,

            "starts_at": None,

            "expires_at": None,

            "payment_status": None,

            "razorpay_order_id": None,

            "razorpay_payment_id": None,

            "can_submit": False,

            "can_generate_model_answer": False,
        }

    is_active = _is_subscription_active(
        subscription
    )

    remaining_answers = max(
        0,
        int(
            subscription.answer_limit
            or 0
        )
        - int(
            subscription.answers_used
            or 0
        ),
    )

    return {
        "has_subscription": True,

        "is_active": is_active,

        "plan": subscription.plan,

        "name": WRITING_PLAN["name"],

        "amount": subscription.amount,

        "currency": WRITING_PLAN[
            "currency"
        ],

        "duration_days": (
            subscription.duration_days
        ),

        "answer_limit": (
            subscription.answer_limit
        ),

        "total_answers": (
            subscription.answer_limit
        ),

        "answers_used": (
            subscription.answers_used
        ),

        "used_answers": (
            subscription.answers_used
        ),

        "remaining_answers": (
            remaining_answers
        ),

        "starts_at": (
            subscription.starts_at.isoformat()
            if subscription.starts_at
            else None
        ),

        "expires_at": (
            subscription.expires_at.isoformat()
            if subscription.expires_at
            else None
        ),

        "payment_status": (
            subscription.payment_status
        ),

        "razorpay_order_id": (
            subscription.razorpay_order_id
            if subscription.razorpay_order_id
            else None
        ),

        "razorpay_payment_id": (
            subscription.razorpay_payment_id
            if subscription.razorpay_payment_id
            else None
        ),

        "can_submit": (
            is_active
            and remaining_answers > 0
        ),

        "can_generate_model_answer": (
            is_active
        ),
    }


# ============================================================
# SUBSCRIPTION STATUS
# ============================================================

def get_subscription_status(
    db: Session,
    user_id: int,
):
    """
    Return current Writing subscription.
    """

    subscription = (
        get_latest_subscription(
            db=db,
            user_id=user_id,
        )
    )

    return _serialize_subscription(
        subscription
    )


# ============================================================
# COMPATIBILITY ALIAS
# ============================================================

def get_writing_subscription(
    db: Session,
    user_id: int,
):
    """
    Backward-compatible alias.
    """

    return get_subscription_status(
        db=db,
        user_id=user_id,
    )


# ============================================================
# REQUIRE ACTIVE SUBSCRIPTION
# ============================================================

def require_writing_subscription(
    db: Session,
    user_id: int,
):
    """
    Require active Writing access.

    Allowed:
        free_trial + free
        paid + active
    """

    subscription = (
        get_latest_subscription(
            db=db,
            user_id=user_id,
        )
    )

    if not subscription:
        raise HTTPException(
            status_code=403,
            detail={
                "code": (
                    "WRITING_SUBSCRIPTION_REQUIRED"
                ),

                "message": (
                    "Your free Writing trial has "
                    "ended. Please purchase the "
                    "₹39 Weekly Writing Plan."
                ),

                "plan": WRITING_PLAN,
            },
        )

    payment_status = str(
        subscription.payment_status
        or ""
    ).strip().lower()

    plan = str(
        subscription.plan
        or ""
    ).strip().lower()

    allowed_access = (
        payment_status == "paid"
        or (
            plan == "free_trial"
            and payment_status == "free"
        )
    )

    if not allowed_access:
        raise HTTPException(
            status_code=403,
            detail={
                "code": (
                    "WRITING_PAYMENT_REQUIRED"
                ),

                "message": (
                    "Your Writing access is not "
                    "active. Please purchase the "
                    "₹39 Weekly Writing Plan."
                ),

                "payment_status": (
                    subscription.payment_status
                ),

                "plan": subscription.plan,

                "subscription_plan": (
                    WRITING_PLAN
                ),
            },
        )

    now = _now_utc()

    expires_at = _as_utc(
        subscription.expires_at
    )

    if (
        not bool(
            subscription.is_active
        )
        or not expires_at
        or expires_at <= now
    ):
        subscription.is_active = False

        if payment_status in {
            "paid",
            "free",
        }:
            subscription.payment_status = (
                "expired"
            )

        try:
            db.commit()

        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=403,
            detail={
                "code": (
                    "WRITING_SUBSCRIPTION_EXPIRED"
                ),

                "message": (
                    "Your Writing free trial/"
                    "subscription has expired. "
                    "Please purchase the ₹39 "
                    "Weekly Writing Plan."
                ),

                "plan": WRITING_PLAN,
            },
        )

    return subscription


# ============================================================
# REQUIRE WRITING ACCESS + QUOTA
# ============================================================

def require_writing_access(
    db: Session,
    user_id: int,
):
    """
    Require active Writing subscription
    and at least one remaining answer.
    """

    subscription = (
        require_writing_subscription(
            db=db,
            user_id=user_id,
        )
    )

    answers_used = int(
        subscription.answers_used
        or 0
    )

    answer_limit = int(
        subscription.answer_limit
        or 0
    )

    if answers_used >= answer_limit:
        raise HTTPException(
            status_code=403,
            detail={
                "code": (
                    "WRITING_ANSWERS_EXHAUSTED"
                ),

                "message": (
                    f"You have used all "
                    f"{answer_limit} answer "
                    "submissions. Please "
                    "purchase the ₹39 Weekly "
                    "Writing Plan."
                ),

                "remaining_answers": 0,

                "answer_limit": answer_limit,

                "answers_used": answers_used,
            },
        )

    return subscription


# ============================================================
# MODEL ANSWER ACCESS
# ============================================================

def require_model_answer_access(
    db: Session,
    user_id: int,
):
    """
    Model Answer requires active Writing access.

    Model Answer does NOT consume quota.
    """

    return require_writing_subscription(
        db=db,
        user_id=user_id,
    )


# ============================================================
# CONSUME ONE ANSWER
# ============================================================

def consume_writing_answer(
    db: Session,
    user_id: int,
):
    """
    Consume exactly one answer submission.

    Call this only after successful
    evaluation and database save.
    """

    subscription = (
        require_writing_access(
            db=db,
            user_id=user_id,
        )
    )

    current_used = int(
        subscription.answers_used
        or 0
    )

    answer_limit = int(
        subscription.answer_limit
        or 0
    )

    if current_used >= answer_limit:
        raise HTTPException(
            status_code=403,
            detail={
                "code": (
                    "WRITING_ANSWERS_EXHAUSTED"
                ),

                "message": (
                    "All Writing answer "
                    "submissions have been used."
                ),

                "remaining_answers": 0,
            },
        )

    subscription.answers_used = (
        current_used + 1
    )

    try:
        db.commit()
        db.refresh(subscription)

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Failed to consume Writing answer | "
            "user_id=%s",
            user_id,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to update Writing "
                "answer quota."
            ),
        ) from exc

    return subscription


# ============================================================
# CREATE WRITING RAZORPAY ORDER
# ============================================================

def create_writing_order(
    db: Session,
    user_id: int,
):
    """
    Create ₹39 Razorpay order.
    """

    # Keep DB parameter for API compatibility.
    _ = db

    client = get_razorpay_client()

    timestamp = int(
        _now_utc().timestamp()
    )

    receipt = (
        f"writing_{user_id}_{timestamp}"
    )

    try:
        order = client.order.create(
            {
                "amount": WRITING_PLAN[
                    "amount_paise"
                ],

                "currency": WRITING_PLAN[
                    "currency"
                ],

                "receipt": receipt,

                "notes": {
                    "user_id": str(user_id),

                    "plan": WRITING_PLAN[
                        "plan"
                    ],

                    "product": "writing",

                    "duration_days": str(
                        WRITING_PLAN[
                            "duration_days"
                        ]
                    ),

                    "answer_limit": str(
                        WRITING_PLAN[
                            "answer_limit"
                        ]
                    ),
                },
            }
        )

    except Exception as exc:
        logger.exception(
            "Writing Razorpay order creation failed | "
            "user_id=%s",
            user_id,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to create Razorpay order: "
                f"{str(exc)}"
            ),
        ) from exc

    order_id = order.get("id")

    if not order_id:
        raise HTTPException(
            status_code=502,
            detail="Invalid Razorpay order response.",
        )

    return {
        "success": True,

        "key_id": RAZORPAY_KEY_ID,

        "key_id_present": bool(
            RAZORPAY_KEY_ID
        ),

        "order_id": order_id,

        "amount": order.get(
            "amount",
            WRITING_PLAN["amount_paise"],
        ),

        "currency": order.get(
            "currency",
            WRITING_PLAN["currency"],
        ),

        "plan": WRITING_PLAN[
            "plan"
        ],

        "name": WRITING_PLAN[
            "name"
        ],

        "duration_days": WRITING_PLAN[
            "duration_days"
        ],

        "answer_limit": WRITING_PLAN[
            "answer_limit"
        ],
    }


# ============================================================
# VERIFY WRITING PAYMENT
# ============================================================

def verify_writing_payment(
    db: Session,
    user_id: int,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
):
    """
    Secure Razorpay verification.

    Verification:

        Signature
        ↓
        Order
        ↓
        Amount
        ↓
        Currency
        ↓
        User
        ↓
        Plan
        ↓
        Payment
        ↓
        Captured
        ↓
        Idempotency
        ↓
        Subscription
    """

    razorpay_order_id = str(
        razorpay_order_id or ""
    ).strip()

    razorpay_payment_id = str(
        razorpay_payment_id or ""
    ).strip()

    razorpay_signature = str(
        razorpay_signature or ""
    ).strip()

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not razorpay_order_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "razorpay_order_id is required."
            ),
        )

    if not razorpay_payment_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "razorpay_payment_id is required."
            ),
        )

    if not razorpay_signature:
        raise HTTPException(
            status_code=400,
            detail=(
                "razorpay_signature is required."
            ),
        )

    client = get_razorpay_client()

    # ========================================================
    # VERIFY SIGNATURE
    # ========================================================

    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id":
                    razorpay_order_id,

                "razorpay_payment_id":
                    razorpay_payment_id,

                "razorpay_signature":
                    razorpay_signature,
            }
        )

    except Exception as exc:
        logger.warning(
            "Writing payment signature verification "
            "failed | user=%s order=%s",
            user_id,
            razorpay_order_id,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid Razorpay payment signature."
            ),
        ) from exc

    # ========================================================
    # FETCH ORDER
    # ========================================================

    try:
        order = client.order.fetch(
            razorpay_order_id
        )

        # ----------------------------------------------------
        # AMOUNT
        # ----------------------------------------------------

        order_amount = int(
            order.get("amount", 0)
        )

        if (
            order_amount
            != WRITING_PLAN[
                "amount_paise"
            ]
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid Writing "
                    "subscription amount."
                ),
            )

        # ----------------------------------------------------
        # CURRENCY
        # ----------------------------------------------------

        order_currency = order.get(
            "currency"
        )

        if (
            order_currency
            != WRITING_PLAN[
                "currency"
            ]
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid payment currency.",
            )

        # ----------------------------------------------------
        # NOTES
        # ----------------------------------------------------

        notes = order.get(
            "notes"
        ) or {}

        order_user_id = notes.get(
            "user_id"
        )

        if (
            order_user_id is not None
            and str(order_user_id)
            != str(user_id)
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "This payment order does "
                    "not belong to the current user."
                ),
            )

        order_plan = notes.get(
            "plan"
        )

        if (
            order_plan is not None
            and order_plan
            != WRITING_PLAN[
                "plan"
            ]
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid Writing "
                    "subscription plan."
                ),
            )

        product = notes.get(
            "product"
        )

        if (
            product is not None
            and product != "writing"
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid Writing payment product."
                ),
            )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Unable to verify Writing Razorpay order | "
            "order=%s",
            razorpay_order_id,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to verify Razorpay order: "
                f"{str(exc)}"
            ),
        ) from exc

    # ========================================================
    # FETCH PAYMENT
    # ========================================================

    try:
        payment = client.payment.fetch(
            razorpay_payment_id
        )

        payment_status = (
            payment.get("status")
        )

        payment_order_id = (
            payment.get("order_id")
        )

        payment_amount = int(
            payment.get("amount", 0)
        )

        payment_currency = (
            payment.get("currency")
        )

        # ----------------------------------------------------
        # ORDER RELATION
        # ----------------------------------------------------

        if (
            payment_order_id
            and payment_order_id
            != razorpay_order_id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment does not belong "
                    "to the specified order."
                ),
            )

        # ----------------------------------------------------
        # AMOUNT
        # ----------------------------------------------------

        if (
            payment_amount
            != WRITING_PLAN[
                "amount_paise"
            ]
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid payment amount.",
            )

        # ----------------------------------------------------
        # CURRENCY
        # ----------------------------------------------------

        if (
            payment_currency
            != WRITING_PLAN[
                "currency"
            ]
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid payment currency.",
            )

        # ----------------------------------------------------
        # CAPTURED
        # ----------------------------------------------------

        if payment_status != "captured":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment has not been captured yet."
                ),
            )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Unable to verify Writing Razorpay payment | "
            "payment=%s",
            razorpay_payment_id,
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to verify Razorpay payment: "
                f"{str(exc)}"
            ),
        ) from exc

    # ========================================================
    # PAYMENT ID IDEMPOTENCY
    # ========================================================

    existing = (
        db.query(WritingSubscription)
        .filter(
            WritingSubscription.razorpay_payment_id
            == razorpay_payment_id
        )
        .first()
    )

    if existing:

        if (
            str(existing.user_id)
            != str(user_id)
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "This payment has already "
                    "been associated with another user."
                ),
            )

        return {
            "success": True,

            "message": (
                "Payment already verified."
            ),

            "subscription": (
                get_subscription_status(
                    db=db,
                    user_id=user_id,
                )
            ),
        }

    # ========================================================
    # ORDER ID IDEMPOTENCY
    # ========================================================

    existing_order = (
        db.query(WritingSubscription)
        .filter(
            WritingSubscription.razorpay_order_id
            == razorpay_order_id
        )
        .first()
    )

    if existing_order:

        if (
            str(existing_order.user_id)
            != str(user_id)
        ):
            raise HTTPException(
                status_code=403,
                detail=(
                    "This payment order "
                    "belongs to another user."
                ),
            )

        raise HTTPException(
            status_code=409,
            detail=(
                "This Razorpay order has "
                "already been processed."
            ),
        )

    # ========================================================
    # EXPIRE PREVIOUS ACTIVE SUBSCRIPTIONS
    # ========================================================

    previous_subscriptions = (
        db.query(WritingSubscription)
        .filter(
            WritingSubscription.user_id
            == user_id,

            WritingSubscription.is_active
            == True,
        )
        .all()
    )

    for previous in previous_subscriptions:

        previous.is_active = False

        if previous.payment_status == "paid":
            previous.payment_status = (
                "replaced"
            )

    # ========================================================
    # CREATE SUBSCRIPTION
    # ========================================================

    now = _now_utc()

    expires_at = (
        now
        + timedelta(
            days=WRITING_PLAN[
                "duration_days"
            ]
        )
    )

    subscription = WritingSubscription(
        user_id=user_id,

        plan=WRITING_PLAN[
            "plan"
        ],

        amount=WRITING_PLAN[
            "amount"
        ],

        duration_days=WRITING_PLAN[
            "duration_days"
        ],

        answer_limit=WRITING_PLAN[
            "answer_limit"
        ],

        answers_used=0,

        is_active=True,

        starts_at=now,

        expires_at=expires_at,

        razorpay_order_id=(
            razorpay_order_id
        ),

        razorpay_payment_id=(
            razorpay_payment_id
        ),

        payment_status="paid",
    )

    db.add(subscription)

    # ========================================================
    # SAVE
    # ========================================================

    try:
        db.commit()
        db.refresh(subscription)

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Failed to save Writing subscription | "
            "user=%s order=%s",
            user_id,
            razorpay_order_id,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Payment verified but "
                "subscription could not be saved."
            ),
        ) from exc

    # ========================================================
    # SUCCESS
    # ========================================================

    logger.info(
        "Writing payment verified successfully | "
        "user=%s order=%s payment=%s",
        user_id,
        razorpay_order_id,
        razorpay_payment_id,
    )

    return {
        "success": True,

        "message": (
            "Writing subscription activated."
        ),

        "subscription": (
            get_subscription_status(
                db=db,
                user_id=user_id,
            )
        ),
    }


# ============================================================
# CAN SUBMIT
# ============================================================

def can_submit_writing(
    db: Session,
    user_id: int,
) -> bool:
    """
    Return True if user can submit another answer.
    """

    try:
        require_writing_access(
            db=db,
            user_id=user_id,
        )

        return True

    except HTTPException:
        return False

    except Exception:
        logger.exception(
            "Unable to determine Writing submit "
            "access | user_id=%s",
            user_id,
        )

        return False


# ============================================================
# REMAINING ANSWERS
# ============================================================

def get_remaining_writing_answers(
    db: Session,
    user_id: int,
) -> int:
    """
    Return remaining Writing answer submissions.
    """

    status = get_subscription_status(
        db=db,
        user_id=user_id,
    )

    return int(
        status.get(
            "remaining_answers",
            0,
        )
    )

