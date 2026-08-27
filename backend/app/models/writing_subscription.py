from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
)

from app.database import Base


# ============================================================================
# DATETIME HELPER
# ============================================================================

def utc_now() -> datetime:
    """
    Return current timezone-aware UTC datetime.
    """
    return datetime.now(timezone.utc)


# ============================================================================
# WRITING SUBSCRIPTION
# ============================================================================

class WritingSubscription(Base):
    __tablename__ = "writing_subscriptions"

    # ------------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------------

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ------------------------------------------------------------------------
    # USER
    # ------------------------------------------------------------------------

    user_id = Column(
        Integer,
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------------
    # PLAN
    # ------------------------------------------------------------------------

    plan = Column(
        String(50),
        nullable=False,
        default="weekly",
        index=True,
    )

    # ₹39
    amount = Column(
        Integer,
        nullable=False,
        default=39,
    )

    # 7 days
    duration_days = Column(
        Integer,
        nullable=False,
        default=7,
    )

    # Maximum answer submissions
    answer_limit = Column(
        Integer,
        nullable=False,
        default=10,
    )

    # Number of answers already submitted
    answers_used = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # ------------------------------------------------------------------------
    # ACCESS STATUS
    # ------------------------------------------------------------------------

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # ------------------------------------------------------------------------
    # SUBSCRIPTION PERIOD
    # ------------------------------------------------------------------------

    starts_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------------
    # RAZORPAY
    # ------------------------------------------------------------------------

    razorpay_order_id = Column(
        String(100),
        nullable=True,
        index=True,
    )

    razorpay_payment_id = Column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
    )

    # ------------------------------------------------------------------------
    # PAYMENT STATUS
    #
    # pending
    # paid
    # expired
    # replaced
    # ------------------------------------------------------------------------

    payment_status = Column(
        String(30),
        nullable=False,
        default="pending",
        index=True,
    )

    # ------------------------------------------------------------------------
    # TIMESTAMPS
    # ------------------------------------------------------------------------

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )