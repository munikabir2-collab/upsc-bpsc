from __future__ import annotations

import inspect
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
)

from pydantic import BaseModel

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db

from app.dependencies.auth import (
    get_current_user,
)

from app.models.current_affair import (
    CurrentAffair,
)

from app.models.mcq import MCQ

from app.schemas.news import (
    NewsArticle,
    NewsSearchResponse,
    NewsMCQListResponse,
    MCQGenerateRequest,
    MCQGenerateResponse,
    MCQPracticeResponse,
)

from app.services.news_service import (
    fetch_news,
)

from app.services.news_filter import (
    classify_news_list,
    filter_news,
    rank_news,
)

# ============================================================
# MCQ SERVICE
# ============================================================

from app.services.news_mcq_service import (
    generate_mcqs,
    delete_article_mcqs,
    mcq_to_dict,
)

from app.services.news_payment_service import (
    create_news_order,
    verify_news_payment,
    require_news_access,
)


logger = logging.getLogger("app.news_router")


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/news",
    tags=["News"],
)


# ============================================================
# CONSTANTS
# ============================================================

SUPPORTED_EXAMS = {
    "UPSC",
    "BPSC",
}

SUPPORTED_LANGUAGES = {
    "en",
    "hi",
}

SUPPORTED_DIFFICULTIES = {
    "Easy",
    "Medium",
    "Hard",
}

SUPPORTED_QUESTION_TYPES = {
    "prelims",
    "mains",
    "mcq",
    "multiple_choice",
    "statement",
    "assertion_reason",
}


# ============================================================
# PAYMENT REQUEST SCHEMA
# ============================================================

class NewsPaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ============================================================
# CATEGORY ALIASES
# ============================================================

CATEGORY_ALIASES = {
    "general": "General",

    "economy": "Economy",
    "economic": "Economy",
    "economics": "Economy",
    "economic affairs": "Economy",
    "finance": "Economy",
    "banking": "Economy",

    "polity": "Polity & Governance",
    "governance": "Polity & Governance",
    "polity & governance": "Polity & Governance",
    "polity and governance": "Polity & Governance",

    "international": "International Relations",
    "international relations": "International Relations",
    "foreign affairs": "International Relations",
    "foreign policy": "International Relations",
    "ir": "International Relations",

    "environment": "Environment",
    "ecology": "Environment",
    "climate": "Environment",

    "science": "Science & Technology",
    "technology": "Science & Technology",
    "science & technology": "Science & Technology",
    "science and technology": "Science & Technology",
    "tech": "Science & Technology",
    "space": "Science & Technology",
    "isro": "Science & Technology",
    "ai": "Science & Technology",
    "artificial intelligence": "Science & Technology",

    "security": "Security",
    "internal security": "Security",
    "defence": "Security",
    "defense": "Security",

    "agriculture": "Agriculture",
    "farming": "Agriculture",

    "education": "Education",

    "health": "Health",
    "healthcare": "Health",

    "social": "Social Issues",
    "social issue": "Social Issues",
    "social issues": "Social Issues",

    "history": "History & Culture",
    "culture": "History & Culture",
    "history & culture": "History & Culture",
    "history and culture": "History & Culture",

    "geography": "Geography",

    "disaster": "Disaster Management",
    "disaster management": "Disaster Management",

    "ethics": "Ethics",
}


# ============================================================
# CATEGORY PROVIDER TERMS
# ============================================================

CATEGORY_QUERY_TERMS = {
    "Economy":
        "economy OR economic OR budget OR finance "
        "OR banking OR GST OR tax OR employment "
        "OR jobs OR investment OR industry OR GDP",

    "Polity & Governance":
        "government OR governance OR polity "
        "OR parliament OR constitution OR court "
        "OR policy OR election OR rights",

    "International Relations":
        "India foreign policy OR diplomacy "
        "OR international OR bilateral OR treaty "
        "OR summit",

    "Environment":
        "environment OR climate OR pollution "
        "OR forest OR biodiversity OR wildlife "
        "OR carbon",

    "Science & Technology":
        "science OR technology OR ISRO OR space "
        "OR AI OR digital OR semiconductor "
        "OR research",

    "Social Issues":
        "education OR health OR poverty OR women "
        "OR child OR welfare OR inclusion",

    "Security":
        "security OR defence OR defense OR cyber "
        "OR border OR military OR terrorism",

    "History & Culture":
        "history OR culture OR heritage OR archaeology "
        "OR monument OR art OR literature",

    "Geography":
        "geography OR river OR soil OR rainfall "
        "OR monsoon OR region",

    "Agriculture":
        "agriculture OR farmer OR farming OR crop "
        "OR irrigation OR MSP",

    "Education":
        "education OR school OR university OR college "
        "OR teacher OR student",

    "Health":
        "health OR healthcare OR disease OR hospital "
        "OR medicine OR public health",

    "Disaster Management":
        "flood OR earthquake OR cyclone OR disaster "
        "OR rescue OR relief OR landslide",

    "Ethics":
        "ethics OR integrity OR transparency "
        "OR accountability OR corruption",
}


# ============================================================
# BIHAR TERMS
# ============================================================

