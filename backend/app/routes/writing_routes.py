from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user

from app.models.writing import (
    WritingQuestion,
    AnswerSubmission,
    EssayQuestion,
    EssaySubmission,
)

from app.schemas.writing import (
    GenerateQuestionRequest,
    SubmitAnswerRequest,
    GenerateAnswerRequest,
    GenerateEssayRequest,
    SubmitEssayRequest,
)

from app.services.question_service import (
    generate_question,
)

from app.services.answer_writing_service import (
    evaluate_answer,
)

from app.services.writing_ai_service import (
    generate_model_answer,
    generate_essay,
    evaluate_essay_with_ai,
)

from app.services.writing_payment_service import (
    create_writing_order,
    verify_writing_payment,
    require_writing_subscription,
    require_writing_access,
    require_model_answer_access,
    get_subscription_status,
    get_writing_subscription,
    consume_writing_answer,
)


# ============================================================================
# LOGGER
# ============================================================================

logger = logging.getLogger("muni48.writing_routes")


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(
    prefix="/writing",
    tags=["Writing"],
)


# ============================================================================
# CONSTANTS
# ============================================================================

SUPPORTED_EXAMS = {
    "UPSC",
    "BPSC",
}

SUPPORTED_LANGUAGES = {
    "hi",
    "en",
}

SUPPORTED_QUESTION_TYPES = {
    "short",
    "long",
}

SUPPORTED_TARGET_WORDS = {
    150,
    250,
}

ESSAY_TARGET_WORDS = 1000


# ============================================================================
# PAYMENT REQUEST
# ============================================================================

class WritingPaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ============================================================================
# AUTH HELPER
# ============================================================================

def _require_authenticated_user(
    current_user: Any,
):
    """
    Require valid authenticated user.
    """

    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    if not getattr(current_user, "id", None):
        raise HTTPException(
            status_code=401,
            detail="Invalid authenticated user.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    return current_user


# ============================================================================
# NORMALIZERS
# ============================================================================

def _normalize_exam(
    exam: str | None,
) -> str:

    exam = (
        exam
        or "UPSC"
    ).strip().upper()

    if exam not in SUPPORTED_EXAMS:
        raise HTTPException(
            status_code=400,
            detail="exam must be either UPSC or BPSC",
        )

    return exam


def _normalize_language(
    language: str | None,
) -> str:

    language = (
        language
        or "hi"
    ).strip().lower()

    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail="language must be either 'hi' or 'en'",
        )

    return language


def _validate_question_type(
    question_type: str | None,
) -> str:

    question_type = (
        question_type
        or "short"
    ).strip().lower()

    if question_type not in SUPPORTED_QUESTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                "question_type must be either "
                "'short' or 'long'"
            ),
        )

    return question_type


# ============================================================================
# TARGET WORD HELPERS
# ============================================================================

def _get_question_target_words(
    question: WritingQuestion,
) -> int:

    try:
        value = int(
            question.target_words
        )
    except (
        TypeError,
        ValueError,
    ):
        value = 0

    if value in SUPPORTED_TARGET_WORDS:
        return value

    return (
        250
        if question.question_type == "long"
        else 150
    )


def _get_essay_target_words(
    essay: EssayQuestion,
) -> int:

    try:
        value = int(
            essay.target_words
        )
    except (
        TypeError,
        ValueError,
    ):
        value = 0

    return (
        value
        if value > 0
        else ESSAY_TARGET_WORDS
    )


# ============================================================================
# WRITING SUBSCRIPTION ACCESS
# ============================================================================

def _require_writing_subscription_access(
    db: Session,
    current_user: Any,
):
    """
    Require authenticated user + active paid Writing subscription.

    Used for:
        - question listing
        - model answer
        - essays
        - history
    """

    user = _require_authenticated_user(
        current_user
    )

    try:

        return require_writing_subscription(
            db=db,
            user_id=user.id,
        )

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Writing subscription check failed | user_id=%s",
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to verify Writing subscription.",
        ) from exc


# ============================================================================
# WRITING ACCESS + ANSWER QUOTA
# ============================================================================

