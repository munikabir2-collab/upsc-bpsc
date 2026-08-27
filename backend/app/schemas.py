from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# ============================================================
# AUTHENTICATION
# ============================================================

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


# ============================================================
# WRITING
# ============================================================

class GenerateQuestionRequest(BaseModel):
    exam: str = Field(..., min_length=3)
    category: str = "General"
    question_type: str = "short"
    language: str = "hi"

    # Student selects the required answer length.
    # Currently supported: 150 or 250 words.
    target_words: Literal[150, 250] = Field(
        default=150,
        description="Answer word limit. Allowed values: 150 or 250."
    )


class GenerateAnswerRequest(BaseModel):
    language: str = "hi"


class SubmitAnswerRequest(BaseModel):
    answer: str = Field(
        ...,
        min_length=1,
        description="Student's written answer"
    )


class GenerateEssayRequest(BaseModel):
    exam: str = Field(..., min_length=3)
    topic: str = Field(..., min_length=3)
    language: str = "hi"
    target_words: int = Field(
        default=1000,
        ge=500,
        le=3000,
        description="Essay target word count"
    )


class SubmitEssayRequest(BaseModel):
    essay: str = Field(
        ...,
        min_length=1,
        description="Student's essay"
    )