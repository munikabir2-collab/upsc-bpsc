from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.current_affair import CurrentAffair
from app.models.mcq import MCQ


logger = logging.getLogger("app.news_mcq_service")


# ============================================================
# HELPERS
# ============================================================

def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default

    try:
        return str(value).strip()
    except Exception:
        return default


def _normalize_answer(value: Any) -> str:
    value = _clean(value, "A").upper()

    value = value.replace("OPTION ", "")
    value = value.replace("ANSWER ", "")
    value = value.replace("CORRECT ANSWER:", "")
    value = value.replace("CORRECT ANSWER", "")

    if value in {"A", "B", "C", "D"}:
        return value

    # Examples:
    # "A)"
    # "(A)"
    # "Option A"
    # "The correct answer is A"
    match = re.search(r"\b([ABCD])\b", value)

    if match:
        return match.group(1)

    match = re.search(r"[\(\[]?([ABCD])[\)\]]?", value)

    if match:
        return match.group(1)

    return "A"


def _normalize_language(value: Any) -> str:
    value = _clean(value, "en").lower()

    aliases = {
        "hindi": "hi",
        "हिंदी": "hi",
        "english": "en",
        "अंग्रेजी": "en",
        "eng": "en",
        "hin": "hi",
    }

    return aliases.get(value, value)


def _normalize_exam(value: Any) -> str:
    value = _clean(value, "UPSC").upper()

    if value not in {"UPSC", "BPSC"}:
        return "UPSC"

    return value


def _normalize_difficulty(value: Any) -> str:
    value = _clean(value, "Medium").capitalize()

    allowed = {
        "Easy": "Easy",
        "Medium": "Medium",
        "Hard": "Hard",
    }

    return allowed.get(value, "Medium")


def _normalize_question_type(value: Any) -> str:
    value = _clean(
        value,
        "single_correct",
    ).lower()

    aliases = {
        "mcq": "single_correct",
        "single": "single_correct",
        "single_correct": "single_correct",
        "single-correct": "single_correct",
        "multiple": "multiple_correct",
        "multiple_correct": "multiple_correct",
        "multiple-correct": "multiple_correct",
    }

    return aliases.get(
        value,
        "single_correct",
    )


# ============================================================
# OPTION EXTRACTION
# ============================================================

def _extract_options(
    item: dict[str, Any],
) -> tuple[str, str, str, str]:

    option_a = _clean(item.get("option_a"))
    option_b = _clean(item.get("option_b"))
    option_c = _clean(item.get("option_c"))
    option_d = _clean(item.get("option_d"))

    options = item.get("options")

    # --------------------------------------------------------
    # FORMAT:
    #
    # options = [
    #   {"key": "A", "text": "..."},
    #   ...
    # ]
    # --------------------------------------------------------

    if isinstance(options, list):

        for option in options:

            if not isinstance(option, dict):
                continue

            key = _clean(
                option.get("key")
                or option.get("label")
            ).upper()

            text = _clean(
                option.get("text")
                or option.get("value")
                or option.get("option")
            )

            if not text:
                continue

            if key == "A" and not option_a:
                option_a = text

            elif key == "B" and not option_b:
                option_b = text

            elif key == "C" and not option_c:
                option_c = text

            elif key == "D" and not option_d:
                option_d = text

    # --------------------------------------------------------
    # FORMAT:
    #
    # options = {
    #   "A": "...",
    #   "B": "...",
    #   ...
    # }
    # --------------------------------------------------------

    elif isinstance(options, dict):

        option_a = option_a or _clean(
            options.get("A")
            or options.get("a")
        )

        option_b = option_b or _clean(
            options.get("B")
            or options.get("b")
        )

        option_c = option_c or _clean(
            options.get("C")
            or options.get("c")
        )

        option_d = option_d or _clean(
            options.get("D")
            or options.get("d")
        )

    return (
        option_a,
        option_b,
        option_c,
        option_d,
    )


# ============================================================
# AI ITEM NORMALIZATION
# ============================================================

