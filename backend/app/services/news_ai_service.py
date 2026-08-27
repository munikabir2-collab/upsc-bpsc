
from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("app.news_ai_service")


# ============================================================
# CONFIGURATION
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "qwen/qwen3.6-27b",
)

GROQ_TEMPERATURE = float(
    os.getenv("GROQ_TEMPERATURE", "0.1")
)

MAX_COMPLETION_TOKENS = int(
    os.getenv("MAX_COMPLETION_TOKENS", "3000")
)

MCQ_MAX_COMPLETION_TOKENS = int(
    os.getenv("MCQ_MAX_COMPLETION_TOKENS", "2200")
)

MCQ_MAX_ATTEMPTS = int(
    os.getenv("MCQ_MAX_ATTEMPTS", "3")
)

MCQ_MAX_ARTICLE_CHARS = int(
    os.getenv("MCQ_MAX_ARTICLE_CHARS", "6500")
)

MCQ_RETRY_DELAY_SECONDS = float(
    os.getenv("MCQ_RETRY_DELAY_SECONDS", "1.5")
)

MCQ_RATE_LIMIT_WAIT_SECONDS = float(
    os.getenv("MCQ_RATE_LIMIT_WAIT_SECONDS", "35")
)

MCQ_RESPONSE_LOG_CHARS = int(
    os.getenv("MCQ_RESPONSE_LOG_CHARS", "1200")
)


# ============================================================
# GROQ CLIENT
# ============================================================

try:
    from groq import Groq
except ImportError:
    Groq = None


_client: Any = None


def _get_client() -> Any:
    global _client

    if _client is not None:
        return _client

    if Groq is None:
        logger.error(
            "Groq package is not installed."
        )
        return None

    if not GROQ_API_KEY:
        logger.error(
            "GROQ_API_KEY is not configured."
        )
        return None

    try:
        _client = Groq(
            api_key=GROQ_API_KEY
        )

        logger.info(
            "Groq client initialized successfully."
        )

        return _client

    except Exception:
        logger.exception(
            "Failed to initialize Groq client."
        )
        return None


# ============================================================
# BASIC HELPERS
# ============================================================

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


def _normalize_language(
    language: Any,
) -> str:

    value = _clean_text(
        language,
        "en",
    ).lower()

    aliases = {
        "english": "en",
        "अंग्रेजी": "en",
        "hindi": "hi",
        "हिंदी": "hi",
    }

    value = aliases.get(
        value,
        value,
    )

    if value not in {"en", "hi"}:
        return "en"

    return value


def _normalize_exam(
    exam: Any,
) -> str:

    value = _clean_text(
        exam,
        "UPSC",
    ).upper()

    if value not in {
        "UPSC",
        "BPSC",
    }:
        return "UPSC"

    return value


def _normalize_difficulty(
    difficulty: Any,
) -> str:

    value = _clean_text(
        difficulty,
        "Medium",
    ).capitalize()

    if value not in {
        "Easy",
        "Medium",
        "Hard",
    }:
        return "Medium"

    return value


def _normalize_question_type(
    question_type: Any,
) -> str:

    value = _clean_text(
        question_type,
        "single_correct",
    ).lower()

    aliases = {
        "mcq": "single_correct",
        "multiple_choice": "single_correct",
        "single_correct": "single_correct",
        "statement": "statement",
        "assertion_reason": "assertion_reason",
    }

    return aliases.get(
        value,
        "single_correct",
    )


# ============================================================
# ARTICLE HELPERS
# ============================================================

def _article_value(
    article: Any,
    *names: str,
) -> str:

    for name in names:

        try:
            value = getattr(
                article,
                name,
                None,
            )
        except Exception:
            value = None

        value = _clean_text(value)

        if value:
            return value

    return ""


def _truncate_text(
    value: str,
    max_chars: int,
) -> str:

    value = _clean_text(value)

    if len(value) <= max_chars:
        return value

    return (
        value[:max_chars].rstrip()
        + "..."
    )


def _build_article_context(
    article: Any,
) -> str:

    title = _article_value(
        article,
        "title",
        "headline",
    )

    description = _article_value(
        article,
        "description",
        "summary",
        "content",
    )

    category = _article_value(
        article,
        "category",
    )

    topic = _article_value(
        article,
        "topic",
    )

    state = _article_value(
        article,
        "state",
    )

    source = _article_value(
        article,
        "source",
        "source_name",
    )

    published_at = _article_value(
        article,
        "published_at",
        "published_date",
    )

    parts: list[str] = []

    if title:
        parts.append(
            f"TITLE: {title}"
        )

    if description:
        parts.append(
            "CONTENT: "
            + _truncate_text(
                description,
                MCQ_MAX_ARTICLE_CHARS,
            )
        )

    if category:
        parts.append(
            f"CATEGORY: {category}"
        )

    if topic:
        parts.append(
            f"TOPIC: {topic}"
        )

    if state:
        parts.append(
            f"STATE: {state}"
        )

    if source:
        parts.append(
            f"SOURCE: {source}"
        )

    if published_at:
        parts.append(
            f"DATE: {published_at}"
        )

    context = "\n".join(parts)

    return _truncate_text(
        context,
        MCQ_MAX_ARTICLE_CHARS,
    )


# ============================================================
# JSON UTILITIES
# ============================================================

def _remove_thinking_blocks(
    text: str,
) -> str:

    if not text:
        return ""

    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return text.strip()


def _remove_markdown_fences(
    text: str,
) -> str:

    text = _clean_text(text)

    text = re.sub(
        r"^\s*```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```\s*$",
        "",
        text,
    )

    return text.strip()


def _extract_balanced_json(
    text: str,
) -> Any:

    if not text:
        return None

    text = _remove_thinking_blocks(text)
    text = _remove_markdown_fences(text)

    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:
        return json.loads(text)
    except Exception:
        pass

    # --------------------------------------------------------
    # Balanced JSON object / array
    # --------------------------------------------------------

    for start_index, char in enumerate(text):

        if char not in "{[":
            continue

        stack: list[str] = []

        in_string = False
        escaped = False

        for index in range(
            start_index,
            len(text),
        ):

            current = text[index]

            if escaped:
                escaped = False
                continue

            if current == "\\" and in_string:
                escaped = True
                continue

            if current == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if current in "{[":
                stack.append(current)

            elif current in "}]":

                if not stack:
                    break

                expected = (
                    "}"
                    if stack[-1] == "{"
                    else "]"
                )

                if current != expected:
                    break

                stack.pop()

                if not stack:

                    candidate = text[
                        start_index:index + 1
                    ]

                    try:
                        return json.loads(
                            candidate
                        )
                    except Exception:
                        break

    return None


_extract_json = _extract_balanced_json


# ============================================================
# RESPONSE EXTRACTION
# ============================================================

def _get_response_content(
    response: Any,
) -> str:

    try:

        choices = getattr(
            response,
            "choices",
            None,
        )

        if not choices:
            return ""

        message = choices[0].message

        content = getattr(
            message,
            "content",
            None,
        )

        if content:
            return _clean_text(
                content
            )

        parsed = getattr(
            message,
            "parsed",
            None,
        )

        if parsed is not None:

            if isinstance(
                parsed,
                str,
            ):
                return parsed

            try:
                return json.dumps(
                    parsed,
                    ensure_ascii=False,
                )
            except Exception:
                return ""

    except Exception:
        logger.exception(
            "Unable to extract Groq response."
        )

    return ""


# ============================================================
# OPTION NORMALIZATION
# ============================================================

def _normalize_answer(
    value: Any,
) -> str:

    value = _clean_text(
        value,
        "A",
    ).upper()

    value = value.replace(
        "OPTION ",
        "",
    )

    value = value.replace(
        "ANSWER ",
        "",
    )

    value = value.strip()

    if value in {
        "A",
        "B",
        "C",
        "D",
    }:
        return value

    match = re.search(
        r"\b([ABCD])\b",
        value,
    )

    if match:
        return match.group(1)

    return "A"


