
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# ============================================================
# CONSTANTS
# ============================================================

DEFAULT_MAX_WORDS = {
    "UPSC": {
        "short": 150,
        "long": 250,
    },
    "BPSC": {
        "short": 150,
        "long": 250,
    },
}


EXAM_MARKS = {
    "UPSC": {
        "short": 10,
        "long": 15,
    },
    "BPSC": {
        "short": 10,
        "long": 15,
    },
}


# AI evaluation is always out of 100
AI_EVALUATION_MAX_SCORE = 100


# ============================================================
# AI RUBRIC
# ============================================================

AI_RUBRIC_LIMITS = {
    "content_score": 20,
    "relevance_score": 20,
    "structure_score": 15,
    "analysis_score": 20,
    "examples_score": 10,
    "presentation_score": 15,
}


# ============================================================
# TEXT UTILITIES
# ============================================================

def normalize_text(value: Any) -> str:
    """
    Normalize user/question text for analysis.
    """

    if value is None:
        return ""

    text = str(value)

    # Normalize Windows / Unix line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Preserve paragraph boundaries while cleaning spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def count_words(text: str) -> int:
    """
    Count words/tokens for normal English, Hindi and Hinglish text.
    """

    text = normalize_text(text)

    if not text:
        return 0

    return len(re.findall(r"\S+", text))


def calculate_word_percentage(
    word_count: int,
    target_words: int,
) -> float:

    if target_words <= 0:
        return 0.0

    return round(
        (word_count / target_words) * 100,
        2,
    )


# ============================================================
# QUESTION TYPE
# ============================================================

def get_target_words(
    exam: str,
    question_type: str = "short",
) -> int:

    exam = normalize_text(exam).upper()
    question_type = normalize_text(question_type).lower()

    return DEFAULT_MAX_WORDS.get(
        exam,
        DEFAULT_MAX_WORDS["UPSC"],
    ).get(
        question_type,
        DEFAULT_MAX_WORDS["UPSC"]["short"],
    )


def get_max_marks(
    exam: str,
    question_type: str = "short",
) -> int:

    exam = normalize_text(exam).upper()
    question_type = normalize_text(question_type).lower()

    return EXAM_MARKS.get(
        exam,
        EXAM_MARKS["UPSC"],
    ).get(
        question_type,
        EXAM_MARKS["UPSC"]["short"],
    )


# ============================================================
# ANSWER STRUCTURE ANALYSIS
# ============================================================

def detect_introduction(text: str) -> bool:
    """
    Basic heuristic introduction detection.
    """

    text = normalize_text(text)

    if not text:
        return False

    paragraphs = [
        p.strip()
        for p in re.split(r"\n+", text)
        if p.strip()
    ]

    if len(paragraphs) >= 2:
        return True

    first_part = text[:300].lower()

    intro_keywords = [
        "भारत",
        "बिहार",
        "वर्तमान",
        "आज",
        "इस संदर्भ में",
        "परिप्रेक्ष्य",
        "introduction",
        "in recent years",
        "भारत में",
        "बिहार में",
    ]

    return any(
        keyword.lower() in first_part
        for keyword in intro_keywords
    )


def detect_conclusion(text: str) -> bool:
    """
    Basic conclusion detection.
    """

    text = normalize_text(text)

    if not text:
        return False

    conclusion_keywords = [
        "निष्कर्ष",
        "अतः",
        "इस प्रकार",
        "अंततः",
        "इस दिशा में",
        "समग्र रूप से",
        "निष्कर्षतः",
        "conclusion",
        "therefore",
        "thus",
        "overall",
        "way forward",
    ]

    last_part = text[-500:].lower()

    return any(
        keyword.lower() in last_part
        for keyword in conclusion_keywords
    )


def detect_bullets_or_points(text: str) -> bool:

    text = normalize_text(text)

    if not text:
        return False

    patterns = [
        r"(^|\n)\s*[-•*]\s+",
        r"(^|\n)\s*\d+[.)]\s+",
        r"(^|\n)\s*[a-zA-Z][.)]\s+",
    ]

    return any(
        re.search(pattern, text)
        for pattern in patterns
    )


def detect_paragraphs(text: str) -> int:

    text = normalize_text(text)

    if not text:
        return 0

    return len(
        [
            p
            for p in re.split(r"\n+", text)
            if p.strip()
        ]
    )


# ============================================================
# CONTENT SIGNALS
# ============================================================

def detect_keywords(
    answer: str,
    keywords: Optional[List[str]] = None,
) -> List[str]:

    if not keywords:
        return []

    text = normalize_text(answer).lower()

    found: List[str] = []

    for keyword in keywords:

        keyword = normalize_text(keyword)

        if not keyword:
            continue

        if keyword.lower() in text:
            found.append(keyword)

    return found


def calculate_content_coverage(
    answer: str,
    expected_keywords: Optional[List[str]] = None,
) -> float:

    if not expected_keywords:
        return 0.0

    found = detect_keywords(
        answer,
        expected_keywords,
    )

    return round(
        (len(found) / len(expected_keywords)) * 100,
        2,
    )


# ============================================================
# BASIC QUALITY SCORE
# ============================================================

def calculate_structure_score(
    answer: str,
) -> int:

    score = 0

    if detect_introduction(answer):
        score += 3

    if detect_conclusion(answer):
        score += 3

    if detect_bullets_or_points(answer):
        score += 2

    if detect_paragraphs(answer) >= 2:
        score += 2

    return min(score, 10)


def calculate_word_score(
    word_count: int,
    target_words: int,
) -> int:

    if word_count <= 0:
        return 0

    percentage = calculate_word_percentage(
        word_count,
        target_words,
    )

    if 80 <= percentage <= 120:
        return 10

    if 65 <= percentage < 80:
        return 8

    if 50 <= percentage < 65:
        return 6

    if 35 <= percentage < 50:
        return 4

    return 2


# ============================================================
# FEEDBACK GENERATOR
# ============================================================

def generate_basic_feedback(
    answer: str,
    word_count: int,
    target_words: int,
    structure_score: int,
    expected_keywords: Optional[List[str]] = None,
) -> List[str]:

    feedback: List[str] = []

    if word_count == 0:
        return [
            "उत्तर खाली है। पहले अपना उत्तर लिखें।"
        ]

    # --------------------------------------------------------
    # Word count
    # --------------------------------------------------------

    if word_count < target_words * 0.6:

        feedback.append(
            f"उत्तर काफी छोटा है। लगभग {target_words} शब्दों "
            "के आसपास उत्तर लिखने का प्रयास करें।"
        )

    elif word_count > target_words * 1.25:

        feedback.append(
            f"उत्तर निर्धारित सीमा से काफी लंबा है। "
            f"लगभग {target_words} शब्दों में उत्तर को अधिक "
            "संक्षिप्त और प्रभावी रखें।"
        )

    else:

        feedback.append(
            "उत्तर की शब्द-सीमा सामान्यतः उचित है।"
        )

    # --------------------------------------------------------
    # Introduction
    # --------------------------------------------------------

    if not detect_introduction(answer):

        feedback.append(
            "उत्तर की शुरुआत में विषय की स्पष्ट भूमिका "
            "या संदर्भ जोड़ें।"
        )

    else:

        feedback.append(
            "भूमिका/Introduction का प्रयास अच्छा है।"
        )

    # --------------------------------------------------------
    # Conclusion
    # --------------------------------------------------------

    if not detect_conclusion(answer):

        feedback.append(
            "अंत में स्पष्ट निष्कर्ष या Way Forward जोड़ें।"
        )

    else:

        feedback.append(
            "निष्कर्ष/Way Forward शामिल किया गया है।"
        )

    # --------------------------------------------------------
    # Structure
    # --------------------------------------------------------

    if not detect_bullets_or_points(answer):

        feedback.append(
            "जहाँ उपयुक्त हो, मुख्य बिंदुओं को "
            "headings/bullets में प्रस्तुत करें।"
        )

    # --------------------------------------------------------
    # Keywords
    # --------------------------------------------------------

    if expected_keywords:

        found = detect_keywords(
            answer,
            expected_keywords,
        )

        if not found:

            feedback.append(
                "प्रश्न से संबंधित प्रमुख अवधारणाओं/keywords "
                "को उत्तर में शामिल करें।"
            )

        elif len(found) < len(expected_keywords) / 2:

            feedback.append(
                "कुछ महत्वपूर्ण keywords शामिल हैं, लेकिन "
                "content coverage और बढ़ाया जा सकता है।"
            )

        else:

            feedback.append(
                "प्रमुख विषयगत keywords का अच्छा उपयोग किया गया है।"
            )

    return feedback


# ============================================================
# BASIC SCORE CALCULATION
# ============================================================

def calculate_answer_score(
    answer: str,
    exam: str,
    question_type: str = "short",
    expected_keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:

    answer = normalize_text(answer)
    exam = normalize_text(exam).upper()

    target_words = get_target_words(
        exam,
        question_type,
    )

    max_marks = get_max_marks(
        exam,
        question_type,
    )

    word_count = count_words(answer)

    structure_score = calculate_structure_score(
        answer
    )

    word_score = calculate_word_score(
        word_count,
        target_words,
    )

    keyword_coverage = calculate_content_coverage(
        answer,
        expected_keywords,
    )

    # --------------------------------------------------------
    # Content score
    # --------------------------------------------------------

    if expected_keywords:

        content_score = round(
            (keyword_coverage / 100) * 10
        )

    else:

        content_score = 5 if word_count > 0 else 0

    # --------------------------------------------------------
    # Basic score
    # --------------------------------------------------------

    raw_score = (
        (structure_score * 0.30)
        + (word_score * 0.20)
        + (content_score * 0.50)
    )

    score = round(
        (raw_score / 10) * max_marks
    )

    score = max(
        0,
        min(score, max_marks),
    )

    return {
        "score": score,
        "max_score": max_marks,
        "word_count": word_count,
        "target_words": target_words,
        "word_percentage": calculate_word_percentage(
            word_count,
            target_words,
        ),
        "structure_score": structure_score,
        "content_score": content_score,
        "keyword_coverage": keyword_coverage,
    }


# ============================================================
# COMPLETE BASIC EVALUATION
# ============================================================

def evaluate_answer(
    answer: str,
    exam: str,
    question: str,
    question_type: str = "short",
    category: Optional[str] = None,
    expected_keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:

    answer = normalize_text(answer)
    question = normalize_text(question)
    exam = normalize_text(exam).upper()
    category = normalize_text(category)

    score_data = calculate_answer_score(
        answer=answer,
        exam=exam,
        question_type=question_type,
        expected_keywords=expected_keywords,
    )

    feedback = generate_basic_feedback(
        answer=answer,
        word_count=score_data["word_count"],
        target_words=score_data["target_words"],
        structure_score=score_data["structure_score"],
        expected_keywords=expected_keywords,
    )

    score = score_data["score"]
    max_score = score_data["max_score"]

    percentage = (
        (score / max_score) * 100
        if max_score > 0
        else 0
    )

    if percentage >= 80:
        rating = "Excellent"

    elif percentage >= 65:
        rating = "Good"

    elif percentage >= 50:
        rating = "Average"

    elif percentage >= 35:
        rating = "Needs Improvement"

    else:
        rating = "Poor"

    return {
        "exam": exam,
        "category": category or None,
        "question": question,
        "answer": answer,

        # Basic/exam score
        "score": score,
        "max_score": max_score,
        "percentage": round(
            percentage,
            2,
        ),

        "rating": rating,

        **score_data,

        "introduction_present": detect_introduction(
            answer
        ),

        "conclusion_present": detect_conclusion(
            answer
        ),

        "points_format_present": detect_bullets_or_points(
            answer
        ),

        "paragraph_count": detect_paragraphs(
            answer
        ),

        "feedback": feedback,

        "evaluation_mode": "basic",
    }


# ============================================================
# AI EVALUATION RESULT MERGER
# ============================================================

def merge_ai_evaluation(
    basic_result: Dict[str, Any],
    ai_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge AI evaluation with deterministic analysis.

    IMPORTANT:

    AI score is always maintained out of 100.

    Exam marks are maintained separately.

    Example:

        AI score     = 72 / 100
        UPSC marks   = 7.2 / 10

    The primary `score` returned to the frontend is
    the AI score out of 100.
    """

    result = dict(basic_result)

    if not ai_result:
        return result

    # ========================================================
    # AI RUBRIC SCORES
    # ========================================================

    ai_scores: Dict[str, int] = {}

    for field, maximum in AI_RUBRIC_LIMITS.items():

        try:
            value = int(ai_result.get(field, 0))
        except (TypeError, ValueError):
            value = 0

        value = max(
            0,
            min(value, maximum),
        )

        ai_scores[field] = value

    # ========================================================
    # AI TOTAL = 100
    # ========================================================

    rubric_total = sum(
        ai_scores.values()
    )

    rubric_total = max(
        0,
        min(
            rubric_total,
            AI_EVALUATION_MAX_SCORE,
        ),
    )

    # ========================================================
    # ACTUAL EXAM MARKS
    # ========================================================

    try:

        exam_max_score = int(
            result.get(
                "max_score",
                ai_result.get(
                    "max_score",
                    10,
                ),
            )
        )

    except (TypeError, ValueError):

        exam_max_score = 10

    exam_max_score = max(
        1,
        exam_max_score,
    )

    # ========================================================
    # CONVERT AI SCORE TO EXAM MARKS
    # ========================================================

    exam_score = round(
        (rubric_total / 100)
        * exam_max_score,
        2,
    )

    exam_score = max(
        0,
        min(
            exam_score,
            exam_max_score,
        ),
    )

    # ========================================================
    # PRIMARY FRONTEND SCORE
    # ========================================================

    # IMPORTANT:
    #
    # Do NOT replace score with 4/10.
    #
    # Frontend evaluation should display:
    #
    # 40 / 100
    #
    # not:
    #
    # 4 / 100
    #

    result["score"] = rubric_total
    result["max_score"] = 100
    result["percentage"] = float(rubric_total)

    # ========================================================
    # EXAM SCORE
    # ========================================================

    result["exam_score"] = exam_score
    result["exam_max_score"] = exam_max_score

    result["exam_percentage"] = round(
        (
            exam_score
            / exam_max_score
        ) * 100,
        2,
    )

    # ========================================================
    # PRESERVE AI RUBRIC SCORES
    # ========================================================

    for field, value in ai_scores.items():
        result[field] = value

    # ========================================================
    # AI FEEDBACK
    # ========================================================

    allowed_feedback_fields = {
        "strengths",
        "weaknesses",
        "missing_points",
        "improvement_tips",
        "model_improvement",
        "feedback",
    }

    for field in allowed_feedback_fields:

        if (
            field in ai_result
            and ai_result[field] is not None
        ):

            result[field] = ai_result[field]

    # ========================================================
    # AI RATING
    # ========================================================

    if rubric_total >= 80:

        rating = "Excellent"

    elif rubric_total >= 65:

        rating = "Good"

    elif rubric_total >= 50:

        rating = "Average"

    elif rubric_total >= 35:

        rating = "Needs Improvement"

    else:

        rating = "Poor"

    result["rating"] = rating

    # ========================================================
    # EVALUATION METADATA
    # ========================================================

    result["evaluation_mode"] = "ai"

    result["ai_score"] = rubric_total
    result["ai_max_score"] = 100
    result["ai_percentage"] = float(rubric_total)

    return result


# ============================================================
# ANSWER SUBMISSION BUILDER
# ============================================================

def build_submission_result(
    *,
    user_id: int,
    question_id: int,
    answer: str,
    exam: str,
    question: str,
    question_type: str = "short",
    category: Optional[str] = None,
    expected_keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:

    evaluation = evaluate_answer(
        answer=answer,
        exam=exam,
        question=question,
        question_type=question_type,
        category=category,
        expected_keywords=expected_keywords,
    )

    return {
        "user_id": user_id,
        "question_id": question_id,
        "exam": normalize_text(exam).upper(),
        "category": normalize_text(category),
        "answer": normalize_text(answer),
        "question": normalize_text(question),
        "question_type": normalize_text(
            question_type
        ).lower(),
        "evaluation": evaluation,
    }


# ============================================================
# AI EVALUATION PROMPT
# ============================================================

def build_ai_evaluation_prompt(
    *,
    exam: str,
    question: str,
    answer: str,
    max_marks: int,
    target_words: int,
    category: Optional[str] = None,
) -> str:

    exam = normalize_text(exam).upper()

    category_text = (
        normalize_text(category)
        if category
        else "General"
    )

    return f"""
You are an expert evaluator for {exam} Mains examination.

Evaluate the candidate's answer strictly according to
Indian competitive examination standards.

Do not be generous merely because the answer is long.

============================================================
EXAM DETAILS
============================================================

Exam:
{exam}

Category:
{category_text}

Question:
{question}

Maximum Examination Marks:
{max_marks}

Expected Answer Length:
Approximately {target_words} words

Candidate Answer:
{answer}

============================================================
STRICT SCORING RUBRIC
============================================================

Evaluate exactly these six dimensions.

1. content_score

Maximum: 20

Evaluate:

- Accuracy and quality of content
- Substance and factual understanding
- Knowledge of the subject
- Coverage of important dimensions
- Whether the content actually answers the question

2. relevance_score

Maximum: 20

Evaluate:

- How directly the answer addresses the exact question
- Understanding of the demand of the question
- Whether the answer stays on topic
- Penalize generic information
- Penalize major topic deviation heavily

If the candidate does not address the question,
relevance_score should be 0 or very low.

3. structure_score

Maximum: 15

Evaluate:

- Introduction
- Logical progression
- Paragraph organization
- Headings/bullets where appropriate
- Logical connection between arguments
- Conclusion

4. analysis_score

Maximum: 20

Evaluate:

- Depth of analysis
- Critical thinking
- Cause-effect relationships
- Arguments and counter-arguments
- Multiple dimensions
- Challenges and implications
- Way forward where relevant

Do not award high analysis marks for simple description.

5. examples_score

Maximum: 10

Evaluate:

- Relevant examples
- Government schemes
- Reports
- Committees
- Case studies
- Constitutional provisions where relevant
- Current affairs
- Real-world illustrations

Do not reward invented or doubtful facts.

6. presentation_score

Maximum: 15

Evaluate:

- Language
- Clarity
- Grammar
- Coherence
- Conciseness
- Examination-oriented presentation
- Effective use of headings, bullets and paragraphs

============================================================
IMPORTANT SCORING RULES
============================================================

1. Each score MUST remain within its maximum.

2. The six scores together represent exactly 100 possible points:

content_score       = maximum 20
relevance_score     = maximum 20
structure_score     = maximum 15
analysis_score      = maximum 20
examples_score      = maximum 10
presentation_score  = maximum 15

TOTAL = 100

3. Do NOT return a "score" field.

4. Do NOT return a "max_score" field.

5. Python will calculate the final AI score.

6. The final AI score MUST be represented out of 100.

7. Do NOT give a high score merely because the answer is long.

8. Penalize major topic deviation.

9. If the answer does not address the exact question,
relevance_score must be 0 or very low.

10. Do not reward generic information that does not answer
the question.

11. Evaluate the candidate's actual answer, not what the
candidate may have intended to write.

12. Do not invent statistics, facts, government schemes,
reports, committees, examples or quotations.

13. If a factual claim appears doubtful or cannot be reliably
assessed, mention that the candidate should verify it.

14. Do not assume that mentioning a keyword means the candidate
has demonstrated proper understanding.

15. Do not award analysis marks simply for listing points.

16. Do not award examples marks for vague or generic examples.

17. A short but precise and relevant answer can score higher
than a long but generic answer.

18. Penalize repetition, filler content and irrelevant material.

19. Consider expected answer length, but do not use word count
as the primary measure of quality.

20. Do not reveal chain-of-thought, hidden reasoning or internal
reasoning steps.

21. Keep all feedback concise and useful.

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

Return EXACTLY these fields:

{{
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

Additional output rules:

- All six scores must be integers.
- Never exceed the specified maximum.
- strengths must be a JSON array of concise strings.
- weaknesses must be a JSON array of concise strings.
- missing_points must be a JSON array of concise strings.
- improvement_tips must be a JSON array of concise strings.
- model_improvement must be concise.
- Do not include Markdown.
- Do not include explanations outside JSON.
- Do not include additional JSON fields.
""".strip()

