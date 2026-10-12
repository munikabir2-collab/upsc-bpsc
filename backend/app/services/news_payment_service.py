
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


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger("app.news_payment")


# ============================================================
# CONFIGURATION
# ============================================================

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()

# ₹1 = 100 paise
NEWS_DAILY_PRICE = 100
NEWS_CURRENCY = "INR"
NEWS_FEATURE = "daily_current_affairs"


# ============================================================
# RAZORPAY CLIENT
# ============================================================

razorpay_client = None

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    razorpay_client = razorpay.Client(
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )


# ============================================================
# RAZORPAY CLIENT HELPER
# ============================================================

def _get_client():
    """Return configured Razorpay client."""

    if not RAZORPAY_KEY_ID:
        logger.error("RAZORPAY_KEY_ID is missing.")
        raise HTTPException(
            status_code=500,
            detail="RAZORPAY_KEY_ID is not configured.",
        )

    if not RAZORPAY_KEY_SECRET:
        logger.error("RAZORPAY_KEY_SECRET is missing.")
        raise HTTPException(
            status_code=500,
            detail="RAZORPAY_KEY_SECRET is not configured.",
        )

    if razorpay_client is None:
        logger.error("Razorpay client could not be initialized.")
        raise HTTPException(
            status_code=500,
            detail="Razorpay is not configured.",
        )

    return razorpay_client


# ============================================================
# INDIA DATE
# ============================================================

def _india_today() -> date:
    """Return today's date in IST."""

    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(timezone.utc).astimezone(ist).date()


# ============================================================
# SUCCESS RESPONSE
# ============================================================

def _success_response(
    payment: NewsDailyPayment,
    message: str,
) -> dict:
    """Standard successful News payment response."""

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
# CREATE NEWS ORDER
# ============================================================

