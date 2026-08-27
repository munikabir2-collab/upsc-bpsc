# app/services/news_normalizer.py

from __future__ import annotations

import hashlib
import html
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


logger = logging.getLogger("muni48.news.normalizer")


# ============================================================
# CONSTANTS
# ============================================================

MAX_TITLE_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 3000
MAX_SOURCE_LENGTH = 200
MAX_URL_LENGTH = 2000
MAX_IMAGE_URL_LENGTH = 2000

DEFAULT_LANGUAGE = "en"


# ============================================================
# GENERIC HELPERS
# ============================================================

def safe_string(
    value: Any,
    default: str = "",
    max_length: int | None = None,
) -> str:
    """
    Safely convert any value to a cleaned string.
    """

    if value is None:
        return default

    try:
        value = str(value).strip()
    except Exception:
        return default

    if not value:
        return default

    # Decode HTML entities
    value = html.unescape(value)

    # Remove NULL characters
    value = value.replace("\x00", "")

    # Normalize whitespace
    value = re.sub(r"\s+", " ", value).strip()

    if max_length:
        value = value[:max_length].strip()

    return value


def clean_title(value: Any) -> str:
    """
    Normalize article title.
    """

    title = safe_string(
        value,
        max_length=MAX_TITLE_LENGTH,
    )

    if not title:
        return ""

    # Remove common trailing separators
    title = re.sub(
        r"\s*[\-|–|—|:|]\s*$",
        "",
        title,
    )

    return title.strip()


def clean_description(value: Any) -> str:
    """
    Normalize article description.
    """

    description = safe_string(
        value,
        max_length=MAX_DESCRIPTION_LENGTH,
    )

    if not description:
        return ""

    # Remove HTML tags if any
    description = re.sub(
        r"<[^>]+>",
        " ",
        description,
    )

    description = re.sub(
        r"\s+",
        " ",
        description,
    ).strip()

    return description


def normalize_lower(value: Any) -> str:
    return safe_string(value).lower()


# ============================================================
# URL NORMALIZATION
# ============================================================

TRACKING_PARAMETERS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_name",
    "gclid",
    "fbclid",
    "mc_cid",
    "mc_eid",
}


def normalize_url(value: Any) -> str:
    """
    Normalize article URL.

    Removes common tracking parameters while keeping
    the actual article URL intact.
    """

    url = safe_string(
        value,
        max_length=MAX_URL_LENGTH,
    )

    if not url:
        return ""

    try:
        parsed = urlsplit(url)

        if not parsed.scheme:
            return url

        if not parsed.netloc:
            return url

        # Remove tracking parameters
        query_items = []

        for key, val in parse_qsl(
            parsed.query,
            keep_blank_values=True,
        ):
            if key.lower() not in TRACKING_PARAMETERS:
                query_items.append(
                    (key, val)
                )

        clean_query = urlencode(
            query_items,
            doseq=True,
        )

        normalized = urlunsplit(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path.rstrip("/"),
                clean_query,
                "",
            )
        )

        return normalized

    except Exception:
        logger.warning(
            "Unable to normalize URL: %r",
            value,
        )

        return url


# ============================================================
# SOURCE NORMALIZATION
# ============================================================

def normalize_source(
    article: dict[str, Any],
) -> str:
    """
    Supports both:

        "source": "BBC"

    and NewsAPI format:

        "source": {
            "id": "...",
            "name": "BBC"
        }
    """

    source = article.get("source")

    if isinstance(source, dict):

        source_name = (
            source.get("name")
            or source.get("title")
            or source.get("id")
        )

    else:

        source_name = source

    return safe_string(
        source_name,
        max_length=MAX_SOURCE_LENGTH,
    )


# ============================================================
# DATE NORMALIZATION
# ============================================================

