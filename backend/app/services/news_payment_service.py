
from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta, timezone

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

# ₹1 = 100 paise
NEWS_DAILY_PRICE = 100

NEWS_CURRENCY = "INR"


# ============================================================
# RAZORPAY CLIENT
# ============================================================

razorpay_client = None

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(
        auth=(
            RAZORPAY_KEY_ID,
            RAZORPAY_KEY_SECRET,
        )
    )


# ============================================================
# HELPERS
# ============================================================

def _get_client():
    if razorpay_client is None:
        logger.error(
            "Razorpay configuration missing. "
            "RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET not configured."
        )

        raise HTTPException(
            status_code=500,
            detail="Razorpay is not configured.",
        )

    return razorpay_client


def _india_today() -> date:
    """
    Current date in IST.

    Payment access is a daily Indian-user feature,
    so do not depend on server UTC/local timezone.
    """

    return datetime.now(
        timezone.utc
    ).astimezone(
        timezone(timedelta(hours=5, minutes=30))
    ).date()


def _success_response(
    payment: NewsDailyPayment,
    message: str,
) -> dict:

    return {
        "status": "success",
        "message": message,

        "has_access": True,

        "access_active": True,

        "access_date": (
            payment.payment_date.isoformat()
            if payment.payment_date
            else _india_today().isoformat()
        ),

        "order_id": payment.order_id,

        "payment_id": payment.payment_id,

        "amount": payment.amount,

        "currency": payment.currency,
    }


# ============================================================
# CREATE ORDER
# ============================================================

def create_news_order(
    db: Session,
    user_id: int,
):
    """
    Create today's ₹1 News access Razorpay order.

    One database payment record is maintained per
    user per Indian calendar day.
    """

    client = _get_client()

    today = _india_today()

    # --------------------------------------------------------
    # FIND TODAY'S RECORD
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

        return _success_response(
            existing,
            "Today's news access is already active.",
        )

    # --------------------------------------------------------
    # CREATE RAZORPAY ORDER
    # --------------------------------------------------------

    try:

        order = client.order.create(
            {
                "amount": NEWS_DAILY_PRICE,
                "currency": NEWS_CURRENCY,

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
        ) from exc

    order_id = order.get("id")

    if not order_id:

        logger.error(
            "Invalid Razorpay order response: %s",
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
        existing.currency = NEWS_CURRENCY

        existing.status = "created"
        existing.verified_at = None

        db.commit()
        db.refresh(existing)

        return {
            "status": "success",
            "message": "Razorpay order created.",

            "order_id": order_id,

            "amount": NEWS_DAILY_PRICE,
            "currency": NEWS_CURRENCY,

            "key_id": RAZORPAY_KEY_ID,

            "has_access": False,
            "access_active": False,
        }

    # --------------------------------------------------------
    # CREATE DATABASE RECORD
    # --------------------------------------------------------

    payment = NewsDailyPayment(
        user_id=user_id,

        order_id=order_id,

        payment_id=None,
        signature=None,

        amount=NEWS_DAILY_PRICE,
        currency=NEWS_CURRENCY,

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

                return _success_response(
                    existing,
                    "Today's news access is already active.",
                )

            return {
                "status": "success",
                "message": "Razorpay order already exists.",

                "order_id": existing.order_id,

                "amount": existing.amount,
                "currency": existing.currency,

                "key_id": RAZORPAY_KEY_ID,

                "has_access": False,
                "access_active": False,
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
        "currency": NEWS_CURRENCY,

        "key_id": RAZORPAY_KEY_ID,

        "has_access": False,
        "access_active": False,
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

    # --------------------------------------------------------
    # CLEAN INPUT
    # --------------------------------------------------------

    razorpay_order_id = (
        str(razorpay_order_id or "").strip()
    )

    razorpay_payment_id = (
        str(razorpay_payment_id or "").strip()
    )

    razorpay_signature = (
        str(razorpay_signature or "").strip()
    )

    if not razorpay_order_id:
        raise HTTPException(
            status_code=422,
            detail="razorpay_order_id is required.",
        )

    if not razorpay_payment_id:
        raise HTTPException(
            status_code=422,
            detail="razorpay_payment_id is required.",
        )

    if not razorpay_signature:
        raise HTTPException(
            status_code=422,
            detail="razorpay_signature is required.",
        )

    # --------------------------------------------------------
    # FIND ORDER
    # --------------------------------------------------------

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
    # ALREADY VERIFIED
    # --------------------------------------------------------

    if payment.status in {
        "paid",
        "verified",
    }:

        return _success_response(
            payment,
            "News access is already active.",
        )

    # --------------------------------------------------------
    # VERIFY RAZORPAY SIGNATURE
    # --------------------------------------------------------

    try:

        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )

    except Exception as exc:

        logger.warning(
            "Invalid Razorpay signature | "
            "user=%s order=%s payment=%s error=%s",
            user_id,
            razorpay_order_id,
            razorpay_payment_id,
            exc,
        )

        payment.status = "failed"

        try:
            db.commit()
        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay payment signature.",
        ) from exc

    # --------------------------------------------------------
    # VERIFY ORDER/PAYMENT
    # --------------------------------------------------------

    payment.payment_id = razorpay_payment_id
    payment.signature = razorpay_signature

    payment.status = "paid"

    payment.verified_at = datetime.now(
        timezone.utc
    )

    try:

        db.commit()
        db.refresh(payment)

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Failed to save verified news payment | "
            "user=%s order=%s",
            user_id,
            razorpay_order_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Payment verified but access could not be saved.",
        ) from exc

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    logger.info(
        "News payment verified successfully | "
        "user=%s order=%s payment=%s",
        user_id,
        razorpay_order_id,
        razorpay_payment_id,
    )

    return _success_response(
        payment,
        "News access activated for today.",
    )


# ============================================================
# CHECK ACCESS
# ============================================================

def has_news_access_today(
    db: Session,
    user_id: int,
) -> bool:

    # IMPORTANT:
    # Use same IST date logic used during order creation.

    today = _india_today()

    payment = (
        db.query(NewsDailyPayment)
        .filter(
            NewsDailyPayment.user_id == user_id,

            NewsDailyPayment.payment_date == today,

            NewsDailyPayment.status.in_(
                [
                    "paid",
                    "verified",
                ]
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

            "message": (
                "Today's News access "
                "requires ₹1 payment."
            ),

            "amount": 1,

            "currency": "INR",

            "payment_endpoint": (
                "/news/payment/create-order"
            ),
        },
    )