def create_news_order(
    db: Session,
    user_id: int,
):
    """
    Create today's ₹1 Razorpay News access order.

    One payment record is maintained per user
    per Indian calendar day.

    Existing orders are reused instead of overwritten.
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

    if existing and existing.status in {"paid", "verified"}:
        return _success_response(
            existing,
            "Today's news access is already active.",
        )

    # --------------------------------------------------------
    # REUSE EXISTING PENDING ORDER
    # --------------------------------------------------------

    if (
        existing
        and existing.status == "created"
        and existing.order_id
    ):
        return {
            "status": "success",
            "message": "Reusing existing pending Razorpay order.",
            "order_id": existing.order_id,
            "amount": existing.amount,
            "currency": existing.currency,
            "key_id": RAZORPAY_KEY_ID,
            "has_access": False,
            "access_active": False,
        }

    # --------------------------------------------------------
    # PROTECT EXISTING PAYMENT HISTORY
    # Do not overwrite order_id/payment_id or erase signature.
    # A failed or unexpected record needs reconciliation first.
    # --------------------------------------------------------

    if existing:
        logger.warning(
            "Existing News payment record needs review | "
            "user_id=%s order_id=%s status=%s",
            user_id,
            existing.order_id,
            existing.status,
        )

        raise HTTPException(
            status_code=409,
            detail=(
                "A payment record already exists for today. "
                "Please verify its Razorpay status before retrying."
            ),
        )

    # --------------------------------------------------------
    # CREATE RAZORPAY ORDER
    # --------------------------------------------------------

    receipt = f"news_{user_id}_{today.strftime('%Y%m%d')}"

    try:
        order = client.order.create(
            {
                "amount": NEWS_DAILY_PRICE,
                "currency": NEWS_CURRENCY,
                "receipt": receipt,
                "notes": {
                    "user_id": str(user_id),
                    "feature": NEWS_FEATURE,
                    "payment_date": today.isoformat(),
                },
            }
        )

    except Exception as exc:
        logger.exception(
            "Failed to create News Razorpay order | user_id=%s",
            user_id,
        )
        raise HTTPException(
            status_code=502,
            detail="Unable to create Razorpay order.",
        ) from exc

    order_id = order.get("id")

    if not order_id:
        logger.error("Invalid Razorpay News order response.")
        raise HTTPException(
            status_code=502,
            detail="Invalid Razorpay order response.",
        )

    # --------------------------------------------------------
    # SAVE NEW DATABASE RECORD
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
            if existing.status in {"paid", "verified"}:
                return _success_response(
                    existing,
                    "Today's news access is already active.",
                )

            if existing.status == "created" and existing.order_id:
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

            raise HTTPException(
                status_code=409,
                detail=(
                    "An existing payment record needs review "
                    "before another order can be created."
                ),
            )

        raise

    except Exception as exc:
        db.rollback()
        logger.exception(
            "Failed to save News payment | user_id=%s",
            user_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to save News payment order.",
        ) from exc

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
# VERIFY NEWS PAYMENT
# ============================================================

def verify_news_payment(
    db: Session,
    user_id: int,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> dict:
    """
    Verify a Razorpay payment before granting News access.

    The local order must exist, the signature must be valid,
    and the Razorpay payment must be captured for the expected
    order, amount, and currency.
    """

    client = _get_client()

    # --------------------------------------------------------
    # CLEAN INPUT
    # --------------------------------------------------------

    razorpay_order_id = str(razorpay_order_id or "").strip()
    razorpay_payment_id = str(razorpay_payment_id or "").strip()
    razorpay_signature = str(razorpay_signature or "").strip()

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
    # FIND LOCAL ORDER
    # --------------------------------------------------------

    payment_record = (
        db.query(NewsDailyPayment)
        .filter(
            NewsDailyPayment.user_id == user_id,
            NewsDailyPayment.order_id == razorpay_order_id,
        )
        .first()
    )

    if not payment_record:
        raise HTTPException(
            status_code=404,
            detail="News payment order not found.",
        )

    # --------------------------------------------------------
    # ALREADY VERIFIED
    # --------------------------------------------------------

    if payment_record.status in {"paid", "verified"}:
        return _success_response(
            payment_record,
            "News access is already active.",
        )

    # --------------------------------------------------------
    # VERIFY SIGNATURE
    # Invalid callbacks must not overwrite the record status.
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
            "Invalid News Razorpay signature | "
            "user=%s order=%s payment=%s error=%s",
            user_id,
            razorpay_order_id,
            razorpay_payment_id,
            exc,
        )

        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay payment signature.",
        ) from exc

    # --------------------------------------------------------
    # FETCH AND VERIFY RAZORPAY ORDER
    # --------------------------------------------------------

    try:
        order = client.order.fetch(razorpay_order_id)

        order_amount = int(order.get("amount", 0))
        order_currency = order.get("currency")

        if order_amount != NEWS_DAILY_PRICE:
            raise HTTPException(
                status_code=400,
                detail="Invalid News payment amount.",
            )

        if order_currency != NEWS_CURRENCY:
            raise HTTPException(
                status_code=400,
                detail="Invalid News payment currency.",
            )

        notes = order.get("notes") or {}

        if str(notes.get("user_id", "")) != str(user_id):
            raise HTTPException(
                status_code=403,
                detail="Payment order user does not match.",
            )

        if notes.get("feature") != NEWS_FEATURE:
            raise HTTPException(
                status_code=400,
                detail="Invalid News payment feature.",
            )

        if notes.get("payment_date") != payment_record.payment_date.isoformat():
            raise HTTPException(
                status_code=400,
                detail="Payment date does not match the local order.",
            )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Unable to verify News Razorpay order | order=%s",
            razorpay_order_id,
        )
        raise HTTPException(
            status_code=400,
            detail="Unable to verify Razorpay order.",
        ) from exc

    # --------------------------------------------------------
    # FETCH AND VERIFY RAZORPAY PAYMENT
    # --------------------------------------------------------

    try:
        razorpay_payment = client.payment.fetch(razorpay_payment_id)

        payment_status = razorpay_payment.get("status")
        payment_order_id = razorpay_payment.get("order_id")
        payment_amount = int(razorpay_payment.get("amount", 0))
        payment_currency = razorpay_payment.get("currency")

        if payment_order_id != razorpay_order_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment does not belong to "
                    "the specified order."
                ),
            )

        if payment_amount != NEWS_DAILY_PRICE:
            raise HTTPException(
                status_code=400,
                detail="Invalid News payment amount.",
            )

        if payment_currency != NEWS_CURRENCY:
            raise HTTPException(
                status_code=400,
                detail="Invalid News payment currency.",
            )

        if payment_status != "captured":
            raise HTTPException(
                status_code=400,
                detail="Payment has not been captured yet.",
            )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Unable to verify News Razorpay payment | payment=%s",
            razorpay_payment_id,
        )
        raise HTTPException(
            status_code=400,
            detail="Unable to verify Razorpay payment.",
        ) from exc

    # --------------------------------------------------------
    # PAYMENT ID IDEMPOTENCY
    # --------------------------------------------------------

    existing_payment = (
        db.query(NewsDailyPayment)
        .filter(
            NewsDailyPayment.payment_id == razorpay_payment_id
        )
        .first()
    )

    if existing_payment:
        if str(existing_payment.user_id) != str(user_id):
            raise HTTPException(
                status_code=403,
                detail=(
                    "This payment has already been associated "
                    "with another user."
                ),
            )

        if existing_payment.status in {"paid", "verified"}:
            return _success_response(
                existing_payment,
                "News access is already active.",
            )

        # Do not allow the same payment ID to be attached to
        # a different local order.
        if existing_payment.order_id != razorpay_order_id:
            raise HTTPException(
                status_code=409,
                detail=(
                    "This payment is associated with a "
                    "different local order."
                ),
            )

    # --------------------------------------------------------
    # SAVE VERIFIED PAYMENT
    # --------------------------------------------------------

    payment_record.payment_id = razorpay_payment_id
    payment_record.signature = razorpay_signature
    payment_record.amount = NEWS_DAILY_PRICE
    payment_record.currency = NEWS_CURRENCY
    payment_record.status = "paid"
    payment_record.verified_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(payment_record)

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Failed to save verified News payment | "
            "user=%s order=%s payment=%s",
            user_id,
            razorpay_order_id,
            razorpay_payment_id,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Payment verified but News access "
                "could not be saved. Check the payment "
                "record before retrying."
            ),
        ) from exc

    logger.info(
        "News payment verified successfully | "
        "user=%s order=%s payment=%s",
        user_id,
        razorpay_order_id,
        razorpay_payment_id,
    )

    return _success_response(
        payment_record,
        "News access activated for today.",
    )


# ============================================================
# CHECK TODAY'S ACCESS
# ============================================================

def has_news_access_today(
    db: Session,
    user_id: int,
) -> bool:
    """Return True when today's News payment is valid."""

    today = _india_today()

    payment = (
        db.query(NewsDailyPayment)
        .filter(
            NewsDailyPayment.user_id == user_id,
            NewsDailyPayment.payment_date == today,
            NewsDailyPayment.status.in_(["paid", "verified"]),
        )
        .first()
    )

    return payment is not None


# ============================================================
# REQUIRE NEWS ACCESS
# ============================================================

def require_news_access(
    db: Session,
    user_id: int,
) -> bool:
    """Require today's ₹1 News access."""

    if has_news_access_today(db=db, user_id=user_id):
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
