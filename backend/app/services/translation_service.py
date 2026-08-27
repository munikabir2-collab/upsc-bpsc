# app/services/translation_service.py

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from dotenv import load_dotenv
from groq import AsyncGroq


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

logger = logging.getLogger("muni48.translation_service")

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    "",
).strip()

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
).strip()


# ============================================================
# CLIENT
# ============================================================

_client: AsyncGroq | None = None

_client_lock = asyncio.Lock()


async def get_groq_client() -> AsyncGroq:

    global _client

    if _client is not None:
        return _client

    async with _client_lock:

        if _client is not None:
            return _client

        if not GROQ_API_KEY:

            raise RuntimeError(
                "GROQ_API_KEY is missing. "
                "Add GROQ_API_KEY=your_key to .env"
            )

        _client = AsyncGroq(
            api_key=GROQ_API_KEY
        )

        logger.info(
            "Groq translation client initialized"
        )

        return _client


# ============================================================
# TRANSLATION
# ============================================================

async def translate_text(
    text: str,
    target_language: str = "hi",
) -> str:

    text = str(text or "").strip()

    if not text:
        return ""

    target_language = (
        str(target_language or "hi")
        .strip()
        .lower()
    )

    if target_language == "hi":

        language_name = "Hindi"

    elif target_language == "en":

        language_name = "English"

    else:

        language_name = target_language

    client = await get_groq_client()

    prompt = f"""
Translate the following news content into {language_name}.

Rules:
- Preserve the original meaning.
- Do not add facts.
- Do not remove important information.
- Keep names of people, organizations, places and schemes accurate.
- Keep numbers, percentages, dates and financial figures unchanged.
- Use natural, professional language suitable for UPSC and BPSC aspirants.
- Do not provide explanations.
- Return only the translated text.

TEXT:
{text}
"""

    try:

        response = await client.chat.completions.create(

            model=GROQ_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional news "
                        "translator for UPSC and BPSC "
                        "current affairs."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],

            temperature=0.1,

            max_tokens=2000,

        )

        result = (
            response
            .choices[0]
            .message
            .content
            or ""
        ).strip()

        return result

    except Exception as exc:

        logger.exception(
            "Groq translation failed"
        )

        raise RuntimeError(
            f"Groq translation failed: {exc}"
        ) from exc


# ============================================================
# ARTICLE TRANSLATION
# ============================================================

async def translate_article(
    article: dict[str, Any],
    target_language: str = "hi",
) -> dict[str, Any]:

    result = dict(article)

    title = str(
        article.get("title")
        or ""
    ).strip()

    description = str(
        article.get("description")
        or ""
    ).strip()

    content = str(
        article.get("content")
        or ""
    ).strip()

    # --------------------------------------------------------
    # Translate title
    # --------------------------------------------------------

    if title:

        result["title"] = await translate_text(
            title,
            target_language,
        )

    # --------------------------------------------------------
    # Translate description
    # --------------------------------------------------------

    if description:

        result["description"] = await translate_text(
            description,
            target_language,
        )

    # --------------------------------------------------------
    # Translate content
    # --------------------------------------------------------

    if content:

        result["content"] = await translate_text(
            content,
            target_language,
        )

    result["language"] = target_language

    result["translated"] = True

    return result


# ============================================================
# BATCH TRANSLATION
# ============================================================

async def translate_articles(
    articles: list[dict[str, Any]],
    target_language: str = "hi",
    max_concurrency: int = 3,
) -> list[dict[str, Any]]:

    if not articles:
        return []

    semaphore = asyncio.Semaphore(
        max_concurrency
    )

    async def translate_one(
        article: dict[str, Any],
    ) -> dict[str, Any]:

        async with semaphore:

            try:

                return await translate_article(
                    article,
                    target_language,
                )

            except Exception as exc:

                logger.warning(
                    "Article translation failed: %s",
                    exc,
                )

                # Do not destroy the original article
                # if translation fails.

                fallback = dict(article)

                fallback["language"] = (
                    article.get("language")
                    or "en"
                )

                fallback["translated"] = False

                fallback["translation_error"] = (
                    str(exc)
                )

                return fallback

    results = await asyncio.gather(
        *[
            translate_one(article)
            for article in articles
        ]
    )

    return results


# ============================================================
# HEALTH CHECK
# ============================================================

async def translation_health() -> dict[str, Any]:

    if not GROQ_API_KEY:

        return {
            "status": "unhealthy",
            "provider": "Groq",
            "reason": "GROQ_API_KEY is missing",
        }

    try:

        result = await translate_text(
            "India's economy is growing rapidly.",
            "hi",
        )

        return {
            "status": "healthy",
            "provider": "Groq",
            "model": GROQ_MODEL,
            "test": result,
        }

    except Exception as exc:

        return {
            "status": "unhealthy",
            "provider": "Groq",
            "model": GROQ_MODEL,
            "reason": type(exc).__name__,
            "detail": str(exc),
        }


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "get_groq_client",
    "translate_text",
    "translate_article",
    "translate_articles",
    "translation_health",
]