def _normalize_options(
    item: dict[str, Any],
) -> list[dict[str, str]]:

    option_map: dict[str, str] = {}

    raw_options = item.get(
        "options"
    )

    if isinstance(
        raw_options,
        list,
    ):

        for option in raw_options:

            if not isinstance(
                option,
                dict,
            ):
                continue

            key = _clean_text(
                option.get("key")
            ).upper()

            text = _clean_text(
                option.get("text")
            )

            if not key:
                key = _clean_text(
                    option.get("label")
                ).upper()

            if not text:
                text = _clean_text(
                    option.get("value")
                )

            if key in {
                "A",
                "B",
                "C",
                "D",
            } and text:

                option_map[key] = text

    aliases = {
        "A": [
            "option_a",
            "A",
            "a",
        ],
        "B": [
            "option_b",
            "B",
            "b",
        ],
        "C": [
            "option_c",
            "C",
            "c",
        ],
        "D": [
            "option_d",
            "D",
            "d",
        ],
    }

    for key, fields in aliases.items():

        if key in option_map:
            continue

        for field in fields:

            text = _clean_text(
                item.get(field)
            )

            if text:
                option_map[key] = text
                break

    return [
        {
            "key": key,
            "text": option_map.get(
                key,
                "",
            ),
        }
        for key in (
            "A",
            "B",
            "C",
            "D",
        )
    ]


# ============================================================
# MCQ VALIDATION
# ============================================================

def _normalize_mcq(
    item: Any,
    exam: str,
    language: str,
    difficulty: str,
    question_type: str,
    article: Any,
) -> dict[str, Any] | None:

    if not isinstance(
        item,
        dict,
    ):
        return None

    question = _clean_text(
        item.get("question")
    )

    if not question:
        return None

    options = _normalize_options(
        item
    )

    option_texts = [
        _clean_text(
            option["text"]
        )
        for option in options
    ]

    if len(options) != 4:
        return None

    if any(
        not value
        for value in option_texts
    ):
        return None

    normalized_options = [
        re.sub(
            r"\s+",
            " ",
            value.casefold(),
        )
        for value in option_texts
    ]

    if len(
        set(normalized_options)
    ) != 4:
        return None

    correct_answer = _normalize_answer(
        item.get(
            "correct_answer",
            item.get(
                "answer",
                "A",
            ),
        )
    )

    explanation = _clean_text(
        item.get(
            "explanation"
        )
    )

    if not explanation:
        explanation = (
            "The answer is supported by "
            "the information given in the article."
        )

    category = _clean_text(
        item.get("category")
    )

    if not category:
        category = _article_value(
            article,
            "category",
        )

    if not category:
        category = "General"

    topic = _clean_text(
        item.get("topic")
    )

    state = _clean_text(
        item.get("state")
    )

    if not state:
        state = _article_value(
            article,
            "state",
        )

    return {
        "question": question,
        "options": options,
        "correct_answer": correct_answer,
        "explanation": explanation,
        "difficulty": difficulty,
        "exam": exam,
        "category": category,
        "topic": topic or None,
        "state": state or None,
        "language": language,
        "question_type": question_type,
    }


# ============================================================
# QUESTION DEDUPLICATION
# ============================================================

