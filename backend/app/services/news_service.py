from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from contextlib import asynccontextmanager
from typing import Any

import httpx
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

logger = logging.getLogger("muni48.news_service")


# ============================================================
# NEWS API CONFIGURATION
# ============================================================

NEWS_API_KEY = os.getenv(
    "NEWS_API_KEY",
    "",
).strip()

NEWS_API_URL = os.getenv(
    "NEWS_API_URL",
    "https://newsapi.org/v2/everything",
).strip()


# ============================================================
# NEWSAPI URL SAFETY
# ============================================================

if not NEWS_API_URL:
    NEWS_API_URL = "https://newsapi.org/v2/everything"


if NEWS_API_URL.startswith("http://"):
    logger.warning(
        "NEWS_API_URL uses HTTP. Forcing HTTPS."
    )

    NEWS_API_URL = (
        "https://"
        + NEWS_API_URL[len("http://"):]
    )


if not NEWS_API_URL.startswith("https://"):
    raise RuntimeError(
        "NEWS_API_URL must use HTTPS. "
        f"Current value: {NEWS_API_URL}"
    )


# ============================================================
# CONFIGURATION LOGGING
# ============================================================

if NEWS_API_KEY:
    logger.info(
        "NEWS_API_KEY loaded successfully"
    )
else:
    logger.warning(
        "NEWS_API_KEY is not configured. "
        "NewsAPI requests will fail until "
        "NEWS_API_KEY is added to .env."
    )


logger.info(
    "NewsAPI URL: %s",
    NEWS_API_URL,
)


# ============================================================
# DEFAULT CONFIGURATION
# ============================================================

DEFAULT_QUERY = "India"
DEFAULT_LANGUAGE = "en"

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# ============================================================
# HTTP TIMEOUT CONFIGURATION
# ============================================================

REQUEST_TIMEOUT = float(
    os.getenv(
        "NEWS_REQUEST_TIMEOUT",
        "15",
    )
)

CONNECT_TIMEOUT = float(
    os.getenv(
        "NEWS_CONNECT_TIMEOUT",
        "5",
    )
)

READ_TIMEOUT = float(
    os.getenv(
        "NEWS_READ_TIMEOUT",
        "15",
    )
)

WRITE_TIMEOUT = float(
    os.getenv(
        "NEWS_WRITE_TIMEOUT",
        "5",
    )
)

POOL_TIMEOUT = float(
    os.getenv(
        "NEWS_POOL_TIMEOUT",
        "5",
    )
)


# ============================================================
# RETRY CONFIGURATION
# ============================================================

MAX_RETRIES = int(
    os.getenv(
        "NEWS_MAX_RETRIES",
        "2",
    )
)


# ============================================================
# CACHE CONFIGURATION
# ============================================================

CACHE_TTL_SECONDS = int(
    os.getenv(
        "NEWS_CACHE_TTL",
        "180",
    )
)

CACHE_MAX_ITEMS = int(
    os.getenv(
        "NEWS_CACHE_MAX_ITEMS",
        "128",
    )
)


# ============================================================
# USER AGENT
# ============================================================

USER_AGENT = os.getenv(
    "NEWS_USER_AGENT",
    "Muni48-News-Service/3.0",
)


# ============================================================
# APPLICATION LANGUAGES
# ============================================================

ALLOWED_LANGUAGES = {
    "ar",
    "de",
    "en",
    "es",
    "fr",
    "he",
    "hi",
    "it",
    "nl",
    "no",
    "pt",
    "ru",
    "sv",
    "ud",
    "zh",
}


LANGUAGE_ALIASES = {
    "hindi": "hi",
    "english": "en",
    "arabic": "ar",
    "german": "de",
    "spanish": "es",
    "french": "fr",
    "italian": "it",
    "chinese": "zh",
    "russian": "ru",
}


# ============================================================
# NEWSAPI SUPPORTED SOURCE LANGUAGES
# ============================================================
#
# Hindi is intentionally NOT sent to NewsAPI.
#
# When user requests:
#
#     language=hi
#
# we fetch English articles and translate them using Groq.
#
# ============================================================

NEWSAPI_SUPPORTED_LANGUAGES = {
    "ar",
    "de",
    "en",
    "es",
    "fr",
    "he",
    "it",
    "nl",
    "no",
    "pt",
    "ru",
    "sv",
    "ud",
    "zh",
}


