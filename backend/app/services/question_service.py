from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from app.services.writing_ai_service import (
    _call_groq,
)


logger = logging.getLogger(
    "muni48.question_service"
)


# ============================================================
# CONFIGURATION
# ============================================================

QUESTION_CONFIG: dict[
    str,
    dict[str, dict[str, int]],
] = {
    "UPSC": {
        "short": {
            "marks": 10,
            "target_words": 150,
        },
        "long": {
            "marks": 15,
            "target_words": 250,
        },
    },
    "BPSC": {
        "short": {
            "marks": 10,
            "target_words": 150,
        },
        "long": {
            "marks": 15,
            "target_words": 250,
        },
    },
}


SUPPORTED_EXAMS = frozenset(
    {
        "UPSC",
        "BPSC",
    }
)


SUPPORTED_QUESTION_TYPES = frozenset(
    {
        "short",
        "long",
    }
)


SUPPORTED_LANGUAGES = frozenset(
    {
        "hi",
        "en",
    }
)


SUPPORTED_TARGET_WORDS = frozenset(
    {
        150,
        250,
    }
)


MAX_TOPIC_LENGTH = 500
MAX_CATEGORY_LENGTH = 100
MAX_QUESTION_LENGTH = 1000
MAX_KEYWORDS = 10


# ============================================================
# HELPERS
# ============================================================

