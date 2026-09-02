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

try:
    GROQ_TEMPERATURE = float(
        os.getenv("GROQ_TEMPERATURE", "0.1")
    )
except (TypeError, ValueError):
    GROQ_TEMPERATURE = 0.1


try:
    MAX_COMPLETION_TOKENS = int(
        os.getenv(
            "MAX_COMPLETION_TOKENS",
            "3000",
        )
    )
except (TypeError, ValueError):
    MAX_COMPLETION_TOKENS = 3000


try:
    MCQ_MAX_COMPLETION_TOKENS = int(
        os.getenv(
            "MCQ_MAX_COMPLETION_TOKENS",
            "2200",
        )
    )
except (TypeError, ValueError):
    MCQ_MAX_COMPLETION_TOKENS = 2200


try:
    MCQ_MAX_ATTEMPTS = int(
        os.getenv(
            "MCQ_MAX_ATTEMPTS",
            "3",
        )
    )
except (TypeError, ValueError):
    MCQ_MAX_ATTEMPTS = 3


try:
    MCQ_MAX_ARTICLE_CHARS = int(
        os.getenv(
            "MCQ_MAX_ARTICLE_CHARS",
            "6500",
        )
    )
except (TypeError, ValueError):
    MCQ_MAX_ARTICLE_CHARS = 6500


try:
    MCQ_RETRY_DELAY_SECONDS = float(
        os.getenv(
            "MCQ_RETRY_DELAY_SECONDS",
            "1.5",
        )
    )
except (TypeError, ValueError):
    MCQ_RETRY_DELAY_SECONDS = 1.5


try:
    MCQ_RATE_LIMIT_WAIT_SECONDS = float(
        os.getenv(
            "MCQ_RATE_LIMIT_WAIT_SECONDS",
            "35",
        )
    )
except (TypeError, ValueError):
    MCQ_RATE_LIMIT_WAIT_SECONDS = 35.0


try:
    MCQ_RESPONSE_LOG_CHARS = int(
        os.getenv(
            "MCQ_RESPONSE_LOG_CHARS",
            "1200",
        )
    )
except (TypeError, ValueError):
    MCQ_RESPONSE_LOG_CHARS = 1200


try:
    MCQ_MAX_RATE_LIMIT_WAIT_SECONDS = float(
        os.getenv(
            "MCQ_MAX_RATE_LIMIT_WAIT_SECONDS",
            "90",
        )
    )
except (TypeError, ValueError):
    MCQ_MAX_RATE_LIMIT_WAIT_SECONDS = 90.0


# ============================================================
# SUPPORTED VALUES
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
    "single_correct",
    "statement",
    "assertion_reason",
}

OPTION_KEYS = (
    "A",
    "B",
    "C",
    "D",
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
    """
    Lazily initialize Groq client.
    """

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

    if value not in SUPPORTED_LANGUAGES:
        return "en"

    return value


def _normalize_exam(
    exam: Any,
) -> str:

    value = _clean_text(
        exam,
        "UPSC",
    ).upper()

    if value not in SUPPORTED_EXAMS:
        return "UPSC"

    return value


def _normalize_difficulty(
    difficulty: Any,
) -> str:

    value = _clean_text(
        difficulty,
        "Medium",
    ).capitalize()

    if value not in SUPPORTED_DIFFICULTIES:
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
        "single": "single_correct",
        "single_correct": "single_correct",
        "statement": "statement",
        "assertion_reason": "assertion_reason",
        "assertion-reason": "assertion_reason",
    }

    return aliases.get(
        value,
        "single_correct",
    )