def _normalize_ai_item(
    item: dict[str, Any],
    article: CurrentAffair,
    exam: str,
    language: str,
    difficulty: str,
    question_type: str,
) -> dict[str, Any] | None:

    if not isinstance(item, dict):
        return None

    # --------------------------------------------------------
    # QUESTION
    # --------------------------------------------------------

    question = _clean(
        item.get("question")
        or item.get("question_text")
        or item.get("text")
    )

    if not question:
        logger.warning(
            "Skipping AI MCQ without question: %s",
            item,
        )
        return None

    # --------------------------------------------------------
    # OPTIONS
    # --------------------------------------------------------

    (
        option_a,
        option_b,
        option_c,
        option_d,
    ) = _extract_options(item)

    if not all(
        [
            option_a,
            option_b,
            option_c,
            option_d,
        ]
    ):
        logger.warning(
            "Skipping MCQ because options are incomplete: %s",
            question,
        )
        return None

    # --------------------------------------------------------
    # ANSWER
    # --------------------------------------------------------

    correct_answer = _normalize_answer(
        item.get("correct_answer")
        or item.get("answer")
        or item.get("correct")
        or item.get("correct_option")
    )

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    category = (
        _clean(item.get("category"))
        or _clean(
            getattr(article, "category", None),
            "General",
        )
        or "General"
    )

    # --------------------------------------------------------
    # STATE
    # --------------------------------------------------------

    state = (
        _clean(item.get("state"))
        or None
    )

    # --------------------------------------------------------
    # TOPIC
    # --------------------------------------------------------

    topic = (
        _clean(item.get("topic"))
        or None
    )

    # --------------------------------------------------------
    # EXPLANATION
    # --------------------------------------------------------

    explanation = (
        _clean(
            item.get("explanation")
            or item.get("reason")
            or item.get("solution")
        )
        or None
    )

    return {
        "question": question,
        "option_a": option_a,
        "option_b": option_b,
        "option_c": option_c,
        "option_d": option_d,
        "correct_answer": correct_answer,
        "explanation": explanation,
        "exam": exam,
        "state": state,
        "language": language,
        "category": category,
        "topic": topic,
        "difficulty": difficulty,
        "question_type": question_type,
    }


# ============================================================
# ORM → API
# ============================================================