BIHAR_LOCATION_TERMS = {
    "bihar",
    "patna",
    "gaya",
    "muzaffarpur",
    "bhagalpur",
    "darbhanga",
    "nalanda",
    "vaishali",
    "begusarai",
    "purnia",
    "purnea",
    "katihar",
    "araria",
    "kishanganj",
    "saharsa",
    "madhepura",
    "supaul",
    "samastipur",
    "sitamarhi",
    "sheohar",
    "motihari",
    "east champaran",
    "west champaran",
    "bettiah",
    "rohtas",
    "sasaram",
    "buxar",
    "bhojpur",
    "ara",
    "aurangabad",
    "jehanabad",
    "jahanabad",
    "arwal",
    "nawada",
    "jamui",
    "lakhisarai",
    "khagaria",
    "munger",
    "mokama",
    "hajipur",
    "mithila",
    "magadh",
    "seemanchal",
    "kosi",
}

# ============================================================
# SAFE HELPERS
# ============================================================

def _safe_int(
    value: Any,
    default: int = 0,
) -> int:

    if value is None:
        return default

    try:
        return int(float(value))
    except (
        TypeError,
        ValueError,
    ):
        return default


def _safe_bool(
    value: Any,
    default: bool = False,
) -> bool:

    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):

        value = value.strip().lower()

        if value in {
            "true",
            "1",
            "yes",
            "y",
            "on",
        }:
            return True

        if value in {
            "false",
            "0",
            "no",
            "n",
            "off",
            "",
        }:
            return False

    return default


def _clean_text(
    value: Any,
    default: str = "",
) -> str:

    if value is None:
        return default

    try:
        return str(value).strip()
    except Exception:
        return default


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_exam(
    exam: Optional[str],
) -> str:

    value = (
        exam.strip().upper()
        if exam
        else "UPSC"
    )

    if value not in SUPPORTED_EXAMS:

        raise HTTPException(
            status_code=400,
            detail="Invalid exam. Use 'UPSC' or 'BPSC'.",
        )

    return value


def normalize_language(
    language: Optional[str],
) -> str:

    value = (
        language.strip().lower()
        if language
        else "en"
    )

    aliases = {
        "english": "en",
        "hindi": "hi",
    }

    value = aliases.get(
        value,
        value,
    )

    if value not in SUPPORTED_LANGUAGES:

        raise HTTPException(
            status_code=400,
            detail="language must be 'en' or 'hi'",
        )

    return value


def normalize_category(
    category: Optional[str],
) -> Optional[str]:

    if not category:
        return None

    value = category.strip()

    if not value:
        return None

    return CATEGORY_ALIASES.get(
        value.lower(),
        value,
    )


def normalize_article_category(
    category: Any,
) -> str:

    value = _clean_text(category)

    if not value:
        return "General"

    return CATEGORY_ALIASES.get(
        value.lower(),
        value,
    )


def normalize_difficulty(
    difficulty: Optional[str],
) -> Optional[str]:

    if not difficulty:
        return None

    value = difficulty.strip().capitalize()

    if value not in SUPPORTED_DIFFICULTIES:

        raise HTTPException(
            status_code=400,
            detail="difficulty must be Easy, Medium or Hard",
        )

    return value


def normalize_question_type(
    question_type: Optional[str],
) -> str:

    value = (
        question_type.strip().lower()
        if question_type
        else "mcq"
    )

    aliases = {
        # MCQ
        "mcq": "mcq",
        "single_correct": "mcq",
        "single-correct": "mcq",
        "single correct": "mcq",
        "multiple_choice": "mcq",
        "multiple-choice": "mcq",
        "multiple choice": "mcq",

        # Other supported types
        "prelims": "prelims",
        "prelim": "prelims",

        "mains": "mains",

        "statement": "statement",

        "assertion-reason": "assertion_reason",
        "assertion reason": "assertion_reason",
        "assertion_reason": "assertion_reason",
    }

    normalized = aliases.get(
        value,
        value,
    )

    if normalized not in SUPPORTED_QUESTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid question_type. "
                "Use 'prelims', 'mains', 'mcq', "
                "'multiple_choice', 'statement' "
                "or 'assertion_reason'."
            ),
        )

    return normalized

# ============================================================
# PAYMENT ACCESS
# ============================================================

def _check_news_access(
    db: Session,
    current_user: Any,
) -> None:

    if not current_user:

        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    user_id = getattr(
        current_user,
        "id",
        None,
    )

    if not user_id:

        raise HTTPException(
            status_code=401,
            detail="Invalid authenticated user.",
        )

    require_news_access(
        db=db,
        user_id=user_id,
    )


# ============================================================
# DATETIME
# ============================================================

def parse_published_at(
    value: Any,
) -> Optional[datetime]:

    if value is None:
        return None

    if isinstance(value, datetime):

        if value.tzinfo is not None:

            value = (
                value
                .astimezone(timezone.utc)
                .replace(tzinfo=None)
            )

        return value

    if isinstance(value, str):

        value = value.strip()

        if not value:
            return None

        normalized = value

        if normalized.endswith("Z"):

            normalized = (
                normalized[:-1]
                + "+00:00"
            )

        try:

            parsed = datetime.fromisoformat(
                normalized
            )

            if parsed.tzinfo is not None:

                parsed = (
                    parsed
                    .astimezone(timezone.utc)
                    .replace(tzinfo=None)
                )

            return parsed

        except ValueError:
            pass

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
        ]

        for fmt in formats:

            try:

                return datetime.strptime(
                    value,
                    fmt,
                )

            except ValueError:
                continue

    return None


# ============================================================
# BIHAR DETECTION
# ============================================================

