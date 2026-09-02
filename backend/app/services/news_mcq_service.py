
from __future__ import annotations

import logging
import re
from typing import Any, Iterable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.mcq import MCQ
from app.services.news_ai_service import generate_news_mcqs


logger = logging.getLogger("app.news_mcq_service")


# ============================================================
# CONFIGURATION
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

OPTION_KEYS = ("A", "B", "C", "D")

DEFAULT_COUNT = 5
MIN_COUNT = 1
MAX_COUNT = 10

MAX_MCQS_PER_ARTICLE_REQUEST = 10

MAX_QUESTION_LENGTH = 2000
MAX_OPTION_LENGTH = 1000
MAX_EXPLANATION_LENGTH = 5000
MAX_CATEGORY_LENGTH = 200
MAX_TOPIC_LENGTH = 300
MAX_STATE_LENGTH = 200


# ============================================================
# RELEVANCE
# ============================================================

MIN_RELEVANCE_SCORE = 0.08
STRONG_RELEVANCE_SCORE = 0.15
MIN_ARTICLE_TERM_OVERLAP = 1


# ============================================================
# META QUESTION BLOCKLIST
# ============================================================

META_QUESTION_PATTERNS = [

    # English
    r"\bwhat\s+is\s+the\s+main\s+topic\b",
    r"\bwhat\s+is\s+the\s+main\s+subject\b",
    r"\bwhat\s+is\s+the\s+main\s+theme\b",
    r"\bwhat\s+type\s+of\s+information\b",
    r"\bwhat\s+kind\s+of\s+information\b",
    r"\bwhat\s+is\s+the\s+exam\s+context\b",
    r"\bwhat\s+is\s+the\s+category\b",
    r"\bwhat\s+category\b",
    r"\bwhat\s+is\s+the\s+source\b",
    r"\bwhich\s+exam\b",
    r"\bwhich\s+examination\b",
    r"\bwhat\s+should\s+be\s+used\b",
    r"\bwhat\s+information\s+should\s+be\s+used\b",
    r"\bwhat\s+information\s+is\s+available\b",
    r"\bwhich\s+of\s+the\s+following\s+describes\s+the\s+article\b",
    r"\bthe\s+main\s+topic\s+of\s+the\s+article\b",
    r"\bthe\s+category\s+of\s+the\s+article\b",

    # Hindi
    r"इस\s+समाचार\s+का\s+मुख्य\s+विषय",
    r"इस\s+समाचार\s+का\s+मुख्य\s+विषय\s+क्या",
    r"दिए\s+गए\s+समाचार\s+के\s+आधार\s+पर\s+किस\s+प्रकार\s+की\s+जानकारी",
    r"किस\s+प्रकार\s+की\s+जानकारी\s+उपलब्ध",
    r"इस\s+एमसीक्यू\s+का\s+परीक्षा\s+संदर्भ",
    r"इस\s+MCQ\s+का\s+परीक्षा\s+संदर्भ",
    r"समाचार\s+की\s+श्रेणी\s+क्या",
    r"समाचार\s+की\s+श्रेणी",
    r"इस\s+समाचार\s+का\s+स्रोत",
    r"इस\s+MCQ\s+को\s+बनाते\s+समय",
    r"इस\s+समाचार\s+से\s+MCQ\s+बनाते\s+समय",
    r"किस\s+जानकारी\s+का\s+उपयोग\s+किया\s+जाना\s+चाहिए",
    r"कौन\s+सी\s+जानकारी\s+उपयोग\s+करनी\s+चाहिए",
]


# ============================================================
# GENERIC / FILLER OPTIONS
# ============================================================

GENERIC_OPTION_PATTERNS = [

    # Hindi
    r"मौसम संबंधी जानकारी",
    r"खेल संबंधी जानकारी",
    r"मनोरंजन संबंधी जानकारी",
    r"कोई जानकारी उपलब्ध नहीं",
    r"केवल मौसम",
    r"केवल खेल",
    r"केवल मनोरंजन",
    r"काल्पनिक तथ्य",
    r"असंबंधित जानकारी",
    r"बाहरी अनुमान",
    r"समाचार की सामग्री",
    r"मुख्य विषय",

    # English
    r"weather information",
    r"sports information",
    r"entertainment information",
    r"no information",
    r"only weather",
    r"only sports",
    r"only entertainment",
    r"fictional facts",
    r"irrelevant information",
    r"external assumption",
    r"article content",
    r"main topic",

    # Other exam fillers
    r"^ssc$",
    r"^banking$",
    r"^railway$",
    r"^upsc$",
    r"^bpsc$",
]


# ============================================================
# BASIC HELPERS
# ============================================================

def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default

    try:
        return str(value).strip()
    except Exception:
        return default


def _normalize_exam(exam: Any) -> str:
    value = _clean_text(exam, "UPSC").upper()

    if value not in SUPPORTED_EXAMS:
        return "UPSC"

    return value


def _normalize_language(language: Any) -> str:
    value = _clean_text(language, "en").lower()

    aliases = {
        "english": "en",
        "en-us": "en",
        "en-in": "en",
        "hindi": "hi",
        "हिंदी": "hi",
        "हिन्दी": "hi",
    }

    value = aliases.get(value, value)

    if value not in SUPPORTED_LANGUAGES:
        return "en"

    return value


def _normalize_difficulty(difficulty: Any) -> str:
    value = _clean_text(
        difficulty,
        "Medium",
    ).capitalize()

    if value not in SUPPORTED_DIFFICULTIES:
        return "Medium"

    return value