def get_newsapi_language(
    language: str,
) -> str:
    """
    Convert application language to NewsAPI language.

    Hindi is not requested directly from NewsAPI.
    Hindi articles are translated from English afterward.
    """

    language = validate_language(language)

    if language == "hi":
        return "en"

    if language not in NEWSAPI_SUPPORTED_LANGUAGES:
        return "en"

    return language


# ============================================================
# EXCEPTIONS
# ============================================================

class NewsAPIError(RuntimeError):
    """Base NewsAPI exception."""


class NewsAPITimeoutError(NewsAPIError):
    """NewsAPI request timeout."""


class NewsAPIConnectionError(NewsAPIError):
    """NewsAPI connection failure."""


class NewsAPIRateLimitError(NewsAPIError):
    """NewsAPI rate limit exceeded."""


class NewsAPIResponseError(NewsAPIError):
    """NewsAPI returned an API/HTTP error."""

    def __init__(
        self,
        message: str,
        code: str = "unknown_error",
        status_code: int | None = None,
    ):
        super().__init__(message)

        self.code = code
        self.status_code = status_code


# ============================================================
# IN-MEMORY CACHE
# ============================================================

_cache: dict[
    str,
    tuple[
        float,
        dict[str, Any],
    ],
] = {}

_cache_lock = asyncio.Lock()


# ============================================================
# HTTP CLIENT
# ============================================================

_client: httpx.AsyncClient | None = None

_client_lock = asyncio.Lock()


# ============================================================
# TIMEOUT
# ============================================================

def _build_timeout() -> httpx.Timeout:
    return httpx.Timeout(
        timeout=REQUEST_TIMEOUT,
        connect=CONNECT_TIMEOUT,
        read=READ_TIMEOUT,
        write=WRITE_TIMEOUT,
        pool=POOL_TIMEOUT,
    )


# ============================================================
# HTTP CLIENT
# ============================================================

async def get_http_client() -> httpx.AsyncClient:

    global _client

    if (
        _client is not None
        and not _client.is_closed
    ):
        return _client

    async with _client_lock:

        if (
            _client is not None
            and not _client.is_closed
        ):
            return _client

        _client = httpx.AsyncClient(
            timeout=_build_timeout(),
            follow_redirects=True,
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30,
            ),
        )

        logger.info(
            "NewsAPI HTTP client initialized"
        )

        return _client


# ============================================================
# CLOSE HTTP CLIENT
# ============================================================

async def close_http_client() -> None:

    global _client

    async with _client_lock:

        if _client is not None:

            try:
                await _client.aclose()

            except Exception:
                logger.exception(
                    "Failed to close NewsAPI HTTP client"
                )

            finally:
                _client = None


# ============================================================
# SERVICE LIFESPAN
# ============================================================

@asynccontextmanager
async def news_service_lifespan():

    await get_http_client()

    try:
        yield

    finally:
        await close_http_client()


# ============================================================
# VALIDATORS
# ============================================================

def validate_page(
    page: Any,
) -> int:

    try:
        value = int(page)

    except (
        TypeError,
        ValueError,
    ):
        return DEFAULT_PAGE

    return max(
        1,
        value,
    )


def validate_page_size(
    page_size: Any,
) -> int:

    try:
        value = int(page_size)

    except (
        TypeError,
        ValueError,
    ):
        return DEFAULT_PAGE_SIZE

    if value < 1:
        return DEFAULT_PAGE_SIZE

    return min(
        value,
        MAX_PAGE_SIZE,
    )


def validate_language(
    language: Any,
) -> str:

    value = str(
        language
        or DEFAULT_LANGUAGE
    ).strip().lower()

    value = LANGUAGE_ALIASES.get(
        value,
        value,
    )

    if value not in ALLOWED_LANGUAGES:
        return DEFAULT_LANGUAGE

    return value


def validate_query(
    query: Any,
) -> str:

    value = str(
        query or ""
    ).strip()

    value = value[:300]

    if not value:
        raise ValueError(
            "News search query cannot be empty."
        )

    return value


# ============================================================
# CACHE KEY
# ============================================================

def _cache_key(
    query: str,
    language: str,
    page: int,
    page_size: int,
) -> str:

    return (
        f"{query.lower().strip()}|"
        f"{language}|"
        f"{page}|"
        f"{page_size}"
    )


# ============================================================
# CLONE RESPONSE
# ============================================================

def _clone_response(
    data: dict[str, Any],
) -> dict[str, Any]:

    result = dict(data)

    result["articles"] = [
        dict(article)
        for article in data.get(
            "articles",
            [],
        )
        if isinstance(
            article,
            dict,
        )
    ]

    return result