def is_bihar_article(
    article: dict[str, Any],
) -> bool:

    if _safe_bool(
        article.get("bihar_relevant"),
        False,
    ):
        return True

    if _safe_int(
        article.get("bihar_score"),
        0,
    ) >= 20:
        return True

    title = _clean_text(
        article.get("title")
    ).lower()

    description = _clean_text(
        article.get("description")
    ).lower()

    content = _clean_text(
        article.get("content")
    ).lower()

    text = (
        f"{title} "
        f"{description} "
        f"{content}"
    )

    return any(
        term in text
        for term in BIHAR_LOCATION_TERMS
    )


# ============================================================
# EXAM RELEVANCE
# ============================================================

def is_bpsc_article(
    article: dict[str, Any],
) -> bool:

    relevance = _clean_text(
        article.get("bpsc_relevance")
    ).lower()

    exam = _clean_text(
        article.get("exam")
    ).upper()

    score = _safe_int(
        article.get("bpsc_score"),
        0,
    )

    if relevance in {
        "high",
        "medium",
    }:
        return True

    if exam == "BPSC":
        return True

    if score >= 25:
        return True

    return False


def is_upsc_article(
    article: dict[str, Any],
) -> bool:

    relevance = _clean_text(
        article.get("upsc_relevance")
    ).lower()

    exam = _clean_text(
        article.get("exam")
    ).upper()

    score = _safe_int(
        article.get("relevance_score"),
        0,
    )

    if relevance in {
        "high",
        "medium",
    }:
        return True

    if exam == "UPSC":
        return True

    if not relevance and score >= 25:
        return True

    return False


# ============================================================
# HARD FILTER
# ============================================================

def article_is_eligible(
    article: dict[str, Any],
    exam: str,
    category: Optional[str],
    bihar_only: bool,
) -> bool:

    if category:

        wanted = normalize_category(
            category
        )

        actual = normalize_article_category(
            article.get("category")
        )

        if (
            not wanted
            or actual.lower()
            != wanted.lower()
        ):
            return False

    if bihar_only:

        if not is_bihar_article(article):
            return False

    if exam == "BPSC":

        if not is_bpsc_article(article):
            return False

    elif exam == "UPSC":

        if not is_upsc_article(article):
            return False

    return True


def apply_hard_filters(
    articles: list[dict[str, Any]],
    exam: str,
    category: Optional[str],
    bihar_only: bool,
) -> list[dict[str, Any]]:

    return [
        article
        for article in articles
        if isinstance(article, dict)
        and article_is_eligible(
            article=article,
            exam=exam,
            category=category,
            bihar_only=bihar_only,
        )
    ]


# ============================================================
# PROVIDER QUERY
# ============================================================

def build_provider_query(
    q: str,
    category: Optional[str],
    bihar_only: bool,
) -> str:

    q = (q or "").strip()

    if not q:
        q = "India"

    if q.lower() == "india":

        parts = [
            "India"
        ]

    elif "india" in q.lower():

        parts = [
            q
        ]

    else:

        parts = [
            q,
            "India",
        ]

    if (
        bihar_only
        and "bihar" not in q.lower()
    ):
        parts.append("Bihar")

    if category:

        terms = CATEGORY_QUERY_TERMS.get(
            category
        )

        if terms:

            parts.append(
                f"({terms})"
            )

    return " ".join(parts)


# ============================================================
# ORM → DICT
# ============================================================

def article_to_dict(
    article: CurrentAffair,
) -> dict[str, Any]:

    return {
        "id": article.id,

        "title": _clean_text(
            article.title
        ),

        "description": (
            _clean_text(
                article.description
            )
            or None
        ),

        "url": (
            _clean_text(
                article.url
            )
            or None
        ),

        "source": (
            _clean_text(
                article.source
            )
            or None
        ),

        "image_url": (
            _clean_text(
                article.image_url
            )
            or None
        ),

        "published_at":
            article.published_at,

        "language": (
            _clean_text(
                article.language,
                "en",
            ).lower()
        ),

        "exam": (
            _clean_text(
                article.exam,
                "UPSC",
            ).upper()
        ),

        "category":
            normalize_article_category(
                article.category
            ),

        "importance": _clean_text(
            article.importance,
            "Low",
        ),

        "exam_relevance": _clean_text(
            article.exam_relevance,
            "Low",
        ),

        "upsc_relevance": _clean_text(
            article.upsc_relevance,
            "Low",
        ),

        "bpsc_relevance": _clean_text(
            article.bpsc_relevance,
            "Low",
        ),

        "bihar_relevant":
            bool(article.bihar_relevant),

        "prelims_relevant":
            bool(article.prelims_relevant),

        "mains_relevant":
            bool(article.mains_relevant),

        "syllabus": {
            "prelims": [],
            "mains": [],
        },

        "relevance_score":
            _safe_int(
                article.relevance_score
            ),

        "query_score":
            _safe_int(
                article.query_score
            ),

        "engine_score":
            _safe_int(
                article.engine_score
            ),

        "freshness_score":
            _safe_int(
                article.freshness_score
            ),

        "final_score":
            _safe_int(
                article.final_score
            ),

        "is_noise":
            bool(article.is_noise),
    }


# ============================================================
# UPSERT
# ============================================================

def _upsert_current_affair(
    db: Session,
    article: dict[str, Any],
    language: str,
    requested_exam: Optional[str] = None,
) -> CurrentAffair:

    url = (
        _clean_text(
            article.get("url")
        )
        or None
    )

    language = (
        _clean_text(
            language,
            "en",
        ).lower()
    )

    if language not in SUPPORTED_LANGUAGES:
        language = "en"

    exam = normalize_exam(
        requested_exam
        or article.get("exam")
        or "UPSC"
    )

    category = normalize_article_category(
        article.get("category")
    )

    existing = None

    if url:

        existing = (
            db.query(CurrentAffair)
            .filter(
                CurrentAffair.url == url
            )
            .first()
        )

    data = {
        "title":
            _clean_text(
                article.get("title")
            ),

        "description":
            _clean_text(
                article.get("description")
            ),

        "content":
            _clean_text(
                article.get("content")
            ),

        "url": url,

        "source":
            _clean_text(
                article.get("source"),
                "Unknown",
            ),

        "image_url": (
            _clean_text(
                article.get("image_url")
            )
            or None
        ),

        "published_at":
            parse_published_at(
                article.get(
                    "published_at"
                )
            ),

        "exam": exam,

        "category": category,

        "subject": (
            _clean_text(
                article.get("subject")
            )
            or None
        ),

        "importance":
            _clean_text(
                article.get("importance"),
                "Medium",
            ),

        "exam_relevance":
            _clean_text(
                article.get("exam_relevance"),
                "Low",
            ),

        "upsc_relevance":
            _clean_text(
                article.get("upsc_relevance"),
                "Low",
            ),

        "bpsc_relevance":
            _clean_text(
                article.get("bpsc_relevance"),
                "Low",
            ),

        "prelims_relevant":
            _safe_bool(
                article.get(
                    "prelims_relevant"
                )
            ),

        "mains_relevant":
            _safe_bool(
                article.get(
                    "mains_relevant"
                )
            ),

        "bihar_relevant":
            _safe_bool(
                article.get(
                    "bihar_relevant"
                )
            ),

        "relevance_score":
            _safe_int(
                article.get(
                    "relevance_score"
                )
            ),

        "query_score":
            _safe_int(
                article.get(
                    "query_score"
                )
            ),

        "engine_score":
            _safe_int(
                article.get(
                    "engine_score"
                )
            ),

        "freshness_score":
            _safe_int(
                article.get(
                    "freshness_score"
                )
            ),

        "final_score":
            _safe_int(
                article.get(
                    "final_score"
                )
            ),

        "is_noise":
            _safe_bool(
                article.get(
                    "is_noise"
                )
            ),

        "bpsc_score":
            _safe_int(
                article.get(
                    "bpsc_score"
                )
            ),

        "bihar_score":
            _safe_int(
                article.get(
                    "bihar_score"
                )
            ),

        "summary": (
            _clean_text(
                article.get("summary")
            )
            or None
        ),

        "language": language,
    }

    valid_data = {}

    for field, value in data.items():

        if hasattr(
            CurrentAffair,
            field,
        ):
            valid_data[field] = value

    if existing:

        for field, value in valid_data.items():

            if (
                field == "title"
                and not value
            ):
                continue

            setattr(
                existing,
                field,
                value,
            )

        return existing

    news = CurrentAffair(
        **valid_data
    )

    db.add(news)
    db.flush()

    return news


# ============================================================
# PAYMENT — CREATE ORDER
# ============================================================

@router.post(
    "/payment/create-order"
)
def create_news_payment_order(
    db: Session = Depends(get_db),
    current_user=Depends(
        get_current_user
    ),
):

    if not current_user:

        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    return create_news_order(
        db=db,
        user_id=current_user.id,
    )


# ============================================================
# PAYMENT — VERIFY
# ============================================================

@router.post(
    "/payment/verify"
)
def verify_news_payment_endpoint(

    request: NewsPaymentVerifyRequest = Body(...),

    # Query fallback भी रखा गया है ताकि
    # पुराना frontend भी काम कर सके।
    razorpay_order_id: Optional[str] = Query(
        None
    ),

    razorpay_payment_id: Optional[str] = Query(
        None
    ),

    razorpay_signature: Optional[str] = Query(
        None
    ),

    db: Session = Depends(get_db),

    current_user=Depends(
        get_current_user
    ),
):

    if not current_user:

        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    # --------------------------------------------------------
    # BODY को प्राथमिकता
    # --------------------------------------------------------

    order_id = (
        _clean_text(
            request.razorpay_order_id
        )
        or _clean_text(
            razorpay_order_id
        )
    )

    payment_id = (
        _clean_text(
            request.razorpay_payment_id
        )
        or _clean_text(
            razorpay_payment_id
        )
    )

    signature = (
        _clean_text(
            request.razorpay_signature
        )
        or _clean_text(
            razorpay_signature
        )
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not order_id:

        raise HTTPException(
            status_code=422,
            detail="razorpay_order_id is required.",
        )

    if not payment_id:

        raise HTTPException(
            status_code=422,
            detail="razorpay_payment_id is required.",
        )

    if not signature:

        raise HTTPException(
            status_code=422,
            detail="razorpay_signature is required.",
        )

    # --------------------------------------------------------
    # VERIFY PAYMENT
    # --------------------------------------------------------

    try:

        result = verify_news_payment(
            db=db,
            user_id=current_user.id,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature=signature,
        )

        return result

    except HTTPException:
        raise

    except ValueError as exc:

        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        db.rollback()

        logger.exception(
            "News payment verification failed"
        )

        raise HTTPException(
            status_code=500,
            detail="Payment verification failed.",
        ) from exc


# ============================================================
# INTERNAL SEARCH IMPLEMENTATION
# ============================================================

async def _search_news_internal(
    q: str,
    page: int,
    page_size: int,
    language: str,
    exam: str,
    category: Optional[str],
    bihar_only: bool,
    db: Session,
):

    q = (q or "").strip()

    if not q:
        q = "India"

    language = normalize_language(
        language
    )

    exam = normalize_exam(
        exam
    )

    category = normalize_category(
        category
    )

    provider_query = build_provider_query(
        q=q,
        category=category,
        bihar_only=bihar_only,
    )

    provider_page_size = min(
        max(
            page_size * 5,
            50,
        ),
        100,
    )

    # --------------------------------------------------------
    # PROVIDER
    # --------------------------------------------------------

    try:

        raw_result = await fetch_news(
            query=provider_query,
            language=language,
            page=1,
            page_size=provider_page_size,
            use_cache=True,
        )

    except Exception:

        logger.exception(
            "News provider failed"
        )

        return _database_fallback(
            db=db,
            q=q,
            page=page,
            page_size=page_size,
            language=language,
            exam=exam,
            category=category,
            bihar_only=bihar_only,
        )

    # --------------------------------------------------------
    # EXTRACT
    # --------------------------------------------------------

    if isinstance(
        raw_result,
        dict,
    ):

        raw_articles = (
            raw_result.get(
                "articles",
                [],
            )
            or []
        )

        raw_total = _safe_int(
            raw_result.get(
                "totalResults",
                raw_result.get(
                    "total_results",
                    len(raw_articles),
                ),
            ),
            len(raw_articles),
        )

    elif isinstance(
        raw_result,
        list,
    ):

        raw_articles = raw_result
        raw_total = len(
            raw_articles
        )

    else:

        raw_articles = []
        raw_total = 0

    raw_articles = [
        article
        for article in raw_articles
        if isinstance(
            article,
            dict,
        )
    ]

    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------

    try:

        try:

            classified = classify_news_list(
                raw_articles,
                exam=exam,
            )

        except TypeError:

            classified = classify_news_list(
                raw_articles
            )

    except Exception:

        logger.exception(
            "Classification failed"
        )

        classified = raw_articles

    if not isinstance(
        classified,
        list,
    ):
        classified = []

    classified = [
        item
        for item in classified
        if isinstance(
            item,
            dict,
        )
    ]

    # --------------------------------------------------------
    # HARD FILTER
    # --------------------------------------------------------

    classified = apply_hard_filters(
        articles=classified,
        exam=exam,
        category=category,
        bihar_only=bihar_only,
    )

    # --------------------------------------------------------
    # FILTER SERVICE
    # --------------------------------------------------------

    try:

        try:

            filtered = filter_news(
                classified,
                min_score=0,
                exam=exam,
                bihar_only=bihar_only,
                already_classified=True,
            )

        except TypeError:

            filtered = filter_news(
                classified,
                min_score=0,
            )

    except Exception:

        logger.exception(
            "News filtering failed"
        )

        filtered = classified

    if not isinstance(
        filtered,
        list,
    ):
        filtered = []

    filtered = [
        article
        for article in filtered
        if isinstance(
            article,
            dict,
        )
    ]

    # --------------------------------------------------------
    # FINAL HARD FILTER
    # --------------------------------------------------------

    filtered = apply_hard_filters(
        articles=filtered,
        exam=exam,
        category=category,
        bihar_only=bihar_only,
    )

    # --------------------------------------------------------
    # RANK
    # --------------------------------------------------------

    try:

        ranked = rank_news(
            filtered
        )

        if isinstance(
            ranked,
            list,
        ):
            filtered = ranked

    except Exception:

        logger.exception(
            "News ranking failed"
        )

    # --------------------------------------------------------
    # SAFETY FILTER
    # --------------------------------------------------------

    filtered = apply_hard_filters(
        articles=filtered,
        exam=exam,
        category=category,
        bihar_only=bihar_only,
    )

    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    total_filtered = len(
        filtered
    )

    start = (
        (page - 1)
        * page_size
    )

    paginated = filtered[
        start:start + page_size
    ]

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    saved_articles = []

    for article in paginated:

        try:

            saved_article = (
                _upsert_current_affair(
                    db=db,
                    article=article,
                    language=language,
                    requested_exam=exam,
                )
            )

            saved_articles.append(
                saved_article
            )

        except IntegrityError:

            db.rollback()

            logger.warning(
                "Integrity error saving news"
            )

        except Exception:

            db.rollback()

            logger.exception(
                "Failed saving article"
            )

    if saved_articles:

        try:

            db.commit()

        except Exception:

            db.rollback()

            logger.exception(
                "News commit failed"
            )

            saved_articles = []

    for article in saved_articles:

        try:
            db.refresh(article)
        except Exception:
            pass

    return {
        "status": "success",
        "query": q,
        "language": language,
        "exam": exam,
        "category": category,
        "bihar_only": bihar_only,
        "page": page,
        "page_size": page_size,
        "raw_total_results": raw_total,
        "raw_articles": len(raw_articles),
        "filtered_results": total_filtered,
        "returned_results": len(saved_articles),
        "total": total_filtered,
        "saved_results": len(saved_articles),
        "articles": [
            article_to_dict(article)
            for article in saved_articles
        ],
    }


# ============================================================
# SEARCH
# ============================================================

@router.get(
    "/search",
    response_model=NewsSearchResponse,
)
async def search_news(

    q: str = Query(
        "India",
        min_length=1,
        max_length=200,
    ),

    page: int = Query(
        1,
        ge=1,
    ),

    page_size: int = Query(
        20,
        ge=1,
        le=100,
    ),

    language: str = Query(
        "en"
    ),

    exam: Optional[str] = Query(
        None
    ),

    category: Optional[str] = Query(
        None
    ),

    bihar_only: bool = Query(
        False
    ),

    db: Session = Depends(
        get_db
    ),

    current_user=Depends(
        get_current_user
    ),
):

    _check_news_access(
        db=db,
        current_user=current_user,
    )

    return await _search_news_internal(
        q=q,
        page=page,
        page_size=page_size,
        language=language,
        exam=normalize_exam(exam),
        category=category,
        bihar_only=bihar_only,
        db=db,
    )


# ============================================================
# UPSC SHORTCUT
# ============================================================

@router.get(
    "/upsc",
    response_model=NewsSearchResponse,
)
async def get_upsc_news(

    q: str = Query(
        "India",
        min_length=1,
        max_length=200,
    ),

    page: int = Query(
        1,
        ge=1,
    ),

    page_size: int = Query(
        20,
        ge=1,
        le=100,
    ),

    language: str = Query(
        "en"
    ),

    category: Optional[str] = Query(
        None
    ),

    bihar_only: bool = Query(
        False
    ),

    db: Session = Depends(
        get_db
    ),

    current_user=Depends(
        get_current_user
    ),
):

    _check_news_access(
        db=db,
        current_user=current_user,
    )

    return await _search_news_internal(
        q=q,
        page=page,
        page_size=page_size,
        language=language,
        exam="UPSC",
        category=category,
        bihar_only=bihar_only,
        db=db,
    )


# ============================================================
# BPSC SHORTCUT
# ============================================================

@router.get(
    "/bpsc",
    response_model=NewsSearchResponse,
)
async def get_bpsc_news(

    q: str = Query(
        "India",
        min_length=1,
        max_length=200,
    ),

    page: int = Query(
        1,
        ge=1,
    ),

    page_size: int = Query(
        20,
        ge=1,
        le=100,
    ),

    language: str = Query(
        "en"
    ),

    category: Optional[str] = Query(
        None
    ),

    bihar_only: bool = Query(
        False
    ),

    db: Session = Depends(
        get_db
    ),

    current_user=Depends(
        get_current_user
    ),
):

    _check_news_access(
        db=db,
        current_user=current_user,
    )

    return await _search_news_internal(
        q=q,
        page=page,
        page_size=page_size,
        language=language,
        exam="BPSC",
        category=category,
        bihar_only=bihar_only,
        db=db,
    )


# ============================================================
# DATABASE FALLBACK
# ============================================================

def _database_fallback(
    db: Session,
    q: str,
    page: int,
    page_size: int,
    language: str,
    exam: Optional[str],
    category: Optional[str],
    bihar_only: bool,
):

    query = db.query(
        CurrentAffair
    )

    query = query.filter(
        CurrentAffair.language
        == language
    )

    if exam:

        query = query.filter(
            CurrentAffair.exam
            == exam
        )

    if category:

        query = query.filter(
            CurrentAffair.category
            == category
        )

    pattern = f"%{q}%"

    search_filters = [
        CurrentAffair.title.ilike(
            pattern
        )
    ]

    if hasattr(
        CurrentAffair,
        "description",
    ):

        search_filters.append(
            CurrentAffair.description.ilike(
                pattern
            )
        )

    if hasattr(
        CurrentAffair,
        "content",
    ):

        search_filters.append(
            CurrentAffair.content.ilike(
                pattern
            )
        )

    query = query.filter(
        or_(*search_filters)
    )

    articles = (
        query
        .order_by(
            CurrentAffair.id.desc()
        )
        .all()
    )

    if bihar_only:

        articles = [
            article
            for article in articles
            if is_bihar_article(
                article_to_dict(
                    article
                )
            )
        ]

    total = len(
        articles
    )

    start = (
        (page - 1)
        * page_size
    )

    paginated = articles[
        start:start + page_size
    ]

    return {
        "status": "success",
        "query": q,
        "language": language,
        "exam": exam,
        "category": category,
        "bihar_only": bihar_only,
        "page": page,
        "page_size": page_size,
        "raw_total_results": total,
        "raw_articles": total,
        "filtered_results": total,
        "returned_results": len(paginated),
        "total": total,
        "saved_results": 0,
        "articles": [
            article_to_dict(
                article
            )
            for article in paginated
        ],
        "fallback": True,
    }


# ============================================================
# PRACTICE MCQs
# ============================================================

@router.get(
    "/mcqs/practice",
    response_model=MCQPracticeResponse,
)
def practice_mcqs(

    exam: str = Query(
        "UPSC"
    ),

    language: str = Query(
        "en"
    ),

    difficulty: Optional[str] = Query(
        None
    ),

    limit: int = Query(
        10,
        ge=1,
        le=50,
    ),

    db: Session = Depends(
        get_db
    ),

    current_user=Depends(
        get_current_user
    ),
):

    _check_news_access(
        db=db,
        current_user=current_user,
    )

    exam = normalize_exam(
        exam
    )

    language = normalize_language(
        language
    )

    difficulty = normalize_difficulty(
        difficulty
    )

    query = (
        db.query(MCQ)
        .filter(
            MCQ.exam == exam,
            MCQ.language == language,
            MCQ.is_active.is_(True),
        )
    )

    if difficulty:

        query = query.filter(
            MCQ.difficulty
            == difficulty
        )

    questions = (
        query
        .order_by(
            func.random()
        )
        .limit(limit)
        .all()
    )

    return {
        "status": "success",
        "exam": exam,
        "language": language,
        "total": len(questions),
        "questions": [
            mcq_to_dict(
                question
            )
            for question in questions
        ],
    }


# ============================================================
# ARTICLE MCQs
# ============================================================

@router.get(
    "/{article_id}/mcqs",
    response_model=NewsMCQListResponse,
)
def get_article_mcqs(
    article_id: int,

    exam: str = Query(
        "UPSC"
    ),

    language: str = Query(
        "en"
    ),

    difficulty: Optional[str] = Query(
        None
    ),

    db: Session = Depends(
        get_db
    ),

    current_user=Depends(
        get_current_user
    ),
):
    # ------------------------------------------------------------
    # NEWS ACCESS CHECK
    # ------------------------------------------------------------

    _check_news_access(
        db=db,
        current_user=current_user,
    )

    # ------------------------------------------------------------
    # VALIDATE ARTICLE ID
    # ------------------------------------------------------------

    if article_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid article ID",
        )

    # ------------------------------------------------------------
    # NORMALIZE FILTERS
    # ------------------------------------------------------------

    exam = normalize_exam(
        exam
    )

    language = normalize_language(
        language
    )

    difficulty = normalize_difficulty(
        difficulty
    )

    # ------------------------------------------------------------
    # CHECK ARTICLE EXISTS
    # ------------------------------------------------------------

    article = (
        db.query(CurrentAffair)
        .filter(
            CurrentAffair.id == article_id
        )
        .first()
    )

    if not article:
        raise HTTPException(
            status_code=404,
            detail="News article not found",
        )

    # ------------------------------------------------------------
    # GET EXISTING MCQs
    # ------------------------------------------------------------

    query = (
        db.query(MCQ)
        .filter(
            MCQ.current_affair_id == article_id,

            MCQ.exam == exam,

            MCQ.language == language,

            MCQ.is_active.is_(True),
        )
    )

    # ------------------------------------------------------------
    # DIFFICULTY FILTER
    # ------------------------------------------------------------

    if difficulty:
        query = query.filter(
            MCQ.difficulty == difficulty
        )

    # ------------------------------------------------------------
    # FETCH
    # ------------------------------------------------------------

    questions = (
        query
        .order_by(
            MCQ.id.asc()
        )
        .all()
    )

    # ------------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------------

    return {
        "status": "success",

        "total": len(
            questions
        ),

        "mcqs": [
            mcq_to_dict(
                question
            )
            for question in questions
        ],
    }
# ============================================================
# GENERATE ARTICLE MCQs
# ============================================================

@router.post(
    "/{article_id}/mcqs/generate",
    response_model=MCQGenerateResponse,
)
async def generate_article_mcqs(
    article_id: int,
    request: MCQGenerateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Generate AI MCQs from a CurrentAffair article.

    MCQ generation is FREE.
    No ₹1 news-payment check is applied here.

    Endpoint:
        POST /news/{article_id}/mcqs/generate
    """

    # ========================================================
    # AUTHENTICATION
    # ========================================================

    # current_user dependency keeps this endpoint authenticated.
    # IMPORTANT:
    # _check_news_access() is intentionally NOT called here.
    #
    # Therefore MCQ generation does NOT require the ₹1 payment.

    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    # ========================================================
    # ARTICLE ID VALIDATION
    # ========================================================

    if article_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid article ID.",
        )

    # ========================================================
    # GET ARTICLE
    # ========================================================

    article = (
        db.query(CurrentAffair)
        .filter(
            CurrentAffair.id == article_id
        )
        .first()
    )

    if article is None:
        raise HTTPException(
            status_code=404,
            detail="News article not found.",
        )

    # ========================================================
    # NORMALIZE REQUEST
    # ========================================================

    try:
        exam = normalize_exam(
            getattr(
                request,
                "exam",
                None,
            )
            or "UPSC"
        )

        language = normalize_language(
            getattr(
                request,
                "language",
                None,
            )
            or "en"
        )

        difficulty = normalize_difficulty(
            getattr(
                request,
                "difficulty",
                None,
            )
            or "Medium"
        )

        question_type = normalize_question_type(
            getattr(
                request,
                "question_type",
                None,
            )
            or "single_correct"
        )

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "MCQ request normalization failed | article=%s",
            article_id,
        )

        raise HTTPException(
            status_code=422,
            detail="Invalid MCQ generation request.",
        ) from exc

    # ========================================================
    # COUNT
    # ========================================================

    try:
        count = _safe_int(
            getattr(
                request,
                "count",
                5,
            ),
            5,
        )

    except Exception:
        count = 5

    if count < 1 or count > 20:
        raise HTTPException(
            status_code=400,
            detail="count must be between 1 and 20.",
        )

    # ========================================================
    # ARTICLE CONTENT
    # ========================================================

    title = _clean_text(
        getattr(
            article,
            "title",
            None,
        )
    )

    description = _clean_text(
        getattr(
            article,
            "description",
            None,
        )
    )

    content = _clean_text(
        getattr(
            article,
            "content",
            None,
        )
    )

    summary = _clean_text(
        getattr(
            article,
            "summary",
            None,
        )
    )

    article_text = " ".join(
        part
        for part in [
            title,
            description,
            content,
            summary,
        ]
        if part
    ).strip()

    if not article_text:
        raise HTTPException(
            status_code=422,
            detail=(
                "This news article does not contain "
                "enough content to generate MCQs."
            ),
        )

    # ========================================================
    # LOG REQUEST
    # ========================================================

    logger.info(
        (
            "FREE MCQ generation started | "
            "article=%s | user=%s | exam=%s | "
            "language=%s | difficulty=%s | "
            "count=%s | type=%s"
        ),
        article_id,
        getattr(current_user, "id", None),
        exam,
        language,
        difficulty,
        count,
        question_type,
    )

    # ========================================================
    # GENERATE MCQs
    # ========================================================

    try:

        result = generate_mcqs(
            db=db,
            article=article,
            exam=exam,
            language=language,
            count=count,
            difficulty=difficulty or "Medium",
            question_type=question_type,
        )

        # ----------------------------------------------------
        # SUPPORT SYNC + ASYNC SERVICE
        # ----------------------------------------------------

        if inspect.isawaitable(result):
            questions = await result
        else:
            questions = result

        # ----------------------------------------------------
        # VALIDATE RESULT
        # ----------------------------------------------------

        if questions is None:

            db.rollback()

            raise HTTPException(
                status_code=422,
                detail="AI returned no MCQs.",
            )

        if not isinstance(
            questions,
            (list, tuple),
        ):

            db.rollback()

            logger.error(
                (
                    "Invalid MCQ service response | "
                    "type=%s | article=%s"
                ),
                type(questions).__name__,
                article_id,
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "MCQ generation service returned "
                    "an invalid response."
                ),
            )

        questions = list(questions)

        if not questions:

            db.rollback()

            raise HTTPException(
                status_code=422,
                detail=(
                    "AI could not generate valid MCQs "
                    "from this article."
                ),
            )

        # ====================================================
        # COMMIT
        # ====================================================

        db.commit()

        # ====================================================
        # REFRESH
        # ====================================================

        refreshed_questions = []

        for question in questions:

            try:

                db.refresh(question)

                refreshed_questions.append(
                    question
                )

            except Exception:

                logger.warning(
                    (
                        "Could not refresh generated MCQ "
                        "| article=%s"
                    ),
                    article_id,
                )

                refreshed_questions.append(
                    question
                )

        questions = refreshed_questions

        # ====================================================
        # SERIALIZE
        # ====================================================

        serialized_questions = []

        for question in questions:

            try:

                serialized = mcq_to_dict(
                    question
                )

                if serialized:
                    serialized_questions.append(
                        serialized
                    )

            except Exception:

                logger.exception(
                    (
                        "Failed to serialize MCQ "
                        "| article=%s"
                    ),
                    article_id,
                )

        if not serialized_questions:

            logger.error(
                (
                    "MCQs generated but serialization "
                    "returned empty result | article=%s"
                ),
                article_id,
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    "MCQs were generated but could "
                    "not be returned."
                ),
            )

        # ====================================================
        # SUCCESS
        # ====================================================

        logger.info(
            (
                "FREE MCQ generation successful | "
                "article=%s | generated=%s"
            ),
            article_id,
            len(serialized_questions),
        )

        return {
            "status": "success",
            "current_affair_id": article.id,
            "generated": len(
                serialized_questions
            ),
            "questions": serialized_questions,
        }

    # ========================================================
    # HTTP EXCEPTION
    # ========================================================

    except HTTPException:

        db.rollback()
        raise

    # ========================================================
    # VALIDATION / VALUE ERROR
    # ========================================================

    except ValueError as exc:

        db.rollback()

        logger.warning(
            (
                "MCQ generation validation error | "
                "article=%s | error=%s"
            ),
            article_id,
            str(exc),
        )

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    # ========================================================
    # DATABASE INTEGRITY ERROR
    # ========================================================

    except IntegrityError as exc:

        db.rollback()

        logger.exception(
            (
                "MCQ database integrity error | "
                "article=%s"
            ),
            article_id,
        )

        raise HTTPException(
            status_code=409,
            detail=(
                "MCQs could not be saved because "
                "of a database constraint."
            ),
        ) from exc

    # ========================================================
    # OTHER ERROR
    # ========================================================

    except Exception as exc:

        db.rollback()

        logger.exception(
            (
                "FREE MCQ generation failed | "
                "article=%s | exam=%s | "
                "language=%s | difficulty=%s"
            ),
            article_id,
            exam,
            language,
            difficulty,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "MCQ generation failed. "
                "Check backend logs for details."
            ),
        ) from exc
# ============================================================
# SINGLE ARTICLE
# ALWAYS LAST
# ============================================================

@router.get(
    "/{article_id}",
    response_model=NewsArticle,
)
def get_news(

    article_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user=Depends(
        get_current_user
    ),
):

    _check_news_access(
        db=db,
        current_user=current_user,
    )

    if article_id <= 0:

        raise HTTPException(
            status_code=400,
            detail="Invalid article ID",
        )

    article = (
        db.query(CurrentAffair)
        .filter(
            CurrentAffair.id
            == article_id
        )
        .first()
    )

    if not article:

        raise HTTPException(
            status_code=404,
            detail="News article not found",
        )

    return article_to_dict(
        article
    )