def _normalize_question_type(question_type: Any) -> str:
    value = _clean_text(
        question_type,
        "single_correct",
    ).lower()

    aliases = {
        "mcq": "single_correct",
        "single": "single_correct",
        "single_correct": "single_correct",
        "single-correct": "single_correct",
        "multiple_choice": "single_correct",
        "multiple-choice": "single_correct",

        "statement": "statement",
        "statement_based": "statement",
        "statement-based": "statement",

        "assertion_reason": "assertion_reason",
        "assertion-reason": "assertion_reason",
        "assertionreason": "assertion_reason",
    }

    return aliases.get(
        value,
        "single_correct",
    )


def _normalize_count(count: Any) -> int:
    try:
        value = int(count)
    except Exception:
        value = DEFAULT_COUNT

    return max(
        MIN_COUNT,
        min(
            value,
            MAX_COUNT,
            MAX_MCQS_PER_ARTICLE_REQUEST,
        ),
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


def _get_article_id(article: Any) -> Any:
    return getattr(
        article,
        "id",
        None,
    )


def _get_article_title(article: Any) -> str:
    return _article_value(
        article,
        "title",
        "headline",
        "news_title",
    )


def _get_article_content(article: Any) -> str:
    return _article_value(
        article,
        "content",
        "description",
        "summary",
        "body",
        "text",
    )


def _get_article_source(article: Any) -> str:
    return _article_value(
        article,
        "source",
        "source_name",
        "publisher",
    )


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def _normalize_for_compare(
    value: Any,
) -> str:

    text = _clean_text(value).casefold()

    text = " ".join(
        text.split()
    )

    text = re.sub(
        r"[^\w\s\u0900-\u097F]",
        "",
        text,
    )

    return text.strip()


def _tokenize_meaningful(
    value: Any,
) -> set[str]:

    text = _normalize_for_compare(value)

    if not text:
        return set()

    tokens: set[str] = set()

    for word in text.split():

        if len(word) >= 4:
            tokens.add(word)

    return tokens


# ============================================================
# ANSWER NORMALIZATION
# ============================================================

def _normalize_answer(
    value: Any,
) -> str | None:

    value = _clean_text(value).upper()

    if not value:
        return None

    value = re.sub(
        r"^(CORRECT\s+ANSWER|ANSWER|OPTION)\s*[:\-]?\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )

    value = value.strip(
        " .:-)("
    )

    if value in OPTION_KEYS:
        return value

    match = re.match(
        r"^([ABCD])(?:[\s\.\)\:\-]|$)",
        value,
    )

    if match:
        return match.group(1)

    return None


# ============================================================
# OPTION NORMALIZATION
# ============================================================

def _normalize_option(
    option: Any,
    expected_key: str,
) -> dict[str, str] | None:

    if isinstance(option, str):

        text = _clean_text(option)

        if not text:
            return None

        return {
            "key": expected_key,
            "text": text[:MAX_OPTION_LENGTH],
        }

    if not isinstance(option, dict):
        return None

    key = _clean_text(
        option.get("key")
        or option.get("label")
        or option.get("option")
        or option.get("id")
        or expected_key
    ).upper()

    key = key.strip(
        " .:)-("
    )

    text = _clean_text(
        option.get("text")
        or option.get("value")
        or option.get("content")
        or option.get("option_text")
    )

    if key not in OPTION_KEYS:
        key = expected_key

    if not text:
        return None

    return {
        "key": key,
        "text": text[:MAX_OPTION_LENGTH],
    }


def _normalize_options(
    raw_options: Any,
) -> list[dict[str, str]]:

    result: dict[str, str] = {}

    # --------------------------------------------------------
    # LIST
    # --------------------------------------------------------

    if isinstance(raw_options, list):

        for index, raw_option in enumerate(
            raw_options[:4]
        ):

            expected_key = OPTION_KEYS[index]

            normalized = _normalize_option(
                raw_option,
                expected_key,
            )

            if normalized is None:
                continue

            result[
                normalized["key"]
            ] = normalized["text"]

    # --------------------------------------------------------
    # DICTIONARY
    # --------------------------------------------------------

    elif isinstance(raw_options, dict):

        for key in OPTION_KEYS:

            raw_value = raw_options.get(key)

            if raw_value is None:
                raw_value = raw_options.get(
                    key.lower()
                )

            if raw_value is None:
                raw_value = raw_options.get(
                    f"option_{key.lower()}"
                )

            if isinstance(raw_value, dict):

                raw_value = (
                    raw_value.get("text")
                    or raw_value.get("value")
                    or raw_value.get("content")
                    or raw_value.get("option_text")
                )

            text = _clean_text(raw_value)

            if text:
                result[key] = text[
                    :MAX_OPTION_LENGTH
                ]

    # --------------------------------------------------------
    # LEGACY
    # --------------------------------------------------------

    if isinstance(raw_options, dict):

        aliases = {
            "A": (
                "option_a",
                "optionA",
                "a",
            ),
            "B": (
                "option_b",
                "optionB",
                "b",
            ),
            "C": (
                "option_c",
                "optionC",
                "c",
            ),
            "D": (
                "option_d",
                "optionD",
                "d",
            ),
        }

        for key, fields in aliases.items():

            if key in result:
                continue

            for field in fields:

                value = _clean_text(
                    raw_options.get(field)
                )

                if value:

                    result[key] = value[
                        :MAX_OPTION_LENGTH
                    ]

                    break

    return [
        {
            "key": key,
            "text": result.get(key, ""),
        }
        for key in OPTION_KEYS
    ]


# ============================================================
# QUESTION NORMALIZATION
# ============================================================

def _normalize_question_text(
    value: Any,
) -> str:

    text = _clean_text(value)

    if not text:
        return ""

    text = text.replace(
        "```json",
        "",
    )

    text = text.replace(
        "```",
        "",
    )

    prefixes = (
        "Question:",
        "QUESTION:",
        "question:",
        "Q:",
        "Q.",
        "प्रश्न:",
        "प्रश्न :",
    )

    for prefix in prefixes:

        if text.startswith(prefix):

            text = text[
                len(prefix):
            ].strip()

    text = text.strip(
        "\"'"
    )

    text = " ".join(
        text.split()
    )

    return text[
        :MAX_QUESTION_LENGTH
    ]


# ============================================================
# META QUESTION DETECTION
# ============================================================

def _is_meta_question(
    question: str,
) -> bool:

    normalized = _normalize_for_compare(
        question
    )

    if not normalized:
        return True

    for pattern in META_QUESTION_PATTERNS:

        try:

            if re.search(
                pattern,
                question,
                flags=re.IGNORECASE,
            ):
                return True

        except re.error:
            continue

    meta_words = (
        "main topic",
        "main subject",
        "main theme",
        "exam context",
        "article category",
        "type of information",
        "what information",
        "what kind of information",
        "मुख्य विषय",
        "मुख्य विषय क्या",
        "परीक्षा संदर्भ",
        "समाचार की श्रेणी",
        "किस प्रकार की जानकारी",
        "किस जानकारी का उपयोग",
    )

    for phrase in meta_words:

        if phrase.casefold() in normalized:
            return True

    return False


# ============================================================
# GENERIC OPTION DETECTION
# ============================================================

def _contains_generic_option(
    options: list[dict[str, Any]],
) -> bool:

    for option in options:

        if not isinstance(option, dict):
            continue

        text = _clean_text(
            option.get("text")
        )

        if not text:
            continue

        for pattern in GENERIC_OPTION_PATTERNS:

            try:

                if re.search(
                    pattern,
                    text,
                    flags=re.IGNORECASE,
                ):
                    return True

            except re.error:
                continue

    return False


# ============================================================
# ARTICLE RELEVANCE
# ============================================================

def _article_relevance_score(
    article: Any,
    question: str,
    options: list[dict[str, Any]],
) -> float:

    title = _get_article_title(article)

    content = _get_article_content(article)

    source_text = _normalize_for_compare(
        f"{title} {content}"
    )

    if not source_text:
        return 0.0

    generated_text = _normalize_for_compare(
        f"{question} "
        + " ".join(
            _clean_text(
                option.get("text")
            )
            for option in options
            if isinstance(option, dict)
        )
    )

    if not generated_text:
        return 0.0

    source_words = _tokenize_meaningful(
        source_text
    )

    generated_words = _tokenize_meaningful(
        generated_text
    )

    if not source_words or not generated_words:
        return 0.0

    overlap = source_words.intersection(
        generated_words
    )

    return len(overlap) / max(
        1,
        len(generated_words),
    )


def _article_title_overlap(
    article: Any,
    question: str,
    options: list[dict[str, Any]],
) -> int:

    title = _get_article_title(article)

    if not title:
        return 0

    title_words = _tokenize_meaningful(
        title
    )

    generated_text = (
        question
        + " "
        + " ".join(
            _clean_text(
                option.get("text")
            )
            for option in options
            if isinstance(option, dict)
        )
    )

    generated_words = _tokenize_meaningful(
        generated_text
    )

    return len(
        title_words.intersection(
            generated_words
        )
    )


# ============================================================
# FACTUAL / COMPETITIVE EXAM GUARD
# ============================================================

def _passes_factual_guard(
    article: Any,
    question: str,
    options: list[dict[str, Any]],
) -> bool:

    # --------------------------------------------------------
    # NO META QUESTIONS
    # --------------------------------------------------------

    if _is_meta_question(question):

        logger.warning(
            "Rejected meta MCQ: %s",
            question[:150],
        )

        return False

    # --------------------------------------------------------
    # NO GENERIC OPTIONS
    # --------------------------------------------------------

    if _contains_generic_option(options):

        logger.warning(
            "Rejected generic/filler MCQ."
        )

        return False

    # --------------------------------------------------------
    # ARTICLE RELEVANCE
    # --------------------------------------------------------

    score = _article_relevance_score(
        article=article,
        question=question,
        options=options,
    )

    title_overlap = _article_title_overlap(
        article=article,
        question=question,
        options=options,
    )

    title = _get_article_title(article)
    content = _get_article_content(article)

    if not title and not content:

        logger.warning(
            "Article has no title/content; "
            "relevance guard skipped."
        )

        return True

    if score >= STRONG_RELEVANCE_SCORE:
        return True

    if (
        title_overlap >= MIN_ARTICLE_TERM_OVERLAP
        and score >= MIN_RELEVANCE_SCORE
    ):
        return True

    logger.warning(
        "Rejected unrelated MCQ | score=%.3f | "
        "title_overlap=%s | question=%s",
        score,
        title_overlap,
        question[:180],
    )

    return False


# ============================================================
# DEDUPLICATION
# ============================================================

def _question_key(
    question: Any,
) -> str:

    return _normalize_for_compare(
        question
    )


def _options_key(
    options: Iterable[dict[str, Any]],
) -> str:

    values: list[str] = []

    for option in options:

        if not isinstance(option, dict):
            continue

        values.append(
            _normalize_for_compare(
                option.get("text")
            )
        )

    return "|".join(values)


def _mcq_fingerprint(
    question: Any,
    options: Iterable[dict[str, Any]],
) -> str:

    question_key = _question_key(
        question
    )

    options_key = _options_key(
        options
    )

    if not question_key:
        return ""

    return (
        question_key
        + "::"
        + options_key
    )


def _deduplicate_mcqs(
    questions: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    result: list[dict[str, Any]] = []

    seen: set[str] = set()

    for question in questions:

        fingerprint = _mcq_fingerprint(
            question.get("question"),
            question.get("options", []),
        )

        if not fingerprint:
            continue

        if fingerprint in seen:

            logger.info(
                "Duplicate MCQ removed."
            )

            continue

        seen.add(
            fingerprint
        )

        result.append(
            question
        )

    return result


# ============================================================
# ARTICLE RELATION
# ============================================================

def _article_relation_column():

    if hasattr(MCQ, "current_affair_id"):
        return MCQ.current_affair_id

    if hasattr(MCQ, "news_id"):
        return MCQ.news_id

    if hasattr(MCQ, "article_id"):
        return MCQ.article_id

    return None


# ============================================================
# VALIDATE + NORMALIZE MCQ
# ============================================================

def _validate_and_normalize_mcq(
    item: Any,
    article: Any,
    exam: str,
    language: str,
    difficulty: str,
    question_type: str,
) -> dict[str, Any] | None:

    if not isinstance(item, dict):
        return None

    # ========================================================
    # QUESTION
    # ========================================================

    question = _normalize_question_text(
        item.get("question")
        or item.get("question_text")
        or item.get("text")
    )

    if len(question) < 10:

        logger.warning(
            "MCQ rejected: question too short."
        )

        return None

    if _is_meta_question(question):

        logger.warning(
            "MCQ rejected: meta-question | %s",
            question[:180],
        )

        return None

    # ========================================================
    # OPTIONS
    # ========================================================

    raw_options = item.get(
        "options"
    )

    if raw_options is None:
        raw_options = item

    options = _normalize_options(
        raw_options
    )

    option_texts = [
        _clean_text(
            option.get("text")
        )
        for option in options
    ]

    if len(option_texts) != 4:
        return None

    if any(
        not text
        for text in option_texts
    ):

        logger.warning(
            "MCQ rejected: missing option."
        )

        return None

    normalized_option_texts = [
        _normalize_for_compare(text)
        for text in option_texts
    ]

    if len(
        set(normalized_option_texts)
    ) != 4:

        logger.warning(
            "MCQ rejected: duplicate options."
        )

        return None

    if _contains_generic_option(options):

        logger.warning(
            "MCQ rejected: generic options."
        )

        return None

    # ========================================================
    # ANSWER
    # ========================================================

    correct_answer = _normalize_answer(
        item.get("correct_answer")
        or item.get("answer")
        or item.get("correct")
        or item.get("correct_option")
    )

    if correct_answer not in OPTION_KEYS:

        logger.warning(
            "MCQ rejected: invalid answer=%s",
            item.get("correct_answer"),
        )

        return None

    answer_index = OPTION_KEYS.index(
        correct_answer
    )

    if not option_texts[answer_index]:

        logger.warning(
            "MCQ rejected: answer points to empty option."
        )

        return None

    # ========================================================
    # EXPLANATION
    # ========================================================

    explanation = _clean_text(
        item.get("explanation")
        or item.get("solution")
        or item.get("reason")
        or item.get("answer_explanation")
    )

    if not explanation:

        logger.warning(
            "MCQ rejected: missing explanation."
        )

        return None

    explanation = explanation[
        :MAX_EXPLANATION_LENGTH
    ]

    generic_explanation_patterns = [
        r"शीर्षक.*मुख्य विषय",
        r"परीक्षा संदर्भ",
        r"article.*category",
        r"main topic",
        r"exam context",
        r"article category",
        r"समाचार की सामग्री",
    ]

    for pattern in generic_explanation_patterns:

        try:

            if re.search(
                pattern,
                explanation,
                flags=re.IGNORECASE,
            ):

                logger.warning(
                    "MCQ rejected: generic explanation."
                )

                return None

        except re.error:
            continue

    # ========================================================
    # CATEGORY
    # ========================================================

    category = _clean_text(
        item.get("category")
    )

    if not category:

        category = _article_value(
            article,
            "category",
        )

    category = (
        category or "General"
    )[:MAX_CATEGORY_LENGTH]

    # ========================================================
    # TOPIC
    # ========================================================

    topic = _clean_text(
        item.get("topic")
    )

    if not topic:

        topic = _article_value(
            article,
            "topic",
        )

    topic = (
        topic[:MAX_TOPIC_LENGTH]
        if topic
        else None
    )

    # ========================================================
    # STATE
    # ========================================================

    state = _clean_text(
        item.get("state")
    )

    if not state:

        state = _article_value(
            article,
            "state",
        )

    state = (
        state[:200]
        if state
        else None
    )

    # ========================================================
    # RELEVANCE
    # ========================================================

    if not _passes_factual_guard(
        article=article,
        question=question,
        options=options,
    ):
        return None

    # ========================================================
    # FINAL
    # ========================================================

    return {
        "question": question,
        "question_text": question,

        "options": options,

        "correct_answer": correct_answer,

        "explanation": explanation,

        "difficulty": difficulty,
        "exam": exam,
        "category": category,
        "topic": topic,
        "state": state,
        "language": language,
        "question_type": question_type,

        "generation_source": _clean_text(
            item.get("generation_source"),
            "groq",
        ),
    }


# ============================================================
# DATABASE DUPLICATE CHECK
# ============================================================

def _existing_question_exists(
    db: Session,
    article_id: Any,
    question: str,
    exam: str,
    language: str,
) -> bool:

    if article_id is None:
        return False

    normalized_question = _question_key(
        question
    )

    if not normalized_question:
        return False

    try:

        query = db.query(MCQ)

        relation_column = (
            _article_relation_column()
        )

        if relation_column is not None:

            query = query.filter(
                relation_column == article_id
            )

        if hasattr(MCQ, "exam"):

            query = query.filter(
                MCQ.exam == exam
            )

        if hasattr(MCQ, "language"):

            query = query.filter(
                MCQ.language == language
            )

        rows = (
            query
            .order_by(
                MCQ.id.desc()
            )
            .limit(200)
            .all()
        )

        for row in rows:

            existing_question = _clean_text(
                getattr(
                    row,
                    "question",
                    None,
                )
                or getattr(
                    row,
                    "question_text",
                    None,
                )
            )

            if (
                _question_key(
                    existing_question
                )
                == normalized_question
            ):
                return True

        return False

    except Exception:

        logger.exception(
            "Database duplicate check failed | "
            "article_id=%s",
            article_id,
        )

        return False


# ============================================================
# BUILD MCQ MODEL
# ============================================================

def _build_mcq_model(
    item: dict[str, Any],
    article: Any,
) -> MCQ:

    article_id = _get_article_id(
        article
    )

    options = item.get(
        "options",
        [],
    )

    option_map = {
        option["key"]: option["text"]
        for option in options
        if isinstance(option, dict)
        and option.get("key")
    }

    payload: dict[str, Any] = {}

    # QUESTION
    if hasattr(MCQ, "question"):
        payload["question"] = item[
            "question"
        ]

    if hasattr(MCQ, "question_text"):
        payload["question_text"] = item[
            "question"
        ]

    # ANSWER
    if hasattr(MCQ, "correct_answer"):
        payload["correct_answer"] = item[
            "correct_answer"
        ]

    if hasattr(MCQ, "answer"):
        payload["answer"] = item[
            "correct_answer"
        ]

    # EXPLANATION
    if hasattr(MCQ, "explanation"):
        payload["explanation"] = item[
            "explanation"
        ]

    # META
    if hasattr(MCQ, "exam"):
        payload["exam"] = item["exam"]

    if hasattr(MCQ, "language"):
        payload["language"] = item[
            "language"
        ]

    if hasattr(MCQ, "difficulty"):
        payload["difficulty"] = item[
            "difficulty"
        ]

    if hasattr(MCQ, "question_type"):
        payload["question_type"] = item[
            "question_type"
        ]

    if hasattr(MCQ, "category"):
        payload["category"] = item[
            "category"
        ]

    if hasattr(MCQ, "topic"):
        payload["topic"] = item.get(
            "topic"
        )

    if hasattr(MCQ, "state"):
        payload["state"] = item.get(
            "state"
        )

    # ARTICLE RELATION
    if hasattr(MCQ, "current_affair_id"):
        payload[
            "current_affair_id"
        ] = article_id

    elif hasattr(MCQ, "news_id"):
        payload[
            "news_id"
        ] = article_id

    elif hasattr(MCQ, "article_id"):
        payload[
            "article_id"
        ] = article_id

    # JSON OPTIONS
    if hasattr(MCQ, "options"):
        payload["options"] = options

    # LEGACY OPTIONS
    legacy_fields = {
        "option_a": option_map.get("A"),
        "option_b": option_map.get("B"),
        "option_c": option_map.get("C"),
        "option_d": option_map.get("D"),
    }

    for field, value in legacy_fields.items():

        if hasattr(MCQ, field):
            payload[field] = value

    # SOURCE
    if hasattr(MCQ, "generation_source"):

        payload[
            "generation_source"
        ] = item.get(
            "generation_source",
            "groq",
        )

    # ACTIVE
    if hasattr(MCQ, "is_active"):
        payload["is_active"] = True

    # VERIFIED
    if hasattr(MCQ, "is_verified"):
        payload["is_verified"] = False

    return MCQ(**payload)


# ============================================================
# SAVE MCQS
# ============================================================

def save_news_mcqs(
    db: Session,
    article: Any,
    questions: list[dict[str, Any]],
) -> list[MCQ]:

    if not questions:
        return []

    article_id = _get_article_id(
        article
    )

    saved: list[MCQ] = []

    try:

        questions = _deduplicate_mcqs(
            questions
        )

        for item in questions:

            question_text = _clean_text(
                item.get("question")
            )

            if not question_text:
                continue

            exists = _existing_question_exists(
                db=db,
                article_id=article_id,
                question=question_text,
                exam=_normalize_exam(
                    item.get("exam")
                ),
                language=_normalize_language(
                    item.get("language")
                ),
            )

            if exists:

                logger.info(
                    "Existing MCQ skipped | "
                    "article_id=%s | question=%s",
                    article_id,
                    question_text[:80],
                )

                continue

            mcq = _build_mcq_model(
                item=item,
                article=article,
            )

            db.add(mcq)

            saved.append(mcq)

        if saved:
            db.flush()

        return saved

    except SQLAlchemyError:

        db.rollback()

        logger.exception(
            "Failed to save news MCQs | "
            "article_id=%s",
            article_id,
        )

        raise

    except Exception:

        db.rollback()

        logger.exception(
            "Unexpected error saving MCQs | "
            "article_id=%s",
            article_id,
        )

        raise


# ============================================================
# AI GENERATION
# ============================================================

def _call_news_mcq_ai(
    article: Any,
    exam: str,
    language: str,
    count: int,
    difficulty: str,
    question_type: str,
) -> list[Any]:

    result = generate_news_mcqs(
        article=article,
        exam=exam,
        language=language,
        count=count,
        difficulty=difficulty,
        question_type=question_type,
    )

    if result is None:
        return []

    if isinstance(result, list):
        return result

    if isinstance(result, dict):

        questions = (
            result.get("questions")
            or result.get("mcqs")
            or result.get("data")
        )

        if isinstance(
            questions,
            list,
        ):
            return questions

    logger.warning(
        "Unexpected AI MCQ response type=%s",
        type(result).__name__,
    )

    return []


# ============================================================
# MAIN GENERATE + SAVE
# ============================================================

def generate_and_save_news_mcqs(
    db: Session,
    article: Any,
    exam: str = "UPSC",
    language: str = "en",
    count: int = 5,
    difficulty: str = "Medium",
    question_type: str = "single_correct",
    save_to_db: bool = True,
) -> list[Any]:

    exam = _normalize_exam(exam)

    language = _normalize_language(
        language
    )

    difficulty = _normalize_difficulty(
        difficulty
    )

    question_type = _normalize_question_type(
        question_type
    )

    count = _normalize_count(
        count
    )

    if article is None:

        logger.error(
            "Cannot generate MCQs: article is None."
        )

        return []

    article_id = _get_article_id(
        article
    )

    logger.info(
        "Starting news MCQ generation | "
        "article_id=%s | exam=%s | language=%s | "
        "count=%s | difficulty=%s | question_type=%s",
        article_id,
        exam,
        language,
        count,
        difficulty,
        question_type,
    )

    # ========================================================
    # AI
    # ========================================================

    try:

        generated = _call_news_mcq_ai(
            article=article,
            exam=exam,
            language=language,
            count=count,
            difficulty=difficulty,
            question_type=question_type,
        )

    except Exception:

        logger.exception(
            "AI MCQ generation failed | "
            "article_id=%s",
            article_id,
        )

        return []

    if not generated:

        logger.warning(
            "AI returned no MCQs | "
            "article_id=%s",
            article_id,
        )

        return []

    # ========================================================
    # VALIDATION
    # ========================================================

    normalized: list[
        dict[str, Any]
    ] = []

    for item in generated:

        validated = _validate_and_normalize_mcq(
            item=item,
            article=article,
            exam=exam,
            language=language,
            difficulty=difficulty,
            question_type=question_type,
        )

        if validated is not None:
            normalized.append(
                validated
            )

    # ========================================================
    # DEDUPLICATE
    # ========================================================

    normalized = _deduplicate_mcqs(
        normalized
    )

    normalized = normalized[
        :count
    ]

    if not normalized:

        logger.warning(
            "No valid factual MCQs after validation | "
            "article_id=%s",
            article_id,
        )

        return []

    # ========================================================
    # GENERATION ONLY
    # ========================================================

    if not save_to_db:

        logger.info(
            "Generation-only completed | "
            "article_id=%s | generated=%s",
            article_id,
            len(normalized),
        )

        return normalized

    # ========================================================
    # SAVE
    # ========================================================

    saved = save_news_mcqs(
        db=db,
        article=article,
        questions=normalized,
    )

    logger.info(
        "News MCQ generation completed | "
        "article_id=%s | generated=%s | saved=%s",
        article_id,
        len(normalized),
        len(saved),
    )

    return saved


# ============================================================
# GENERATION ONLY
# ============================================================

def generate_news_mcqs_only(
    article: Any,
    exam: str = "UPSC",
    language: str = "en",
    count: int = 5,
    difficulty: str = "Medium",
    question_type: str = "single_correct",
) -> list[dict[str, Any]]:

    exam = _normalize_exam(exam)

    language = _normalize_language(
        language
    )

    difficulty = _normalize_difficulty(
        difficulty
    )

    question_type = _normalize_question_type(
        question_type
    )

    count = _normalize_count(
        count
    )

    if article is None:
        return []

    try:

        generated = _call_news_mcq_ai(
            article=article,
            exam=exam,
            language=language,
            count=count,
            difficulty=difficulty,
            question_type=question_type,
        )

    except Exception:

        logger.exception(
            "Generation-only MCQ request failed."
        )

        return []

    if not generated:
        return []

    normalized: list[
        dict[str, Any]
    ] = []

    for item in generated:

        validated = _validate_and_normalize_mcq(
            item=item,
            article=article,
            exam=exam,
            language=language,
            difficulty=difficulty,
            question_type=question_type,
        )

        if validated is not None:
            normalized.append(
                validated
            )

    normalized = _deduplicate_mcqs(
        normalized
    )

    return normalized[:count]


# ============================================================
# GET MCQS
# ============================================================

def get_news_mcqs(
    db: Session,
    article_id: int | None = None,
    exam: str | None = None,
    language: str | None = None,
    difficulty: str | None = None,
    question_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[MCQ]:

    try:
        limit = int(limit)
    except Exception:
        limit = 50

    try:
        offset = int(offset)
    except Exception:
        offset = 0

    limit = max(
        1,
        min(limit, 100),
    )

    offset = max(
        0,
        offset,
    )

    query = db.query(MCQ)

    # ARTICLE
    if article_id is not None:

        relation_column = (
            _article_relation_column()
        )

        if relation_column is not None:

            query = query.filter(
                relation_column == article_id
            )

    # EXAM
    if exam and hasattr(MCQ, "exam"):

        query = query.filter(
            MCQ.exam
            == _normalize_exam(exam)
        )

    # LANGUAGE
    if language and hasattr(
        MCQ,
        "language",
    ):

        query = query.filter(
            MCQ.language
            == _normalize_language(language)
        )

    # DIFFICULTY
    if difficulty and hasattr(
        MCQ,
        "difficulty",
    ):

        query = query.filter(
            MCQ.difficulty
            == _normalize_difficulty(
                difficulty
            )
        )

    # QUESTION TYPE
    if question_type and hasattr(
        MCQ,
        "question_type",
    ):

        query = query.filter(
            MCQ.question_type
            == _normalize_question_type(
                question_type
            )
        )

    # ACTIVE
    if hasattr(MCQ, "is_active"):

        query = query.filter(
            MCQ.is_active.is_(True)
        )

    # ORDER
    if hasattr(MCQ, "created_at"):

        query = query.order_by(
            MCQ.created_at.desc()
        )

    elif hasattr(MCQ, "id"):

        query = query.order_by(
            MCQ.id.desc()
        )

    return (
        query
        .offset(offset)
        .limit(limit)
        .all()
    )


# ============================================================
# SERIALIZE OPTIONS
# ============================================================

def _serialize_options(
    mcq: MCQ,
) -> list[dict[str, str]]:

    raw_options = getattr(
        mcq,
        "options",
        None,
    )

    if isinstance(
        raw_options,
        (list, dict),
    ):

        options = _normalize_options(
            raw_options
        )

        if all(
            option.get("text")
            for option in options
        ):
            return options

    return [
        {
            "key": "A",
            "text": _clean_text(
                getattr(
                    mcq,
                    "option_a",
                    None,
                )
            ),
        },
        {
            "key": "B",
            "text": _clean_text(
                getattr(
                    mcq,
                    "option_b",
                    None,
                )
            ),
        },
        {
            "key": "C",
            "text": _clean_text(
                getattr(
                    mcq,
                    "option_c",
                    None,
                )
            ),
        },
        {
            "key": "D",
            "text": _clean_text(
                getattr(
                    mcq,
                    "option_d",
                    None,
                )
            ),
        },
    ]


# ============================================================
# SERIALIZE SINGLE MCQ
# ============================================================

def serialize_mcq(
    mcq: MCQ,
) -> dict[str, Any]:

    question = _clean_text(
        getattr(
            mcq,
            "question",
            None,
        )
        or getattr(
            mcq,
            "question_text",
            None,
        )
    )

    correct_answer = _normalize_answer(
        getattr(
            mcq,
            "correct_answer",
            None,
        )
        or getattr(
            mcq,
            "answer",
            None,
        )
    )

    options = _serialize_options(
        mcq
    )

    article_id = (
        getattr(
            mcq,
            "current_affair_id",
            None,
        )
        or getattr(
            mcq,
            "news_id",
            None,
        )
        or getattr(
            mcq,
            "article_id",
            None,
        )
    )

    return {
        "id": getattr(
            mcq,
            "id",
            None,
        ),

        "current_affair_id": article_id,
        "article_id": article_id,
        "news_id": article_id,

        "question": question,
        "question_text": question,

        "option_a": (
            options[0]["text"]
            if len(options) > 0
            else None
        ),

        "option_b": (
            options[1]["text"]
            if len(options) > 1
            else None
        ),

        "option_c": (
            options[2]["text"]
            if len(options) > 2
            else None
        ),

        "option_d": (
            options[3]["text"]
            if len(options) > 3
            else None
        ),

        "options": options,

        "correct_answer": correct_answer,
        "answer": correct_answer,

        "explanation": _clean_text(
            getattr(
                mcq,
                "explanation",
                None,
            )
        ),

        "exam": _clean_text(
            getattr(
                mcq,
                "exam",
                None,
            )
        ),

        "language": _clean_text(
            getattr(
                mcq,
                "language",
                None,
            )
        ),

        "difficulty": _clean_text(
            getattr(
                mcq,
                "difficulty",
                None,
            )
        ),

        "question_type": _clean_text(
            getattr(
                mcq,
                "question_type",
                None,
            ),
            "single_correct",
        ),

        "category": _clean_text(
            getattr(
                mcq,
                "category",
                None,
            ),
            "General",
        ),

        "topic": (
            _clean_text(
                getattr(
                    mcq,
                    "topic",
                    None,
                )
            )
            or None
        ),

        "state": (
            _clean_text(
                getattr(
                    mcq,
                    "state",
                    None,
                )
            )
            or None
        ),

        "generation_source": _clean_text(
            getattr(
                mcq,
                "generation_source",
                None,
            ),
            "groq",
        ),

        "is_verified": bool(
            getattr(
                mcq,
                "is_verified",
                False,
            )
        ),

        "is_active": bool(
            getattr(
                mcq,
                "is_active",
                True,
            )
        ),

        "created_at": getattr(
            mcq,
            "created_at",
            None,
        ),

        "updated_at": getattr(
            mcq,
            "updated_at",
            None,
        ),
    }


# ============================================================
# COMPATIBILITY
# ============================================================

def mcq_to_dict(
    mcq: MCQ,
) -> dict[str, Any]:

    return serialize_mcq(
        mcq
    )


def serialize_mcqs(
    mcqs: Iterable[MCQ],
) -> list[dict[str, Any]]:

    return [
        serialize_mcq(mcq)
        for mcq in mcqs
    ]


def mcqs_to_dict(
    mcqs: Iterable[MCQ],
) -> list[dict[str, Any]]:

    return [
        mcq_to_dict(mcq)
        for mcq in mcqs
    ]


# ============================================================
# REGENERATE
# ============================================================

def regenerate_news_mcqs(
    db: Session,
    article: Any,
    exam: str = "UPSC",
    language: str = "en",
    count: int = 5,
    difficulty: str = "Medium",
    question_type: str = "single_correct",
) -> list[Any]:

    return generate_and_save_news_mcqs(
        db=db,
        article=article,
        exam=exam,
        language=language,
        count=count,
        difficulty=difficulty,
        question_type=question_type,
        save_to_db=True,
    )


# ============================================================
# LEGACY
# ============================================================

def generate_mcqs_for_article(
    db: Session,
    article: Any,
    exam: str = "UPSC",
    language: str = "en",
    count: int = 5,
    difficulty: str = "Medium",
    question_type: str = "single_correct",
) -> list[Any]:

    return generate_and_save_news_mcqs(
        db=db,
        article=article,
        exam=exam,
        language=language,
        count=count,
        difficulty=difficulty,
        question_type=question_type,
        save_to_db=True,
    )


# ============================================================
# VERY IMPORTANT LEGACY NAME
# ============================================================

def generate_mcqs(
    db: Session | None = None,
    article: Any = None,
    exam: str = "UPSC",
    language: str = "en",
    count: int = 5,
    difficulty: str = "Medium",
    question_type: str = "single_correct",
    save_to_db: bool = True,
) -> list[Any]:

    if article is None:
        return []

    if db is None:

        return generate_news_mcqs_only(
            article=article,
            exam=exam,
            language=language,
            count=count,
            difficulty=difficulty,
            question_type=question_type,
        )

    return generate_and_save_news_mcqs(
        db=db,
        article=article,
        exam=exam,
        language=language,
        count=count,
        difficulty=difficulty,
        question_type=question_type,
        save_to_db=save_to_db,
    )


# ============================================================
# ARTICLE-BASED NAME
# ============================================================

def generate_mcqs_for_news(
    db: Session,
    article: Any,
    exam: str = "UPSC",
    language: str = "en",
    count: int = 5,
    difficulty: str = "Medium",
    question_type: str = "single_correct",
) -> list[Any]:

    return generate_mcqs(
        db=db,
        article=article,
        exam=exam,
        language=language,
        count=count,
        difficulty=difficulty,
        question_type=question_type,
        save_to_db=True,
    )


# ============================================================
# CURRENT AFFAIR COMPATIBILITY
# ============================================================

def generate_mcqs_for_current_affair(
    db: Session,
    current_affair: Any,
    exam: str = "UPSC",
    language: str = "en",
    count: int = 5,
    difficulty: str = "Medium",
    question_type: str = "single_correct",
) -> list[Any]:

    return generate_mcqs(
        db=db,
        article=current_affair,
        exam=exam,
        language=language,
        count=count,
        difficulty=difficulty,
        question_type=question_type,
        save_to_db=True,
    )


# ============================================================
# DELETE MCQS FOR ARTICLE
# ============================================================

def delete_news_mcqs(
    db: Session,
    article_id: int,
) -> int:

    if article_id is None:
        return 0

    try:

        query = db.query(MCQ)

        relation_column = (
            _article_relation_column()
        )

        if relation_column is None:

            logger.warning(
                "MCQ model has no article relation."
            )

            return 0

        query = query.filter(
            relation_column == article_id
        )

        deleted = query.delete(
            synchronize_session=False
        )

        db.flush()

        logger.info(
            "Deleted MCQs | article_id=%s | count=%s",
            article_id,
            deleted,
        )

        return int(
            deleted or 0
        )

    except SQLAlchemyError:

        db.rollback()

        logger.exception(
            "Failed deleting article MCQs | "
            "article_id=%s",
            article_id,
        )

        raise

    except Exception:

        db.rollback()

        logger.exception(
            "Unexpected error deleting MCQs | "
            "article_id=%s",
            article_id,
        )

        raise


# ============================================================
# IMPORTANT ROUTER COMPATIBILITY ALIAS
# ============================================================

def delete_article_mcqs(
    db: Session,
    article_id: int,
) -> int:

    """
    Backward-compatible alias.

    news_routes.py may import:
        delete_article_mcqs

    Internally we use:
        delete_news_mcqs
    """

    return delete_news_mcqs(
        db=db,
        article_id=article_id,
    )


# ============================================================
# COUNT MCQS
# ============================================================

def count_news_mcqs(
    db: Session,
    article_id: int | None = None,
    exam: str | None = None,
    language: str | None = None,
) -> int:

    query = db.query(MCQ)

    # ARTICLE
    if article_id is not None:

        relation_column = (
            _article_relation_column()
        )

        if relation_column is not None:

            query = query.filter(
                relation_column == article_id
            )

    # EXAM
    if exam and hasattr(
        MCQ,
        "exam",
    ):

        query = query.filter(
            MCQ.exam
            == _normalize_exam(exam)
        )

    # LANGUAGE
    if language and hasattr(
        MCQ,
        "language",
    ):

        query = query.filter(
            MCQ.language
            == _normalize_language(language)
        )

    # ACTIVE
    if hasattr(
        MCQ,
        "is_active",
    ):

        query = query.filter(
            MCQ.is_active.is_(True)
        )

    return int(
        query.count()
    )