def parse_datetime(
    value: Any,
) -> datetime | None:
    """
    Convert common date formats into timezone-aware UTC datetime.
    """

    if value is None:
        return None

    if isinstance(value, datetime):

        if value.tzinfo is None:

            return value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        )

    value = safe_string(value)

    if not value:
        return None

    # ISO format
    try:

        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

        if parsed.tzinfo is None:

            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed.astimezone(
            timezone.utc
        )

    except ValueError:
        pass

    # Common formats
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
    )

    for fmt in formats:

        try:

            parsed = datetime.strptime(
                value,
                fmt,
            )

            return parsed.replace(
                tzinfo=timezone.utc
            )

        except ValueError:
            continue

    logger.debug(
        "Could not parse article date: %r",
        value,
    )

    return None


def get_published_at(
    article: dict[str, Any],
) -> datetime | None:

    value = (
        article.get("published_at")
        or article.get("publishedAt")
        or article.get("published")
        or article.get("date")
        or article.get("pubDate")
    )

    return parse_datetime(value)


# ============================================================
# IMAGE NORMALIZATION
# ============================================================

def get_image_url(
    article: dict[str, Any],
) -> str:
    """
    Supports multiple providers.
    """

    candidates = (
        article.get("image_url"),
        article.get("image"),
        article.get("urlToImage"),
        article.get("thumbnail"),
        article.get("imageUrl"),
    )

    for value in candidates:

        image_url = safe_string(
            value,
            max_length=MAX_IMAGE_URL_LENGTH,
        )

        if image_url:
            return image_url

    return ""


# ============================================================
# AUTHOR
# ============================================================

def normalize_author(
    article: dict[str, Any],
) -> str:

    return safe_string(
        article.get("author")
        or article.get("creator")
        or article.get("byline"),
        max_length=300,
    )


# ============================================================
# CATEGORY
# ============================================================

def normalize_category(
    article: dict[str, Any],
) -> str:

    return safe_string(
        article.get("category")
        or article.get("section")
        or article.get("topic"),
        max_length=100,
    )


# ============================================================
# LANGUAGE
# ============================================================

def normalize_language(
    article: dict[str, Any],
) -> str:

    language = safe_string(
        article.get("language")
        or DEFAULT_LANGUAGE,
        max_length=10,
    )

    return language.lower()


# ============================================================
# TEXT FOR SEARCH / SCORING
# ============================================================

def build_search_text(
    article: dict[str, Any],
) -> str:
    """
    Creates a single normalized text field for
    topic matching and relevance scoring.
    """

    parts = [
        article.get("title", ""),
        article.get("description", ""),
        article.get("content", ""),
        article.get("category", ""),
    ]

    text_parts = []

    for part in parts:

        cleaned = safe_string(part)

        if cleaned:
            text_parts.append(cleaned)

    return " ".join(
        text_parts
    ).strip()


def normalize_search_text(
    value: Any,
) -> str:

    text = safe_string(value)

    if not text:
        return ""

    text = text.lower()

    # Normalize punctuation to spaces
    text = re.sub(
        r"[^\w\s\-]",
        " ",
        text,
        flags=re.UNICODE,
    )

    # Normalize whitespace
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# ============================================================
# ARTICLE ID
# ============================================================

