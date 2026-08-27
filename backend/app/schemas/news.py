from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# SYLLABUS
# ============================================================

class NewsSyllabus(BaseModel):

    prelims: List[str] = Field(
        default_factory=list
    )

    mains: List[str] = Field(
        default_factory=list
    )


# ============================================================
# NEWS ARTICLE
# ============================================================

class NewsArticle(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: Optional[int] = None

    title: str

    description: Optional[str] = None

    content: Optional[str] = None

    url: Optional[str] = None

    source: Optional[str] = None

    image_url: Optional[str] = None

    published_at: Optional[datetime] = None

    summary: Optional[str] = None

    created_at: Optional[datetime] = None

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    language: str = "en"

    exam: str = "UPSC"

    category: str = "General"

    subject: Optional[str] = None

    importance: str = "Medium"

    exam_relevance: str = "Low"

    upsc_relevance: str = "Low"

    bpsc_relevance: str = "Low"

    # --------------------------------------------------------
    # Relevance
    # --------------------------------------------------------

    prelims_relevant: bool = False

    mains_relevant: bool = False

    bihar_relevant: bool = False

    syllabus: NewsSyllabus = Field(
        default_factory=NewsSyllabus
    )

    # --------------------------------------------------------
    # Scores
    # --------------------------------------------------------

    relevance_score: int = 0

    query_score: int = 0

    engine_score: int = 0

    freshness_score: int = 0

    final_score: int = 0

    bpsc_score: int = 0

    bihar_score: int = 0

    # --------------------------------------------------------
    # Noise
    # --------------------------------------------------------

    is_noise: bool = False


# ============================================================
# NEWS SEARCH RESPONSE
# ============================================================

class NewsSearchResponse(BaseModel):

    status: str = "success"

    query: Optional[str] = None

    language: str = "en"

    exam: Optional[str] = None

    category: Optional[str] = None

    bihar_only: bool = False

    page: int = 1

    page_size: int = 20

    raw_total_results: int = 0

    raw_articles: int = 0

    filtered_results: int = 0

    returned_results: int = 0

    saved_results: int = 0

    total: int = 0

    articles: List[NewsArticle] = Field(
        default_factory=list
    )


# ============================================================
# NEWS LIST RESPONSE
# ============================================================

class NewsListResponse(BaseModel):

    status: str = "success"

    query: Optional[str] = None

    language: str = "en"

    exam: Optional[str] = None

    category: Optional[str] = None

    bihar_only: bool = False

    page: int = 1

    page_size: int = 20

    raw_total_results: int = 0

    raw_articles: int = 0

    filtered_results: int = 0

    returned_results: int = 0

    saved_results: int = 0

    total: int = 0

    articles: List[NewsArticle] = Field(
        default_factory=list
    )


# ============================================================
# DETAIL
# ============================================================

class NewsDetailResponse(BaseModel):

    status: str = "success"

    article: NewsArticle


# ============================================================
# FILTER REQUEST
# ============================================================

class NewsFilterRequest(BaseModel):

    category: Optional[str] = None

    exam: Optional[str] = None

    language: str = "en"

    importance: Optional[str] = None

    prelims: Optional[bool] = None

    mains: Optional[bool] = None

    bihar_only: bool = False

    page: int = Field(
        default=1,
        ge=1,
    )

    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
    )


# ============================================================
# MCQ OPTION
# ============================================================

class NewsMCQOption(BaseModel):

    key: str

    text: str


# ============================================================
# MCQ
# ============================================================

class NewsMCQ(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: Optional[int] = None

    current_affair_id: Optional[int] = None

    question: str

    # Database fields
    option_a: Optional[str] = None

    option_b: Optional[str] = None

    option_c: Optional[str] = None

    option_d: Optional[str] = None

    # Frontend fields
    options: List[NewsMCQOption] = Field(
        default_factory=list
    )

    correct_answer: Optional[str] = None

    explanation: Optional[str] = None

    difficulty: str = "Medium"

    exam: str = "UPSC"

    state: Optional[str] = None

    category: str = "General"

    topic: Optional[str] = None

    language: str = "en"

    question_type: str = "single_correct"

    is_verified: bool = False

    is_active: bool = True

    created_at: Optional[datetime] = None

    updated_at: Optional[datetime] = None


# ============================================================
# MCQ RESPONSE
# ============================================================

class NewsMCQResponse(BaseModel):

    status: str = "success"

    mcq: NewsMCQ


# ============================================================
# MCQ LIST
# ============================================================

class NewsMCQListResponse(BaseModel):

    status: str = "success"

    total: int = 0

    mcqs: List[NewsMCQ] = Field(
        default_factory=list
    )


# ============================================================
# MCQ GENERATE REQUEST
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

    question_type: str = "single_correct"


# ============================================================
# MCQ GENERATE RESPONSE
# ============================================================

class MCQGenerateResponse(BaseModel):

    status: str = "success"

    current_affair_id: int

    generated: int = 0

    questions: List[NewsMCQ] = Field(
        default_factory=list
    )


# ============================================================
# PRACTICE MCQ
# ============================================================

class MCQPracticeResponse(BaseModel):

    status: str = "success"

    exam: str

    language: str

    difficulty: Optional[str] = None

    limit: int = 10

    total: int = 0

    questions: List[NewsMCQ] = Field(
        default_factory=list
    )