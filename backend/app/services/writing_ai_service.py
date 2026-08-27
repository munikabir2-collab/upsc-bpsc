from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from dotenv import load_dotenv
from groq import Groq


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

logger = logging.getLogger("muni48.writing_ai_service")


# ============================================================
# CONFIGURATION
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "qwen/qwen3.6-27b",
)


# ============================================================
# TOKEN CONFIGURATION
# ============================================================

MAX_COMPLETION_TOKENS = int(
    os.getenv(
        "GROQ_MAX_COMPLETION_TOKENS",
        "1800",
    )
)

QUESTION_MAX_TOKENS = int(
    os.getenv(
        "GROQ_WRITING_QUESTION_MAX_TOKENS",
        os.getenv(
            "GROQ_QUESTION_MAX_TOKENS",
            "500",
        ),
    )
)

MODEL_ANSWER_150_MAX_TOKENS = int(
    os.getenv(
        "GROQ_WRITING_MODEL_ANSWER_150_MAX_TOKENS",
        "700",
    )
)

MODEL_ANSWER_250_MAX_TOKENS = int(
    os.getenv(
        "GROQ_WRITING_MODEL_ANSWER_250_MAX_TOKENS",
        "900",
    )
)

ESSAY_MAX_TOKENS = int(
    os.getenv(
        "GROQ_WRITING_ESSAY_MAX_TOKENS",
        "1600",
    )
)

EVALUATION_MAX_TOKENS = int(
    os.getenv(
        "GROQ_WRITING_EVALUATION_MAX_TOKENS",
        "700",
    )
)


# ============================================================
# RETRY CONFIGURATION
# ============================================================

MAX_RETRIES = int(
    os.getenv(
        "GROQ_WRITING_MAX_RETRIES",
        os.getenv(
            "GROQ_MAX_RETRIES",
            "0",
        ),
    )
)

RETRY_DELAY_SECONDS = float(
    os.getenv(
        "GROQ_RETRY_DELAY_SECONDS",
        "2",
    )
)


# ============================================================
# TEMPERATURE
# ============================================================

GROQ_TEMPERATURE = float(
    os.getenv(
        "GROQ_TEMPERATURE",
        "0.3",
    )
)


# ============================================================
# CLIENT
# ============================================================

client = (
    Groq(api_key=GROQ_API_KEY)
    if GROQ_API_KEY
    else None
)


# ============================================================
# LANGUAGE
# ============================================================

def _language_name(language: str) -> str:

    language = str(
        language or ""
    ).lower().strip()

    aliases = {
        "hi": "Hindi",
        "hindi": "Hindi",
        "hin": "Hindi",
        "en": "English",
        "english": "English",
        "eng": "English",
    }

    return aliases.get(
        language,
        "English",
    )


# ============================================================
# EXAM NORMALIZATION
# ============================================================

def _normalize_exam(
    exam: str,
) -> str:

    exam = str(
        exam or "UPSC"
    ).upper().strip()

    if exam not in {
        "UPSC",
        "BPSC",
    }:
        exam = "UPSC"

    return exam


# ============================================================
# CATEGORY NORMALIZATION
# ============================================================

def _normalize_category(
    category: str,
) -> str:

    category = str(
        category or "General"
    ).strip()

    return category or "General"


# ============================================================
# QUESTION TYPE NORMALIZATION
# ============================================================

def _normalize_question_type(
    question_type: str,
) -> str:

    value = str(
        question_type or "short"
    ).lower().strip()

    if value in {
        "long",
        "long answer",
        "250",
        "250 words",
    }:
        return "long"

    return "short"


# ============================================================
# TARGET WORD NORMALIZATION
# ============================================================

def _normalize_target_words(
    target_words: int | None,
    question_type: str | None = None,
) -> int:

    # Explicit target_words has highest priority.
    if target_words is not None:

        try:
            target_words = int(
                target_words
            )
        except (
            TypeError,
            ValueError,
        ):
            target_words = None

    if target_words not in {
        150,
        250,
    }:

        normalized_type = (
            _normalize_question_type(
                question_type or "short"
            )
        )

        return (
            250
            if normalized_type == "long"
            else 150
        )

    return target_words


# ============================================================
# MARKS
# ============================================================

def _marks_for_target_words(
    target_words: int,
) -> int:

    return (
        15
        if target_words == 250
        else 10
    )


# ============================================================
# THINK / REASONING CLEANER
# ============================================================

