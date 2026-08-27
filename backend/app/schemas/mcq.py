# app/schemas/mcq.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================
# BASE
# ============================================================

class MCQBase(BaseModel):
    """
    Common fields shared by MCQ create and response schemas.
    """

    question: str = Field(
        ...,
        min_length=10,
        max_length=2000,
    )

    option_a: str = Field(
        ...,
        min_length=1,
        max_length=1000,
    )

    option_b: str = Field(
        ...,
        min_length=1,
        max_length=1000,
    )

    option_c: str = Field(
        ...,
        min_length=1,
        max_length=1000,
    )

    option_d: str = Field(
        ...,
        min_length=1,
        max_length=1000,
    )

    correct_answer: str = Field(
        ...,
        min_length=1,
        max_length=1,
    )

    explanation: Optional[str] = Field(
        default=None,
        max_length=5000,
    )

    exam: str = "UPSC"

    state: Optional[str] = None

    language: str = "en"

    category: Optional[str] = None

    topic: Optional[str] = None

    difficulty: str = "Medium"

    question_type: str = "Prelims"

    # --------------------------------------------------------
    # CORRECT ANSWER
    # --------------------------------------------------------

    @field_validator("correct_answer")
    @classmethod
    def validate_answer(cls, value: str) -> str:

        value = value.strip().upper()

        if value not in {"A", "B", "C", "D"}:
            raise ValueError(
                "correct_answer must be A, B, C or D"
            )

        return value

    # --------------------------------------------------------
    # EXAM
    # --------------------------------------------------------

    @field_validator("exam")
    @classmethod
    def validate_exam(cls, value: str) -> str:

        value = value.strip().upper()

        allowed = {
            "UPSC",
            "BPSC",
        }

        if value not in allowed:
            raise ValueError(
                "exam must be UPSC or BPSC"
            )

        return value

    # --------------------------------------------------------
    # DIFFICULTY
    # --------------------------------------------------------

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: str) -> str:

        value = value.strip().capitalize()

        allowed = {
            "Easy",
            "Medium",
            "Hard",
        }

        if value not in allowed:
            raise ValueError(
                "difficulty must be Easy, Medium or Hard"
            )

        return value

    # --------------------------------------------------------
    # LANGUAGE
    # --------------------------------------------------------

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:

        value = value.strip().lower()

        allowed = {
            "en",
            "hi",
        }

        if value not in allowed:
            raise ValueError(
                "language must be en or hi"
            )

        return value

    # --------------------------------------------------------
    # QUESTION TYPE
    # --------------------------------------------------------

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, value: str) -> str:

        value = value.strip().lower()

        mapping = {
            "prelims": "Prelims",
            "prelims_mcq": "Prelims",
            "mains": "Mains",
            "single_correct": "Prelims",
        }

        if value not in mapping:
            raise ValueError(
                "question_type must be Prelims or Mains"
            )

        return mapping[value]


# ============================================================
# CREATE
# ============================================================

class MCQCreate(MCQBase):

    current_affair_id: int = Field(
        ...,
        ge=1,
    )


# ============================================================
# RESPONSE
# ============================================================

class MCQResponse(MCQBase):

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    current_affair_id: int

    is_verified: bool = False

    is_active: bool = True

    created_at: datetime

    updated_at: datetime


# ============================================================
# LIST RESPONSE
# ============================================================

class MCQListResponse(BaseModel):

    status: str = "success"

    total: int = 0

    page: int = Field(
        default=1,
        ge=1,
    )

    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    questions: list[MCQResponse] = Field(
        default_factory=list
    )


# ============================================================
# GENERATION REQUEST
# ============================================================

class MCQGenerateRequest(BaseModel):

    exam: str = "UPSC"

    language: str = "en"

    count: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    difficulty: str = "Medium"

    question_type: str = "Prelims"

    # --------------------------------------------------------
    # EXAM
    # --------------------------------------------------------

    @field_validator("exam")
    @classmethod
    def validate_exam(cls, value: str) -> str:

        value = value.strip().upper()

        if value not in {"UPSC", "BPSC"}:
            raise ValueError(
                "exam must be UPSC or BPSC"
            )

        return value

    # --------------------------------------------------------
    # LANGUAGE
    # --------------------------------------------------------

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:

        value = value.strip().lower()

        if value not in {"en", "hi"}:
            raise ValueError(
                "language must be en or hi"
            )

        return value

    # --------------------------------------------------------
    # DIFFICULTY
    # --------------------------------------------------------

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: str) -> str:

        value = value.strip().capitalize()

        if value not in {
            "Easy",
            "Medium",
            "Hard",
        }:
            raise ValueError(
                "difficulty must be Easy, Medium or Hard"
            )

        return value

    # --------------------------------------------------------
    # QUESTION TYPE
    # --------------------------------------------------------

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, value: str) -> str:

        value = value.strip().lower()

        mapping = {
            "prelims": "Prelims",
            "prelims_mcq": "Prelims",
            "mains": "Mains",
            "single_correct": "Prelims",
        }

        if value not in mapping:
            raise ValueError(
                "question_type must be Prelims or Mains"
            )

        return mapping[value]


# ============================================================
# GENERATION RESPONSE
# ============================================================

class MCQGenerateResponse(BaseModel):

    status: str = "success"

    current_affair_id: int

    generated: int = 0

    questions: list[MCQResponse] = Field(
        default_factory=list
    )