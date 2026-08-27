from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import relationship

from app.database import Base


class MCQ(Base):
    __tablename__ = "mcqs"

    # =========================================================
    # PRIMARY KEY
    # =========================================================

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    # =========================================================
    # RELATION
    # =========================================================

    current_affair_id = Column(
        Integer,
        ForeignKey(
            "current_affairs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # =========================================================
    # QUESTION
    # =========================================================

    question = Column(
        Text,
        nullable=False,
    )

    option_a = Column(
        Text,
        nullable=False,
    )

    option_b = Column(
        Text,
        nullable=False,
    )

    option_c = Column(
        Text,
        nullable=False,
    )

    option_d = Column(
        Text,
        nullable=False,
    )

    correct_answer = Column(
        String(1),
        nullable=False,
    )

    explanation = Column(
        Text,
        nullable=True,
    )

    # =========================================================
    # CLASSIFICATION
    # =========================================================

    exam = Column(
        String(20),
        nullable=False,
        default="UPSC",
        index=True,
    )

    state = Column(
        String(50),
        nullable=True,
        index=True,
    )

    language = Column(
        String(10),
        nullable=False,
        default="en",
        index=True,
    )

    category = Column(
        String(100),
        nullable=True,
        index=True,
    )

    topic = Column(
        String(200),
        nullable=True,
    )

    difficulty = Column(
        String(20),
        nullable=False,
        default="Medium",
        index=True,
    )

    question_type = Column(
        String(30),
        nullable=False,
        default="Prelims",
        index=True,
    )

    # =========================================================
    # QUALITY
    # =========================================================

    is_verified = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # =========================================================
    # TIMESTAMPS
    # =========================================================

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # =========================================================
    # RELATIONSHIP
    # =========================================================

    current_affair = relationship(
        "CurrentAffair",
        back_populates="mcqs",
    )

    # =========================================================
    # INDEXES
    # =========================================================

    __table_args__ = (
        Index(
            "ix_mcq_exam_language",
            "exam",
            "language",
        ),

        Index(
            "ix_mcq_exam_difficulty",
            "exam",
            "difficulty",
        ),

        Index(
            "ix_mcq_affair_exam",
            "current_affair_id",
            "exam",
        ),

        Index(
            "ix_mcq_exam_language_active",
            "exam",
            "language",
            "is_active",
        ),
    )