def _safe_int(
    value: Any,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:

    try:
        value = int(value)
    except Exception:
        value = default

    if minimum is not None:
        value = max(
            minimum,
            value,
        )

    if maximum is not None:
        value = min(
            maximum,
            value,
        )

    return value


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

    if max_chars <= 0:
        return ""

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
        "body",
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
        "published",
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
# THINKING / MARKDOWN CLEANING
# ============================================================

def _remove_thinking_blocks(
    text: str,
) -> str:

    if not text:
        return ""

    text = str(text)

    patterns = (
        r"<think>.*?</think>",
        r"<thinking>.*?</thinking>",
        r"<analysis>.*?</analysis>",
    )

    for pattern in patterns:

        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

    text = re.sub(
        r"<think>.*$",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<thinking>.*$",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<analysis>.*$",
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
        flags=re.IGNORECASE,
    )

    return text.strip()


# ============================================================
# JSON EXTRACTION
# ============================================================

def _extract_balanced_json(
    text: str,
) -> Any:

    if not text:
        return None

    text = _remove_thinking_blocks(text)
    text = _remove_markdown_fences(text)

    try:
        return json.loads(text)
    except Exception:
        pass

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
# GROQ RESPONSE EXTRACTION
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
            logger.warning(
                "Groq response contains no choices."
            )
            return ""

        message = choices[0].message

        content = getattr(
            message,
            "content",
            None,
        )

        if content:

            return _remove_thinking_blocks(
                _clean_text(content)
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
                return _remove_thinking_blocks(
                    parsed
                )

            try:
                return _remove_thinking_blocks(
                    json.dumps(
                        parsed,
                        ensure_ascii=False,
                    )
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
) -> str | None:

    value = _clean_text(
        value
    ).upper()

    value = value.replace(
        "OPTION ",
        "",
    )

    value = value.replace(
        "ANSWER ",
        "",
    )

    value = value.strip(
        " .:-)"
    )

    if value in OPTION_KEYS:
        return value

    match = re.search(
        r"\b([ABCD])\b",
        value,
    )

    if match:
        return match.group(1)

    return None


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

            key = key.strip(
                " .:)"
            )

            if (
                key in OPTION_KEYS
                and text
            ):
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
        for key in OPTION_KEYS
    ]


# ============================================================
# BAD / META QUESTION DETECTION
# ============================================================

META_QUESTION_PATTERNS = [
    r"\bwhat is the exam\b",
    r"\bwhich exam\b",
    r"\bexamination context\b",
    r"\bmcq generation\b",
    r"\bquestion generation\b",
    r"\bwhat should be used\b",
    r"\bwhat category\b",
    r"\bwhich category\b",
    r"\barticle category\b",
    r"\bprovided article\b",
    r"\bsupplied article\b",
    r"\bwhat is the language\b",
    r"\bwhich language\b",
    r"\bwhat type of question\b",
    r"\bquestion type\b",
    r"\bthis mcq\b",
    r"\bthis article\b",
    r"\bnews article\b",
]


def _is_meta_question(
    question: str,
) -> bool:

    text = _clean_text(
        question
    ).casefold()

    if not text:
        return True

    for pattern in META_QUESTION_PATTERNS:

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return True

    return False


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

    if len(question) < 15:
        return None

    # Reject meta questions.
    if _is_meta_question(question):
        logger.warning(
            "Rejected meta MCQ: %s",
            question,
        )
        return None

    options = _normalize_options(
        item
    )

    if len(options) != 4:
        return None

    option_texts = [
        _clean_text(
            option["text"]
        )
        for option in options
    ]

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

        logger.warning(
            "MCQ rejected because options are duplicated."
        )

        return None

    correct_answer = _normalize_answer(
        item.get(
            "correct_answer",
            item.get("answer"),
        )
    )

    if correct_answer not in OPTION_KEYS:

        logger.warning(
            "Invalid correct_answer from AI: %s",
            item.get("correct_answer"),
        )

        return None

    explanation = _clean_text(
        item.get("explanation")
    )

    if not explanation:
        return None

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

def _question_key(
    question: str,
) -> str:

    value = _clean_text(
        question
    ).casefold()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    value = re.sub(
        r"[^\w\s\u0900-\u097F]",
        "",
        value,
    )

    return value.strip()


def _deduplicate_questions(
    questions: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    seen: set[str] = set()

    result: list[
        dict[str, Any]
    ] = []

    for question in questions:

        key = _question_key(
            question.get(
                "question",
                "",
            )
        )

        if not key:
            continue

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
    existing_questions: list[str] | None = None,
    retry: bool = False,
) -> str:

    article_context = _build_article_context(
        article
    )

    # --------------------------------------------------------
    # Language
    # --------------------------------------------------------

    if language == "hi":

        language_instruction = """
Write the question, all options and explanation in
natural competitive-examination Hindi.

Use English only for unavoidable proper nouns,
technical names, institutions, abbreviations,
scientific terms and official names.

Do NOT copy the entire English article title as an option.
""".strip()

    else:

        language_instruction = """
Write the question, all options and explanation
in formal competitive-examination English.
""".strip()

    # --------------------------------------------------------
    # Exam
    # --------------------------------------------------------

    if exam == "BPSC":

        exam_instruction = """
Target BPSC examination.

Use Bihar-specific relevance ONLY if Bihar-related
facts are explicitly present in the ARTICLE.
""".strip()

    else:

        exam_instruction = """
Target UPSC Civil Services examination.

Focus on factual, conceptual and analytical
current-affairs questions.
""".strip()

    # --------------------------------------------------------
    # Question type
    # --------------------------------------------------------

    if question_type == "statement":

        question_type_instruction = """
Use statement-based MCQs.

Each question should contain 2-4 numbered statements.
Options must represent combinations of those statements.
There must be exactly one correct combination.
""".strip()

    elif question_type == "assertion_reason":

        question_type_instruction = """
Use Assertion-Reason format.

Both Assertion and Reason must be based ONLY
on information explicitly present in the ARTICLE.

Do not use outside knowledge.
""".strip()

    else:

        question_type_instruction = """
Use standard single-correct-answer MCQs.
""".strip()

    # --------------------------------------------------------
    # Duplicate avoidance
    # --------------------------------------------------------

    duplicate_instruction = ""

    if existing_questions:

        clean_existing = [
            _clean_text(q)
            for q in existing_questions
            if _clean_text(q)
        ]

        if clean_existing:

            duplicate_lines = "\n".join(
                f"- {question}"
                for question in clean_existing[:20]
            )

            duplicate_instruction = f"""
DO NOT repeat or rephrase these already generated questions:

{duplicate_lines}
""".strip()

    # --------------------------------------------------------
    # Retry
    # --------------------------------------------------------

    retry_instruction = ""

    if retry:

        retry_instruction = """
IMPORTANT RETRY:

The previous response failed local validation
or did not contain enough valid MCQs.

Return ONLY valid JSON.

Do not use Markdown.
Do not use code fences.
Do not add commentary.
Do not generate meta questions.
""".strip()

    # --------------------------------------------------------
    # Critical anti-meta instructions
    # --------------------------------------------------------

    anti_meta_instruction = """
CRITICAL QUESTION QUALITY RULES:

NEVER ask:

- What is the exam?
- Which exam is this for?
- What is the category?
- Which category does the article belong to?
- What is the language?
- What is the question type?
- What is the MCQ generation context?
- What should be used to generate an MCQ?
- What is the source of this article?
- What is the article about in a generic way?
- Whether the article contains information.

NEVER make UPSC, BPSC, category, language,
question_type or generation request itself
the subject of a question.

The question MUST test an actual factual,
conceptual or analytical point contained in ARTICLE.

For example, if ARTICLE says:

"NASA considered 86,000 satellite designs,
selected a satellite built for about $1,500,
the satellite weighed 64 grams,
and it demonstrated 3D-printed satellite technology."

Good questions include:

- Approximately how many satellite designs were considered?
- What was notable about the satellite's weight?
- What was the approximate development cost mentioned?
- What technology was the satellite intended to demonstrate?

Bad questions include:

- Which exam is this MCQ for?
- What is the article category?
- What should be used to generate this MCQ?
- What is the source of the article?

Every question must be answerable from ARTICLE alone.
""".strip()

    # --------------------------------------------------------
    # Final prompt
    # --------------------------------------------------------

    return f"""
You are an expert UPSC and BPSC current-affairs MCQ creator.

Generate exactly {count} high-quality competitive-examination MCQs.

EXAM:
{exam}

LANGUAGE:
{language}

DIFFICULTY:
{difficulty}

QUESTION TYPE:
{question_type}

{language_instruction}

{exam_instruction}

{question_type_instruction}

{anti_meta_instruction}

STRICT FACTUAL RULES:

1. Use ONLY information explicitly present in ARTICLE.
2. Never invent facts.
3. Never use outside knowledge.
4. Every correct answer must be directly supported by ARTICLE.
5. Every explanation must be directly supported by ARTICLE.
6. Generate exactly {count} questions.
7. Every question must have exactly four options.
8. Option keys must be exactly A, B, C and D.
9. There must be exactly one correct answer.
10. correct_answer must be exactly A, B, C or D.
11. All four options must be different.
12. Questions must be meaningfully different.
13. Do not repeat the same fact unnecessarily.
14. Avoid generic questions.
15. Avoid article-existence questions.
16. Avoid category-only questions.
17. Avoid exam-only questions.
18. Avoid source-only questions.
19. Avoid language-only questions.
20. Avoid generation-context questions.
21. Prefer concrete facts, numbers, names, technologies,
    institutions, events, causes, objectives and implications
    explicitly mentioned in ARTICLE.
22. For numerical facts, create plausible distractors
    using different numbers but do not introduce unrelated facts.
23. For conceptual questions, keep the concept directly
    grounded in ARTICLE.
24. Do not invent Bihar relevance for BPSC.
25. Do not include Markdown.
26. Do not include ```json.
27. Do not include commentary before or after JSON.
28. Return exactly ONE JSON object.

{duplicate_instruction}

REQUIRED JSON STRUCTURE:

{{
  "questions": [
    {{
      "question": "Actual factual question based on ARTICLE",
      "options": [
        {{
          "key": "A",
          "text": "Option A"
        }},
        {{
          "key": "B",
          "text": "Option B"
        }},
        {{
          "key": "C",
          "text": "Option C"
        }},
        {{
          "key": "D",
          "text": "Option D"
        }}
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
        or "too many requests" in text
    )


def _extract_retry_seconds(
    exc: Exception,
) -> float:

    text = str(exc)

    patterns = [
        r"retry\s+after\s+(\d+(?:\.\d+)?)\s*s",
        r"retry\s+in\s+(\d+(?:\.\d+)?)\s*s",
        r"(\d+(?:\.\d+)?)\s*seconds?",
        r"(\d+(?:\.\d+)?)\s*s\b",
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not matches:
            continue

        try:

            value = float(
                matches[-1]
            )

            return max(
                1.0,
                min(
                    value,
                    MCQ_MAX_RATE_LIMIT_WAIT_SECONDS,
                ),
            )

        except Exception:
            continue

    return max(
        1.0,
        min(
            MCQ_RATE_LIMIT_WAIT_SECONDS,
            MCQ_MAX_RATE_LIMIT_WAIT_SECONDS,
        ),
    )


# ============================================================
# GROQ MCQ CALL
# ============================================================

def _call_groq_mcq(
    client: Any,
    prompt: str,
) -> str:

    kwargs: dict[str, Any] = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict JSON-only "
                    "competitive examination MCQ generator. "
                    "Return exactly one JSON object. "
                    "Every question must be based on "
                    "actual facts in the ARTICLE. "
                    "Never create meta questions about "
                    "exam, category, language or generation. "
                    "Do not return Markdown. "
                    "Do not return reasoning. "
                    "Do not return commentary."
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

    try:

        response = (
            client
            .chat
            .completions
            .create(
                **kwargs
            )
        )

    except Exception:

        logger.exception(
            "Groq MCQ request failed."
        )

        raise

    content = _get_response_content(
        response
    )

    logger.debug(
        "Groq cleaned MCQ response | "
        "chars=%s | preview=%s",
        len(content),
        content[
            :MCQ_RESPONSE_LOG_CHARS
        ],
    )

    return content


# ============================================================
# SENTENCE EXTRACTION
# ============================================================

def _extract_sentences(
    text: str,
    limit: int = 20,
) -> list[str]:

    text = _clean_text(text)

    if not text:
        return []

    parts = re.split(
        r"(?<=[.!?।])\s+",
        text,
    )

    result: list[str] = []

    for part in parts:

        part = _clean_text(part)

        if len(part) < 25:
            continue

        result.append(part)

        if len(result) >= limit:
            break

    return result


# ============================================================
# FACT EXTRACTION FOR FALLBACK
# ============================================================

def _extract_numeric_facts(
    text: str,
) -> list[tuple[str, str]]:

    facts: list[
        tuple[str, str]
    ] = []

    text = _clean_text(text)

    if not text:
        return facts

    patterns = [
        r"\b\d[\d,]*(?:\.\d+)?\s*(?:grams?|kg|kilograms?|km|million|billion|crore|lakh|years?|days?|percent|%)\b",
        r"\$\s?\d[\d,]*(?:\.\d+)?",
        r"\b\d[\d,]*\b",
    ]

    seen: set[str] = set()

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):

            value = match.group(0).strip()

            key = value.casefold()

            if key in seen:
                continue

            seen.add(key)

            start = max(
                0,
                match.start() - 90,
            )

            end = min(
                len(text),
                match.end() + 120,
            )

            context = _clean_text(
                text[start:end]
            )

            if context:
                facts.append(
                    (
                        value,
                        context,
                    )
                )

    return facts[:12]


# ============================================================
# FALLBACK OPTION BUILDER
# ============================================================

def _fallback_option_set(
    correct: str,
    alternatives: list[str],
) -> list[dict[str, str]]:

    values = [
        correct,
        *alternatives,
    ]

    values = [
        _clean_text(value)
        for value in values
        if _clean_text(value)
    ]

    unique: list[str] = []

    seen: set[str] = set()

    for value in values:

        key = value.casefold()

        if key in seen:
            continue

        seen.add(key)

        unique.append(value)

    while len(unique) < 4:

        unique.append(
            f"Not stated in the article ({len(unique) + 1})"
        )

    unique = unique[:4]

    # Shuffle correct answer position.
    correct_value = unique[0]

    other_values = unique[1:]

    random.shuffle(other_values)

    shuffled = [
        correct_value,
        *other_values,
    ]

    random.shuffle(shuffled)

    result: list[
        dict[str, str]
    ] = []

    for key, text in zip(
        OPTION_KEYS,
        shuffled,
    ):

        result.append(
            {
                "key": key,
                "text": text,
            }
        )

    return result


def _find_correct_option_key(
    options: list[dict[str, str]],
    correct_text: str,
) -> str:

    correct_key = "A"

    target = _clean_text(
        correct_text
    ).casefold()

    for option in options:

        if (
            _clean_text(
                option.get("text")
            ).casefold()
            == target
        ):
            correct_key = option["key"]
            break

    return correct_key


# ============================================================
# INTELLIGENT DETERMINISTIC FALLBACK
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
        "body",
    )

    category = (
        _article_value(
            article,
            "category",
        )
        or "General"
    )

    topic = _article_value(
        article,
        "topic",
    )

    state = _article_value(
        article,
        "state",
    )

    if not description:
        description = title

    if not description:
        return []

    sentences = _extract_sentences(
        description,
        limit=20,
    )

    numeric_facts = _extract_numeric_facts(
        description
    )

    result: list[
        dict[str, Any]
    ] = []

    used_questions: set[str] = set()

    # --------------------------------------------------------
    # Numeric factual questions
    # --------------------------------------------------------

    numeric_templates_hi = [
        (
            "समाचार के अनुसार, निम्नलिखित में से कौन-सा "
            "आंकड़ा/मान सही है?"
        ),
        (
            "दिए गए समाचार के अनुसार, निम्नलिखित में से "
            "कौन-सा आंकड़ा उल्लेखित है?"
        ),
        (
            "समाचार में उल्लिखित संख्या/मान के संबंध में "
            "निम्नलिखित में से कौन-सा सही है?"
        ),
    ]

    numeric_templates_en = [
        (
            "According to the article, which of the "
            "following figures is correct?"
        ),
        (
            "Which of the following figures is mentioned "
            "in the article?"
        ),
        (
            "According to the article, which of the "
            "following values is correct?"
        ),
    ]

    for index, (
        value,
        context,
    ) in enumerate(numeric_facts):

        if len(result) >= count:
            break

        if language == "hi":

            question_text = (
                numeric_templates_hi[
                    index % len(
                        numeric_templates_hi
                    )
                ]
            )

            explanation = (
                f"समाचार में यह आंकड़ा स्पष्ट रूप से "
                f"उल्लेखित है: {value}।"
            )

        else:

            question_text = (
                numeric_templates_en[
                    index % len(
                        numeric_templates_en
                    )
                ]
            )

            explanation = (
                f"The article explicitly mentions "
                f"the figure {value}."
            )

        key = _question_key(
            question_text
        )

        if key in used_questions:
            continue

        used_questions.add(key)

        # Generate numeric distractors.
        number_match = re.search(
            r"\d[\d,]*(?:\.\d+)?",
            value,
        )

        if number_match:

            raw_number = number_match.group(0)

            try:

                number = float(
                    raw_number.replace(
                        ",",
                        "",
                    )
                )

                if number >= 1000:

                    alternatives = [
                        f"{int(number * 0.5):,}",
                        f"{int(number * 0.75):,}",
                        f"{int(number * 1.25):,}",
                    ]

                elif number >= 100:

                    alternatives = [
                        f"{int(number * 0.5)}",
                        f"{int(number * 0.75)}",
                        f"{int(number * 1.5)}",
                    ]

                else:

                    alternatives = [
                        f"{max(1, int(number) - 10)}",
                        f"{max(1, int(number) + 10)}",
                        f"{max(1, int(number) * 2)}",
                    ]

                suffix = value[
                    number_match.end():
                ]

                correct = (
                    raw_number
                    + suffix
                )

                alternatives = [
                    alt + suffix
                    for alt in alternatives
                ]

            except Exception:

                correct = value

                alternatives = [
                    "The article does not specify this",
                    "A different value",
                    "No figure is mentioned",
                ]

        else:

            correct = value

            alternatives = [
                "The article does not specify this",
                "A different value",
                "No figure is mentioned",
            ]

        options = _fallback_option_set(
            correct=correct,
            alternatives=alternatives,
        )

        correct_key = _find_correct_option_key(
            options,
            correct,
        )

        result.append(
            {
                "question": question_text,
                "options": options,
                "correct_answer": correct_key,
                "explanation": explanation,
                "difficulty": difficulty,
                "exam": exam,
                "category": category,
                "topic": topic or None,
                "state": state or None,
                "language": language,
                "question_type": question_type,
                "generation_source": "fallback",
            }
        )

    # --------------------------------------------------------
    # Sentence-based factual questions
    # --------------------------------------------------------

    for index, sentence in enumerate(
        sentences
    ):

        if len(result) >= count:
            break

        if len(sentence) < 30:
            continue

        if language == "hi":

            question_text = (
                "दिए गए समाचार के अनुसार, "
                "निम्नलिखित में से कौन-सा कथन सही है?"
            )

            correct = sentence

            alternatives = [
                "यह तथ्य समाचार में उल्लेखित नहीं है",
                "यह केवल काल्पनिक जानकारी है",
                "यह समाचार की सामग्री के विपरीत है",
            ]

            explanation = (
                "सही विकल्प दिए गए समाचार की सामग्री "
                "से सीधे लिया गया है।"
            )

        else:

            question_text = (
                "According to the article, which of "
                "the following statements is correct?"
            )

            correct = sentence

            alternatives = [
                "This fact is not mentioned in the article",
                "This is only hypothetical information",
                "This contradicts the article",
            ]

            explanation = (
                "The correct option is directly supported "
                "by the supplied article."
            )

        key = _question_key(
            question_text
        )

        # Add sentence-specific uniqueness.
        key = key + "|" + _question_key(
            sentence[:80]
        )

        if key in used_questions:
            continue

        used_questions.add(key)

        options = _fallback_option_set(
            correct=correct,
            alternatives=alternatives,
        )

        correct_key = _find_correct_option_key(
            options,
            correct,
        )

        result.append(
            {
                "question": question_text,
                "options": options,
                "correct_answer": correct_key,
                "explanation": explanation,
                "difficulty": difficulty,
                "exam": exam,
                "category": category,
                "topic": topic or None,
                "state": state or None,
                "language": language,
                "question_type": question_type,
                "generation_source": "fallback",
            }
        )

    # --------------------------------------------------------
    # Final deduplication
    # --------------------------------------------------------

    result = _deduplicate_questions(
        result
    )

    return result[:count]


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

    # --------------------------------------------------------
    # Normalize inputs
    # --------------------------------------------------------

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

    count = _safe_int(
        count,
        default=5,
        minimum=1,
        maximum=10,
    )

    # --------------------------------------------------------
    # Article validation
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Groq client
    # --------------------------------------------------------

    client = _get_client()

    if client is None:

        logger.warning(
            "Groq unavailable | article_id=%s | "
            "using intelligent fallback.",
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

    # --------------------------------------------------------
    # Generate requested MCQs
    # --------------------------------------------------------

    collected: list[
        dict[str, Any]
    ] = []

    total_attempts = max(
        1,
        MCQ_MAX_ATTEMPTS,
    )

    for attempt in range(
        1,
        total_attempts + 1,
    ):

        remaining = count - len(
            collected
        )

        if remaining <= 0:
            break

        logger.info(
            "Generating MCQs | "
            "article_id=%s | attempt=%s/%s | "
            "requested=%s | collected=%s | remaining=%s | "
            "exam=%s | language=%s | type=%s | model=%s",
            article_id,
            attempt,
            total_attempts,
            count,
            len(collected),
            remaining,
            exam,
            language,
            question_type,
            GROQ_MODEL,
        )

        # ----------------------------------------------------
        # Existing generated questions
        # ----------------------------------------------------

        existing_questions = [
            item.get(
                "question",
                "",
            )
            for item in collected
            if item.get("question")
        ]

        # ----------------------------------------------------
        # Prompt
        # ----------------------------------------------------

        prompt = _build_mcq_prompt(
            article=article,
            exam=exam,
            language=language,
            count=remaining,
            difficulty=difficulty,
            question_type=question_type,
            existing_questions=existing_questions,
            retry=attempt > 1,
        )

        # ----------------------------------------------------
        # Groq request
        # ----------------------------------------------------

        try:

            content = _call_groq_mcq(
                client=client,
                prompt=prompt,
            )

        except Exception as exc:

            if _is_rate_limit_error(exc):

                wait_seconds = (
                    _extract_retry_seconds(
                        exc
                    )
                )

                logger.warning(
                    "Groq rate limit | "
                    "article_id=%s | attempt=%s | "
                    "waiting=%.1fs",
                    article_id,
                    attempt,
                    wait_seconds,
                )

                if attempt < total_attempts:

                    time.sleep(
                        wait_seconds
                    )

                continue

            logger.error(
                "Groq MCQ API failed | "
                "article_id=%s | attempt=%s | "
                "error=%s",
                article_id,
                attempt,
                exc,
            )

            if attempt < total_attempts:

                delay = (
                    MCQ_RETRY_DELAY_SECONDS
                    + random.uniform(
                        0.0,
                        0.5,
                    )
                )

                time.sleep(
                    delay
                )

            continue

        # ----------------------------------------------------
        # Empty response
        # ----------------------------------------------------

        if not content:

            logger.warning(
                "Empty Groq response | "
                "article_id=%s | attempt=%s",
                article_id,
                attempt,
            )

            continue

        logger.debug(
            "Groq raw response preview | "
            "article_id=%s | attempt=%s | response=%s",
            article_id,
            attempt,
            content[
                :MCQ_RESPONSE_LOG_CHARS
            ],
        )

        # ----------------------------------------------------
        # Parse JSON
        # ----------------------------------------------------

        parsed = _extract_json(
            content
        )

        if parsed is None:

            logger.warning(
                "Invalid JSON returned by Groq | "
                "article_id=%s | attempt=%s",
                article_id,
                attempt,
            )

            continue

        # ----------------------------------------------------
        # Extract questions
        # ----------------------------------------------------

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
                "article_id=%s | attempt=%s",
                article_id,
                attempt,
            )

            continue

        # ----------------------------------------------------
        # Normalize + validate
        # ----------------------------------------------------

        accepted_this_attempt = 0

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
                    "article_id=%s | attempt=%s",
                    article_id,
                    attempt,
                )

                continue

            # ------------------------------------------------
            # Duplicate detection
            # ------------------------------------------------

            candidate_key = _question_key(
                normalized["question"]
            )

            duplicate = False

            for existing in collected:

                existing_key = _question_key(
                    existing.get(
                        "question",
                        "",
                    )
                )

                if (
                    candidate_key
                    and candidate_key
                    == existing_key
                ):

                    duplicate = True
                    break

            if duplicate:

                logger.warning(
                    "Duplicate MCQ skipped | "
                    "article_id=%s",
                    article_id,
                )

                continue

            normalized[
                "generation_source"
            ] = "groq"

            collected.append(
                normalized
            )

            accepted_this_attempt += 1

            logger.info(
                "MCQ accepted | "
                "article_id=%s | "
                "attempt=%s | collected=%s/%s",
                article_id,
                attempt,
                len(collected),
                count,
            )

            if len(collected) >= count:
                break

        logger.info(
            "MCQ attempt completed | "
            "article_id=%s | attempt=%s | "
            "accepted=%s | total=%s/%s",
            article_id,
            attempt,
            accepted_this_attempt,
            len(collected),
            count,
        )

        # ----------------------------------------------------
        # Success
        # ----------------------------------------------------

        if len(collected) >= count:
            break

        # ----------------------------------------------------
        # Delay before retry
        # ----------------------------------------------------

        if attempt < total_attempts:

            time.sleep(
                0.25
            )

    # --------------------------------------------------------
    # Final deduplication
    # --------------------------------------------------------

    collected = _deduplicate_questions(
        collected
    )

    # --------------------------------------------------------
    # Full success
    # --------------------------------------------------------

    if len(collected) >= count:

        logger.info(
            "Groq MCQ generation successful | "
            "article_id=%s | generated=%s",
            article_id,
            len(collected),
        )

        return collected[:count]

    # --------------------------------------------------------
    # Partial AI result
    # --------------------------------------------------------

    if collected:

        logger.warning(
            "Groq generated partial MCQs | "
            "article_id=%s | generated=%s/%s",
            article_id,
            len(collected),
            count,
        )

        # Try intelligent fallback only for missing questions.
        fallback_needed = count - len(
            collected
        )

        fallback_items = _fallback_mcqs(
            article=article,
            exam=exam,
            language=language,
            count=fallback_needed + 2,
            difficulty=difficulty,
            question_type=question_type,
        )

        for item in fallback_items:

            candidate_key = _question_key(
                item.get(
                    "question",
                    "",
                )
            )

            duplicate = any(
                candidate_key
                == _question_key(
                    existing.get(
                        "question",
                        "",
                    )
                )
                for existing in collected
            )

            if duplicate:
                continue

            collected.append(item)

            if len(collected) >= count:
                break

        return _deduplicate_questions(
            collected
        )[:count]

    # --------------------------------------------------------
    # Final intelligent fallback
    # --------------------------------------------------------

    logger.warning(
        "Groq MCQ generation failed completely | "
        "article_id=%s | using intelligent fallback.",
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

    description = _clean_text(
        description
    )

    if description:

        return (
            "Important for competitive examinations:\n\n"
            f"{title}\n\n"
            f"{description}"
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

    description = _clean_text(
        description
    )

    if description:

        return (
            "Analyze the following current-affairs issue "
            "from a mains perspective:\n\n"
            f"{title}\n\n"
            f"{description}\n\n"
            "Focus on significance, impact, "
            "opportunities, challenges, "
            "stakeholders and possible way forward."
        )

    return (
        "Analyze the significance, impact, "
        "opportunities and challenges related to: "
        f"{title}"
    )