def _strip_reasoning(
    text: str,
) -> str:

    if not text:
        return ""

    text = str(text)

    # --------------------------------------------------------
    # Closed <think> blocks
    # --------------------------------------------------------

    text = re.sub(
        r"<think\b[^>]*>.*?</think\s*>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Closed <thinking> blocks
    # --------------------------------------------------------

    text = re.sub(
        r"<thinking\b[^>]*>.*?</thinking\s*>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Unclosed <think>
    # --------------------------------------------------------

    text = re.sub(
        r"<think\b[^>]*>.*$",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Unclosed <thinking>
    # --------------------------------------------------------

    text = re.sub(
        r"<thinking\b[^>]*>.*$",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Orphan tags
    # --------------------------------------------------------

    text = re.sub(
        r"</?(?:think|thinking)\s*>",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


# ============================================================
# MARKDOWN CLEANER
# ============================================================

def _remove_markdown_fences(
    text: str,
) -> str:

    if not text:
        return ""

    text = re.sub(
        r"```(?:json|JSON|text|TEXT)?",
        "",
        text,
    )

    text = text.replace(
        "```",
        "",
    )

    return text.strip()


# ============================================================
# GENERAL AI OUTPUT CLEANER
# ============================================================

def _clean_ai_output(
    text: str,
) -> str:

    if not text:
        return ""

    text = _strip_reasoning(
        text
    )

    text = _remove_markdown_fences(
        text
    )

    text = re.sub(
        r"^\s*(?:final answer|final|response)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


# ============================================================
# JSON EXTRACTION
# ============================================================

def _extract_json(
    text: str,
) -> dict[str, Any] | None:

    if not text:
        return None

    text = _clean_ai_output(
        text
    )

    if not text:
        return None

    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:

        data = json.loads(
            text
        )

        if isinstance(
            data,
            dict,
        ):
            return data

    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ):
        pass

    # --------------------------------------------------------
    # Find first JSON object
    # --------------------------------------------------------

    start = text.find(
        "{"
    )

    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for index in range(
        start,
        len(text),
    ):

        char = text[index]

        if escaped:

            escaped = False
            continue

        if char == "\\" and in_string:

            escaped = True
            continue

        if char == '"':

            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":

            depth += 1

        elif char == "}":

            depth -= 1

            if depth == 0:

                candidate = text[
                    start:index + 1
                ]

                try:

                    data = json.loads(
                        candidate
                    )

                    if isinstance(
                        data,
                        dict,
                    ):
                        return data

                except (
                    json.JSONDecodeError,
                    TypeError,
                    ValueError,
                ):

                    return None

    return None


# ============================================================
# SAFE HELPERS
# ============================================================

def _safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(
        value
    ).strip()


def _safe_list(
    value: Any,
) -> list[Any]:

    if isinstance(
        value,
        list,
    ):
        return value

    return []


def _safe_int(
    value: Any,
    default: int = 0,
) -> int:

    try:

        return int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return default


# ============================================================
# WORD LIMIT
# ============================================================

def _limit_words(
    text: str,
    target_words: int,
) -> str:

    if not text:
        return ""

    try:

        target_words = int(
            target_words
        )

    except (
        TypeError,
        ValueError,
    ):

        target_words = 150

    target_words = max(
        1,
        target_words,
    )

    words = text.split()

    if len(words) <= target_words:
        return text.strip()

    return " ".join(
        words[:target_words]
    ).strip()


# ============================================================
# REMOVE WORD LIMIT FROM QUESTION
# ============================================================

def _remove_word_limit_from_question(
    question: str,
) -> str:

    if not question:
        return ""

    # Hindi:
    # (150 शब्द)
    # (250 शब्द)
    # - 150 शब्द
    # — 250 शब्द

    question = re.sub(
        r"\s*\(\s*\d+\s*(?:शब्द|शब्दों)\s*\)\s*$",
        "",
        question,
        flags=re.IGNORECASE,
    )

    # English:
    # (150 words)
    # (250 words)

    question = re.sub(
        r"\s*\(\s*\d+\s*words?\s*\)\s*$",
        "",
        question,
        flags=re.IGNORECASE,
    )

    # Generic suffix.

    question = re.sub(
        r"\s*[-–—]\s*\d+\s*(?:शब्द|शब्दों|words?)\s*$",
        "",
        question,
        flags=re.IGNORECASE,
    )

    return question.strip()


# ============================================================
# ANSWER CLEANER
# ============================================================

def _clean_generated_answer(
    answer: str,
    question: str,
) -> str:

    if not answer:
        return ""

    answer = _clean_ai_output(
        answer
    )

    question = (
        question or ""
    ).strip()

    if question:

        if answer.startswith(
            question
        ):

            answer = answer[
                len(question):
            ].lstrip(
                " \n:-"
            )

    answer = re.sub(
        r"^(?:उत्तर|Answer)\s*:\s*",
        "",
        answer,
        flags=re.IGNORECASE,
    )

    return answer.strip()


# ============================================================
# KEY POINT NORMALIZATION
# ============================================================

def _normalize_key_points(
    value: Any,
) -> list[str]:

    if not isinstance(
        value,
        list,
    ):
        return []

    result: list[str] = []

    for item in value:

        text = _safe_string(
            item
        )

        if text:
            result.append(
                text
            )

    return result[:5]


# ============================================================
# ERROR HELPERS
# ============================================================

def _is_rate_limit_error(
    exc: Exception,
) -> bool:

    message = str(
        exc
    ).lower()

    patterns = (
        "rate_limit",
        "rate limit",
        "tokens per minute",
        "token limit",
        "error code: 429",
        "error code: 413",
        "too many requests",
        "tpm",
        "tokens per day",
        "tpd",
    )

    return any(
        pattern in message
        for pattern in patterns
    )


def _is_json_error(
    exc: Exception,
) -> bool:

    message = str(
        exc
    ).lower()

    patterns = (
        "json_validate_failed",
        "failed to validate json",
        "failed to generate json",
        "invalid json",
        "json validation",
        "response_format",
        "json_object",
        "invalid schema",
    )

    return any(
        pattern in message
        for pattern in patterns
    )


# ============================================================
# GROQ CALL
# ============================================================

# ============================================================
# GROQ CALL
# ============================================================

def _call_groq(
    prompt: str,
    *,
    json_mode: bool = False,
    max_completion_tokens: int | None = None,
    max_retries: int | None = None,
) -> str:

    if client is None:
        raise RuntimeError(
            "GROQ_API_KEY is not configured."
        )

    # --------------------------------------------------------
    # TOKEN CONFIG
    # --------------------------------------------------------

    requested_tokens = (
        max_completion_tokens
        if max_completion_tokens is not None
        else MAX_COMPLETION_TOKENS
    )

    try:
        requested_tokens = int(
            requested_tokens
        )
    except (TypeError, ValueError):
        requested_tokens = MAX_COMPLETION_TOKENS

    completion_tokens = max(
        256,
        min(
            requested_tokens,
            MAX_COMPLETION_TOKENS,
        ),
    )

    # --------------------------------------------------------
    # RETRY CONFIG
    # --------------------------------------------------------

    if max_retries is None:
        retries = MAX_RETRIES
    else:
        try:
            retries = max(
                0,
                int(max_retries),
            )
        except (TypeError, ValueError):
            retries = 0

    # --------------------------------------------------------
    # IMPORTANT FOR QWEN 3.6
    # --------------------------------------------------------
    #
    # Qwen 3.6 supports:
    #
    # reasoning_effort = "none"
    # reasoning_format = "hidden"
    #
    # We don't need reasoning for:
    # - question generation
    # - model answers
    # - evaluation
    #
    # This prevents the model from spending the completion
    # budget on reasoning and returning empty final content.
    # --------------------------------------------------------

    total_attempts = max(
        1,
        retries + 1,
    )

    last_exception: Exception | None = None

    for attempt in range(
        total_attempts
    ):

        request: dict[str, Any] = {

            "model": GROQ_MODEL,

            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert UPSC and BPSC "
                        "Mains preparation assistant. "
                        "Return only the requested final output. "
                        "Never reveal reasoning. "
                        "Never output <think> tags. "
                        "Never output <thinking> tags."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],

            "temperature": GROQ_TEMPERATURE,

            "max_completion_tokens":
                completion_tokens,

            # ------------------------------------------------
            # QWEN REASONING CONTROL
            # ------------------------------------------------

            "reasoning_effort": "none",

            "reasoning_format": "hidden",
        }

        # ----------------------------------------------------
        # JSON MODE
        # ----------------------------------------------------

        if json_mode:

            request["response_format"] = {
                "type": "json_object"
            }

        logger.info(
            "Groq request | model=%s | json=%s | "
            "reasoning_effort=none | attempt=%s/%s | "
            "tokens=%s",
            GROQ_MODEL,
            json_mode,
            attempt + 1,
            total_attempts,
            completion_tokens,
        )

        try:

            response = (
                client
                .chat
                .completions
                .create(
                    **request
                )
            )

            # ------------------------------------------------
            # CHOICES
            # ------------------------------------------------

            if not response.choices:

                raise RuntimeError(
                    "Groq returned no choices."
                )

            choice = response.choices[0]

            message = getattr(
                choice,
                "message",
                None,
            )

            if message is None:

                raise RuntimeError(
                    "Groq returned no message."
                )

            finish_reason = getattr(
                choice,
                "finish_reason",
                None,
            )

            logger.info(
                "Groq response | finish_reason=%s",
                finish_reason,
            )

            # ------------------------------------------------
            # CONTENT
            # ------------------------------------------------

            content = getattr(
                message,
                "content",
                None,
            )

            text = ""

            if isinstance(
                content,
                str,
            ):

                text = content.strip()

            elif isinstance(
                content,
                list,
            ):

                parts: list[str] = []

                for item in content:

                    if isinstance(
                        item,
                        str,
                    ):
                        parts.append(
                            item
                        )

                    elif isinstance(
                        item,
                        dict,
                    ):

                        value = item.get(
                            "text"
                        )

                        if value:
                            parts.append(
                                str(value)
                            )

                text = "\n".join(
                    parts
                ).strip()

            # ------------------------------------------------
            # DEBUG MESSAGE
            # ------------------------------------------------

            if not text:

                logger.error(
                    "Groq returned empty content. "
                    "finish_reason=%s | "
                    "message_type=%s | "
                    "message=%r",
                    finish_reason,
                    type(message).__name__,
                    message,
                )

                # --------------------------------------------
                # RETRY
                # --------------------------------------------

                if attempt < total_attempts - 1:

                    time.sleep(
                        RETRY_DELAY_SECONDS
                    )

                    continue

                raise RuntimeError(
                    "Groq returned an empty response."
                )

            # ------------------------------------------------
            # CLEAN
            # ------------------------------------------------

            cleaned = _clean_ai_output(
                text
            )

            if not cleaned:

                logger.error(
                    "Groq response became empty "
                    "after cleaning. raw=%r",
                    text[:1000],
                )

                if attempt < total_attempts - 1:

                    time.sleep(
                        RETRY_DELAY_SECONDS
                    )

                    continue

                raise RuntimeError(
                    "Groq returned an empty response "
                    "after cleaning."
                )

            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            logger.info(
                "Groq response successful | "
                "length=%s",
                len(cleaned),
            )

            return cleaned

        except Exception as exc:

            last_exception = exc

            # -----------------------------------------------
            # RATE LIMIT
            # -----------------------------------------------

            if _is_rate_limit_error(
                exc
            ):

                raise RuntimeError(
                    "Groq API rate limit reached. "
                    "Please wait a moment and try again."
                ) from exc

            # -----------------------------------------------
            # RETRY
            # -----------------------------------------------

            if attempt < total_attempts - 1:

                logger.warning(
                    "Groq request failed. "
                    "Retrying in %.2f seconds. "
                    "attempt=%s/%s error=%s",
                    RETRY_DELAY_SECONDS,
                    attempt + 1,
                    total_attempts,
                    exc,
                )

                time.sleep(
                    RETRY_DELAY_SECONDS
                )

                continue

            break

    # --------------------------------------------------------
    # FINAL ERROR
    # --------------------------------------------------------

    error_message = (
        str(last_exception)
        if last_exception
        else "Unknown Groq error."
    )

    raise RuntimeError(
        "Groq API request failed: "
        f"{error_message}"
    ) from last_exception

# ============================================================
# QUESTION GENERATION
# ============================================================

def generate_writing_question(
    *,
    exam: str,
    category: str,
    question_type: str,
    language: str = "hi",
    target_words: int | None = None,
) -> dict[str, Any]:

    exam = _normalize_exam(
        exam
    )

    category = _normalize_category(
        category
    )

    question_type = _normalize_question_type(
        question_type
    )

    target_words = _normalize_target_words(
        target_words,
        question_type,
    )

    # --------------------------------------------------------
    # Make target_words authoritative.
    # --------------------------------------------------------

    question_type = (
        "long"
        if target_words == 250
        else "short"
    )

    marks = _marks_for_target_words(
        target_words
    )

    language_name = _language_name(
        language
    )

    # --------------------------------------------------------
    # Exam-specific instructions
    # --------------------------------------------------------

    if exam == "BPSC":

        exam_context = """
BPSC-SPECIFIC RULES:

- Prefer Bihar-related context where naturally relevant.
- Do not force Bihar into every question.
- Use Bihar institutions, geography, economy, society,
  governance or development only when factually relevant.
- Maintain BPSC Mains analytical standard.
"""

    else:

        exam_context = """
UPSC-SPECIFIC RULES:

- Maintain national and constitutional relevance.
- Use Indian examples where relevant.
- Do not artificially insert Bihar-specific context.
- Maintain UPSC Mains analytical standard.
"""

    # --------------------------------------------------------
    # Prompt
    # --------------------------------------------------------

    prompt = f"""
You are a senior {exam} Mains question setter.

Generate EXACTLY ONE high-quality descriptive
Mains question.

Exam: {exam}
Category: {category}
Question type: {question_type}
Language: {language_name}
Target answer length: {target_words} words
Marks: {marks}

{exam_context}

QUESTION REQUIREMENTS:

1. Suitable for {exam} Mains.
2. Analytical and conceptual.
3. Avoid purely factual questions.
4. Use an appropriate directive such as:
   Discuss, Analyze, Examine, Evaluate,
   Critically Examine, Explain, or Elucidate.
5. Directly relevant to the selected category.
6. Keep the scope manageable within {target_words} words.
7. The question must have a clear analytical demand.
8. Do not invent statistics.
9. Do not invent government schemes.
10. Do not invent constitutional provisions.
11. Do not invent laws or Acts.
12. Do not invent reports.
13. Do not invent institutions.
14. Do not misuse the mandate of an institution.
15. Do not combine unrelated constitutional Articles,
    laws, institutions or schemes.
16. If mentioning a constitutional Article, ensure that
    it is directly relevant to the question.
17. If mentioning an Act, ensure that its name and purpose
    are factually appropriate.
18. Do not provide the answer.
19. Do not explain the question.
20. Generate exactly ONE question.
21. Do not add the word limit to the question.
22. Do not add marks to the question.
23. Generate exactly 5 important answer concepts.
24. Write the question entirely in {language_name}.

QUALITY RULES:

- The question must resemble a real Mains question.
- Avoid artificial combinations of unrelated topics.
- Avoid fabricated current affairs.
- Avoid sensational or vague wording.
- Avoid quotation marks around ordinary terms unless necessary.
- The question should be answerable within {target_words} words.

CRITICAL OUTPUT RULES:

Return ONLY one JSON object.

DO NOT output:
- <think>
- <thinking>
- reasoning
- analysis
- markdown
- code fences
- explanation
- text before JSON
- text after JSON
- word limit
- marks

Use EXACTLY these keys:

{{
  "question": "question text",
  "marks": {marks},
  "target_words": {target_words},
  "expected_keywords": [
    "keyword 1",
    "keyword 2",
    "keyword 3",
    "keyword 4",
    "keyword 5"
  ]
}}
"""

    raw = _call_groq(
        prompt,
        json_mode=True,
        max_completion_tokens=QUESTION_MAX_TOKENS,
        max_retries=MAX_RETRIES,
    )

    # --------------------------------------------------------
    # STRICT JSON PARSING
    # --------------------------------------------------------

    data = _extract_json(
        raw
    )

    if not data:

        logger.error(
            "Question generation returned "
            "non-JSON response: %s",
            raw[:1000],
        )

        raise RuntimeError(
            "Groq returned an invalid question response. "
            "Expected a valid JSON object."
        )

    # --------------------------------------------------------
    # QUESTION
    # --------------------------------------------------------

    question = _clean_ai_output(
        _safe_string(
            data.get(
                "question"
            )
        )
    )

    question = _remove_word_limit_from_question(
        question
    )

    if not question:

        raise RuntimeError(
            "Groq returned JSON without a valid question."
        )

    # --------------------------------------------------------
    # Reject leaked reasoning
    # --------------------------------------------------------

    lowered = question.lower()

    forbidden_markers = (
        "<think>",
        "<thinking>",
        "reasoning",
        "here's a thinking process",
        "here is a thinking process",
        "analyze user input",
        "deconstruct requirements",
        "i need to",
        "i should",
    )

    if any(
        marker in lowered
        for marker in forbidden_markers
    ):

        raise RuntimeError(
            "Groq returned reasoning instead of "
            "a valid question."
        )

    # --------------------------------------------------------
    # Validate returned target words
    # --------------------------------------------------------

    returned_target_words = _safe_int(
        data.get(
            "target_words"
        ),
        target_words,
    )

    # Server-side target is authoritative.
    returned_target_words = target_words

    # --------------------------------------------------------
    # Validate returned marks
    # --------------------------------------------------------

    returned_marks = _safe_int(
        data.get(
            "marks"
        ),
        marks,
    )

    # Server-side marks are authoritative.
    returned_marks = marks

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    return {
        "question": question,
        "marks": returned_marks,
        "target_words": returned_target_words,
        "expected_keywords":
            _normalize_key_points(
                data.get(
                    "expected_keywords"
                )
            ),
    }


# ============================================================
# MODEL ANSWER
# ============================================================
def generate_model_answer(
    *,
    exam: str,
    category: str,
    question: str,
    marks: int,
    target_words: int,
    language: str = "hi",
) -> dict[str, Any]:

    # ========================================================
    # NORMALIZE INPUT
    # ========================================================

    exam = _normalize_exam(exam)

    category = _normalize_category(category)

    question = _clean_ai_output(question)

    question = _remove_word_limit_from_question(question)

    if not question:
        raise ValueError(
            "Cannot generate model answer because "
            "the question is empty."
        )

    # ========================================================
    # TARGET WORDS
    # ========================================================

    target_words = _normalize_target_words(
        target_words
    )

    if target_words not in (150, 250):
        target_words = 150

    # ========================================================
    # MARKS
    # ========================================================

    marks = _safe_int(
        marks,
        _marks_for_target_words(target_words),
    )

    # ========================================================
    # REJECT REASONING
    # ========================================================

    lowered_question = question.lower()

    forbidden_question_markers = (
        "<think>",
        "<thinking>",
        "here's a thinking process",
        "here is a thinking process",
        "analyze user input",
        "deconstruct requirements",
    )

    if any(
        marker in lowered_question
        for marker in forbidden_question_markers
    ):
        raise ValueError(
            "Cannot generate model answer because "
            "the selected question contains AI reasoning."
        )

    # ========================================================
    # LANGUAGE
    # ========================================================

    language_name = _language_name(language)

    # ========================================================
    # TOKEN BUDGET
    # ========================================================
    #
    # JSON contains:
    # answer
    # introduction
    # body
    # way_forward
    # conclusion
    # key_points
    #
    # Therefore token budget must be higher than the
    # requested answer word count.
    #
    # ========================================================

    if target_words == 250:
        answer_tokens = max(
            MODEL_ANSWER_250_MAX_TOKENS,
            1400,
        )
    else:
        answer_tokens = max(
            MODEL_ANSWER_150_MAX_TOKENS,
            1000,
        )

    # ========================================================
    # PROMPT
    # ========================================================

    prompt = f"""
You are an expert {exam} Mains answer writer.

Generate ONE high-quality model answer for the EXACT
question provided below.

Exam: {exam}
Category: {category}
Marks: {marks}
Target answer length: approximately {target_words} words
Language: {language_name}

QUESTION:
{question}

RULES:

- Answer the EXACT question.
- Do not create a different question.
- Do not repeat the question.
- Do not discuss the question.
- Do not reveal reasoning.
- Do not output <think>.
- Do not output <thinking>.
- Do not mention token count.
- Do not mention word count.
- Do not invent statistics.
- Do not invent government schemes.
- Do not invent reports.
- Do not invent constitutional provisions.
- Use relevant and reliable Indian examples where appropriate.
- Maintain UPSC/BPSC Mains quality.
- Use a concise introduction.
- Use an analytical body.
- Cover the major dimensions demanded by the question.
- Give a practical way forward where appropriate.
- End with a balanced conclusion.

IMPORTANT LENGTH RULE:

The main "answer" must be approximately {target_words} words.

Do not make the JSON unnecessarily verbose.

Return ONLY valid JSON.

Required JSON:

{{
  "answer": "complete model answer",
  "introduction": "short introduction",
  "body": "analytical body",
  "way_forward": "short way forward",
  "conclusion": "short conclusion",
  "key_points": [
    "point 1",
    "point 2",
    "point 3"
  ]
}}
"""

    # ========================================================
    # GROQ
    # ========================================================

    try:

        logger.info(
            "Generating model answer | exam=%s | target_words=%s | "
            "marks=%s | language=%s | tokens=%s",
            exam,
            target_words,
            marks,
            language,
            answer_tokens,
        )

        raw = _call_groq(
            prompt,
            json_mode=True,
            max_completion_tokens=answer_tokens,
            max_retries=MAX_RETRIES,
        )

    except Exception:

        logger.exception(
            "Groq model answer generation failed | "
            "exam=%s | target_words=%s | question=%s",
            exam,
            target_words,
            question[:500],
        )

        raise

    # ========================================================
    # EMPTY RESPONSE
    # ========================================================

    if not raw or not str(raw).strip():
        raise RuntimeError(
            "Groq returned an empty model answer response."
        )

    logger.info(
        "Model answer response received | length=%s",
        len(raw),
    )

    # ========================================================
    # JSON EXTRACTION
    # ========================================================

    try:

        data = _extract_json(raw)

    except Exception:

        logger.exception(
            "Model answer JSON extraction failed | response=%s",
            str(raw)[:2000],
        )

        raise RuntimeError(
            "Failed to parse Groq model answer response."
        )

    # ========================================================
    # VALIDATE JSON
    # ========================================================

    if not isinstance(data, dict):

        logger.error(
            "Invalid model answer JSON type: %r",
            type(data),
        )

        raise RuntimeError(
            "Groq returned an invalid model answer response."
        )

    # ========================================================
    # ANSWER
    # ========================================================

    answer = _clean_generated_answer(
        _safe_string(
            data.get("answer")
        ),
        question,
    )

    # Fallback to body
    if not answer:

        answer = _clean_generated_answer(
            _safe_string(
                data.get("body")
            ),
            question,
        )

    if not answer:

        logger.error(
            "Groq JSON contains no valid answer | data=%s",
            str(data)[:2000],
        )

        raise RuntimeError(
            "Groq returned JSON without a valid model answer."
        )

    # ========================================================
    # FINAL ANSWER
    # ========================================================

    answer = _limit_words(
        answer,
        target_words,
    )

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "answer": answer,

        "introduction": _clean_ai_output(
            _safe_string(
                data.get("introduction")
            )
        ),

        "body": _clean_ai_output(
            _safe_string(
                data.get("body")
            )
        ),

        "way_forward": _clean_ai_output(
            _safe_string(
                data.get("way_forward")
            )
        ),

        "conclusion": _clean_ai_output(
            _safe_string(
                data.get("conclusion")
            )
        ),

        "key_points": _normalize_key_points(
            data.get("key_points")
        ),

        "target_words": target_words,
    }
# ============================================================
# ANSWER EVALUATION WITH AI
# ============================================================
# ============================================================
# AI ANSWER EVALUATION
# ============================================================

def evaluate_answer_with_ai(
    *,
    exam: str,
    question: str,
    answer: str,
    marks: int,
    language: str = "hi",
) -> dict[str, Any]:

    exam = _normalize_exam(exam)

    question = _clean_ai_output(question)
    answer = _clean_ai_output(answer)

    if not question:
        raise ValueError(
            "Question is required for evaluation."
        )

    if not answer:
        raise ValueError(
            "Answer is required for evaluation."
        )

    marks = max(
        1,
        _safe_int(
            marks,
            10,
        ),
    )

    language_name = _language_name(language)

    candidate_answer = _limit_words(
        answer,
        300,
    )

    # --------------------------------------------------------
    # SCORING RUBRIC
    # --------------------------------------------------------

    # Convert marks into a practical 100-point evaluation
    # internally, then scale back to actual question marks.

    prompt = f"""
You are an expert {exam} Mains answer evaluator.

Evaluate the candidate answer strictly against the
EXACT question.

Language: {language_name}

Maximum question marks: {marks}

QUESTION:
{question}

CANDIDATE ANSWER:
{candidate_answer}

============================================================
EVALUATION CRITERIA
============================================================

Evaluate these six dimensions:

1. Content
   - factual accuracy
   - relevant knowledge
   - conceptual clarity

2. Relevance
   - directly answers the question
   - stays focused on the demand
   - avoids unnecessary information

3. Structure
   - introduction
   - logically organised body
   - conclusion
   - appropriate headings/bullets where useful

4. Analysis
   - causes
   - implications
   - arguments
   - multiple dimensions
   - critical analysis
   - balanced view

5. Examples
   - relevant examples
   - constitutional/institutional examples where appropriate
   - schemes/reports/data ONLY when reliable

6. Presentation
   - clarity
   - readability
   - concise expression
   - effective organisation

============================================================
SCORING
============================================================

Give every dimension a score from 0 to 10.

Then calculate:

raw_total =
content_score
+ relevance_score
+ structure_score
+ analysis_score
+ examples_score
+ presentation_score

raw_total maximum = 60.

Convert raw_total proportionally to the actual
question marks.

For example:

If marks = 10:

score = round(raw_total / 60 * 10)

If marks = 15:

score = round(raw_total / 60 * 15)

The final score MUST be between 0 and {marks}.

Do NOT reward length alone.

Do NOT invent facts.

Do NOT reveal reasoning.

Do NOT output <think> or <thinking>.

Keep feedback concise and useful for a UPSC/BPSC student.

Return ONLY valid JSON.

Required JSON:

{{
  "score": 0,
  "max_marks": {marks},

  "content_score": 0,
  "relevance_score": 0,
  "structure_score": 0,
  "analysis_score": 0,
  "examples_score": 0,
  "presentation_score": 0,

  "strengths": [],
  "weaknesses": [],
  "missing_points": [],
  "improvement_tips": [],

  "model_improvement": ""
}}
"""

    # --------------------------------------------------------
    # GROQ
    # --------------------------------------------------------

    raw = _call_groq(
        prompt,
        json_mode=True,
        max_completion_tokens=EVALUATION_MAX_TOKENS,
        max_retries=MAX_RETRIES,
    )

    # --------------------------------------------------------
    # PARSE JSON
    # --------------------------------------------------------

    data = _extract_json(raw)

    if data is None:
        logger.error(
            "Invalid AI evaluation JSON: %s",
            raw[:2000],
        )

        raise RuntimeError(
            "Groq returned an invalid answer evaluation response."
        )

    # --------------------------------------------------------
    # FINAL SCORE
    # --------------------------------------------------------

    score = _safe_int(
        data.get("score"),
        0,
    )

    score = max(
        0,
        min(
            marks,
            score,
        ),
    )

    # --------------------------------------------------------
    # DIMENSION SCORES
    # --------------------------------------------------------

    content_score = max(
        0,
        min(
            10,
            _safe_int(
                data.get("content_score"),
                0,
            ),
        ),
    )

    relevance_score = max(
        0,
        min(
            10,
            _safe_int(
                data.get("relevance_score"),
                0,
            ),
        ),
    )

    structure_score = max(
        0,
        min(
            10,
            _safe_int(
                data.get("structure_score"),
                0,
            ),
        ),
    )

    analysis_score = max(
        0,
        min(
            10,
            _safe_int(
                data.get("analysis_score"),
                0,
            ),
        ),
    )

    examples_score = max(
        0,
        min(
            10,
            _safe_int(
                data.get("examples_score"),
                0,
            ),
        ),
    )

    presentation_score = max(
        0,
        min(
            10,
            _safe_int(
                data.get("presentation_score"),
                0,
            ),
        ),
    )

    # --------------------------------------------------------
    # PERCENTAGE
    # --------------------------------------------------------

    percentage = round(
        (score / marks) * 100,
        2,
    )

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    return {
        "score": score,

        "max_marks": marks,

        "percentage": percentage,

        "content_score": content_score,

        "relevance_score": relevance_score,

        "structure_score": structure_score,

        "analysis_score": analysis_score,

        "examples_score": examples_score,

        "presentation_score": presentation_score,

        "strengths": _safe_list(
            data.get("strengths")
        ),

        "weaknesses": _safe_list(
            data.get("weaknesses")
        ),

        "missing_points": _safe_list(
            data.get("missing_points")
        ),

        "improvement_tips": _safe_list(
            data.get("improvement_tips")
        ),

        "model_improvement": _clean_ai_output(
            _safe_string(
                data.get("model_improvement")
            )
        ),
    }



# ============================================================
# AI ESSAY TOPIC GENERATOR
# ============================================================

def generate_essay_topic(
    *,
    exam: str,
    language: str = "hi",
) -> str:

    exam = _normalize_exam(exam)
    language_name = _language_name(language)

    prompt = f"""
You are an expert {exam} Mains essay topic setter.

Generate ONE fresh and high-quality essay topic
for the {exam} Mains examination.

Language: {language_name}

Requirements:

1. Generate exactly ONE essay topic.
2. Suitable for a 1000-word Mains essay.
3. Encourage multidimensional analysis.
4. Topic should be suitable for UPSC/BPSC Mains.
5. Prefer philosophical, social, governance, economic,
   ethical, environmental, technological or developmental themes.
6. Avoid purely factual topics.
7. Avoid narrow factual questions.
8. Do not repeat common generic topics if possible.
9. Do not invent statistics.
10. Do not invent schemes.
11. Do not invent reports.
12. Do not invent quotations.
13. Do not explain the topic.
14. Do not provide multiple topics.
15. Do not number the topic.
16. Do not include "1000 words".
17. Do not reveal reasoning.
18. Do not output <think> or <thinking>.
19. Return ONLY valid JSON.

Required JSON:

{{
    "topic": "ONE essay topic"
}}
"""

    raw = _call_groq(
        prompt,
        json_mode=True,
        max_completion_tokens=300,
        max_retries=MAX_RETRIES,
    )

    data = _extract_json(raw)

    if not isinstance(data, dict):
        raise RuntimeError(
            "Groq returned invalid essay topic JSON."
        )

    topic = _clean_ai_output(
        _safe_string(
            data.get("topic")
        )
    ).strip()

    if not topic:
        raise RuntimeError(
            "AI returned an empty essay topic."
        )

    # --------------------------------------------------------
    # Remove accidental prefix
    # --------------------------------------------------------

    topic = re.sub(
        r"^(topic|essay topic)\s*:\s*",
        "",
        topic,
        flags=re.IGNORECASE,
    ).strip()

    # --------------------------------------------------------
    # Reject reasoning
    # --------------------------------------------------------

    lowered = topic.lower()

    forbidden_markers = (
        "<think>",
        "</think>",
        "<thinking>",
        "</thinking>",
        "here's a thinking process",
        "here is a thinking process",
        "analyze user input",
        "deconstruct requirements",
    )

    if any(
        marker in lowered
        for marker in forbidden_markers
    ):
        raise RuntimeError(
            "AI generated reasoning instead of an essay topic."
        )

    return topic
# ============================================================
# ESSAY GENERATION
# ============================================================

def generate_essay(
    *,
    exam: str,
    topic: str | None = None,
    target_words: int = 1000,
    language: str = "hi",
) -> dict[str, Any]:

    # ========================================================
    # NORMALIZE
    # ========================================================

    exam = _normalize_exam(exam)

    language = str(
        language or "hi"
    ).strip().lower()

    language_name = _language_name(
        language
    )

    # ========================================================
    # FIXED TARGET
    # ========================================================

    target_words = 1000

    # ========================================================
    # STUDENT TOPIC / AI TOPIC
    # ========================================================

    topic = str(
        topic or ""
    ).strip()

    # --------------------------------------------------------
    # If student did NOT provide a topic,
    # AI will generate one.
    # --------------------------------------------------------

    if not topic:

        topic_prompt = f"""
You are an expert {exam} Mains essay topic setter.

Generate ONE high-quality essay topic for
the {exam} Mains examination.

Language: {language_name}

Requirements:

1. Generate exactly ONE essay topic.
2. The topic must be suitable for a 1000-word Mains essay.
3. It should allow multidimensional analysis.
4. Prefer philosophical, social, governance, economic,
   ethical, environmental, technological or developmental themes.
5. Avoid purely factual topics.
6. Avoid narrow factual topics.
7. Avoid invented statistics.
8. Avoid invented schemes.
9. Avoid invented reports.
10. Do not explain the topic.
11. Do not provide multiple topics.
12. Do not number the topic.
13. Do not include "1000 words".
14. Do not reveal reasoning.
15. Do not output <think>.
16. Do not output <thinking>.
17. Return ONLY JSON.

Required JSON:

{{
    "topic": "ONE essay topic"
}}
"""

        try:

            topic_raw = _call_groq(
                topic_prompt,
                json_mode=True,
                max_completion_tokens=300,
                max_retries=MAX_RETRIES,
            )

        except Exception:

            logger.exception(
                "AI essay topic generation failed | "
                "exam=%s | language=%s",
                exam,
                language,
            )

            raise

        # ----------------------------------------------------
        # Extract JSON
        # ----------------------------------------------------

        topic_data = _extract_json(
            topic_raw
        )

        if not isinstance(
            topic_data,
            dict,
        ):

            raise RuntimeError(
                "AI returned invalid essay topic response."
            )

        topic = _clean_ai_output(
            _safe_string(
                topic_data.get(
                    "topic"
                )
            )
        ).strip()

        # ----------------------------------------------------
        # Remove accidental prefix
        # ----------------------------------------------------

        topic = re.sub(
            r"^(topic|essay topic)\s*:\s*",
            "",
            topic,
            flags=re.IGNORECASE,
        ).strip()

        # ----------------------------------------------------
        # Reject reasoning
        # ----------------------------------------------------

        lowered_topic = topic.lower()

        forbidden_topic_markers = (
            "<think>",
            "<thinking>",
            "here's a thinking process",
            "here is a thinking process",
            "analyze user input",
            "deconstruct requirements",
        )

        if any(
            marker in lowered_topic
            for marker in forbidden_topic_markers
        ):

            raise RuntimeError(
                "AI generated reasoning instead of an essay topic."
            )

        # ----------------------------------------------------
        # Empty topic check
        # ----------------------------------------------------

        if not topic:

            raise RuntimeError(
                "AI failed to generate an essay topic."
            )

        logger.info(
            "Essay topic generated by AI | "
            "exam=%s | topic=%s",
            exam,
            topic,
        )

    # ========================================================
    # STUDENT TOPIC VALIDATION
    # ========================================================

    else:

        topic = _clean_ai_output(
            topic
        ).strip()

        if not topic:

            raise ValueError(
                "Essay topic is required."
            )

    # ========================================================
    # ESSAY PROMPT
    # ========================================================

    prompt = f"""
You are an expert {exam} Mains essay writer.

Write ONE high-quality {exam} Mains essay.

Exam:
{exam}

Language:
{language_name}

Essay Topic:
{topic}

Target length:
approximately 1000 words.

IMPORTANT:

1. Write the essay ONLY in {language_name}.
2. Stay strictly focused on the exact topic.
3. Do not change the topic.
4. Do not create a different topic.
5. Do not repeat the topic unnecessarily.
6. Do not reveal reasoning.
7. Do not output <think>.
8. Do not output <thinking>.
9. Do not mention token count.
10. Do not mention word count.
11. Do not invent statistics.
12. Do not invent government schemes.
13. Do not invent reports.
14. Do not invent constitutional provisions.
15. Do not invent quotations.
16. Use reliable and well-known examples where appropriate.
17. Maintain balanced and mature UPSC/BPSC Mains analysis.
18. Cover multiple relevant dimensions.
19. Include Indian context where relevant.
20. Discuss challenges where appropriate.
21. Include practical solutions.
22. End with a balanced and mature conclusion.

Suggested structure:

1. Introduction
2. Meaning and interpretation
3. Multiple dimensions
4. Indian context and examples
5. Challenges
6. Way forward
7. Conclusion

IMPORTANT OUTPUT RULE:

Return ONLY the complete essay text.

DO NOT return JSON.

DO NOT use Markdown code fences.

DO NOT add "JSON", "Answer",
"Response" or similar labels.

Do not provide any explanation before or after the essay.
"""

    # ========================================================
    # TOKEN BUDGET
    # ========================================================

    essay_tokens = max(
        ESSAY_MAX_TOKENS,
        3000,
    )

    # ========================================================
    # GROQ
    # ========================================================

    try:

        raw = _call_groq(
            prompt,
            json_mode=False,
            max_completion_tokens=essay_tokens,
            max_retries=MAX_RETRIES,
        )

    except Exception:

        logger.exception(
            "Groq essay generation failed | "
            "exam=%s | language=%s | topic=%s",
            exam,
            language,
            topic,
        )

        raise

    # ========================================================
    # EMPTY RESPONSE
    # ========================================================

    if not raw or not str(raw).strip():

        raise RuntimeError(
            "Groq returned an empty essay response."
        )

    # ========================================================
    # CLEAN ESSAY
    # ========================================================

    essay = _clean_ai_output(
        str(raw).strip()
    )

    if not essay:

        raise RuntimeError(
            "Groq returned an empty essay."
        )

    # ========================================================
    # REMOVE MARKDOWN FENCES
    # ========================================================

    essay = re.sub(
        r"^```(?:text|markdown)?\s*",
        "",
        essay,
        flags=re.IGNORECASE,
    )

    essay = re.sub(
        r"\s*```$",
        "",
        essay,
        flags=re.IGNORECASE,
    )

    essay = essay.strip()

    # ========================================================
    # REMOVE ACCIDENTAL REASONING
    # ========================================================

    lowered_essay = essay.lower()

    forbidden_essay_markers = (
        "<think>",
        "<thinking>",
        "here's a thinking process",
        "here is a thinking process",
        "analyze user input",
        "deconstruct requirements",
    )

    if any(
        marker in lowered_essay
        for marker in forbidden_essay_markers
    ):

        raise RuntimeError(
            "AI returned reasoning instead of an essay."
        )

    # ========================================================
    # LIMIT WORDS
    # ========================================================

    essay = _limit_words(
        essay,
        target_words,
    )

    # ========================================================
    # SUPPORTING DATA
    # ========================================================

    introduction = ""
    dimensions = []
    examples = []
    way_forward = ""
    conclusion = ""

    # --------------------------------------------------------
    # Paragraph extraction
    # --------------------------------------------------------

    paragraphs = [
        p.strip()
        for p in re.split(
            r"\n\s*\n",
            essay,
        )
        if p.strip()
    ]

    if paragraphs:

        introduction = paragraphs[0]

    if len(paragraphs) >= 2:

        dimensions = [
            p
            for p in paragraphs[1:5]
        ]

    if paragraphs:

        conclusion = paragraphs[-1]

    # ========================================================
    # RETURN
    # ========================================================

    return {
        "essay": essay,

        "topic": topic,

        "topic_source": (
            "student"
            if topic
            else "ai"
        ),

        "introduction": introduction,

        "dimensions": dimensions,

        "examples": examples,

        "way_forward": way_forward,

        "conclusion": conclusion,

        "target_words": 1000,
    }
# ============================================================
# ESSAY EVALUATION
# ============================================================

def evaluate_essay_with_ai(
    *,
    exam: str,
    topic: str,
    essay: str,
    target_words: int,
    language: str = "hi",
) -> dict[str, Any]:

    exam = _normalize_exam(
        exam
    )

    topic = str(
        topic or ""
    ).strip()

    essay = _clean_ai_output(
        essay
    )

    if not topic:

        raise ValueError(
            "Essay topic is required."
        )

    if not essay:

        raise ValueError(
            "Essay is required."
        )

    language_name = _language_name(
        language
    )

    try:

        target_words = int(
            target_words
        )

    except (
        TypeError,
        ValueError,
    ):

        target_words = 1000

    candidate_essay = _limit_words(
        essay,
        1600,
    )

    prompt = f"""
Evaluate this {exam} Mains essay.

Language: {language_name}

Topic:
{topic}

Target words:
{target_words}

Essay:
{candidate_essay}

Evaluate:

- topic relevance
- structure
- analysis
- examples
- multi-dimensionality
- conclusion
- presentation

Do not reward length alone.

Keep feedback concise.

Do not reveal reasoning.

Do not output <think> or <thinking>.

Return ONLY JSON.

{{
  "score": 0,
  "max_score": 100,
  "content_score": 0,
  "relevance_score": 0,
  "structure_score": 0,
  "analysis_score": 0,
  "examples_score": 0,
  "presentation_score": 0,
  "strengths": [],
  "weaknesses": [],
  "missing_points": [],
  "improvement_tips": [],
  "model_improvement": ""
}}
"""

    raw = _call_groq(
        prompt,
        json_mode=True,
        max_completion_tokens=EVALUATION_MAX_TOKENS,
        max_retries=MAX_RETRIES,
    )

    data = _extract_json(
        raw
    )

    if data is None:

        raise RuntimeError(
            "Groq returned an invalid essay evaluation response."
        )

    score = _safe_int(
        data.get(
            "score"
        ),
        0,
    )

    score = max(
        0,
        min(
            100,
            score,
        ),
    )

    return {
        "score": score,
        "max_score": 100,

        "content_score":
            _safe_int(
                data.get(
                    "content_score"
                ),
                0,
            ),

        "relevance_score":
            _safe_int(
                data.get(
                    "relevance_score"
                ),
                0,
            ),

        "structure_score":
            _safe_int(
                data.get(
                    "structure_score"
                ),
                0,
            ),

        "analysis_score":
            _safe_int(
                data.get(
                    "analysis_score"
                ),
                0,
            ),

        "examples_score":
            _safe_int(
                data.get(
                    "examples_score"
                ),
                0,
            ),

        "presentation_score":
            _safe_int(
                data.get(
                    "presentation_score"
                ),
                0,
            ),

        "strengths":
            _safe_list(
                data.get(
                    "strengths"
                )
            ),

        "weaknesses":
            _safe_list(
                data.get(
                    "weaknesses"
                )
            ),

        "missing_points":
            _safe_list(
                data.get(
                    "missing_points"
                )
            ),

        "improvement_tips":
            _safe_list(
                data.get(
                    "improvement_tips"
                )
            ),

        "model_improvement":
            _clean_ai_output(
                _safe_string(
                    data.get(
                        "model_improvement"
                    )
                )
            ),
    }