def _normalize(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _get_language_name(
    language: str,
) -> str:

    language = (
        _normalize(language)
        .lower()
    )

    if language == "hi":
        return "Hindi"

    return "English"


def _get_config(
    exam: str,
    question_type: str,
) -> dict[str, int]:

    exam = (
        _normalize(exam)
        .upper()
    )

    question_type = (
        _normalize(question_type)
        .lower()
    )

    try:
        return QUESTION_CONFIG[
            exam
        ][
            question_type
        ]

    except KeyError as exc:

        raise ValueError(
            "No configuration found for "
            f"exam={exam}, "
            f"question_type={question_type}"
        ) from exc


def _get_config_by_target_words(
    target_words: int,
) -> dict[str, Any]:
    """
    Resolve question configuration
    from selected answer length.

    150 -> short -> 10 marks
    250 -> long  -> 15 marks
    """

    if target_words == 150:
        return {
            "question_type": "short",
            "marks": 10,
            "target_words": 150,
        }

    if target_words == 250:
        return {
            "question_type": "long",
            "marks": 15,
            "target_words": 250,
        }

    raise ValueError(
        "Invalid target_words. "
        "Allowed values are 150 or 250."
    )


def _safe_keywords(
    value: Any,
) -> list[str]:
    """
    Normalize AI-generated keywords.
    """

    if not isinstance(
        value,
        list,
    ):
        return []

    keywords: list[str] = []

    for item in value:

        keyword = _normalize(item)

        if not keyword:
            continue

        if len(keyword) > 150:
            keyword = (
                keyword[:150]
                .rstrip()
            )

        existing_keys = {
            existing.casefold()
            for existing in keywords
        }

        if (
            keyword.casefold()
            not in existing_keys
        ):
            keywords.append(keyword)

    return keywords[:MAX_KEYWORDS]


def _clean_question(
    text: Any,
) -> str:
    """
    Clean and validate generated question.
    """

    text = _normalize(text)

    if not text:
        raise RuntimeError(
            "Groq returned an empty question."
        )

    # --------------------------------------------------------
    # Remove markdown fences
    # --------------------------------------------------------

    text = re.sub(
        r"^```(?:json|text)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = text.strip()

    # --------------------------------------------------------
    # Remove common prefixes
    # --------------------------------------------------------

    prefixes = (
        "Question:",
        "QUESTION:",
        "प्रश्न:",
        "प्रश्न :",
        "Q:",
        "Q.",
    )

    for prefix in prefixes:

        if text.startswith(prefix):

            text = text[
                len(prefix):
            ].strip()

            break

    # --------------------------------------------------------
    # Normalize whitespace
    # --------------------------------------------------------

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    text = text.strip()

    if not text:

        raise RuntimeError(
            "Generated question became empty "
            "after cleaning."
        )

    # --------------------------------------------------------
    # Maximum question length
    # --------------------------------------------------------

    if len(text) > MAX_QUESTION_LENGTH:

        logger.warning(
            "Generated question exceeded %s "
            "characters; truncating.",
            MAX_QUESTION_LENGTH,
        )

        text = text[
            :MAX_QUESTION_LENGTH
        ].rstrip()

    return text


# ============================================================
# REMOVE EXISTING WORD LIMIT
# ============================================================

def _remove_existing_word_limit(
    question: str,
) -> str:
    """
    Remove AI-generated endings such as:

    (150 शब्द)
    (250 words)
    (150 शब्दों में)

    Backend will append the correct limit.
    """

    question = re.sub(
        r"\s*\(\s*\d+\s*"
        r"(?:शब्द|शब्दों|words?|word)"
        r"\s*\)\s*$",
        "",
        question,
        flags=re.IGNORECASE,
    )

    return question.strip()


def _append_word_limit(
    question: str,
    target_words: int,
    language: str,
) -> str:

    question = (
        _remove_existing_word_limit(
            question
        )
    )

    if language == "hi":

        return (
            f"{question} "
            f"({target_words} शब्द)"
        )

    return (
        f"{question} "
        f"({target_words} words)"
    )


# ============================================================
# JSON PARSER
# ============================================================

def _parse_ai_response(
    raw: str,
) -> tuple[str, list[str]]:

    raw = _normalize(raw)

    if not raw:

        raise RuntimeError(
            "Groq returned an empty response."
        )

    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:

        data = json.loads(raw)

        if isinstance(data, dict):

            question = _clean_question(
                data.get("question")
            )

            keywords = _safe_keywords(
                data.get(
                    "expected_keywords"
                )
            )

            return (
                question,
                keywords,
            )

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        pass

    # --------------------------------------------------------
    # Remove markdown fences
    # --------------------------------------------------------

    cleaned = re.sub(
        r"```(?:json|text)?",
        "",
        raw,
        flags=re.IGNORECASE,
    )

    cleaned = (
        cleaned
        .replace("```", "")
        .strip()
    )

    # --------------------------------------------------------
    # Extract JSON object
    # --------------------------------------------------------

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start >= 0 and end > start:

        candidate = cleaned[
            start:end + 1
        ]

        try:

            data = json.loads(
                candidate
            )

            if isinstance(
                data,
                dict,
            ):

                question = (
                    _clean_question(
                        data.get(
                            "question"
                        )
                    )
                )

                keywords = (
                    _safe_keywords(
                        data.get(
                            "expected_keywords"
                        )
                    )
                )

                return (
                    question,
                    keywords,
                )

        except (
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):

            logger.warning(
                "Unable to parse extracted "
                "Groq JSON."
            )

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    logger.warning(
        "Groq did not return valid JSON; "
        "using raw response as question."
    )

    question = _clean_question(raw)

    return (
        question,
        [],
    )


# ============================================================
# INPUT VALIDATION
# ============================================================

def _validate_inputs(
    *,
    exam: str,
    category: str,
    question_type: str,
    language: str,
    topic: str,
    target_words: int,
) -> None:

    if exam not in SUPPORTED_EXAMS:

        raise ValueError(
            f"Unsupported exam: {exam}. "
            f"Supported exams: "
            f"{sorted(SUPPORTED_EXAMS)}"
        )

    if (
        question_type
        not in SUPPORTED_QUESTION_TYPES
    ):

        raise ValueError(
            "Unsupported question_type: "
            f"{question_type}. "
            "Supported types: "
            f"{sorted(SUPPORTED_QUESTION_TYPES)}"
        )

    if language not in SUPPORTED_LANGUAGES:

        raise ValueError(
            f"Unsupported language: {language}. "
            "Supported languages: "
            f"{sorted(SUPPORTED_LANGUAGES)}"
        )

    if (
        target_words
        not in SUPPORTED_TARGET_WORDS
    ):

        raise ValueError(
            "Invalid target_words. "
            "Allowed values are 150 or 250."
        )

    if len(category) > MAX_CATEGORY_LENGTH:

        raise ValueError(
            "Category is too long. "
            f"Maximum length is "
            f"{MAX_CATEGORY_LENGTH}."
        )

    if len(topic) > MAX_TOPIC_LENGTH:

        raise ValueError(
            "Topic is too long. "
            f"Maximum length is "
            f"{MAX_TOPIC_LENGTH}."
        )


# ============================================================
# PROMPT BUILDER
# ============================================================

def _build_question_prompt(
    *,
    exam: str,
    category: str,
    question_type: str,
    marks: int,
    target_words: int,
    language_name: str,
    topic: str,
) -> str:

    topic_instruction = ""

    if topic:

        topic_instruction = f"""

SPECIFIC TOPIC:

{topic}

Generate the question specifically around
this topic.

Do not move away from the requested topic.
"""

    return f"""
You are a senior {exam} Mains question setter.

Generate exactly ONE high-quality descriptive
Mains question.

EXAM:
{exam}

CATEGORY:
{category}

QUESTION TYPE:
{question_type}

MARKS:
{marks}

EXPECTED ANSWER LENGTH:
{target_words} words

LANGUAGE:
{language_name}

{topic_instruction}

QUESTION QUALITY REQUIREMENTS:

1. The question must be suitable for
   {exam} Mains.

2. It must test analytical and conceptual
   ability.

3. Avoid purely factual questions.

4. Use an appropriate directive such as:
   Discuss, Analyze, Examine, Evaluate,
   Critically Examine, Explain, or Elucidate.

5. Keep the question directly relevant to:
   {category}

6. For BPSC, use Bihar-specific context
   when naturally relevant.

7. For UPSC, maintain appropriate
   national-level relevance.

8. The question must have a clear demand.

9. The scope must be manageable within
   approximately {target_words} words.

10. Do not invent statistics.

11. Do not invent government schemes.

12. Do not invent constitutional provisions.

13. Do not invent reports, indices,
    institutions, committees or programmes.

14. Use only well-established factual
    references when necessary.

15. Do not provide an answer.

16. Do not provide explanations.

17. Generate exactly ONE question.

18. Generate 5 to 10 important answer
    concepts/keywords.

IMPORTANT:

Do NOT add the word limit to the question.

The backend will add the correct word limit.

OUTPUT:

Return ONLY a JSON object.

Use exactly this structure:

{{
  "question": "question text",
  "expected_keywords": [
    "keyword 1",
    "keyword 2",
    "keyword 3",
    "keyword 4",
    "keyword 5"
  ]
}}

Do not use markdown.
Do not use code fences.
Do not include any text outside
the JSON object.
"""


# ============================================================
# GENERATE QUESTION
# ============================================================

def generate_question(
    *,
    exam: str,
    category: str = "General",
    question_type: str = "short",
    language: str = "hi",
    topic: Optional[str] = None,
    target_words: Optional[int] = None,
) -> dict[str, Any]:

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    exam = (
        _normalize(exam)
        .upper()
    )

    category = (
        _normalize(category)
        or "General"
    )

    question_type = (
        _normalize(question_type)
        .lower()
        or "short"
    )

    language = (
        _normalize(language)
        .lower()
        or "hi"
    )

    topic = _normalize(topic)

    # --------------------------------------------------------
    # Resolve target_words
    # --------------------------------------------------------

    if target_words is None:

        config = _get_config(
            exam,
            question_type,
        )

        target_words = config[
            "target_words"
        ]

    else:

        try:

            target_words = int(
                target_words
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise ValueError(
                "target_words must be "
                "either 150 or 250."
            ) from exc

    # --------------------------------------------------------
    # TARGET WORDS ARE AUTHORITATIVE
    #
    # 150 -> short -> 10 marks
    # 250 -> long  -> 15 marks
    # --------------------------------------------------------

    target_config = (
        _get_config_by_target_words(
            target_words
        )
    )

    question_type = (
        target_config[
            "question_type"
        ]
    )

    marks = target_config[
        "marks"
    ]

    target_words = target_config[
        "target_words"
    ]

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    _validate_inputs(
        exam=exam,
        category=category,
        question_type=question_type,
        language=language,
        topic=topic,
        target_words=target_words,
    )

    language_name = (
        _get_language_name(
            language
        )
    )

    # --------------------------------------------------------
    # Prompt
    # --------------------------------------------------------

    prompt = _build_question_prompt(
        exam=exam,
        category=category,
        question_type=question_type,
        marks=marks,
        target_words=target_words,
        language_name=language_name,
        topic=topic,
    )

    # --------------------------------------------------------
    # Groq
    # --------------------------------------------------------
    #
    # IMPORTANT:
    # json_mode=False is intentional.
    #
    # Qwen may return:
    # 400 json_validate_failed
    #
    # when Groq server-side JSON validation
    # is enabled.
    #
    # We therefore parse JSON ourselves below.
    # --------------------------------------------------------

    try:

        raw = _call_groq(
            prompt,
            json_mode=False,
            max_completion_tokens=500,
        )

    except Exception as exc:

        logger.exception(
            "Question generation failed: "
            "exam=%s category=%s "
            "type=%s language=%s "
            "target_words=%s",
            exam,
            category,
            question_type,
            language,
            target_words,
        )

        raise RuntimeError(
            "Unable to generate question "
            "using AI. Please try again."
        ) from exc

    # --------------------------------------------------------
    # Parse
    # --------------------------------------------------------

    try:

        (
            question,
            expected_keywords,
        ) = _parse_ai_response(raw)

    except Exception as exc:

        logger.exception(
            "Failed to parse generated question."
        )

        raise RuntimeError(
            "AI generated an invalid "
            "question response. "
            "Please try again."
        ) from exc

    # --------------------------------------------------------
    # Basic quality validation
    # --------------------------------------------------------

    if len(question) < 20:

        raise RuntimeError(
            "AI generated a question "
            "that is too short."
        )

    # --------------------------------------------------------
    # Avoid accidental multi-question output
    # --------------------------------------------------------

    question_count = len(
        re.findall(
            r"[?？]",
            question,
        )
    )

    if question_count > 1:

        logger.warning(
            "AI may have generated "
            "multiple questions."
        )

    # --------------------------------------------------------
    # Backend-controlled word limit
    # --------------------------------------------------------

    question = _append_word_limit(
        question,
        target_words,
        language,
    )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    return {
        "question": question,
        "exam": exam,
        "category": category,
        "question_type": question_type,
        "marks": marks,
        "target_words": target_words,
        "language": language,
        "topic": topic or None,
        "expected_keywords": (
            expected_keywords
        ),
        "generated_by": "groq",
    }


# ============================================================
# QUESTION METADATA
# ============================================================

def get_question_config(
    exam: str,
    question_type: str = "short",
) -> dict[str, int]:

    exam = (
        _normalize(exam)
        .upper()
    )

    question_type = (
        _normalize(question_type)
        .lower()
    )

    if exam not in SUPPORTED_EXAMS:

        raise ValueError(
            f"Unsupported exam: {exam}"
        )

    if (
        question_type
        not in SUPPORTED_QUESTION_TYPES
    ):

        raise ValueError(
            "Unsupported question_type: "
            f"{question_type}"
        )

    return dict(
        _get_config(
            exam,
            question_type,
        )
    )


# ============================================================
# AVAILABLE QUESTION TYPES
# ============================================================

def get_question_types() -> list[
    dict[str, Any]
]:

    return [
        {
            "type": "short",
            "marks": 10,
            "target_words": 150,
        },
        {
            "type": "long",
            "marks": 15,
            "target_words": 250,
        },
    ]


# ============================================================
# AVAILABLE TARGET WORDS
# ============================================================

def get_target_word_options() -> list[
    dict[str, Any]
]:

    return [
        {
            "target_words": 150,
            "question_type": "short",
            "marks": 10,
        },
        {
            "target_words": 250,
            "question_type": "long",
            "marks": 15,
        },
    ]


# ============================================================
# AVAILABLE EXAMS
# ============================================================

def get_supported_exams() -> list[str]:

    return sorted(
        SUPPORTED_EXAMS
    )


# ============================================================
# AVAILABLE LANGUAGES
# ============================================================

def get_supported_languages() -> list[str]:

    return sorted(
        SUPPORTED_LANGUAGES
    )