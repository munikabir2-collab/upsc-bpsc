from __future__ import annotations

import json
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

logger = logging.getLogger("app.news_payment")


# ============================================================
# CONFIGURATION
# ============================================================

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()

# NEW: secret you set while creating the webhook in Razorpay dashboard
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()

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


def _pending_order_response(
    record: NewsDailyPayment,
    message: str,
) -> dict:
    """Response for an order that still waits for payment."""

    return {
        "status": "success",
        "message": message,
        "order_id": record.order_id,
        "amount": record.amount,
        "currency": record.currency,
        "key_id": RAZORPAY_KEY_ID,
        "has_access": False,
        "access_active": False,
    }


# ============================================================
# NEW: MARK A RECORD AS PAID (shared by reconcile + webhook)
# ============================================================

def _mark_paid(
    db: Session,
    record: NewsDailyPayment,
    payment_id: str | None,
    signature: str | None = None,
) -> bool:
    """Mark a local order as paid. Returns True on success."""

    if record.status in {"paid", "verified"}:
        return True

    # Never attach one payment id to two different records.
    if payment_id:
        other = (
            db.query(NewsDailyPayment)
            .filter(
                NewsDailyPayment.payment_id == payment_id,
                NewsDailyPayment.id != record.id,
            )
            .first()
        )

        if other:
            logger.warning(
                "Payment id already used by another record | payment=%s",
                payment_id,
            )
            return False

    record.payment_id = payment_id
    record.amount = NEWS_DAILY_PRICE
    record.currency = NEWS_CURRENCY
    record.status = "paid"
    record.verified_at = datetime.now(timezone.utc)

    if signature:
        record.signature = signature

    try:
        db.commit()
        db.refresh(record)
        return True

    except Exception:
        db.rollback()
        logger.exception(
            "Failed to mark News payment paid | order=%s",
            record.order_id,
        )
        return False


# ============================================================
# NEW: ASK RAZORPAY IF A PENDING ORDER WAS ALREADY PAID
# ============================================================

def _reconcile_record(
    db: Session,
    client,
    record: NewsDailyPayment,
) -> bool:
    """
    Look at Razorpay for a captured payment on this order.

    Fixes the case where the user paid but the app never called
    /verify (WebView callback lost). Returns True if access was
    activated.
    """

    if not record.order_id:
        return False

    try:
        result = client.order.payments(record.order_id)

    except Exception:
        logger.exception(
            "Unable to fetch payments for order | order=%s",
            record.order_id,
        )
        return False

    for item in (result or {}).get("items", []) or []:
        if (
            item.get("status") == "captured"
            and item.get("order_id") == record.order_id
            and int(item.get("amount", 0)) == NEWS_DAILY_PRICE
            and item.get("currency") == NEWS_CURRENCY
        ):
            logger.info(
                "Recovered paid News order | order=%s payment=%s",
                record.order_id,
                item.get("id"),
            )
            return _mark_paid(db, record, item.get("id"))

    return False


# ============================================================
# CREATE NEWS ORDER
# ============================================================

def create_news_order(
    db: Session,
    user_id: int,
):
    """
    Create today's ₹1 Razorpay News access order.

    One payment record per user per Indian calendar day.
    A pending order is first checked on Razorpay: if it was
    already paid, access is activated instead of reusing a
    paid order (which Razorpay would reject).
    """

    client = _get_client()
    today = _india_today()

    existing = (
        db.query(NewsDailyPayment)
        .filter(
            NewsDailyPayment.user_id == user_id,
            NewsDailyPayment.payment_date == today,
        )
        .first()
    )

    # ALREADY PAID
    if existing and existing.status in {"paid", "verified"}:
        return _success_response(
            existing,
            "Today's news access is already active.",
        )

    # PENDING ORDER: reconcile first, then reuse
    if (
        existing
        and existing.status == "created"
        and existing.order_id
    ):
        if _reconcile_record(db, client, existing):
            return _success_response(
                existing,
                "Payment found. Today's news access is active.",
            )

        return _pending_order_response(
            existing,
            "Reusing existing pending Razorpay order.",
        )

    # OTHER STATES NEED REVIEW
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

    # CREATE RAZORPAY ORDER
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
            if existing.status in {"paid", "verified"}:
                return _success_response(
                    existing,
                    "Today's news access is already active.",
                )

            if existing.status == "created" and existing.order_id:
                return _pending_order_response(
                    existing,
                    "Razorpay order already exists.",
                )

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
# VERIFY NEWS PAYMENT (unchanged logic)
# ============================================================