def _require_writing_access(
    db: Session,
    current_user: Any,
):
    """
    Require:
        - authenticated user
        - active paid subscription
        - remaining answer quota

    Used only where an answer submission quota is required.
    """

    user = _require_authenticated_user(
        current_user
    )

    try:

        return require_writing_access(
            db=db,
            user_id=user.id,
        )

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Writing access check failed | user_id=%s",
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to verify Writing access.",
        ) from exc


# ============================================================================
# QUESTION GENERATION
# ============================================================================

@router.post(
    "/questions/generate"
)
def generate_writing_question(
    request: GenerateQuestionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Generate a new UPSC/BPSC answer-writing question.

    Requires active Writing subscription.

    Supported target words:
        150
        250
    """

    user = _require_authenticated_user(
        current_user
    )

    # ------------------------------------------------------------------------
    # SUBSCRIPTION CHECK
    # ------------------------------------------------------------------------

    _require_writing_subscription_access(
        db=db,
        current_user=user,
    )

    # ------------------------------------------------------------------------
    # NORMALIZE
    # ------------------------------------------------------------------------

    exam = _normalize_exam(
        request.exam
    )

    language = _normalize_language(
        request.language
    )

    question_type = _validate_question_type(
        request.question_type
    )

    # ------------------------------------------------------------------------
    # TARGET WORDS
    # ------------------------------------------------------------------------

    try:
        target_words = int(
            request.target_words
        )
    except (
        TypeError,
        ValueError,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "target_words must be either "
                "150 or 250"
            ),
        )

    if target_words not in SUPPORTED_TARGET_WORDS:
        raise HTTPException(
            status_code=400,
            detail=(
                "target_words must be either "
                "150 or 250"
            ),
        )

    # ------------------------------------------------------------------------
    # CATEGORY
    # ------------------------------------------------------------------------

    category = (
        request.category
        or "General"
    ).strip()

    if not category:
        category = "General"

    # ------------------------------------------------------------------------
    # GENERATE
    # ------------------------------------------------------------------------

    try:

        data = generate_question(
            exam=exam,
            category=category,
            question_type=question_type,
            language=language,
            target_words=target_words,
        )

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Question generation failed | "
            "user_id=%s | exam=%s | type=%s",
            user.id,
            exam,
            question_type,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Question generation failed: "
                f"{str(exc)}"
            ),
        ) from exc

    # ------------------------------------------------------------------------
    # VALIDATE AI RESULT
    # ------------------------------------------------------------------------

    if not isinstance(
        data,
        dict,
    ):
        raise HTTPException(
            status_code=502,
            detail=(
                "Question generator returned "
                "an invalid response."
            ),
        )

    question_text = str(
        data.get("question")
        or ""
    ).strip()

    if not question_text:

        raise HTTPException(
            status_code=502,
            detail="AI returned an empty question.",
        )

    # ------------------------------------------------------------------------
    # MARKS
    # ------------------------------------------------------------------------

    try:
        marks = int(
            data.get(
                "marks",
                10,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        marks = 10

    marks = max(
        1,
        min(
            100,
            marks,
        ),
    )

    # ------------------------------------------------------------------------
    # EXPECTED KEYWORDS
    # ------------------------------------------------------------------------

    expected_keywords = (
        data.get(
            "expected_keywords",
            [],
        )
        or []
    )

    if not isinstance(
        expected_keywords,
        list,
    ):
        expected_keywords = []

    # ------------------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------------------

    try:

        question = WritingQuestion(
            exam=exam,
            category=category,
            question_type=question_type,
            question=question_text,
            marks=marks,
            target_words=target_words,
            expected_keywords=expected_keywords,
            source="ai",
        )

        db.add(question)

        db.commit()

        db.refresh(question)

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Failed to save writing question | "
            "user_id=%s",
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Question could not be saved.",
        ) from exc

    # ------------------------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------------------------

    return {
        "status": "success",
        "question": {
            "id": question.id,
            "exam": question.exam,
            "category": question.category,
            "question_type": question.question_type,
            "question": question.question,
            "marks": question.marks,
            "target_words": _get_question_target_words(
                question
            ),
            "expected_keywords": (
                question.expected_keywords
                or []
            ),
        },
    }


# ============================================================================
# GET QUESTIONS
# ============================================================================

@router.get(
    "/questions"
)
def get_questions(
    exam: str = "UPSC",
    category: str | None = None,
    question_type: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get saved answer-writing questions.

    Requires active Writing subscription.
    """

    user = _require_authenticated_user(
        current_user
    )

    _require_writing_subscription_access(
        db=db,
        current_user=user,
    )

    exam = _normalize_exam(
        exam
    )

    query = (
        db.query(WritingQuestion)
        .filter(
            WritingQuestion.exam == exam,
            WritingQuestion.is_active == 1,
        )
    )

    # ------------------------------------------------------------------------
    # CATEGORY
    # ------------------------------------------------------------------------

    if category:

        category = category.strip()

        if category:
            query = query.filter(
                WritingQuestion.category == category
            )

    # ------------------------------------------------------------------------
    # QUESTION TYPE
    # ------------------------------------------------------------------------

    if question_type:

        question_type = _validate_question_type(
            question_type
        )

        query = query.filter(
            WritingQuestion.question_type
            == question_type
        )

    # ------------------------------------------------------------------------
    # FETCH
    # ------------------------------------------------------------------------

    questions = (
        query
        .order_by(
            WritingQuestion.id.desc()
        )
        .all()
    )

    # ------------------------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------------------------

    return {
        "status": "success",
        "total": len(
            questions
        ),
        "questions": [
            {
                "id": q.id,
                "exam": q.exam,
                "category": q.category,
                "question_type": q.question_type,
                "question": q.question,
                "marks": q.marks,
                "target_words": (
                    _get_question_target_words(q)
                ),
                "expected_keywords": (
                    q.expected_keywords
                    or []
                ),
            }
            for q in questions
        ],
    }


# ============================================================================
# GENERATE AI MODEL ANSWER
# ============================================================================

@router.post(
    "/questions/{question_id}/generate-answer"
)
def generate_answer(
    question_id: int,
    request: GenerateAnswerRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Generate AI model answer.

    Target words always come from database.

    Subscription required.
    Answer quota is NOT consumed.
    """

    user = _require_authenticated_user(
        current_user
    )

    _require_writing_subscription_access(
        db=db,
        current_user=user,
    )

    # ------------------------------------------------------------------------
    # QUESTION
    # ------------------------------------------------------------------------

    question = (
        db.query(WritingQuestion)
        .filter(
            WritingQuestion.id
            == question_id
        )
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

    # ------------------------------------------------------------------------
    # LANGUAGE
    # ------------------------------------------------------------------------

    language = _normalize_language(
        request.language
    )

    # ------------------------------------------------------------------------
    # TARGET WORDS
    # ------------------------------------------------------------------------

    target_words = _get_question_target_words(
        question
    )

    # ------------------------------------------------------------------------
    # AI
    # ------------------------------------------------------------------------

    try:

        result = generate_model_answer(
            exam=question.exam,
            category=(
                question.category
                or "General"
            ),
            question=question.question,
            marks=question.marks,
            target_words=target_words,
            language=language,
        )

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "AI answer generation failed | "
            "question_id=%s | user_id=%s",
            question_id,
            user.id,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "AI answer generation failed: "
                f"{str(exc)}"
            ),
        ) from exc

    if not isinstance(
        result,
        dict,
    ):
        raise HTTPException(
            status_code=502,
            detail=(
                "AI answer generator returned "
                "an invalid response."
            ),
        )

    # ------------------------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------------------------

    return {
        "status": "success",
        "question_id": question.id,
        "question": question.question,
        "exam": question.exam,
        "category": question.category,
        "marks": question.marks,
        "target_words": target_words,
        **result,
    }


# ============================================================================
# SUBMIT ANSWER
# ============================================================================

@router.post(
    "/questions/{question_id}/submit"
)
def submit_answer(
    question_id: int,
    request: SubmitAnswerRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Submit student's answer for evaluation.

    One answer quota is consumed only after
    successful evaluation + database save.
    """

    user = _require_authenticated_user(
        current_user
    )

    # ------------------------------------------------------------------------
    # CHECK QUOTA BEFORE EXPENSIVE AI CALL
    # ------------------------------------------------------------------------

    subscription = _require_writing_access(
        db=db,
        current_user=user,
    )

    # ------------------------------------------------------------------------
    # QUESTION
    # ------------------------------------------------------------------------

    question = (
        db.query(WritingQuestion)
        .filter(
            WritingQuestion.id
            == question_id
        )
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

    # ------------------------------------------------------------------------
    # ANSWER
    # ------------------------------------------------------------------------

    answer = (
        request.answer
        or ""
    ).strip()

    if not answer:
        raise HTTPException(
            status_code=400,
            detail="Answer cannot be empty",
        )

    # ------------------------------------------------------------------------
    # TARGET WORDS
    # ------------------------------------------------------------------------

    target_words = _get_question_target_words(
        question
    )

    # ------------------------------------------------------------------------
    # EVALUATE
    # ------------------------------------------------------------------------

    try:

        evaluation = evaluate_answer(
            answer=answer,
            exam=question.exam,
            question=question.question,
            question_type=question.question_type,
            category=question.category,
            expected_keywords=(
                question.expected_keywords
                or []
            ),
            target_words=target_words,
        )

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Answer evaluation failed | "
            "question_id=%s | user_id=%s",
            question_id,
            user.id,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Answer evaluation failed: "
                f"{str(exc)}"
            ),
        ) from exc

    if not isinstance(
        evaluation,
        dict,
    ):
        raise HTTPException(
            status_code=502,
            detail="Invalid answer evaluation response.",
        )

    # ------------------------------------------------------------------------
    # SAVE SUBMISSION
    # ------------------------------------------------------------------------

    try:

        submission = AnswerSubmission(
            user_id=user.id,
            question_id=question.id,
            answer=answer,
            score=evaluation.get(
                "score",
                0,
            ),
            max_score=evaluation.get(
                "max_score",
                question.marks or 10,
            ),
            percentage=evaluation.get(
                "percentage",
                0,
            ),
            word_count=evaluation.get(
                "word_count",
                len(answer.split()),
            ),
            evaluation=evaluation,
            evaluation_mode="basic",
        )

        db.add(submission)

        db.commit()

        db.refresh(submission)

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Failed to save answer submission | "
            "user_id=%s | question_id=%s",
            user.id,
            question_id,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Answer submission could not "
                "be saved."
            ),
        ) from exc

    # ------------------------------------------------------------------------
    # CONSUME ONE ANSWER
    #
    # IMPORTANT:
    # The submission is already successfully saved.
    # ------------------------------------------------------------------------

    try:

        updated_subscription = (
            consume_writing_answer(
                db=db,
                user_id=user.id,
            )
        )

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Failed to consume Writing answer quota | "
            "user_id=%s | submission_id=%s",
            user.id,
            submission.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to update answer quota.",
        ) from exc

    # ------------------------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------------------------

    remaining_answers = max(
        0,
        int(
            updated_subscription.answer_limit
            or 0
        )
        - int(
            updated_subscription.answers_used
            or 0
        ),
    )

    return {
        "status": "success",
        "submission_id": submission.id,
        "question_id": question.id,
        "target_words": target_words,
        "remaining_answers": remaining_answers,
        **evaluation,
    }


# ============================================================================
# GET ANSWER SUBMISSIONS
# ============================================================================

@router.get(
    "/questions/{question_id}/submissions"
)
def get_answer_submissions(
    question_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get current user's submissions for a question.
    """

    user = _require_authenticated_user(
        current_user
    )

    _require_writing_subscription_access(
        db=db,
        current_user=user,
    )

    question = (
        db.query(WritingQuestion)
        .filter(
            WritingQuestion.id
            == question_id
        )
        .first()
    )

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

    submissions = (
        db.query(AnswerSubmission)
        .filter(
            AnswerSubmission.question_id
            == question_id,
            AnswerSubmission.user_id
            == user.id,
        )
        .order_by(
            AnswerSubmission.id.desc()
        )
        .all()
    )

    return {
        "status": "success",
        "question": {
            "id": question.id,
            "exam": question.exam,
            "category": question.category,
            "question_type": question.question_type,
            "question": question.question,
            "marks": question.marks,
            "target_words": (
                _get_question_target_words(
                    question
                )
            ),
        },
        "total": len(
            submissions
        ),
        "submissions": [
            {
                "id": submission.id,
                "question_id": submission.question_id,
                "answer": submission.answer,
                "score": submission.score,
                "max_score": submission.max_score,
                "percentage": submission.percentage,
                "word_count": submission.word_count,
                "evaluation": submission.evaluation,
                "evaluation_mode": (
                    submission.evaluation_mode
                ),
            }
            for submission in submissions
        ],
    }


# ============================================================================
# ESSAY GENERATION
# ============================================================================

@router.post(
    "/essays/generate"
)
def generate_essay_endpoint(
    request: GenerateEssayRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Generate and save an AI essay.

    Target = 1000 words.
    """

    user = _require_authenticated_user(
        current_user
    )

    _require_writing_subscription_access(
        db=db,
        current_user=user,
    )

    # ------------------------------------------------------------------------
    # NORMALIZE
    # ------------------------------------------------------------------------

    exam = _normalize_exam(
        request.exam
    )

    language = _normalize_language(
        request.language
    )

    student_topic = (
        request.topic.strip()
        if request.topic
        and request.topic.strip()
        else None
    )

    target_words = ESSAY_TARGET_WORDS

    # ------------------------------------------------------------------------
    # AI
    # ------------------------------------------------------------------------

    try:

        result = generate_essay(
            exam=exam,
            topic=student_topic,
            target_words=target_words,
            language=language,
        )

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Essay generation failed | "
            "user_id=%s | exam=%s",
            user.id,
            exam,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Essay generation failed: "
                f"{str(exc)}"
            ),
        ) from exc

    if not isinstance(
        result,
        dict,
    ):
        raise HTTPException(
            status_code=502,
            detail=(
                "Essay generator returned "
                "an invalid response."
            ),
        )

    # ------------------------------------------------------------------------
    # TOPIC
    # ------------------------------------------------------------------------

    final_topic = str(
        result.get("topic")
        or student_topic
        or ""
    ).strip()

    if not final_topic:
        raise HTTPException(
            status_code=502,
            detail=(
                "Essay topic could not "
                "be generated."
            ),
        )

    # ------------------------------------------------------------------------
    # ESSAY
    # ------------------------------------------------------------------------

    essay_text = str(
        result.get("essay")
        or ""
    ).strip()

    if not essay_text:
        raise HTTPException(
            status_code=502,
            detail="AI returned an empty essay.",
        )

    # ------------------------------------------------------------------------
    # SOURCE
    # ------------------------------------------------------------------------

    topic_source = (
        result.get("topic_source")
        or (
            "student"
            if student_topic
            else "ai"
        )
    )

    if topic_source not in {
        "student",
        "ai",
    }:
        topic_source = (
            "student"
            if student_topic
            else "ai"
        )

    # ------------------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------------------

    try:

        essay_question = EssayQuestion(
            exam=exam,
            language=language,
            topic=final_topic,
            target_words=target_words,
            source=topic_source,
        )

        db.add(
            essay_question
        )

        db.commit()

        db.refresh(
            essay_question
        )

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Failed to save essay | "
            "user_id=%s",
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Essay could not be saved.",
        ) from exc

    # ------------------------------------------------------------------------
    # RESPONSE
    # ------------------------------------------------------------------------

    return {
        "status": "success",
        "essay_id": essay_question.id,
        "exam": exam,
        "language": language,
        "topic": final_topic,
        "topic_source": topic_source,
        "target_words": target_words,
        "essay": essay_text,
        "introduction": result.get(
            "introduction",
            "",
        ),
        "dimensions": result.get(
            "dimensions",
            [],
        ),
        "examples": result.get(
            "examples",
            [],
        ),
        "way_forward": result.get(
            "way_forward",
            "",
        ),
        "conclusion": result.get(
            "conclusion",
            "",
        ),
    }


# ============================================================================
# SUBMIT ESSAY
# ============================================================================

@router.post(
    "/essays/{essay_id}/submit"
)
def submit_essay(
    essay_id: int,
    request: SubmitEssayRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Submit student's essay for AI evaluation.
    """

    user = _require_authenticated_user(
        current_user
    )

    _require_writing_subscription_access(
        db=db,
        current_user=user,
    )

    # ------------------------------------------------------------------------
    # ESSAY
    # ------------------------------------------------------------------------

    essay = (
        db.query(EssayQuestion)
        .filter(
            EssayQuestion.id
            == essay_id
        )
        .first()
    )

    if not essay:
        raise HTTPException(
            status_code=404,
            detail="Essay topic not found",
        )

    # ------------------------------------------------------------------------
    # TEXT
    # ------------------------------------------------------------------------

    essay_text = (
        request.essay
        or ""
    ).strip()

    if not essay_text:
        raise HTTPException(
            status_code=400,
            detail="Essay cannot be empty",
        )

    # ------------------------------------------------------------------------
    # TARGET
    # ------------------------------------------------------------------------

    target_words = _get_essay_target_words(
        essay
    )

    word_count = len(
        essay_text.split()
    )

    # ------------------------------------------------------------------------
    # AI EVALUATION
    # ------------------------------------------------------------------------

    try:

        ai_evaluation = (
            evaluate_essay_with_ai(
                exam=essay.exam,
                topic=essay.topic,
                essay=essay_text,
                target_words=target_words,
                language=essay.language,
            )
        )

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "AI essay evaluation failed | "
            "essay_id=%s | user_id=%s",
            essay_id,
            user.id,
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "AI essay evaluation failed: "
                f"{str(exc)}"
            ),
        ) from exc

    if not isinstance(
        ai_evaluation,
        dict,
    ):
        raise HTTPException(
            status_code=502,
            detail=(
                "AI essay evaluator returned "
                "an invalid response."
            ),
        )

    # ------------------------------------------------------------------------
    # SCORE
    # ------------------------------------------------------------------------

    try:

        score = int(
            ai_evaluation.get(
                "score",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        score = 0

    score = max(
        0,
        min(
            100,
            score,
        ),
    )

    max_score = 100

    percentage = score

    # ------------------------------------------------------------------------
    # EVALUATION
    # ------------------------------------------------------------------------

    evaluation = {
        **ai_evaluation,
        "score": score,
        "max_score": max_score,
        "percentage": percentage,
        "word_count": word_count,
        "target_words": target_words,
        "feedback": ai_evaluation.get(
            "feedback",
            "Essay evaluated successfully by AI.",
        ),
    }

    # ------------------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------------------

    try:

        submission = EssaySubmission(
            user_id=user.id,
            essay_id=essay.id,
            essay=essay_text,
            score=score,
            max_score=max_score,
            percentage=percentage,
            word_count=word_count,
            evaluation=evaluation,
            evaluation_mode="ai",
        )

        db.add(
            submission
        )

        db.commit()

        db.refresh(
            submission
        )

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Failed to save essay submission | "
            "user_id=%s | essay_id=%s",
            user.id,
            essay_id,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Essay submission could not "
                "be saved."
            ),
        ) from exc

    return {
        "status": "success",
        "submission_id": submission.id,
        "essay_id": essay.id,
        "exam": essay.exam,
        "topic": essay.topic,
        "score": score,
        "max_score": max_score,
        "percentage": percentage,
        "word_count": word_count,
        "target_words": target_words,
        "evaluation_mode": "ai",
        "evaluation": evaluation,
    }


# ============================================================================
# GET ESSAY SUBMISSIONS
# ============================================================================

@router.get(
    "/essays/{essay_id}/submissions"
)
def get_essay_submissions(
    essay_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get current user's essay submissions.
    """

    user = _require_authenticated_user(
        current_user
    )

    _require_writing_subscription_access(
        db=db,
        current_user=user,
    )

    essay = (
        db.query(EssayQuestion)
        .filter(
            EssayQuestion.id
            == essay_id
        )
        .first()
    )

    if not essay:
        raise HTTPException(
            status_code=404,
            detail="Essay topic not found",
        )

    submissions = (
        db.query(EssaySubmission)
        .filter(
            EssaySubmission.essay_id
            == essay_id,
            EssaySubmission.user_id
            == user.id,
        )
        .order_by(
            EssaySubmission.id.desc()
        )
        .all()
    )

    return {
        "status": "success",
        "essay": {
            "id": essay.id,
            "exam": essay.exam,
            "language": essay.language,
            "topic": essay.topic,
            "target_words": (
                _get_essay_target_words(
                    essay
                )
            ),
        },
        "total": len(
            submissions
        ),
        "submissions": [
            {
                "id": submission.id,
                "essay_id": submission.essay_id,
                "essay": submission.essay,
                "score": submission.score,
                "max_score": submission.max_score,
                "percentage": submission.percentage,
                "word_count": submission.word_count,
                "evaluation": submission.evaluation,
                "evaluation_mode": (
                    submission.evaluation_mode
                ),
            }
            for submission in submissions
        ],
    }


# ============================================================================
# GET ESSAYS
# ============================================================================

@router.get(
    "/essays"
)
def get_essays(
    exam: str = "UPSC",
    language: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get saved essay topics.
    """

    user = _require_authenticated_user(
        current_user
    )

    _require_writing_subscription_access(
        db=db,
        current_user=user,
    )

    exam = _normalize_exam(
        exam
    )

    if language:
        language = _normalize_language(
            language
        )

    query = (
        db.query(EssayQuestion)
        .filter(
            EssayQuestion.exam == exam
        )
    )

    if language:
        query = query.filter(
            EssayQuestion.language
            == language
        )

    essays = (
        query
        .order_by(
            EssayQuestion.id.desc()
        )
        .all()
    )

    return {
        "status": "success",
        "exam": exam,
        "language": language,
        "total": len(
            essays
        ),
        "essays": [
            {
                "id": essay.id,
                "exam": essay.exam,
                "language": essay.language,
                "topic": essay.topic,
                "target_words": (
                    _get_essay_target_words(
                        essay
                    )
                ),
                "source": essay.source,
            }
            for essay in essays
        ],
    }


# ============================================================================
# PAYMENT SUBSCRIPTION STATUS
# ============================================================================

@router.get(
    "/payment/subscription"
)
def get_writing_subscription_endpoint(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get current user's Writing subscription.
    """

    user = _require_authenticated_user(
        current_user
    )

    try:

        result = get_writing_subscription(
            db=db,
            user_id=user.id,
        )

        return {
            "status": "success",
            "subscription": result,
        }

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Failed to get Writing subscription | "
            "user_id=%s",
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to get Writing subscription."
            ),
        ) from exc


# ============================================================================
# CREATE PAYMENT ORDER
# ============================================================================

@router.post(
    "/payment/create-order"
)
def create_writing_payment_order(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create ₹39 Razorpay order.
    """

    user = _require_authenticated_user(
        current_user
    )

    try:

        return create_writing_order(
            db=db,
            user_id=user.id,
        )

    except HTTPException:
        raise

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Writing payment order creation failed | "
            "user_id=%s",
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Payment order creation failed."
            ),
        ) from exc


# ============================================================================
# VERIFY PAYMENT
# ============================================================================

@router.post(
    "/payment/verify"
)
def verify_writing_payment_endpoint(
    request: WritingPaymentVerifyRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Verify Razorpay payment and activate subscription.
    """

    user = _require_authenticated_user(
        current_user
    )

    # ------------------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------------------

    if not request.razorpay_order_id.strip():
        raise HTTPException(
            status_code=400,
            detail="razorpay_order_id is required.",
        )

    if not request.razorpay_payment_id.strip():
        raise HTTPException(
            status_code=400,
            detail="razorpay_payment_id is required.",
        )

    if not request.razorpay_signature.strip():
        raise HTTPException(
            status_code=400,
            detail="razorpay_signature is required.",
        )

    # ------------------------------------------------------------------------
    # VERIFY
    # ------------------------------------------------------------------------

    try:

        return verify_writing_payment(
            db=db,
            user_id=user.id,
            razorpay_order_id=(
                request.razorpay_order_id
            ),
            razorpay_payment_id=(
                request.razorpay_payment_id
            ),
            razorpay_signature=(
                request.razorpay_signature
            ),
        )

    except HTTPException:
        raise

    except Exception as exc:

        db.rollback()

        logger.exception(
            "Writing payment verification failed | "
            "user_id=%s",
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail="Payment verification failed.",
        ) from exc


# ============================================================================
# SUBSCRIPTION STATUS
# ============================================================================

@router.get(
    "/subscription/status"
)
def writing_subscription_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Frontend-friendly Writing subscription status.

    IMPORTANT:
    This endpoint does NOT require an active subscription.

    It is intentionally accessible to authenticated users
    so the frontend can determine whether to show:

        Buy ₹39 Plan

    or

        Generate Question
    """

    user = _require_authenticated_user(
        current_user
    )

    try:

        status = get_subscription_status(
            db=db,
            user_id=user.id,
        )

        return {
            "status": "success",
            "subscription": status,
        }

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Writing subscription status failed | "
            "user_id=%s",
            user.id,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to get Writing subscription status."
            ),
        ) from exc