def mcq_to_dict(
    mcq: MCQ,
) -> dict[str, Any]:

    options = [
        {
            "key": "A",
            "text": _clean(
                mcq.option_a
            ),
        },
        {
            "key": "B",
            "text": _clean(
                mcq.option_b
            ),
        },
        {
            "key": "C",
            "text": _clean(
                mcq.option_c
            ),
        },
        {
            "key": "D",
            "text": _clean(
                mcq.option_d
            ),
        },
    ]

    return {
        "id": mcq.id,

        "current_affair_id": (
            mcq.current_affair_id
        ),

        "question": _clean(
            mcq.question
        ),

        "options": options,

        "correct_answer": _normalize_answer(
            mcq.correct_answer
        ),

        "explanation": (
            _clean(mcq.explanation)
            or None
        ),

        "difficulty": _normalize_difficulty(
            mcq.difficulty
        ),

        "exam": _normalize_exam(
            mcq.exam
        ),

        "category": (
            _clean(
                mcq.category,
                "General",
            )
            or "General"
        ),

        "language": _normalize_language(
            mcq.language
        ),

        "question_type": _normalize_question_type(
            mcq.question_type
        ),

        "state": (
            _clean(
                getattr(mcq, "state", None)
            )
            or None
        ),

        "topic": (
            _clean(
                getattr(mcq, "topic", None)
            )
            or None
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
    }


# ============================================================
# LIST CONVERTER
# ============================================================

def mcqs_to_dict(
    questions: list[MCQ],
) -> list[dict[str, Any]]:

    return [
        mcq_to_dict(question)
        for question in questions
    ]


# ============================================================
# GENERATE MCQS
# ============================================================

def generate_mcqs(
    db: Session,
    article: CurrentAffair,
    exam: str,
    language: str,
    count: int,
    difficulty: str,
    question_type: str,
) -> list[MCQ]:

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

    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 5

    # --------------------------------------------------------
    # SAFE LIMIT
    # --------------------------------------------------------

    count = max(
        1,
        min(count, 20),
    )

    # --------------------------------------------------------
    # ARTICLE VALIDATION
    # --------------------------------------------------------

    if article is None:
        raise ValueError(
            "Current affair article not found."
        )

    if not getattr(article, "id", None):
        raise ValueError(
            "Current affair article must be saved before generating MCQs."
        )

    logger.info(
        "Generating MCQs | article_id=%s | exam=%s | language=%s | "
        "count=%s | difficulty=%s | question_type=%s",
        article.id,
        exam,
        language,
        count,
        difficulty,
        question_type,
    )

    # --------------------------------------------------------
    # AI GENERATION
    # --------------------------------------------------------

    generated_data = _call_ai_generator(
        article=article,
        exam=exam,
        language=language,
        count=count,
        difficulty=difficulty,
        question_type=question_type,
    )

    if not generated_data:
        raise ValueError(
            "AI could not generate MCQs. "
            "Check GROQ_API_KEY and news_ai_service.py."
        )

    if not isinstance(
        generated_data,
        list,
    ):
        generated_data = [
            generated_data
        ]

    questions: list[MCQ] = []

    # --------------------------------------------------------
    # CONVERT AI → ORM
    # --------------------------------------------------------

    for item in generated_data:

        if len(questions) >= count:
            break

        normalized = _normalize_ai_item(
            item=item,
            article=article,
            exam=exam,
            language=language,
            difficulty=difficulty,
            question_type=question_type,
        )

        if not normalized:
            continue

        # ----------------------------------------------------
        # CREATE ORM
        # ----------------------------------------------------

        mcq = MCQ(
            current_affair_id=article.id,

            question=normalized[
                "question"
            ],

            option_a=normalized[
                "option_a"
            ],

            option_b=normalized[
                "option_b"
            ],

            option_c=normalized[
                "option_c"
            ],

            option_d=normalized[
                "option_d"
            ],

            correct_answer=normalized[
                "correct_answer"
            ],

            explanation=normalized[
                "explanation"
            ],

            exam=exam,

            state=normalized[
                "state"
            ],

            language=language,

            category=normalized[
                "category"
            ],

            topic=normalized[
                "topic"
            ],

            difficulty=difficulty,

            question_type=question_type,

            is_verified=False,

            is_active=True,
        )

        db.add(mcq)

        questions.append(mcq)

    # --------------------------------------------------------
    # NOTHING VALID GENERATED
    # --------------------------------------------------------

    if not questions:
        raise ValueError(
            "AI returned MCQs, but none passed validation. "
            "Check the AI response format."
        )

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    try:

        db.flush()

        logger.info(
            "Generated %s MCQs successfully for article %s",
            len(questions),
            article.id,
        )

    except Exception as exc:

        logger.exception(
            "Database error while saving MCQs: %s",
            exc,
        )

        db.rollback()

        raise ValueError(
            "MCQs were generated but could not be saved to the database."
        ) from exc

    return questions


# ============================================================
# AI GENERATOR ADAPTER
# ============================================================

def _call_ai_generator(
    article: CurrentAffair,
    exam: str,
    language: str,
    count: int,
    difficulty: str,
    question_type: str,
) -> list[dict[str, Any]]:

    try:

        from app.services.news_ai_service import (
            generate_news_mcqs,
        )

    except ImportError as exc:

        logger.exception(
            "Could not import generate_news_mcqs."
        )

        raise ValueError(
            "News AI service is not available."
        ) from exc

    try:

        result = generate_news_mcqs(
            article=article,
            exam=exam,
            language=language,
            count=count,
            difficulty=difficulty,
            question_type=question_type,
        )

    except Exception as exc:

        logger.exception(
            "news_ai_service.generate_news_mcqs failed."
        )

        raise ValueError(
            f"AI MCQ generation failed: {str(exc)}"
        ) from exc

    logger.info(
        "AI MCQ raw result type: %s",
        type(result).__name__,
    )

    # --------------------------------------------------------
    # LIST
    # --------------------------------------------------------

    if isinstance(result, list):

        logger.info(
            "AI returned %s MCQs",
            len(result),
        )

        return result

    # --------------------------------------------------------
    # DICT
    # --------------------------------------------------------

    if isinstance(result, dict):

        questions = result.get(
            "questions"
        )

        if isinstance(
            questions,
            list,
        ):

            logger.info(
                "AI returned %s MCQs inside questions[]",
                len(questions),
            )

            return questions

        # Single MCQ object
        if result.get("question"):

            return [result]

        # Some APIs return:
        # {"data": [...]}

        data = result.get("data")

        if isinstance(
            data,
            list,
        ):
            return data

        if isinstance(
            data,
            dict,
        ):

            nested_questions = data.get(
                "questions"
            )

            if isinstance(
                nested_questions,
                list,
            ):
                return nested_questions

    # --------------------------------------------------------
    # STRING
    # --------------------------------------------------------

    if isinstance(result, str):

        logger.error(
            "AI returned raw string instead of JSON: %s",
            result[:1000],
        )

        raise ValueError(
            "AI returned invalid MCQ JSON."
        )

    logger.error(
        "Unsupported AI MCQ response: %r",
        result,
    )

    raise ValueError(
        "AI returned an unsupported MCQ response format."
    )