def verify_news_payment(
    db: Session,
    user_id: int,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> dict:
    """Verify a Razorpay payment before granting News access."""

    client = _get_client()

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

    if payment_record.status in {"paid", "verified"}:
        return _success_response(
            payment_record,
            "News access is already active.",
        )

    # SIGNATURE
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

    # ORDER CHECKS
    try:
        order = client.order.fetch(razorpay_order_id)

        if int(order.get("amount", 0)) != NEWS_DAILY_PRICE:
            raise HTTPException(
                status_code=400,
                detail="Invalid News payment amount.",
            )

        if order.get("currency") != NEWS_CURRENCY:
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

    # PAYMENT CHECKS
    try:
        razorpay_payment = client.payment.fetch(razorpay_payment_id)

        if razorpay_payment.get("order_id") != razorpay_order_id:
            raise HTTPException(
                status_code=400,
                detail="Payment does not belong to the specified order.",
            )

        if int(razorpay_payment.get("amount", 0)) != NEWS_DAILY_PRICE:
            raise HTTPException(
                status_code=400,
                detail="Invalid News payment amount.",
            )

        if razorpay_payment.get("currency") != NEWS_CURRENCY:
            raise HTTPException(
                status_code=400,
                detail="Invalid News payment currency.",
            )

        if razorpay_payment.get("status") != "captured":
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

    # IDEMPOTENCY
    existing_payment = (
        db.query(NewsDailyPayment)
        .filter(NewsDailyPayment.payment_id == razorpay_payment_id)
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

        if existing_payment.order_id != razorpay_order_id:
            raise HTTPException(
                status_code=409,
                detail=(
                    "This payment is associated with a "
                    "different local order."
                ),
            )

    # SAVE
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
# NEW: RAZORPAY WEBHOOK
# ============================================================

def handle_razorpay_webhook(
    db: Session,
    raw_body: bytes,
    signature: str | None,
) -> dict:
    """
    Handle Razorpay webhooks (payment.captured / order.paid).

    Razorpay calls this directly, so access is activated even
    if the app never reaches /verify.
    """

    if not RAZORPAY_WEBHOOK_SECRET:
        logger.error("RAZORPAY_WEBHOOK_SECRET is missing.")
        raise HTTPException(
            status_code=500,
            detail="Webhook secret is not configured.",
        )

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing webhook signature.",
        )

    client = _get_client()
    body_text = raw_body.decode("utf-8")

    try:
        client.utility.verify_webhook_signature(
            body_text,
            signature,
            RAZORPAY_WEBHOOK_SECRET,
        )

    except Exception as exc:
        logger.warning("Invalid Razorpay webhook signature.")
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook signature.",
        ) from exc

    try:
        event = json.loads(body_text)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook body.",
        ) from exc

    event_name = event.get("event")

    if event_name not in {"payment.captured", "order.paid"}:
        return {"status": "ignored", "event": event_name}

    payload = event.get("payload") or {}
    payment = (payload.get("payment") or {}).get("entity") or {}

    order_id = payment.get("order_id")
    payment_id = payment.get("id")

    if not order_id or not payment_id:
        return {"status": "ignored", "reason": "no order/payment id"}

    if (
        int(payment.get("amount", 0)) != NEWS_DAILY_PRICE
        or payment.get("currency") != NEWS_CURRENCY
    ):
        logger.warning(
            "Webhook amount/currency mismatch | order=%s",
            order_id,
        )
        return {"status": "ignored", "reason": "amount mismatch"}

    record = (
        db.query(NewsDailyPayment)
        .filter(NewsDailyPayment.order_id == order_id)
        .first()
    )

    if not record:
        # Not one of our News orders.
        return {"status": "ignored", "reason": "unknown order"}

    if _mark_paid(db, record, payment_id):
        logger.info(
            "News access activated by webhook | order=%s payment=%s",
            order_id,
            payment_id,
        )
        return {"status": "ok"}

    # 500 makes Razorpay retry the webhook later.
    raise HTTPException(
        status_code=500,
        detail="Could not record payment.",
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