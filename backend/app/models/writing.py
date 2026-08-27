from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
)

from app.database import Base


# ============================================================================
# HELPERS
# ============================================================================

def utc_now() -> datetime:
    """
    Return timezone-aware UTC datetime.
    """
    return datetime.now(timezone.utc)


# ============================================================================
# WRITING QUESTION
# ============================================================================

class WritingQuestion(Base):
    __tablename__ = "writing_questions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    exam = Column(
        String(20),
        nullable=False,
        index=True,
    )

    category = Column(
        String(100),
        nullable=True,
        index=True,
    )

    question_type = Column(
        String(30),
        nullable=False,
        default="short",
        index=True,
    )

    question = Column(
        Text,
        nullable=False,
    )

    marks = Column(
        Integer,
        nullable=False,
        default=10,
    )

    # ------------------------------------------------------------------------
    # Dynamic UPSC/BPSC answer length
    # 150 = short
    # 250 = long
    # ------------------------------------------------------------------------

    target_words = Column(
        Integer,
        nullable=False,
        default=150,
        index=True,
    )

    expected_keywords = Column(
        JSON,
        nullable=True,
        default=list,
    )

    source = Column(
        String(50),
        nullable=False,
        default="ai",
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


# ============================================================================
# ANSWER SUBMISSION
# ============================================================================

class AnswerSubmission(Base):
    __tablename__ = "answer_submissions"

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

    question_id = Column(
        Integer,
        nullable=False,
        index=True,
    )

    answer = Column(
        Text,
        nullable=False,
    )

    score = Column(
        Integer,
        nullable=False,
        default=0,
    )

    max_score = Column(
        Integer,
        nullable=False,
        default=10,
    )

    percentage = Column(
        Integer,
        nullable=False,
        default=0,
    )

    word_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    evaluation = Column(
        JSON,
        nullable=True,
    )

    evaluation_mode = Column(
        String(20),
        nullable=False,
        default="basic",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


# ============================================================================
# ESSAY QUESTION
# ============================================================================

class EssayQuestion(Base):
    __tablename__ = "essay_questions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    exam = Column(
        String(20),
        nullable=False,
        index=True,
    )

    language = Column(
        String(10),
        nullable=False,
        default="hi",
        index=True,
    )

    topic = Column(
        Text,
        nullable=False,
    )

    # UPSC/BPSC essay target
    target_words = Column(
        Integer,
        nullable=False,
        default=1000,
        index=True,
    )

    source = Column(
        String(50),
        nullable=False,
        default="ai",
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


# ============================================================================
# ESSAY SUBMISSION
# ============================================================================

class EssaySubmission(Base):
    __tablename__ = "essay_submissions"

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

    essay_id = Column(
        Integer,
        nullable=False,
        index=True,
    )

    essay = Column(
        Text,
        nullable=False,
    )

    score = Column(
        Integer,
        nullable=False,
        default=0,
    )

    max_score = Column(
        Integer,
        nullable=False,
        default=100,
    )

    percentage = Column(
        Integer,
        nullable=False,
        default=0,
    )

    word_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    evaluation = Column(
        JSON,
        nullable=True,
    )

    evaluation_mode = Column(
        String(20),
        nullable=False,
        default="basic",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )