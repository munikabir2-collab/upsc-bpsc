# app/services/news_scoring.py

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


# ============================================================
# SCORE LIMITS
# ============================================================

MAX_SCORE = 100

TITLE_WEIGHT = 25
DESCRIPTION_WEIGHT = 15
KEYWORD_WEIGHT = 20
EXAM_WEIGHT = 20
FRESHNESS_WEIGHT = 10
SOURCE_WEIGHT = 10


# ============================================================
# EXAM KEYWORDS
# ============================================================

UPSC_KEYWORDS = {
    "constitution",
    "parliament",
    "supreme court",
    "high court",
    "fundamental rights",
    "directive principles",
    "governance",
    "policy",
    "cabinet",
    "lok sabha",
    "rajya sabha",
    "election commission",
    "finance commission",
    "niti aayog",
    "economy",
    "inflation",
    "gdp",
    "fiscal policy",
    "monetary policy",
    "banking",
    "rbi",
    "sebi",
    "environment",
    "climate change",
    "biodiversity",
    "pollution",
    "renewable energy",
    "science",
    "technology",
    "artificial intelligence",
    "space",
    "isro",
    "defence",
    "military",
    "international relations",
    "diplomacy",
    "united nations",
    "world bank",
    "imf",
    "geopolitics",
}


BPSC_KEYWORDS = {
    "bihar",
    "patna",
    "bihar government",
    "bihar cabinet",
    "bihar assembly",
    "bihar legislature",
    "bihar budget",
    "bihar economy",
    "bihar development",
    "bihar education",
    "bihar health",
    "bihar agriculture",
    "bihar irrigation",
    "bihar industry",
    "bihar employment",
    "bihar scheme",
    "bihar yojana",
    "bihar police",
    "bihar administration",
    "bihar panchayat",
    "bihar election",
    "bihar infrastructure",
    "bihar flood",
    "bihar drought",
    "bihar river",
    "ganga",
    "kosi",
    "gandak",
    "son river",
    "nitish kumar",
    "bihar chief minister",
}


BIHAR_KEYWORDS = {
    "bihar",
    "patna",
    "gaya",
    "muzaffarpur",
    "bhagalpur",
    "darbhanga",
    "purnia",
    "begusarai",
    "nalanda",
    "vaishali",
    "aurangabad",
    "bhojpur",
    "rohtas",
    "sitamarhi",
    "madhubani",
    "samastipur",
    "saran",
    "chapra",
    "motihari",
    "east champaran",
    "west champaran",
    "nitish kumar",
    "bihar government",
}


# ============================================================
# IMPORTANT SOURCES
# ============================================================

HIGH_QUALITY_SOURCES = {
    "the hindu",
    "indian express",
    "pib",
    "press information bureau",
    "prs india",
    "rajya sabha",
    "lok sabha",
    "ministry of finance",
    "ministry of home affairs",
    "ministry of defence",
    "ministry of environment",
    "niti aayog",
    "rbi",
    "sebi",
    "supreme court",
    "isro",
}


MEDIUM_QUALITY_SOURCES = {
    "times of india",
    "hindustan times",
    "business standard",
    "economic times",
    "ndtv",
    "news18",
    "the indian express",
    "deccan herald",
    "telegraph india",
}


# ============================================================
# NOISE KEYWORDS
# ============================================================

NOISE_KEYWORDS = {
    "celebrity",
    "bollywood",
    "hollywood",
    "movie review",
    "box office",
    "tv serial",
    "entertainment",
    "viral video",
    "trending video",
    "fashion",
    "lifestyle",
    "cricket score",
    "match result",
    "ipl",
    "football score",
    "horoscope",
    "astrology",
    "recipe",
    "shopping",
    "discount",
    "sale",
}


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(value: Any) -> str:

    if value is None:
        return ""

    text = str(value).strip().lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


def build_article_text(
    article: dict[str, Any],
) -> str:

    title = normalize_text(
        article.get("title")
    )

    description = normalize_text(
        article.get("description")
    )

    category = normalize_text(
        article.get("category")
    )

    source = normalize_text(
        article.get("source")
    )

    return " ".join(
        part
        for part in [
            title,
            description,
            category,
            source,
        ]
        if part
    )


# ============================================================
# KEYWORD MATCHING
# ============================================================

def keyword_matches(
    text: str,
    keywords: set[str],
) -> list[str]:

    matches: list[str] = []

    for keyword in keywords:

        keyword = normalize_text(
            keyword
        )

        if not keyword:
            continue

        if keyword in text:
            matches.append(keyword)

    return sorted(
        set(matches)
    )


# ============================================================
# TITLE SCORE
# ============================================================

def calculate_title_score(
    article: dict[str, Any],
    keywords: set[str],
) -> int:

    title = normalize_text(
        article.get("title")
    )

    if not title:
        return 0

    matches = keyword_matches(
        title,
        keywords,
    )

    if not matches:
        return 0

    return min(
        TITLE_WEIGHT,
        len(matches) * 8,
    )


# ============================================================
# DESCRIPTION SCORE
# ============================================================

def calculate_description_score(
    article: dict[str, Any],
    keywords: set[str],
) -> int:

    description = normalize_text(
        article.get("description")
    )

    if not description:
        return 0

    matches = keyword_matches(
        description,
        keywords,
    )

    if not matches:
        return 0

    return min(
        DESCRIPTION_WEIGHT,
        len(matches) * 3,
    )


# ============================================================
# KEYWORD SCORE
# ============================================================

def calculate_keyword_score(
    article: dict[str, Any],
    keywords: set[str],
) -> int:

    text = build_article_text(
        article
    )

    if not text:
        return 0

    matches = keyword_matches(
        text,
        keywords,
    )

    if not matches:
        return 0

    return min(
        KEYWORD_WEIGHT,
        len(matches) * 2,
    )


# ============================================================
# EXAM SCORE
# ============================================================

def calculate_exam_score(
    article: dict[str, Any],
    exam: str | None = None,
) -> int:

    if not exam:
        return 0

    exam = exam.strip().upper()

    article_exam = normalize_text(
        article.get("exam")
    ).upper()

    relevance = normalize_text(
        article.get(
            "upsc_relevance"
            if exam == "UPSC"
            else "bpsc_relevance"
        )
    )

    score = 0

    if article_exam == exam:
        score += 12

    if relevance == "high":
        score += 8

    elif relevance == "medium":
        score += 5

    elif relevance == "low":
        score += 1

    return min(
        EXAM_WEIGHT,
        score,
    )


# ============================================================
# FRESHNESS SCORE
# ============================================================

def parse_datetime(
    value: Any,
) -> datetime | None:

    if not value:
        return None

    if isinstance(value, datetime):
        dt = value

    else:

        try:
            dt = datetime.fromisoformat(
                str(value)
                .strip()
                .replace(
                    "Z",
                    "+00:00",
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt


def calculate_freshness_score(
    article: dict[str, Any],
) -> int:

    published_at = (
        article.get("published_at")
        or article.get("publishedAt")
    )

    published = parse_datetime(
        published_at
    )

    if published is None:
        return 0

    now = datetime.now(
        timezone.utc
    )

    age_hours = (
        now - published
    ).total_seconds() / 3600

    if age_hours < 0:
        age_hours = 0

    if age_hours <= 24:
        return FRESHNESS_WEIGHT

    if age_hours <= 48:
        return 8

    if age_hours <= 72:
        return 6

    if age_hours <= 168:
        return 4

    if age_hours <= 336:
        return 2

    return 0


# ============================================================
# SOURCE SCORE
# ============================================================

def calculate_source_score(
    article: dict[str, Any],
) -> int:

    source = normalize_text(
        article.get("source")
    )

    if not source:
        return 0

    if source in HIGH_QUALITY_SOURCES:
        return SOURCE_WEIGHT

    if source in MEDIUM_QUALITY_SOURCES:
        return 6

    return 3


# ============================================================
# NOISE DETECTION
# ============================================================

def detect_noise(
    article: dict[str, Any],
) -> tuple[bool, list[str]]:

    text = build_article_text(
        article
    )

    matches = keyword_matches(
        text,
        NOISE_KEYWORDS,
    )

    return (
        bool(matches),
        matches,
    )


# ============================================================
# EXAM KEYWORDS
# ============================================================

def get_exam_keywords(
    exam: str | None,
) -> set[str]:

    if not exam:
        return (
            UPSC_KEYWORDS
            | BPSC_KEYWORDS
            | BIHAR_KEYWORDS
        )

    exam = exam.upper()

    if exam == "UPSC":
        return UPSC_KEYWORDS

    if exam == "BPSC":
        return (
            BPSC_KEYWORDS
            | BIHAR_KEYWORDS
        )

    return (
        UPSC_KEYWORDS
        | BPSC_KEYWORDS
        | BIHAR_KEYWORDS
    )


# ============================================================
# FINAL SCORE
# ============================================================

def calculate_news_score(
    article: dict[str, Any],
    exam: str | None = None,
) -> dict[str, Any]:

    keywords = get_exam_keywords(
        exam
    )

    # --------------------------------------------------------
    # Individual components
    # --------------------------------------------------------

    title_score = calculate_title_score(
        article,
        keywords,
    )

    description_score = (
        calculate_description_score(
            article,
            keywords,
        )
    )

    keyword_score = calculate_keyword_score(
        article,
        keywords,
    )

    exam_score = calculate_exam_score(
        article,
        exam,
    )

    freshness_score = (
        calculate_freshness_score(
            article
        )
    )

    source_score = (
        calculate_source_score(
            article
        )
    )

    # --------------------------------------------------------
    # Query score
    #
    # Title + description + keyword relevance
    #
    # Maximum:
    # 25 + 15 + 20 = 60
    # --------------------------------------------------------

    query_score = min(
        TITLE_WEIGHT
        + DESCRIPTION_WEIGHT
        + KEYWORD_WEIGHT,
        (
            title_score
            + description_score
            + keyword_score
        ),
    )

    # --------------------------------------------------------
    # Engine score
    #
    # Exam relevance + source quality
    #
    # Maximum:
    # 20 + 10 = 30
    # --------------------------------------------------------

    engine_score = min(
        EXAM_WEIGHT
        + SOURCE_WEIGHT,
        (
            exam_score
            + source_score
        ),
    )

    # --------------------------------------------------------
    # Relevance score
    #
    # Query + engine
    #
    # Maximum = 90
    # --------------------------------------------------------

    relevance_score = min(
        MAX_SCORE,
        query_score
        + engine_score,
    )

    # --------------------------------------------------------
    # Noise
    # --------------------------------------------------------

    is_noise, noise_matches = detect_noise(
        article
    )

    # --------------------------------------------------------
    # Final score
    #
    # Relevance + freshness
    # Maximum = 100
    # --------------------------------------------------------

    final_score = (
        relevance_score
        + freshness_score
    )

    if is_noise:
        final_score -= 30

    final_score = max(
        0,
        min(
            MAX_SCORE,
            final_score,
        ),
    )

    # --------------------------------------------------------
    # Importance
    # --------------------------------------------------------

    if final_score >= 80:
        importance = "High"

    elif final_score >= 55:
        importance = "Medium"

    elif final_score >= 30:
        importance = "Low"

    else:
        importance = "Very Low"

    # --------------------------------------------------------
    # Return API-compatible scoring
    # --------------------------------------------------------

    return {
        # Main API fields
        "relevance_score": relevance_score,
        "query_score": query_score,
        "engine_score": engine_score,
        "freshness_score": freshness_score,
        "final_score": final_score,
        "is_noise": is_noise,

        # Detailed internal scores
        "title_score": title_score,
        "description_score": description_score,
        "keyword_score": keyword_score,
        "exam_score": exam_score,
        "source_score": source_score,

        # Classification
        "importance": importance,
        "noise_keywords": noise_matches,
    }


# ============================================================
# APPLY SCORE TO ARTICLE
# ============================================================

def score_article(
    article: dict[str, Any],
    exam: str | None = None,
) -> dict[str, Any]:

    if not isinstance(
        article,
        dict,
    ):
        return {}

    result = dict(article)

    scoring = calculate_news_score(
        result,
        exam=exam,
    )

    result.update(
        scoring
    )

    return result


# ============================================================
# SCORE MANY ARTICLES
# ============================================================

def score_articles(
    articles: list[dict[str, Any]],
    exam: str | None = None,
) -> list[dict[str, Any]]:

    scored: list[
        dict[str, Any]
    ] = []

    for article in articles:

        if not isinstance(
            article,
            dict,
        ):
            continue

        try:

            result = score_article(
                article,
                exam=exam,
            )

            if result:
                scored.append(
                    result
                )

        except Exception:
            continue

    # Highest final score first
    scored.sort(
        key=lambda item: (
            item.get(
                "final_score",
                0,
            ),
            item.get(
                "freshness_score",
                0,
            ),
        ),
        reverse=True,
    )

    return scored


# ============================================================
# FILTER BY MINIMUM SCORE
# ============================================================

def filter_scored_articles(
    articles: list[dict[str, Any]],
    min_score: int = 30,
) -> list[dict[str, Any]]:

    return [
        article
        for article in articles
        if int(
            article.get(
                "final_score",
                0,
            )
        ) >= min_score
    ]