def generate_article_hash(
    title: str,
    url: str = "",
) -> str:
    """
    Stable hash used for duplicate detection.
    """

    normalized_title = normalize_search_text(
        title
    )

    normalized_url = normalize_url(
        url
    )

    # URL is preferred when available
    if normalized_url:

        base = normalized_url

    else:

        base = normalized_title

    if not base:
        return ""

    return hashlib.sha256(
        base.encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()


# ============================================================
# DUPLICATE KEY
# ============================================================

def build_duplicate_key(
    article: dict[str, Any],
) -> str:

    title = clean_title(
        article.get("title")
    )

    url = normalize_url(
        article.get("url")
    )

    return generate_article_hash(
        title=title,
        url=url,
    )


# ============================================================
# RAW ARTICLE NORMALIZER
# ============================================================

def normalize_article(
    article: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert a raw news-provider article into a stable
    Muni48 internal article structure.

    IMPORTANT:
    This function does NOT score or filter the article.
    """

    if not isinstance(
        article,
        dict,
    ):
        return {}

    title = clean_title(
        article.get("title")
    )

    description = clean_description(
        article.get("description")
        or article.get("content")
    )

    url = normalize_url(
        article.get("url")
    )

    source = normalize_source(
        article
    )

    image_url = get_image_url(
        article
    )

    published_at = get_published_at(
        article
    )

    author = normalize_author(
        article
    )

    category = normalize_category(
        article
    )

    language = normalize_language(
        article
    )

    normalized = {
        # ----------------------------------------------------
        # Core
        # ----------------------------------------------------

        "title": title,

        "description": description,

        "url": url,

        "source": source,

        "image_url": image_url,

        "published_at": published_at,

        "author": author,

        "category": category,

        "language": language,

        # ----------------------------------------------------
        # Internal search fields
        # ----------------------------------------------------

        "search_text": "",

        "normalized_title": normalize_search_text(
            title
        ),

        "duplicate_key": "",

        # ----------------------------------------------------
        # Classification placeholders
        # ----------------------------------------------------

        "exam": "",

        "importance": "",

        "exam_relevance": "",

        "upsc_relevance": "",

        "bpsc_relevance": "",

        "region": "",

        # ----------------------------------------------------
        # Scoring placeholders
        # ----------------------------------------------------

        "relevance_score": 0,

        "query_score": 0,

        "engine_score": 0,

        "freshness_score": 0,

        "source_score": 0,

        "quality_score": 0,

        "final_score": 0,

        # ----------------------------------------------------
        # Exam relevance
        # ----------------------------------------------------

        "prelims_relevant": False,

        "mains_relevant": False,

        # ----------------------------------------------------
        # Noise
        # ----------------------------------------------------

        "is_noise": False,

        "noise_reason": "",
    }

    normalized["search_text"] = (
        normalize_search_text(
            build_search_text(
                normalized
            )
        )
    )

    normalized["duplicate_key"] = (
        build_duplicate_key(
            normalized
        )
    )

    return normalized


# ============================================================
# NORMALIZE MANY
# ============================================================

def normalize_articles(
    articles: Any,
) -> list[dict[str, Any]]:
    """
    Normalize a list of raw articles.
    """

    if not isinstance(
        articles,
        list,
    ):
        return []

    normalized_articles = []

    for article in articles:

        try:

            normalized = normalize_article(
                article
            )

            if not normalized:
                continue

            # Title is required
            if not normalized.get(
                "title"
            ):
                continue

            normalized_articles.append(
                normalized
            )

        except Exception:

            logger.exception(
                "Failed to normalize article."
            )

    return normalized_articles


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def deduplicate_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Remove duplicate articles using duplicate_key.

    Keeps the first occurrence.
    """

    if not articles:
        return []

    seen: set[str] = set()

    result = []

    for article in articles:

        if not isinstance(
            article,
            dict,
        ):
            continue

        key = safe_string(
            article.get(
                "duplicate_key"
            )
        )

        # Fallback if key is missing
        if not key:

            key = build_duplicate_key(
                article
            )

        # If absolutely no identity exists,
        # keep the article.
        if not key:

            result.append(
                article
            )

            continue

        if key in seen:
            continue

        seen.add(key)

        result.append(
            article
        )

    return result


# ============================================================
# COMPLETE NORMALIZATION PIPELINE
# ============================================================

def prepare_articles(
    articles: Any,
) -> list[dict[str, Any]]:
    """
    Full normalization pipeline:

        raw articles
             ↓
        normalize
             ↓
        remove duplicates
             ↓
        ready for topics/scoring/filter
    """

    normalized = normalize_articles(
        articles
    )

    return deduplicate_articles(
        normalized
    )


# ============================================================
# PUBLIC EXPORTS
# ============================================================

__all__ = [
    "safe_string",
    "clean_title",
    "clean_description",
    "normalize_url",
    "normalize_source",
    "parse_datetime",
    "get_published_at",
    "get_image_url",
    "normalize_author",
    "normalize_category",
    "normalize_language",
    "build_search_text",
    "normalize_search_text",
    "generate_article_hash",
    "build_duplicate_key",
    "normalize_article",
    "normalize_articles",
    "deduplicate_articles",
    "prepare_articles",
]