from __future__ import annotations

import logging
import os
from datetime import date, datetime, timezone

import razorpay
from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.news_payment import NewsDailyPayment


load_dotenv()

logger = logging.getLogger("app.news_payment")


# ============================================================
# CONFIG
# ============================================================

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

NEWS_DAILY_PRICE = 100  # ₹1 = 100 paise


# ============================================================
# RAZORPAY CLIENT
# ============================================================

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(
        auth=(
            RAZORPAY_KEY_ID,
            RAZORPAY_KEY_SECRET,
        )
    )
else:
    razorpay_client = None


# ============================================================
# CLIENT
# ============================================================

def _get_client():
    if razorpay_client is None:
        raise HTTPException(
            status_code=500,
            detail="Razorpay is not configured.",
        )

    return razorpay_client


# ============================================================
# CREATE ORDER
# ============================================================

def create_news_order(
    db: Session,
    user_id: int,
):
    """
    Create or reuse today's ₹1 current-affairs order.

    One NewsDailyPayment row is maintained per user/day.
    """

    client = _get_client()

    today = datetime.now(timezone.utc).date()

    # --------------------------------------------------------
    # FIND TODAY'S PAYMENT
    # --------------------------------------------------------

    existing = (
        db.query(NewsDailyPayment)
        .filter(
            NewsDailyPayment.user_id == user_id,
            NewsDailyPayment.payment_date == today,
        )
        .first()
    )

    # --------------------------------------------------------
    # ALREADY PAID
    # --------------------------------------------------------

    if existing and existing.status in {
        "paid",
        "verified",
    }:
        return {
            "status": "success",
            "message": "Today's news access is already active.",
            "has_access": True,
            "order_id": existing.order_id,
            "amount": existing.amount,
            "currency": existing.currency,
            "key_id": RAZORPAY_KEY_ID,
        }

    # --------------------------------------------------------
    # CREATE RAZORPAY ORDER
    # --------------------------------------------------------

    try:
        order = client.order.create(
            {
                "amount": NEWS_DAILY_PRICE,
                "currency": "INR",
                "receipt": (
                    f"news_{user_id}_"
                    f"{today.strftime('%Y%m%d')}"
                ),
                "notes": {
                    "user_id": str(user_id),
                    "feature": "daily_current_affairs",
                    "payment_date": today.isoformat(),
                },
            }
        )

    except Exception as exc:
        logger.exception(
            "Failed to create Razorpay order"
        )

        raise HTTPException(
            status_code=502,
            detail=f"Unable to create Razorpay order: {exc}",
        )

    order_id = order.get("id")

    if not order_id:
        logger.error(
            "Razorpay returned invalid order: %s",
            order,
        )

        raise HTTPException(
            status_code=502,
            detail="Invalid Razorpay order response.",
        )

    # --------------------------------------------------------
    # UPDATE EXISTING PENDING RECORD
    # --------------------------------------------------------

    if existing:

        existing.order_id = order_id
        existing.payment_id = None
        existing.signature = None
        existing.amount = NEWS_DAILY_PRICE
        existing.currency = "INR"
        existing.status = "created"
        existing.verified_at = None

        db.commit()
        db.refresh(existing)

        return {
            "status": "success",
            "message": "Razorpay order created.",
            "order_id": order_id,
            "amount": NEWS_DAILY_PRICE,
            "currency": "INR",
            "key_id": RAZORPAY_KEY_ID,
            "has_access": False,
        }

    # --------------------------------------------------------
    # CREATE NEW PAYMENT RECORD
    # --------------------------------------------------------

    payment = NewsDailyPayment(
        user_id=user_id,
        order_id=order_id,
        payment_id=None,
        signature=None,
        amount=NEWS_DAILY_PRICE,
        currency="INR",
        payment_date=today,
        status="created",
        verified_at=None,
    )

    db.add(payment)

    try:
        db.commit()
        db.refresh(payment)

    except IntegrityError:

        db.rollback()

        # Another request may have created today's record.
        existing = (
            db.query(NewsDailyPayment)
            .filter(
                NewsDailyPayment.user_id == user_id,
                NewsDailyPayment.payment_date == today,
            )
            .first()
        )

        if existing:

            if existing.status in {
                "paid",
                "verified",
            }:
                return {
                    "status": "success",
                    "message": "Today's news access is already active.",
                    "has_access": True,
                    "order_id": existing.order_id,
                    "amount": existing.amount,
                    "currency": existing.currency,
                    "key_id": RAZORPAY_KEY_ID,
                }

            return {
                "status": "success",
                "message": "Razorpay order already exists.",
                "order_id": existing.order_id,
                "amount": existing.amount,
                "currency": existing.currency,
                "key_id": RAZORPAY_KEY_ID,
                "has_access": False,
            }

        raise

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "status": "success",
        "message": "Razorpay order created.",
        "order_id": order_id,
        "amount": NEWS_DAILY_PRICE,
        "currency": "INR",
        "key_id": RAZORPAY_KEY_ID,
        "has_access": False,
    }


# ============================================================
# VERIFY PAYMENT
# ============================================================

def verify_news_payment(
    db: Session,
    user_id: int,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> dict:

    client = _get_client()

    payment = (
        db.query(NewsDailyPayment)
        .filter(
            NewsDailyPayment.user_id == user_id,
            NewsDailyPayment.order_id == razorpay_order_id,
        )
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="News payment order not found.",
        )

    # --------------------------------------------------------
    # ALREADY PAID
    # --------------------------------------------------------

    if payment.status in {
        "paid",
        "verified",
    }:
        return {
            "status": "success",
            "message": "News access is already active.",
            "access_date": payment.payment_date.isoformat(),
        }

    # --------------------------------------------------------
    # VERIFY SIGNATURE
    # --------------------------------------------------------

    try:

        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )

    except Exception:

        payment.status = "failed"

        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay payment signature.",
        )

    # --------------------------------------------------------
    # MARK PAID
    # --------------------------------------------------------

    payment.payment_id = razorpay_payment_id
    payment.signature = razorpay_signature
    payment.status = "paid"
    payment.verified_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "status": "success",
        "message": "News access activated for today.",
        "access_date": payment.payment_date.isoformat(),
    }


# ============================================================
# CHECK ACCESS
# ============================================================

def has_news_access_today(
    db: Session,
    user_id: int,
) -> bool:

    today = date.today()

    payment = (
        db.query(NewsDailyPayment)
        .filter(
            NewsDailyPayment.user_id == user_id,
            NewsDailyPayment.payment_date == today,
            NewsDailyPayment.status.in_(
                ["paid", "verified"]
            ),
        )
        .first()
    )

    return payment is not None


# ============================================================
# REQUIRE ACCESS
# ============================================================

def require_news_access(
    db: Session,
    user_id: int,
) -> bool:

    if has_news_access_today(
        db=db,
        user_id=user_id,
    ):
        return True

    raise HTTPException(
        status_code=402,
        detail={
            "code": "NEWS_PAYMENT_REQUIRED",
            "message": "Today's News access requires ₹1 payment.",
            "amount": 1,
            "currency": "INR",
            "payment_endpoint": "/news/payment/create-order",
        },
    )