# ============================================================
# CACHE GET
# ============================================================

async def _get_cache(
    key: str,
) -> dict[str, Any] | None:

    now = time.monotonic()

    async with _cache_lock:

        item = _cache.get(key)

        if not item:
            return None

        expires_at, data = item

        if expires_at <= now:

            _cache.pop(
                key,
                None,
            )

            return None

        result = _clone_response(data)

        result["cache"] = {
            "hit": True,
            "ttl_seconds": max(
                0,
                int(
                    expires_at - now
                ),
            ),
        }

        return result


# ============================================================
# CACHE SET
# ============================================================

async def _set_cache(
    key: str,
    data: dict[str, Any],
) -> None:

    async with _cache_lock:

        now = time.monotonic()

        expired_keys = [
            cache_key
            for cache_key, (
                expires_at,
                _,
            ) in _cache.items()
            if expires_at <= now
        ]

        for cache_key in expired_keys:

            _cache.pop(
                cache_key,
                None,
            )

        if len(_cache) >= CACHE_MAX_ITEMS:

            oldest_key = min(
                _cache,
                key=lambda item: _cache[item][0],
            )

            _cache.pop(
                oldest_key,
                None,
            )

        _cache[key] = (
            time.monotonic()
            + CACHE_TTL_SECONDS,
            _clone_response(data),
        )


# ============================================================
# CLEAR CACHE
# ============================================================

async def clear_news_cache() -> None:

    async with _cache_lock:
        _cache.clear()

    logger.info(
        "NewsAPI cache cleared"
    )


# ============================================================
# ERROR EXTRACTION
# ============================================================

def extract_api_error(
    response: httpx.Response,
) -> tuple[str, str]:

    try:
        data = response.json()

    except ValueError:

        return (
            "http_error",
            (
                "NewsAPI HTTP "
                f"{response.status_code}"
            ),
        )

    if not isinstance(
        data,
        dict,
    ):

        return (
            "http_error",
            (
                "NewsAPI HTTP "
                f"{response.status_code}"
            ),
        )

    code = str(
        data.get("code")
        or "unknown_error"
    )

    message = str(
        data.get("message")
        or "NewsAPI request failed"
    )

    return (
        code,
        message,
    )


# ============================================================
# RETRYABLE STATUS
# ============================================================

def _is_retryable_status(
    status_code: int,
) -> bool:

    return status_code in {
        408,
        425,
        429,
        500,
        502,
        503,
        504,
    }


# ============================================================
# BACKOFF
# ============================================================

def _backoff_seconds(
    attempt: int,
) -> float:

    base = 0.4 * (
        2 ** attempt
    )

    jitter = random.uniform(
        0.0,
        0.25,
    )

    return min(
        3.0,
        base + jitter,
    )


# ============================================================
# NORMALIZE ARTICLE
# ============================================================

def _normalize_article(
    article: Any,
) -> dict[str, Any] | None:

    if not isinstance(
        article,
        dict,
    ):
        return None

    title = str(
        article.get("title")
        or ""
    ).strip()

    if not title:
        return None

    source_data = article.get(
        "source"
    )

    if isinstance(
        source_data,
        dict,
    ):

        source_name = str(
            source_data.get("name")
            or ""
        ).strip()

    else:

        source_name = str(
            source_data
            or ""
        ).strip()

    normalized: dict[str, Any] = {

        "title": title,

        "description": (
            str(
                article.get(
                    "description"
                )
                or ""
            ).strip()
            or None
        ),

        "url": (
            str(
                article.get("url")
                or ""
            ).strip()
            or None
        ),

        "source": (
            source_name
            or "Unknown"
        ),

        "image_url": (
            str(
                article.get(
                    "urlToImage"
                )
                or ""
            ).strip()
            or None
        ),

        "published_at": article.get(
            "publishedAt"
        ),

        "content": (
            str(
                article.get(
                    "content"
                )
                or ""
            ).strip()
            or None
        ),

        "author": (
            str(
                article.get(
                    "author"
                )
                or ""
            ).strip()
            or None
        ),
    }

    # IMPORTANT:
    # All strings here are correctly closed.
    preserved_fields = {
        "category",
        "exam",
        "importance",
        "exam_relevance",
        "upsc_relevance",
        "bpsc_relevance",
        "prelims_relevant",
        "mains_relevant",
        "bihar_relevant",
        "relevance_score",
        "bpsc_score",
        "bihar_score",
        "query_score",
        "engine_score",
        "freshness_score",
        "final_score",
        "is_noise",
        "syllabus",
    }

    for field in preserved_fields:

        if field in article:

            normalized[field] = article[field]

    return normalized