def _deduplicate_questions(
    questions: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    seen: set[str] = set()

    result: list[
        dict[str, Any]
    ] = []

    for question in questions:

        key = re.sub(
            r"\s+",
            " ",
            question["question"].casefold(),
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(
            question
        )

    return result


# ============================================================
# MCQ PROMPT
# ============================================================

def _build_mcq_prompt(
    article: Any,
    exam: str,
    language: str,
    count: int,
    difficulty: str,
    question_type: str,
    retry: bool = False,
) -> str:

    article_context = _build_article_context(
        article
    )

    if language == "hi":

        language_instruction = (
            "Write questions, options and "
            "explanations in natural Hindi. "
            "Keep proper nouns and technical "
            "terms in commonly used English."
        )

    else:

        language_instruction = (
            "Write all questions, options and "
            "explanations in formal English."
        )

    if exam == "BPSC":

        exam_instruction = (
            "Target BPSC examination. "
            "Use Bihar relevance only when "
            "it is explicitly present in ARTICLE."
        )

    else:

        exam_instruction = (
            "Target UPSC examination."
        )

    retry_instruction = ""

    if retry:

        retry_instruction = (
            "IMPORTANT: Previous response failed "
            "local validation. Return ONLY one "
            "valid JSON object. Do not use Markdown. "
            "Do not use code fences. Do not explain."
        )

    return f"""
You are an expert UPSC and BPSC current-affairs MCQ creator.

Generate exactly {count} competitive-examination MCQs.

EXAM: {exam}
LANGUAGE: {language}
DIFFICULTY: {difficulty}
QUESTION TYPE: {question_type}

{language_instruction}

{exam_instruction}

STRICT RULES:

1. Use ONLY information explicitly present in ARTICLE.
2. Never invent facts.
3. Generate exactly {count} questions.
4. Each question must contain exactly four options.
5. Option keys must be A, B, C and D.
6. There must be exactly one correct answer.
7. correct_answer must be exactly A, B, C or D.
8. Explanations must be supported by ARTICLE.
9. Questions must be meaningfully different.
10. Avoid generic questions about the fact that an article exists.
11. Prefer factual, conceptual, analytical and examination-oriented questions.
12. Do NOT add Markdown.
13. Do NOT add ```json.
14. Do NOT add commentary before or after the JSON.
15. Return exactly ONE JSON object.

The response must have this structure:

{{
  "questions": [
    {{
      "question": "Question text",
      "options": [
        {{"key": "A", "text": "Option A"}},
        {{"key": "B", "text": "Option B"}},
        {{"key": "C", "text": "Option C"}},
        {{"key": "D", "text": "Option D"}}
      ],
      "correct_answer": "A",
      "explanation": "Explanation based only on ARTICLE",
      "category": "General",
      "topic": null,
      "state": null
    }}
  ]
}}

{retry_instruction}

ARTICLE:
{article_context}
""".strip()


# ============================================================
# GROQ ERROR HELPERS
# ============================================================

def _is_rate_limit_error(
    exc: Exception,
) -> bool:

    text = str(exc).lower()

    return (
        "429" in text
        or "rate limit" in text
        or "rate_limit_exceeded" in text
        or "tokens per minute" in text
        or "tpm" in text
    )


def _extract_retry_seconds(
    exc: Exception,
) -> float:

    text = str(exc)

    matches = re.findall(
        r"(\d+(?:\.\d+)?)\s*s",
        text,
        flags=re.IGNORECASE,
    )

    if matches:

        try:

            value = float(
                matches[-1]
            )

            return max(
                1.0,
                min(value, 90.0),
            )

        except Exception:
            pass

    return MCQ_RATE_LIMIT_WAIT_SECONDS


# ============================================================
# GROQ MCQ CALL
# ============================================================

def _call_groq_mcq(
    client: Any,
    prompt: str,
) -> str:

    """
    IMPORTANT:

    Do NOT use response_format=json_object here.

    Qwen + Groq can return:
        json_validate_failed

    before the application receives any response.

    We therefore request normal text and perform
    JSON extraction/validation locally.
    """

    kwargs: dict[str, Any] = {
        "model": GROQ_MODEL,

        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict JSON-only "
                    "competitive examination MCQ generator. "
                    "Return one JSON object and nothing else."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],

        "temperature": GROQ_TEMPERATURE,

        "max_completion_tokens": (
            MCQ_MAX_COMPLETION_TOKENS
        ),

        "stream": False,
    }

    # --------------------------------------------------------
    # First try with hidden reasoning.
    # If model/SDK rejects it, retry without it.
    # --------------------------------------------------------

    kwargs_with_reasoning = dict(
        kwargs
    )

    kwargs_with_reasoning[
        "reasoning_format"
    ] = "hidden"

    try:

        response = (
            client
            .chat
            .completions
            .create(
                **kwargs_with_reasoning
            )
        )

    except Exception as exc:

        error_text = str(
            exc
        ).lower()

        if (
            "reasoning_format" in error_text
            or "reasoning format" in error_text
            or "unsupported" in error_text
        ):

            logger.warning(
                "Groq model rejected reasoning_format; "
                "retrying without reasoning_format."
            )

            response = (
                client
                .chat
                .completions
                .create(
                    **kwargs
                )
            )

        else:
            raise

    return _get_response_content(
        response
    )


# ============================================================
# DETERMINISTIC FALLBACK
# ============================================================

def _fallback_mcqs(
    article: Any,
    exam: str,
    language: str,
    count: int,
    difficulty: str,
    question_type: str,
) -> list[dict[str, Any]]:

    title = _article_value(
        article,
        "title",
        "headline",
    )

    description = _article_value(
        article,
        "description",
        "summary",
        "content",
    )

    category = (
        _article_value(
            article,
            "category",
        )
        or "General"
    )

    state = _article_value(
        article,
        "state",
    )

    if not title:
        title = (
            "इस समाचार"
            if language == "hi"
            else "this news article"
        )

    if not description:
        description = title

    if language == "hi":

        questions = [

            {
                "question": (
                    "इस समाचार का मुख्य विषय "
                    "निम्नलिखित में से क्या है?"
                ),
                "options": [
                    {
                        "key": "A",
                        "text": title,
                    },
                    {
                        "key": "B",
                        "text": "मौसम संबंधी जानकारी",
                    },
                    {
                        "key": "C",
                        "text": "खेल संबंधी जानकारी",
                    },
                    {
                        "key": "D",
                        "text": "मनोरंजन संबंधी जानकारी",
                    },
                ],
                "correct_answer": "A",
                "explanation": (
                    "समाचार का शीर्षक "
                    "मुख्य विषय को दर्शाता है।"
                ),
            },

            {
                "question": (
                    "दिए गए समाचार के आधार पर "
                    "किस प्रकार की जानकारी उपलब्ध है?"
                ),
                "options": [
                    {
                        "key": "A",
                        "text": "समाचार की सामग्री",
                    },
                    {
                        "key": "B",
                        "text": "केवल मौसम की जानकारी",
                    },
                    {
                        "key": "C",
                        "text": "केवल खेल की जानकारी",
                    },
                    {
                        "key": "D",
                        "text": "कोई जानकारी उपलब्ध नहीं",
                    },
                ],
                "correct_answer": "A",
                "explanation": (
                    "दिए गए article में "
                    "समाचार की सामग्री उपलब्ध है।"
                ),
            },

            {
                "question": (
                    "इस MCQ का परीक्षा संदर्भ "
                    "क्या है?"
                ),
                "options": [
                    {
                        "key": "A",
                        "text": exam,
                    },
                    {
                        "key": "B",
                        "text": "SSC",
                    },
                    {
                        "key": "C",
                        "text": "Banking",
                    },
                    {
                        "key": "D",
                        "text": "Railway",
                    },
                ],
                "correct_answer": "A",
                "explanation": (
                    f"इस MCQ generation request "
                    f"का examination context {exam} है।"
                ),
            },

            {
                "question": (
                    "समाचार की श्रेणी क्या है?"
                ),
                "options": [
                    {
                        "key": "A",
                        "text": category,
                    },
                    {
                        "key": "B",
                        "text": "मनोरंजन",
                    },
                    {
                        "key": "C",
                        "text": "खेल",
                    },
                    {
                        "key": "D",
                        "text": "मौसम",
                    },
                ],
                "correct_answer": "A",
                "explanation": (
                    f"Article की category "
                    f"{category} है।"
                ),
            },

            {
                "question": (
                    "इस समाचार से MCQ बनाते समय "
                    "किस जानकारी का उपयोग किया जाना चाहिए?"
                ),
                "options": [
                    {
                        "key": "A",
                        "text": (
                            "केवल article में उपलब्ध जानकारी"
                        ),
                    },
                    {
                        "key": "B",
                        "text": "काल्पनिक तथ्य",
                    },
                    {
                        "key": "C",
                        "text": "असंबंधित जानकारी",
                    },
                    {
                        "key": "D",
                        "text": "बाहरी अनुमान",
                    },
                ],
                "correct_answer": "A",
                "explanation": (
                    "MCQ को दिए गए article की "
                    "उपलब्ध जानकारी पर आधारित होना चाहिए।"
                ),
            },
        ]

    else:

        questions = [

            {
                "question": (
                    "What is the primary subject "
                    "of this news article?"
                ),
                "options": [
                    {
                        "key": "A",
                        "text": title,
                    },
                    {
                        "key": "B",
                        "text": "Weather information",
                    },
                    {
                        "key": "C",
                        "text": "Sports information",
                    },
                    {
                        "key": "D",
                        "text": "Entertainment information",
                    },
                ],
                "correct_answer": "A",
                "explanation": (
                    "The article title identifies "
                    "the primary subject."
                ),
            },

            {
                "question": (
                    "What type of information is "
                    "provided in the article?"
                ),
                "options": [
                    {
                        "key": "A",
                        "text": "News content",
                    },
                    {
                        "key": "B",
                        "text": "Only weather information",
                    },
                    {
                        "key": "C",
                        "text": "Only sports information",
                    },
                    {
                        "key": "D",
                        "text": "No information",
                    },
                ],
                "correct_answer": "A",
                "explanation": (
                    "The supplied article contains "
                    "news-related content."
                ),
            },

            {
                "question": (
                    "Which examination context "
                    "is specified?"
                ),
                "options": [
                    {
                        "key": "A",
                        "text": exam,
                    },
                    {
                        "key": "B",
                        "text": "SSC",
                    },
                    {
                        "key": "C",
                        "text": "Banking",
                    },
                    {
                        "key": "D",
                        "text": "Railway",
                    },
                ],
                "correct_answer": "A",
                "explanation": (
                    f"The requested examination "
                    f"context is {exam}."
                ),
            },

            {
                "question": (
                    "What is the category of "
                    "the news article?"
                ),
                "options": [
                    {
                        "key": "A",
                        "text": category,
                    },
                    {
                        "key": "B",
                        "text": "Entertainment",
                    },
                    {
                        "key": "C",
                        "text": "Sports",
                    },
                    {
                        "key": "D",
                        "text": "Weather",
                    },
                ],
                "correct_answer": "A",
                "explanation": (
                    f"The article category is "
                    f"{category}."
                ),
            },

            {
                "question": (
                    "What information should be "
                    "used when generating questions "
                    "from this article?"
                ),
                "options": [
                    {
                        "key": "A",
                        "text": (
                            "Only information available "
                            "in the article"
                        ),
                    },
                    {
                        "key": "B",
                        "text": "Invented facts",
                    },
                    {
                        "key": "C",
                        "text": "Unrelated information",
                    },
                    {
                        "key": "D",
                        "text": "Unsupported assumptions",
                    },
                ],
                "correct_answer": "A",
                "explanation": (
                    "Questions should be based only "
                    "on information contained in "
                    "the supplied article."
                ),
            },
        ]

    result: list[
        dict[str, Any]
    ] = []

    for item in questions[:count]:

        result.append(
            {
                "question": item["question"],
                "options": item["options"],
                "correct_answer": item[
                    "correct_answer"
                ],
                "explanation": item[
                    "explanation"
                ],
                "difficulty": difficulty,
                "exam": exam,
                "category": category,
                "topic": None,
                "state": state or None,
                "language": language,
                "question_type": question_type,
                "generation_source": "fallback",
            }
        )

    return result


# ============================================================
# MAIN MCQ GENERATOR
# ============================================================

def generate_news_mcqs(
    article: Any,
    exam: str = "UPSC",
    language: str = "en",
    count: int = 5,
    difficulty: str = "Medium",
    question_type: str = "single_correct",
) -> list[dict[str, Any]]:

    exam = _normalize_exam(
        exam
    )

    language = _normalize_language(
        language
    )

    difficulty = _normalize_difficulty(
        difficulty
    )

    question_type = _normalize_question_type(
        question_type
    )

    try:
        count = int(count)
    except Exception:
        count = 5

    count = max(
        1,
        min(count, 10),
    )

    # ========================================================
    # ARTICLE VALIDATION
    # ========================================================

    if article is None:

        logger.error(
            "MCQ generation failed: article=None."
        )

        return []

    article_id = getattr(
        article,
        "id",
        None,
    )

    article_context = _build_article_context(
        article
    )

    if not article_context:

        logger.error(
            "MCQ generation failed: "
            "article_id=%s has no usable content.",
            article_id,
        )

        return []

    # ========================================================
    # GROQ CLIENT
    # ========================================================

    client = _get_client()

    if client is None:

        logger.warning(
            "Groq unavailable | article_id=%s | "
            "using deterministic fallback.",
            article_id,
        )

        return _fallback_mcqs(
            article=article,
            exam=exam,
            language=language,
            count=count,
            difficulty=difficulty,
            question_type=question_type,
        )

    best_questions: list[
        dict[str, Any]
    ] = []

    # ========================================================
    # RETRY LOOP
    # ========================================================

    for attempt in range(
        1,
        MCQ_MAX_ATTEMPTS + 1,
    ):

        prompt = _build_mcq_prompt(
            article=article,
            exam=exam,
            language=language,
            count=count,
            difficulty=difficulty,
            question_type=question_type,
            retry=attempt > 1,
        )

        logger.info(
            "Generating MCQs | "
            "article_id=%s | "
            "attempt=%s/%s | "
            "count=%s | "
            "exam=%s | "
            "language=%s | "
            "model=%s",
            article_id,
            attempt,
            MCQ_MAX_ATTEMPTS,
            count,
            exam,
            language,
            GROQ_MODEL,
        )

        try:

            # IMPORTANT:
            # Never pass response_format=json_object.
            content = _call_groq_mcq(
                client=client,
                prompt=prompt,
            )

        except Exception as exc:

            # ------------------------------------------------
            # RATE LIMIT
            # ------------------------------------------------

            if _is_rate_limit_error(exc):

                wait_seconds = (
                    _extract_retry_seconds(
                        exc
                    )
                )

                if attempt < MCQ_MAX_ATTEMPTS:

                    logger.warning(
                        "Groq rate limit | "
                        "article_id=%s | "
                        "attempt=%s | "
                        "waiting=%.1fs",
                        article_id,
                        attempt,
                        wait_seconds,
                    )

                    time.sleep(
                        wait_seconds
                    )

                continue

            # ------------------------------------------------
            # OTHER API ERROR
            # ------------------------------------------------

            logger.error(
                "Groq MCQ API failed | "
                "article_id=%s | "
                "attempt=%s | "
                "error=%s",
                article_id,
                attempt,
                exc,
            )

            if attempt < MCQ_MAX_ATTEMPTS:

                delay = (
                    MCQ_RETRY_DELAY_SECONDS
                    * attempt
                    + random.uniform(
                        0.0,
                        0.5,
                    )
                )

                time.sleep(
                    delay
                )

            continue

        # ====================================================
        # EMPTY RESPONSE
        # ====================================================

        if not content:

            logger.warning(
                "Empty Groq response | "
                "article_id=%s | "
                "attempt=%s",
                article_id,
                attempt,
            )

            if attempt < MCQ_MAX_ATTEMPTS:

                time.sleep(
                    MCQ_RETRY_DELAY_SECONDS
                    * attempt
                )

            continue

        # ====================================================
        # RESPONSE PREVIEW
        # ====================================================

        logger.debug(
            "Groq raw response preview | "
            "article_id=%s | "
            "attempt=%s | "
            "response=%s",
            article_id,
            attempt,
            content[
                :MCQ_RESPONSE_LOG_CHARS
            ],
        )

        # ====================================================
        # PARSE JSON LOCALLY
        # ====================================================

        parsed = _extract_json(
            content
        )

        if parsed is None:

            logger.warning(
                "Invalid JSON returned by Groq | "
                "article_id=%s | "
                "attempt=%s",
                article_id,
                attempt,
            )

            if attempt < MCQ_MAX_ATTEMPTS:

                time.sleep(
                    MCQ_RETRY_DELAY_SECONDS
                    * attempt
                )

            continue

        # ====================================================
        # EXTRACT QUESTIONS
        # ====================================================

        if isinstance(
            parsed,
            dict,
        ):

            raw_questions = parsed.get(
                "questions"
            )

            if not isinstance(
                raw_questions,
                list,
            ):

                if parsed.get(
                    "question"
                ):
                    raw_questions = [
                        parsed
                    ]
                else:
                    raw_questions = []

        elif isinstance(
            parsed,
            list,
        ):

            raw_questions = parsed

        else:

            raw_questions = []

        if not raw_questions:

            logger.warning(
                "Groq JSON contains no questions | "
                "article_id=%s | "
                "attempt=%s",
                article_id,
                attempt,
            )

            continue

        # ====================================================
        # NORMALIZE + VALIDATE
        # ====================================================

        current_questions: list[
            dict[str, Any]
        ] = []

        for item in raw_questions:

            normalized = _normalize_mcq(
                item=item,
                exam=exam,
                language=language,
                difficulty=difficulty,
                question_type=question_type,
                article=article,
            )

            if normalized is None:

                logger.warning(
                    "Skipping invalid AI-generated MCQ | "
                    "article_id=%s",
                    article_id,
                )

                continue

            current_questions.append(
                normalized
            )

        # ====================================================
        # DEDUPLICATE
        # ====================================================

        current_questions = (
            _deduplicate_questions(
                current_questions
            )
        )

        # ====================================================
        # KEEP BEST RESULT
        # ====================================================

        if len(
            current_questions
        ) > len(
            best_questions
        ):

            best_questions = (
                current_questions
            )

        # ====================================================
        # COMPLETE RESULT
        # ====================================================

        if len(
            current_questions
        ) >= count:

            result = current_questions[
                :count
            ]

            for item in result:

                item[
                    "generation_source"
                ] = "groq"

            logger.info(
                "Groq MCQ generation successful | "
                "article_id=%s | "
                "generated=%s | "
                "attempt=%s",
                article_id,
                len(result),
                attempt,
            )

            return result

        logger.warning(
            "Partial Groq MCQ result | "
            "article_id=%s | "
            "generated=%s/%s | "
            "attempt=%s",
            article_id,
            len(current_questions),
            count,
            attempt,
        )

    # ========================================================
    # PARTIAL AI RESULT
    # ========================================================

    if len(
        best_questions
    ) >= 1:

        logger.warning(
            "Groq generated partial MCQs | "
            "article_id=%s | "
            "generated=%s/%s | "
            "using partial result.",
            article_id,
            len(best_questions),
            count,
        )

        for item in best_questions:

            item[
                "generation_source"
            ] = "groq_partial"

        return best_questions

    # ========================================================
    # FINAL FALLBACK
    # ========================================================

    logger.warning(
        "Groq MCQ generation failed completely | "
        "article_id=%s | "
        "attempts=%s | "
        "using deterministic fallback.",
        article_id,
        MCQ_MAX_ATTEMPTS,
    )

    return _fallback_mcqs(
        article=article,
        exam=exam,
        language=language,
        count=count,
        difficulty=difficulty,
        question_type=question_type,
    )


# ============================================================
# SIMPLE NEWS HELPERS
# ============================================================

def generate_summary(
    title: str,
    description: str | None,
) -> str:

    title = _clean_text(
        title
    )

    description = _clean_text(
        description
    )

    if description:
        return description

    return title


def generate_prelims_notes(
    title: str,
    description: str | None,
) -> str:

    title = _clean_text(
        title
    )

    return (
        "Important for competitive examinations: "
        f"{title}"
    )


def generate_mains_notes(
    title: str,
    description: str | None,
) -> str:

    title = _clean_text(
        title
    )

    return (
        "Analyze the significance, impact, "
        "opportunities and challenges related to: "
        f"{title}"
    )

