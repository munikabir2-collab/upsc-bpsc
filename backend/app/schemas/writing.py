from __future__ import annotations

from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


# ============================================================================
# GENERATE QUESTION
# ============================================================================

class GenerateQuestionRequest(BaseModel):
    exam: str = Field(
        default="UPSC",
        min_length=3,
        max_length=20,
    )

    category: str = Field(
        default="General",
        min_length=1,
        max_length=100,
    )

    question_type: Literal[
        "short",
        "long",
    ] = "short"

    language: Literal[
        "hi",
        "en",
    ] = "hi"

    # ------------------------------------------------------------------------
    # UPSC / BPSC Mains answer length
    #
    # short = 150 words
    # long  = 250 words
    # ------------------------------------------------------------------------

    target_words: Literal[
        150,
        250,
    ] = 150


# ============================================================================
# QUESTION RESPONSE
# ============================================================================

class QuestionResponse(BaseModel):
    id: int

    exam: str

    category: Optional[str] = None

    question_type: str

    question: str

    marks: int

    target_words: int

    expected_keywords: List[str] = Field(
        default_factory=list
    )


# ============================================================================
# SUBMIT ANSWER
# ============================================================================

class SubmitAnswerRequest(BaseModel):
    answer: str = Field(
        ...,
        min_length=1,
    )


# ============================================================================
# GENERATE MODEL ANSWER
# ============================================================================

class GenerateAnswerRequest(BaseModel):
    language: Literal[
        "hi",
        "en",
    ] = "hi"


# ============================================================================
# GENERATE ESSAY
# ============================================================================

class GenerateEssayRequest(BaseModel):
    exam: str = Field(
        default="UPSC",
        min_length=3,
        max_length=20,
    )

    language: Literal[
        "hi",
        "en",
    ] = "hi"

    topic: Optional[str] = Field(
        default=None,
        max_length=500,
    )


# ============================================================================
# SUBMIT ESSAY
# ============================================================================

class SubmitEssayRequest(BaseModel):
    essay: str = Field(
        ...,
        min_length=1,
    )


# ============================================================================
# GENERIC RESPONSE
# ============================================================================

class WritingResponse(BaseModel):
    status: str

    data: dict[str, Any]