# ============================================================
# HINDI TRANSLATION
# ============================================================

async def _translate_articles_to_hindi(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    try:

        from app.services.groq_service import (
            translate_articles,
        )

    except ImportError:

        logger.warning(
            "Groq translation service not available. "
            "Returning English articles."
        )

        return articles

    try:

        result = await translate_articles(
            articles=articles,
            target_language="hi",
            max_concurrency=3,
        )

    except Exception as exc:

        logger.exception(
            "Groq translation service failed: %s",
            exc,
        )

        return articles

    if not isinstance(
        result,
        list,
    ):

        logger.warning(
            "Groq translation returned invalid data."
        )

        return articles

    return result


# ============================================================
# FETCH NEWS
# ============================================================

async def fetch_news(
    query: str = DEFAULT_QUERY,
    language: str = DEFAULT_LANGUAGE,
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    *,
    use_cache: bool = True,
) -> dict[str, Any]:

    # ========================================================
    # API KEY
    # ========================================================

    if not NEWS_API_KEY:

        raise NewsAPIError(
            "NEWS_API_KEY is missing. "
            "Add NEWS_API_KEY=your_key to backend .env"
        )

    # ========================================================
    # VALIDATION
    # ========================================================

    query = validate_query(query)

    language = validate_language(language)

    page = validate_page(page)

    page_size = validate_page_size(page_size)

    # ========================================================
    # CACHE
    # ========================================================

    key = _cache_key(
        query,
        language,
        page,
        page_size,
    )

    if use_cache:

        cached = await _get_cache(key)

        if cached:

            logger.debug(
                "NewsAPI cache hit: %s",
                key,
            )

            return cached

    # ========================================================
    # NEWSAPI LANGUAGE
    # ========================================================

    newsapi_language = get_newsapi_language(
        language
    )

    # ========================================================
    # PARAMETERS
    # ========================================================

    params = {
        "q": query,
        "language": newsapi_language,
        "page": page,
        "pageSize": page_size,
        "sortBy": "publishedAt",
        "apiKey": NEWS_API_KEY,
    }

    client = await get_http_client()

    response: httpx.Response | None = None

    # ========================================================
    # REQUEST + RETRIES
    # ========================================================

    for attempt in range(
        MAX_RETRIES + 1
    ):

        try:

            logger.info(
                (
                    "NewsAPI request: "
                    "q=%s page=%s size=%s "
                    "requested_language=%s "
                    "provider_language=%s "
                    "attempt=%s/%s"
                ),
                query,
                page,
                page_size,
                language,
                newsapi_language,
                attempt + 1,
                MAX_RETRIES + 1,
            )

            response = await client.get(
                NEWS_API_URL,
                params=params,
            )

            if response.status_code == 200:
                break

            code, message = extract_api_error(
                response
            )

            logger.warning(
                (
                    "NewsAPI returned HTTP %s "
                    "code=%s message=%s"
                ),
                response.status_code,
                code,
                message,
            )

            # =================================================
            # RATE LIMIT
            # =================================================

            if response.status_code == 429:

                if attempt < MAX_RETRIES:

                    retry_after = (
                        response.headers.get(
                            "Retry-After"
                        )
                    )

                    try:

                        delay = float(
                            retry_after
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):

                        delay = _backoff_seconds(
                            attempt
                        )

                    await asyncio.sleep(
                        min(
                            delay,
                            5.0,
                        )
                    )

                    continue

                raise NewsAPIRateLimitError(
                    (
                        "NewsAPI rate limit exceeded: "
                        f"{message}"
                    )
                )

            # =================================================
            # TEMPORARY ERRORS
            # =================================================

            if (
                _is_retryable_status(
                    response.status_code
                )
                and attempt < MAX_RETRIES
            ):

                await asyncio.sleep(
                    _backoff_seconds(
                        attempt
                    )
                )

                continue

            # =================================================
            # FINAL ERROR
            # =================================================

            raise NewsAPIResponseError(
                (
                    f"NewsAPI [{code}]: "
                    f"{message}"
                ),
                code=code,
                status_code=response.status_code,
            )

        except httpx.TimeoutException as exc:

            logger.warning(
                (
                    "NewsAPI timeout "
                    "attempt=%s/%s"
                ),
                attempt + 1,
                MAX_RETRIES + 1,
            )

            if attempt >= MAX_RETRIES:

                raise NewsAPITimeoutError(
                    "NewsAPI request timed out."
                ) from exc

            await asyncio.sleep(
                _backoff_seconds(
                    attempt
                )
            )

        except httpx.RequestError as exc:

            logger.warning(
                (
                    "NewsAPI connection error "
                    "attempt=%s/%s: %s"
                ),
                attempt + 1,
                MAX_RETRIES + 1,
                exc,
            )

            if attempt >= MAX_RETRIES:

                raise NewsAPIConnectionError(
                    (
                        "Unable to connect to NewsAPI: "
                        f"{exc}"
                    )
                ) from exc

            await asyncio.sleep(
                _backoff_seconds(
                    attempt
                )
            )

    # ========================================================
    # SAFETY
    # ========================================================

    if response is None:

        raise NewsAPIError(
            "NewsAPI returned no response."
        )

    # ========================================================
    # JSON
    # ========================================================

    try:

        data = response.json()

    except ValueError as exc:

        raise NewsAPIResponseError(
            "NewsAPI returned invalid JSON.",
            code="invalid_json",
            status_code=response.status_code,
        ) from exc

    if not isinstance(
        data,
        dict,
    ):

        raise NewsAPIResponseError(
            "NewsAPI returned an invalid response.",
            code="invalid_response",
            status_code=response.status_code,
        )

    # ========================================================
    # API STATUS
    # ========================================================

    status = str(
        data.get("status")
        or ""
    ).lower()

    if status != "ok":

        raise NewsAPIResponseError(
            str(
                data.get(
                    "message",
                    "NewsAPI request failed",
                )
            ),
            code=str(
                data.get(
                    "code",
                    "unknown_error",
                )
            ),
            status_code=response.status_code,
        )

    # ========================================================
    # RAW ARTICLES
    # ========================================================

    raw_articles = data.get(
        "articles",
        [],
    )

    if not isinstance(
        raw_articles,
        list,
    ):
        raw_articles = []

    # ========================================================
    # NORMALIZE + DEDUPLICATE
    # ========================================================

    articles: list[
        dict[str, Any]
    ] = []

    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for raw_article in raw_articles:

        article = _normalize_article(
            raw_article
        )

        if not article:
            continue

        title_key = (
            str(
                article.get(
                    "title",
                    "",
                )
            )
            .lower()
            .strip()
        )

        url_key = (
            str(
                article.get(
                    "url",
                    "",
                )
                or ""
            )
            .lower()
            .strip()
        )

        if (
            url_key
            and url_key in seen_urls
        ):
            continue

        if (
            title_key
            and title_key in seen_titles
        ):
            continue

        if url_key:
            seen_urls.add(url_key)

        if title_key:
            seen_titles.add(title_key)

        articles.append(article)

    # ========================================================
    # TOTAL RESULTS
    # ========================================================

    total_results = data.get(
        "totalResults",
        len(articles),
    )

    try:

        total_results = max(
            0,
            int(total_results),
        )

    except (
        TypeError,
        ValueError,
    ):

        total_results = len(articles)

    # ========================================================
    # HINDI TRANSLATION
    # ========================================================

    translated = False

    if (
        language == "hi"
        and articles
    ):

        logger.info(
            (
                "Hindi requested. "
                "Translating %s English articles "
                "using Groq."
            ),
            len(articles),
        )

        try:

            translated_articles = (
                await _translate_articles_to_hindi(
                    articles
                )
            )

            if translated_articles:
                articles = translated_articles
                translated = True

        except Exception as exc:

            logger.exception(
                "Hindi translation failed: %s",
                exc,
            )

            translated = False

    # ========================================================
    # RESULT
    # ========================================================

    result = {

        "status": "success",

        "totalResults": total_results,

        "total_results": total_results,

        "articles": articles,

        "page": page,

        "page_size": page_size,

        "language": language,

        "source_language": (
            "en"
            if language == "hi"
            else language
        ),

        "provider_language": newsapi_language,

        "translated": translated,

        "cache": {
            "hit": False,
            "ttl_seconds": CACHE_TTL_SECONDS,
        },
    }

    # ========================================================
    # CACHE
    # ========================================================

    if use_cache:

        await _set_cache(
            key,
            result,
        )

    return result


# ============================================================
# FETCH MULTIPLE QUERIES
# ============================================================

async def fetch_news_pool(
    queries: list[str],
    *,
    language: str = "en",
    page_size: int = 50,
    use_cache: bool = True,
) -> dict[str, Any]:

    clean_queries: list[str] = []

    seen_queries: set[str] = set()

    for query in queries:

        try:

            normalized = validate_query(
                query
            )

        except ValueError:
            continue

        key = normalized.lower()

        if key in seen_queries:
            continue

        seen_queries.add(key)

        clean_queries.append(
            normalized
        )

    validated_language = validate_language(
        language
    )

    validated_page_size = validate_page_size(
        page_size
    )

    if not clean_queries:

        return {

            "status": "success",

            "totalResults": 0,

            "total_results": 0,

            "articles": [],

            "queries": [],

            "errors": [],

            "language": validated_language,
        }

    tasks = [
        fetch_news(
            query=query,
            language=validated_language,
            page=1,
            page_size=validated_page_size,
            use_cache=use_cache,
        )
        for query in clean_queries
    ]

    results = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    merged: list[
        dict[str, Any]
    ] = []

    total_results = 0

    seen_urls: set[str] = set()

    seen_titles: set[str] = set()

    errors: list[str] = []

    for query, result in zip(
        clean_queries,
        results,
    ):

        if isinstance(
            result,
            Exception,
        ):

            logger.warning(
                "Query failed: %s -> %s",
                query,
                result,
            )

            errors.append(
                f"{query}: {result}"
            )

            continue

        try:

            total_results += int(
                result.get(
                    "totalResults",
                    result.get(
                        "total_results",
                        0,
                    ),
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            pass

        for article in result.get(
            "articles",
            [],
        ):

            if not isinstance(
                article,
                dict,
            ):
                continue

            title_key = (
                str(
                    article.get(
                        "title",
                        "",
                    )
                )
                .strip()
                .lower()
            )

            url_key = (
                str(
                    article.get(
                        "url",
                        "",
                    )
                    or ""
                )
                .strip()
                .lower()
            )

            if (
                url_key
                and url_key in seen_urls
            ):
                continue

            if (
                title_key
                and title_key in seen_titles
            ):
                continue

            if url_key:
                seen_urls.add(url_key)

            if title_key:
                seen_titles.add(title_key)

            merged.append(article)

    return {

        "status": "success",

        "totalResults": total_results,

        "total_results": total_results,

        "articles": merged,

        "queries": clean_queries,

        "errors": errors,

        "language": validated_language,
    }


# ============================================================
# HEALTH CHECK
# ============================================================

async def news_api_health() -> dict[str, Any]:

    if not NEWS_API_KEY:

        return {

            "status": "unhealthy",

            "provider": "NewsAPI",

            "reason": "NEWS_API_KEY is missing",
        }

    try:

        data = await fetch_news(
            query="India",
            language="en",
            page=1,
            page_size=1,
            use_cache=False,
        )

        return {

            "status": "healthy",

            "provider": "NewsAPI",

            "articles": len(
                data.get(
                    "articles",
                    [],
                )
            ),
        }

    except NewsAPITimeoutError as exc:

        return {

            "status": "unhealthy",

            "provider": "NewsAPI",

            "reason": "timeout",

            "detail": str(exc),
        }

    except NewsAPIRateLimitError as exc:

        return {

            "status": "unhealthy",

            "provider": "NewsAPI",

            "reason": "rate_limit",

            "detail": str(exc),
        }

    except NewsAPIConnectionError as exc:

        return {

            "status": "unhealthy",

            "provider": "NewsAPI",

            "reason": "connection_error",

            "detail": str(exc),
        }

    except NewsAPIResponseError as exc:

        return {

            "status": "unhealthy",

            "provider": "NewsAPI",

            "reason": "api_error",

            "code": exc.code,

            "status_code": exc.status_code,

            "detail": str(exc),
        }

    except Exception as exc:

        logger.exception(
            "NewsAPI health check failed"
        )

        return {

            "status": "unhealthy",

            "provider": "NewsAPI",

            "reason": type(exc).__name__,

            "detail": str(exc),
        }


# ============================================================
# EXPORTS
# ============================================================

__all__ = [

    "NEWS_API_KEY",
    "NEWS_API_URL",

    "NewsAPIError",
    "NewsAPITimeoutError",
    "NewsAPIConnectionError",
    "NewsAPIRateLimitError",
    "NewsAPIResponseError",

    "fetch_news",
    "fetch_news_pool",

    "clear_news_cache",

    "get_http_client",
    "close_http_client",

    "news_service_lifespan",

    "news_api_health",

    "validate_page",
    "validate_page_size",
    "validate_language",
    "validate_query",

    "get_newsapi_language",
]