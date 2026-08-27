from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
)

from app.database import Base


class NewsDailyPayment(Base):

    __tablename__ = "news_daily_payments"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        nullable=False,
        index=True,
    )

    order_id = Column(
        String(255),
        nullable=True,
        index=True,
    )

    payment_id = Column(
        String(255),
        nullable=True,
        index=True,
    )

    signature = Column(
        String(500),
        nullable=True,
    )

    amount = Column(
        Integer,
        nullable=False,
        default=100,
    )

    currency = Column(
        String(10),
        nullable=False,
        default="INR",
    )

    payment_date = Column(
        Date,
        nullable=False,
        index=True,
    )

    status = Column(
        String(30),
        nullable=False,
        default="created",
        index=True,
    )

    verified_at = Column(
        DateTime,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "payment_date",
            name="uq_news_daily_user_date",
        ),
    )