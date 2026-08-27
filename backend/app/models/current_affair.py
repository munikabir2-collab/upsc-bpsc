from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import relationship

from app.database import Base


class CurrentAffair(Base):
    __tablename__ = "current_affairs"

    # =========================================================
    # PRIMARY KEY
    # =========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # =========================================================
    # CONTENT
    # =========================================================

    title = Column(
        String(500),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    content = Column(
        Text,
        nullable=True,
    )

    url = Column(
        String(1000),
        nullable=True,
    )

    source = Column(
        String(200),
        nullable=True,
    )

    image_url = Column(
        String(1000),
        nullable=True,
    )

    published_at = Column(
        DateTime,
        nullable=True,
    )

    # =========================================================
    # CLASSIFICATION
    # =========================================================

    exam = Column(
        String(100),
        nullable=False,
        default="UPSC",
        index=True,
    )

    category = Column(
        String(100),
        nullable=True,
        index=True,
    )

    subject = Column(
        String(100),
        nullable=True,
    )

    importance = Column(
        String(20),
        nullable=False,
        default="Medium",
    )

    exam_relevance = Column(
        String(50),
        nullable=True,
        default="Low",
    )

    upsc_relevance = Column(
        String(50),
        nullable=True,
        default="Low",
    )

    bpsc_relevance = Column(
        String(50),
        nullable=True,
        default="Low",
    )

    prelims_relevant = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    mains_relevant = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    bihar_relevant = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    # =========================================================
    # SCORING
    # =========================================================

    relevance_score = Column(
        Integer,
        nullable=False,
        default=0,
    )

    query_score = Column(
        Integer,
        nullable=False,
        default=0,
    )

    engine_score = Column(
        Integer,
        nullable=False,
        default=0,
    )

    freshness_score = Column(
        Integer,
        nullable=False,
        default=0,
    )

    final_score = Column(
        Integer,
        nullable=False,
        default=0,
    )

    bpsc_score = Column(
        Integer,
        nullable=False,
        default=0,
    )

    bihar_score = Column(
        Integer,
        nullable=False,
        default=0,
    )

    is_noise = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    # =========================================================
    # SUMMARY
    # =========================================================

    summary = Column(
        Text,
        nullable=True,
    )

    language = Column(
        String(10),
        nullable=False,
        default="en",
        index=True,
    )

    # =========================================================
    # TIMESTAMP
    # =========================================================

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # =========================================================
    # RELATIONSHIP
    # =========================================================

    mcqs = relationship(
        "MCQ",
        back_populates="current_affair",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )