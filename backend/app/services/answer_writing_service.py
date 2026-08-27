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

# Your current Writing SaaS uses 1000-word essays.
# Keep this aligned with the essay generation endpoint.
ESSAY_DEFAULT_WORDS = {
    "UPSC": 1000,
    "BPSC": 1000,
}

ESSAY_MAX_MARKS = {
    "UPSC": 100,
    "BPSC": 100,
}


# ============================================================
# TEXT UTILITIES
# ============================================================

def normalize_text(value: Any) -> str:
    """
    Normalize text while preserving paragraph/newline structure.

    Supports:
    - English
    - Hindi
    - Hinglish
    - Unicode text
    """

    if value is None:
        return ""

    text = str(value)

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Normalize tabs
    text = text.replace("\t", " ")

    # Normalize non-breaking spaces
    text = text.replace("\u00A0", " ")

    # Remove spaces before newline
    text = re.sub(r"[ \t]+\n", "\n", text)

    # Remove spaces after newline
    text = re.sub(r"\n[ \t]+", "\n", text)

    # Collapse multiple spaces
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Maximum two consecutive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def count_words(text: str) -> int:
    """
    Unicode-friendly word counter.

    Whitespace-separated tokens are counted as words.
    Works for Hindi, English and mixed text.
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
# PARAGRAPH UTILITIES
# ============================================================

def get_paragraphs(text: str) -> List[str]:
    """
    Return non-empty paragraphs.

    Paragraphs are separated by blank lines.
    """

    text = normalize_text(text)

    if not text:
        return []

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n+", text)
        if paragraph.strip()
    ]

    return paragraphs


def detect_paragraphs(text: str) -> int:
    return len(get_paragraphs(text))


# ============================================================
# INTRODUCTION DETECTION
# ============================================================

def detect_introduction(text: str) -> bool:

    text = normalize_text(text)

    if not text:
        return False

    paragraphs = get_paragraphs(text)

    if not paragraphs:
        return False

    first_paragraph = paragraphs[0].strip()
    first_part = first_paragraph[:500].lower()

    intro_keywords = [

        # Hindi
        "भारत",
        "बिहार",
        "वर्तमान",
        "आज",
        "इस संदर्भ में",
        "परिप्रेक्ष्य",
        "भारत में",
        "बिहार में",
        "वर्तमान समय में",
        "वर्तमान परिदृश्य",
        "ऐतिहासिक रूप से",
        "यह प्रश्न",
        "इस विषय",
        "उल्लेखनीय है",
        "आज के संदर्भ में",
        "समकालीन",
        "आधुनिक भारत",
        "शिक्षा",
        "लोकतंत्र",
        "विकास",
        "समाज",

        # English
        "introduction",
        "in recent years",
        "in india",
        "in bihar",
        "historically",
        "in the present context",
        "in the present scenario",
        "in contemporary india",
        "the issue",
        "the topic",
        "this question",
        "in this context",
        "education",
        "development",
        "democracy",
        "society",
    ]

    if any(
        keyword.lower() in first_part
        for keyword in intro_keywords
    ):
        return True

    # A concise first paragraph followed by body
    if len(paragraphs) >= 2:

        first_word_count = count_words(
            first_paragraph
        )

        if 8 <= first_word_count <= 100:
            return True

    intro_patterns = [
        r"^\w+.*\brefers to\b",
        r"^\w+.*\bcan be understood as\b",
        r"^\w+.*\bis defined as\b",
        r"^\w+.*\bmeans\b",
        r"^\w+.*\bके संदर्भ में\b",
        r"^\w+.*\bका अर्थ है\b",
        r"^\w+.*\bको समझने के लिए\b",
    ]

    return any(
        re.search(
            pattern,
            first_part,
            flags=re.IGNORECASE,
        )
        for pattern in intro_patterns
    )


# ============================================================
# CONCLUSION DETECTION
# ============================================================

def detect_conclusion(text: str) -> bool:

    text = normalize_text(text)

    if not text:
        return False

    paragraphs = get_paragraphs(text)

    if not paragraphs:
        return False

    last_part = paragraphs[-1].lower()

    conclusion_keywords = [

        # Hindi
        "निष्कर्ष",
        "अतः",
        "इस प्रकार",
        "अंततः",
        "इस दिशा में",
        "समग्र रूप से",
        "निष्कर्षतः",
        "आगे की राह",
        "उपसंहार",
        "भविष्य में",
        "आवश्यक है कि",
        "जरूरत है कि",
        "इसलिए",
        "इस प्रकार से",
        "भविष्य की राह",
        "आगे बढ़ते हुए",
        "अंत में",

        # English
        "conclusion",
        "therefore",
        "thus",
        "overall",
        "way forward",
        "in conclusion",
        "to conclude",
        "going forward",
        "hence",
        "ultimately",
        "it is therefore",
        "finally",
    ]

    if any(
        keyword.lower() in last_part
        for keyword in conclusion_keywords
    ):
        return True

    if len(paragraphs) >= 3:

        last_word_count = count_words(
            paragraphs[-1]
        )

        if 8 <= last_word_count <= 120:

            conclusion_patterns = [
                r"\bshould\b",
                r"\bmust\b",
                r"\bneed to\b",
                r"\brequires\b",
                r"\bneeded\b",
                r"\bआवश्यक\b",
                r"\bजरूरी\b",
                r"\bचाहिए\b",
                r"\bसुनिश्चित\b",
                r"\bसशक्त\b",
                r"\bकरना होगा\b",
                r"\bअपनाना होगा\b",
            ]

            if any(
                re.search(
                    pattern,
                    last_part,
                    flags=re.IGNORECASE,
                )
                for pattern in conclusion_patterns
            ):
                return True

    return False


# ============================================================
# BULLET / POINT DETECTION
# ============================================================

def detect_bullets_or_points(text: str) -> bool:
    """
    Detect:

    - Point
    * Point
    • Point
    1. Point
    1) Point
    a. Point
    A) Point
    १. Point

    Bullets are OPTIONAL for essays.
    """

    text = normalize_text(text)

    if not text:
        return False

    patterns = [

        # Bullet symbols
        r"(?:^|\n)\s*[-*•]\s+\S+",

        # Numbered
        r"(?:^|\n)\s*\d+[.)]\s+\S+",

        # Alphabetical
        r"(?:^|\n)\s*[a-zA-Z][.)]\s+\S+",

        # Hindi numerals
        r"(?:^|\n)\s*[०-९]+[.)]\s+\S+",
    ]

    return any(
        re.search(
            pattern,
            text,
        )
        for pattern in patterns
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

    unique_keywords = list(
        dict.fromkeys(
            normalize_text(keyword)
            for keyword in expected_keywords
            if normalize_text(keyword)
        )
    )

    if not unique_keywords:
        return 0.0

    found = detect_keywords(
        answer,
        unique_keywords,
    )

    return round(
        (len(found) / len(unique_keywords)) * 100,
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
# BASIC FEEDBACK
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

    # Word count
    if word_count < target_words * 0.60:

        feedback.append(
            f"उत्तर काफी छोटा है। लगभग {target_words} "
            "शब्दों के आसपास उत्तर लिखने का प्रयास करें।"
        )

    elif word_count > target_words * 1.25:

        feedback.append(
            f"उत्तर निर्धारित सीमा से काफी लंबा है। "
            f"लगभग {target_words} शब्दों में उत्तर को "
            "अधिक संक्षिप्त और प्रभावी रखें।"
        )

    else:

        feedback.append(
            "उत्तर की शब्द-सीमा सामान्यतः उचित है।"
        )

    # Introduction
    if not detect_introduction(answer):

        feedback.append(
            "उत्तर की शुरुआत में विषय की स्पष्ट भूमिका "
            "या संदर्भ जोड़ें।"
        )

    else:

        feedback.append(
            "भूमिका/Introduction का प्रयास अच्छा है।"
        )

    # Conclusion
    if not detect_conclusion(answer):

        feedback.append(
            "अंत में स्पष्ट निष्कर्ष या Way Forward जोड़ें।"
        )

    else:

        feedback.append(
            "निष्कर्ष/Way Forward शामिल किया गया है।"
        )

    # Structure
    if not detect_bullets_or_points(answer):

        feedback.append(
            "जहाँ उपयुक्त हो, मुख्य बिंदुओं को "
            "headings/bullets में प्रस्तुत करें।"
        )

    if detect_paragraphs(answer) < 2:

        feedback.append(
            "उत्तर को introduction, body और conclusion "
            "जैसे स्पष्ट भागों में व्यवस्थित करें।"
        )

    # Keywords
    if expected_keywords:

        found = detect_keywords(
            answer,
            expected_keywords,
        )

        if not found:

            feedback.append(
                "प्रश्न से संबंधित प्रमुख अवधारणाओं/"
                "keywords को उत्तर में शामिल करें।"
            )

        elif len(found) < len(expected_keywords) / 2:

            feedback.append(
                "कुछ महत्वपूर्ण keywords शामिल हैं, "
                "लेकिन content coverage और बढ़ाया जा सकता है।"
            )

        else:

            feedback.append(
                "प्रमुख विषयगत keywords का अच्छा उपयोग "
                "किया गया है।"
            )

    return feedback


# ============================================================
# SCORE CALCULATION
# ============================================================

def calculate_answer_score(
    answer: str,
    exam: str,
    question_type: str = "short",
    expected_keywords: Optional[List[str]] = None,
    target_words: Optional[int] = None,
) -> Dict[str, Any]:

    answer = normalize_text(answer)
    exam = normalize_text(exam).upper()
    question_type = normalize_text(question_type).lower()

    # --------------------------------------------------------
    # Dynamic target words
    # --------------------------------------------------------

    if target_words is not None:

        try:
            target_words = int(target_words)

        except (TypeError, ValueError):

            target_words = get_target_words(
                exam,
                question_type,
            )

        if target_words <= 0:

            target_words = get_target_words(
                exam,
                question_type,
            )

    else:

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

        # Neutral baseline if no keyword rubric exists
        content_score = 5 if word_count > 0 else 0

    # --------------------------------------------------------
    # Weighted score
    #
    # Content    = 50%
    # Structure  = 30%
    # Words      = 20%
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
        "word_score": word_score,
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
    target_words: Optional[int] = None,
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
        target_words=target_words,
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
    *,
    ai_evaluation: Optional[dict[str, Any]],
    answer: str,
    target_words: int,
    max_marks: int = 10,
) -> dict[str, Any]:
    """
    Normalize AI evaluation into a stable frontend/API response.

    IMPORTANT:
    - score is always the actual examination score.
    - max_score is the actual maximum marks.
    - percentage is calculated from score/max_score.
    - Never convert a 10-mark score into /100.
    """

    # ============================================================
    # SAFE INPUT
    # ============================================================

    if not isinstance(ai_evaluation, dict):
        ai_evaluation = {}

    try:
        max_marks = int(max_marks)
    except (TypeError, ValueError):
        max_marks = 10

    try:
        target_words = int(target_words)
    except (TypeError, ValueError):
        target_words = 150

    max_marks = max(1, max_marks)
    target_words = max(1, target_words)

    answer = normalize_text(answer or "")

    # ============================================================
    # WORD COUNT
    # ============================================================

    word_count = (
        len(answer.split())
        if answer.strip()
        else 0
    )

    # ============================================================
    # SAFE INTEGER
    # ============================================================

    def to_int(
        value: Any,
        default: int = 0,
        minimum: int = 0,
        maximum: Optional[int] = None,
    ) -> int:

        try:
            if value is None:
                return default

            if isinstance(value, bool):
                number = int(value)

            elif isinstance(value, (int, float)):
                number = int(round(value))

            elif isinstance(value, str):
                value = value.strip()

                if not value:
                    return default

                number = int(float(value))

            else:
                return default

        except (TypeError, ValueError):
            return default

        number = max(minimum, number)

        if maximum is not None:
            number = min(maximum, number)

        return number

    # ============================================================
    # SAFE STRING
    # ============================================================

    def safe_string(value: Any) -> str:

        if value is None:
            return ""

        if isinstance(value, str):
            return normalize_text(value)

        return normalize_text(str(value))

    # ============================================================
    # SAFE STRING LIST
    # ============================================================

    def safe_list(
        value: Any,
        limit: int = 5,
    ) -> list[str]:

        if value is None:
            return []

        if isinstance(value, str):
            text = safe_string(value)

            return [text] if text else []

        if not isinstance(value, list):
            return []

        result: list[str] = []

        for item in value:

            text = safe_string(item)

            if not text:
                continue

            result.append(text)

            if len(result) >= limit:
                break

        return result

    # ============================================================
    # COMPONENT LIMITS
    # ============================================================

    if max_marks <= 10:

        intro_max = 1
        content_max = 2
        analysis_max = 2
        current_max = 1
        presentation_max = 1
        conclusion_max = 1

    elif max_marks <= 15:

        intro_max = 1
        content_max = 3
        analysis_max = 3
        current_max = 2
        presentation_max = 1
        conclusion_max = 2

    else:

        # Proportional safety limits.
        intro_max = max(1, round(max_marks * 0.10))
        content_max = max(1, round(max_marks * 0.20))
        analysis_max = max(1, round(max_marks * 0.20))
        current_max = max(1, round(max_marks * 0.10))
        presentation_max = max(1, round(max_marks * 0.10))
        conclusion_max = max(1, round(max_marks * 0.10))

    # ============================================================
    # COMPONENT SCORES
    # ============================================================

    introduction_score = to_int(
        ai_evaluation.get("introduction_score"),
        maximum=intro_max,
    )

    content_score = to_int(
        ai_evaluation.get("content_score"),
        maximum=content_max,
    )

    analysis_score = to_int(
        ai_evaluation.get("analysis_score"),
        maximum=analysis_max,
    )

    current_affairs_score = to_int(
        ai_evaluation.get(
            "current_affairs_score"
        ),
        maximum=current_max,
    )

    presentation_score = to_int(
        ai_evaluation.get(
            "presentation_score"
        ),
        maximum=presentation_max,
    )

    conclusion_score = to_int(
        ai_evaluation.get("conclusion_score"),
        maximum=conclusion_max,
    )

    # ============================================================
    # FINAL SCORE
    # ============================================================

    score_present = (
        "score" in ai_evaluation
        and ai_evaluation.get("score") is not None
    )

    score = to_int(
        ai_evaluation.get("score"),
        default=0,
        minimum=0,
        maximum=max_marks,
    )

    # ============================================================
    # FALLBACK SCORE
    # ============================================================
    #
    # Only use this when AI did NOT return a score.
    #
    # NEVER divide a 10-mark score by 100.
    #

    if not score_present:

        component_score = (
            introduction_score
            + content_score
            + analysis_score
            + current_affairs_score
            + presentation_score
            + conclusion_score
        )

        component_max = (
            intro_max
            + content_max
            + analysis_max
            + current_max
            + presentation_max
            + conclusion_max
        )

        if component_max > 0:

            score = round(
                (
                    component_score
                    / component_max
                )
                * max_marks
            )

        else:
            score = 0

        score = max(
            0,
            min(score, max_marks),
        )

    # ============================================================
    # PERCENTAGE
    # ============================================================

    percentage = round(
        (score / max_marks) * 100,
        2,
    )

    # ============================================================
    # TEXT FIELDS
    # ============================================================

    strengths = safe_list(
        ai_evaluation.get("strengths"),
        4,
    )

    weaknesses = safe_list(
        ai_evaluation.get("weaknesses"),
        4,
    )

    missing_points = safe_list(
        ai_evaluation.get("missing_points"),
        5,
    )

    improvement_tips = safe_list(
        ai_evaluation.get("improvement_tips"),
        5,
    )

    feedback = safe_list(
        ai_evaluation.get("feedback"),
        5,
    )

    model_answer = safe_string(
        ai_evaluation.get("model_answer")
    )

    model_improvement = safe_string(
        ai_evaluation.get(
            "model_improvement"
        )
    )

    # ============================================================
    # CONSISTENCY CHECK
    # ============================================================
    #
    # If AI says introduction_score = 0,
    # do NOT allow merge layer to claim that
    # introduction was good.
    #

    if introduction_score == 0:

        feedback = [
            item
            for item in feedback
            if "भूमिका" not in item
            and "Introduction" not in item
            and "introduction" not in item
        ]

    if conclusion_score == 0:

        feedback = [
            item
            for item in feedback
            if "निष्कर्ष" not in item
            and "Conclusion" not in item
            and "conclusion" not in item
        ]

    if analysis_score == 0:

        feedback = [
            item
            for item in feedback
            if "विश्लेषण अच्छा" not in item
            and "analysis" not in item.lower()
        ]

    # ============================================================
    # DEFAULT FEEDBACK
    # ============================================================

    if not feedback:

        if score >= max_marks * 0.75:

            feedback = [
                "उत्तर प्रश्न की मुख्य मांग को अच्छी तरह संबोधित करता है।"
            ]

        elif score >= max_marks * 0.60:

            feedback = [
                "उत्तर संतोषजनक है, लेकिन विश्लेषण और प्रश्न की मांग के अनुरूप प्रस्तुति को और मजबूत किया जा सकता है।"
            ]

        elif score >= max_marks * 0.40:

            feedback = [
                "उत्तर में कुछ प्रासंगिक समझ है, लेकिन content और analysis को अधिक मजबूत करने की आवश्यकता है।"
            ]

        else:

            feedback = [
                "उत्तर को अधिक प्रश्न-केंद्रित, विश्लेषणात्मक और संरचित बनाने की आवश्यकता है।"
            ]

    # ============================================================
    # WORD COUNT
    # ============================================================

    if (
        word_count > target_words * 1.20
        and len(weaknesses) < 4
    ):

        weaknesses.append(
            f"उत्तर {word_count} शब्दों का है, जो निर्धारित {target_words} शब्दों से काफी अधिक है।"
        )

    elif (
        word_count < target_words * 0.60
        and len(improvement_tips) < 5
    ):

        improvement_tips.append(
            f"उत्तर को लगभग {target_words} शब्दों के आसपास अधिक पर्याप्त रूप से विकसित करें।"
        )

    # ============================================================
    # FINAL NORMALIZED RESPONSE
    # ============================================================

    return {
        "score": score,
        "max_score": max_marks,
        "percentage": percentage,

        "introduction_score": introduction_score,
        "content_score": content_score,
        "analysis_score": analysis_score,
        "current_affairs_score": current_affairs_score,
        "presentation_score": presentation_score,
        "conclusion_score": conclusion_score,

        "word_count": word_count,
        "target_words": target_words,

        "strengths": strengths,
        "weaknesses": weaknesses,
        "missing_points": missing_points,
        "improvement_tips": improvement_tips,
        "feedback": feedback,

        "model_answer": model_answer,
        "model_improvement": model_improvement,

        "evaluation_mode": "ai",
    }

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
    target_words: Optional[int] = None,
) -> Dict[str, Any]:

    evaluation = evaluate_answer(
        answer=answer,
        exam=exam,
        question=question,
        question_type=question_type,
        category=category,
        expected_keywords=expected_keywords,
        target_words=target_words,
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
        "target_words": evaluation["target_words"],
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
    question = normalize_text(question)
    answer = normalize_text(answer)

    category_text = (
        normalize_text(category)
        if category
        else "General"
    )

    # ============================================================
    # SAFE VALUES
    # ============================================================

    try:
        max_marks = int(max_marks)
    except (TypeError, ValueError):
        max_marks = 10

    try:
        target_words = int(target_words)
    except (TypeError, ValueError):
        target_words = 150

    # Supported UPSC/BPSC answer-writing scales.
    if max_marks not in (10, 15):
        max_marks = 10

    target_words = max(1, target_words)

    # ============================================================
    # MARK DISTRIBUTION
    # ============================================================
    #
    # IMPORTANT:
    #
    # All diagnostic component scores MUST add up to the
    # final "score".
    #
    # This prevents situations such as:
    #
    # score = 4
    # content = 1
    # structure = 6
    #
    # where component scores contradict the final score.
    #
    # ============================================================

    if max_marks == 10:

        rubric = """
10-MARK ANSWER RUBRIC

Introduction            = 1 mark
Content                  = 2 marks
Analysis                 = 2 marks
Question Relevance       = 2 marks
Current Affairs/Examples = 1 mark
Structure                = 1 mark
Conclusion               = 1 mark

TOTAL = 10 MARKS
"""

        component_limits = """
COMPONENT LIMITS:

introduction_score      : 0-1
content_score           : 0-2
analysis_score          : 0-2
current_affairs_score   : 0-1
presentation_score      : 0-1
conclusion_score        : 0-1

IMPORTANT:

There is no separate relevance_score field in the JSON.

The 2 marks for Question Relevance must be reflected mainly
through the content_score, analysis_score and final score.

The component fields above are diagnostic.

Their combined total MUST NOT exceed the final score.
"""

    else:

        rubric = """
15-MARK ANSWER RUBRIC

Introduction            = 1 mark
Content                  = 3 marks
Analysis                 = 3 marks
Question Relevance       = 3 marks
Current Affairs/Examples = 2 marks
Structure                = 1 mark
Conclusion               = 2 marks

TOTAL = 15 MARKS
"""

        component_limits = """
COMPONENT LIMITS:

introduction_score      : 0-1
content_score           : 0-3
analysis_score          : 0-3
current_affairs_score   : 0-2
presentation_score      : 0-1
conclusion_score        : 0-2

IMPORTANT:

There is no separate relevance_score field in the JSON.

Question relevance is reflected in the overall score and
through the quality of content and analysis.

The component fields are diagnostic.

Their combined total MUST NOT exceed the final score.
"""

    # ============================================================
    # RETURN PROMPT
    # ============================================================

    return f"""
You are a senior UPSC/BPSC Mains answer evaluator.

Evaluate the candidate's answer realistically and fairly.

Your task is to estimate the marks that a competent human
examiner would reasonably award.

Do NOT reward the answer merely for being long.

Do NOT punish the answer merely because it lacks statistics,
schemes, quotations or sophisticated terminology.

============================================================
EXAM DETAILS
============================================================

Exam:
{exam}

Category:
{category_text}

Question:
{question}

Maximum Marks:
{max_marks}

Expected Answer Length:
Approximately {target_words} words

============================================================
CANDIDATE ANSWER
============================================================

{answer}

============================================================
PRIMARY EVALUATION PRINCIPLE
============================================================

Evaluate ONLY the content actually written by the candidate.

Do not evaluate what the candidate may have intended to write.

First understand exactly what the question demands.

Then judge whether the candidate has actually addressed
that demand.

The final score must represent the overall quality of the
answer as a UPSC/BPSC examination answer.

============================================================
QUESTION DEMAND
============================================================

Identify the actual demand of the question.

Pay attention to directive words.

Discuss:
Explain the issue using relevant dimensions and provide
a balanced discussion where appropriate.

Analyse:
Explain causes, effects, relationships, implications and
reasoning.

Critically Examine:
Present relevant positive and negative aspects followed by
a balanced assessment.

Evaluate:
Assess the issue and provide a reasoned judgement.

Explain:
Provide a clear and relevant explanation.

Comment:
Give a reasoned position supported by relevant arguments.

Examine:
Investigate the issue through relevant dimensions and
arrive at a reasoned conclusion.

To what extent:
Assess how far the statement is valid and explain limitations
or qualifications where relevant.

Do NOT penalize the candidate merely because the directive
word itself is not repeated.

============================================================
RELEVANCE
============================================================

Relevance is one of the most important factors.

Ask:

1. Does the answer address the exact question?
2. Does it understand the central demand?
3. Are the arguments connected to the question?
4. Is unnecessary generic information included?
5. Does the answer remain focused?

If the answer is substantially off-topic, marks should fall.

If the answer directly addresses the question with several
relevant arguments, do NOT give an unnecessarily low score.

A relevant answer does not need to mention every possible
dimension.

============================================================
CONTENT
============================================================

Reward:

- correct concepts,
- relevant arguments,
- important dimensions,
- factual understanding,
- logical points,
- constitutional provisions where relevant,
- institutional aspects where relevant,
- social dimensions where relevant,
- economic dimensions where relevant,
- political dimensions where relevant,
- environmental dimensions where relevant,
- relevant examples.

Do NOT reward irrelevant facts merely because they are factual.

Do NOT require every possible dimension.

============================================================
ANALYSIS
============================================================

Analysis includes:

- WHY
- HOW
- CAUSES
- EFFECTS
- IMPACT
- CONSEQUENCES
- CHALLENGES
- TRADE-OFFS
- RELATIONSHIPS
- IMPLICATIONS
- SOLUTIONS
- WAY FORWARD

A list of statements without explanation is mainly descriptive.

A point followed by reasoning, cause-effect relationship,
impact or explanation demonstrates analysis.

Do not demand advanced analysis from a very short answer.

============================================================
CURRENT AFFAIRS / EXAMPLES
============================================================

Reward relevant and accurate:

- current affairs,
- examples,
- government schemes,
- reports,
- committees,
- constitutional provisions,
- court judgements,
- data,
- real-world cases.

However:

Missing statistics alone MUST NOT cause a severe penalty.

Missing government schemes alone MUST NOT cause a severe
penalty.

Missing quotations alone MUST NOT cause a severe penalty.

Never invent a statistic to criticize the candidate.

Never invent a factual error.

If a factual claim appears doubtful, mention:

"Candidate should verify the factual claim."

Do not treat an uncertain claim as definitely false.

============================================================
STRUCTURE / PRESENTATION
============================================================

Reward:

- logical flow,
- clear sequencing,
- introduction,
- body,
- conclusion,
- useful headings,
- coherent paragraphs,
- readable presentation,
- concise expression,
- examination-oriented writing.

Bullets are OPTIONAL.

Paragraph-based answers can score highly.

Do NOT penalize simple language when the meaning is clear.

Do NOT penalize the candidate merely for not using headings.

============================================================
INTRODUCTION
============================================================

Evaluate whether the answer begins effectively.

A good introduction should:

- establish the context,
- define or frame the issue where useful,
- directly connect to the question.

Do not require a lengthy introduction.

A concise relevant introduction can receive full introduction marks.

============================================================
CONCLUSION
============================================================

Evaluate whether the answer ends appropriately.

A good conclusion may:

- answer the central issue,
- provide a balanced judgement,
- give a practical way forward,
- connect to constitutional/democratic/developmental values
  where relevant.

Do not require a separate "Way Forward" heading.

============================================================
WORD LIMIT
============================================================

Expected length:

Approximately {target_words} words.

Word count is a SUPPORTING factor.

It is NOT the primary determinant of marks.

A shorter but highly relevant answer can score well.

A long but irrelevant answer should not score highly.

Do not drastically reduce marks merely because the answer is
somewhat shorter than the target.

If the answer is close to the target word count, do not penalize
it merely for being slightly above or below the target.

============================================================
FAIRNESS RULES
============================================================

DO NOT give an extremely low score merely because:

- statistics are missing,
- schemes are missing,
- committee names are missing,
- expert quotations are missing,
- sophisticated terminology is missing,
- the answer uses simple language,
- bullets are not used,
- headings are not used,
- every possible dimension is not covered.

Give very low marks only when the answer genuinely deserves
them because of:

- irrelevance,
- serious factual problems,
- lack of substance,
- failure to address the question,
- severe conceptual misunderstanding.

============================================================
MARKING RUBRIC
============================================================

{rubric}

============================================================
COMPONENT GUIDANCE
============================================================

{component_limits}

============================================================
FINAL SCORE CALIBRATION
============================================================

FOR 10-MARK QUESTIONS:

0-1
Blank, completely irrelevant, severely incorrect or
does not address the question.

2-3
Very weak answer with major deficiencies.

4-5
Below average answer but containing some relevant
understanding.

6
Satisfactory answer addressing the main demand.

7
Good answer with relevant content and reasonable analysis.

8
Very good answer with strong relevance, content and analysis.

9
Excellent answer with strong depth, structure and evidence.

10
Exceptional / near-model answer.

IMPORTANT:

A genuinely relevant answer should NOT automatically receive
2 or 3 merely because statistics or schemes are absent.

------------------------------------------------------------

FOR 15-MARK QUESTIONS:

0-2
Extremely poor, blank, irrelevant or severely incorrect.

3-5
Weak answer with major deficiencies.

6-8
Developing / below-average answer.

9
Satisfactory answer.

10
Good answer.

11
Very good answer.

12
Strong answer.

13
Excellent answer.

14-15
Exceptional / near-model answer.

IMPORTANT:

A relevant answer with several correct arguments, reasonable
analysis and a conclusion should normally score above the
lowest range.

============================================================
SCORE CONSISTENCY RULE
============================================================

The final "score" is the authoritative examination score.

The diagnostic component scores must be internally consistent
with the final score.

NEVER produce contradictory values such as:

score = 4

while:
content_score = 1
structure_score = 6

because the diagnostic scores already exceed the final score.

The component scores must support the final judgement.

For a 10-mark answer, the following six diagnostic dimensions
must be distributed conservatively:

introduction_score      : maximum 1
content_score           : maximum 2
analysis_score          : maximum 2
current_affairs_score   : maximum 1
presentation_score      : maximum 1
conclusion_score        : maximum 1

The remaining relevance/question-demand judgement is reflected
in the final score.

IMPORTANT:

Do not artificially make all component scores high.

Score each dimension independently based only on evidence
present in the candidate's answer.

============================================================
SCORE SAFETY
============================================================

1. score MUST be an integer.

2. max_score MUST be exactly {max_marks}.

3. score MUST be between 0 and {max_marks}.

4. Never return negative marks.

5. Never return marks greater than {max_marks}.

6. Never use percentage as the score.

7. The score is examination marks, NOT percentage.

8. Do not increase the score simply because the answer reaches
   the target word count.

9. Do not decrease the score drastically merely because the
   answer is slightly below the target word count.

10. Relevance is more important than decorative content.

11. Do not reward keyword stuffing.

12. Mentioning a keyword does not prove understanding.

13. Do not invent facts.

14. Do not invent statistics.

15. Do not expose internal reasoning.

============================================================
FEEDBACK
============================================================

strengths:

Give 1-4 concise strengths that are genuinely present.

weaknesses:

Give 1-4 specific weaknesses.

missing_points:

Mention ONLY important points whose addition would materially
improve the answer.

Do not list every possible missing point.

improvement_tips:

Give practical UPSC/BPSC answer-writing suggestions.

feedback:

Give concise examiner-style feedback specific to this answer.

Do not write generic statements such as:

"Improve your answer."

Instead explain what should specifically be improved.

model_improvement:

Explain how the candidate can convert this answer into a
stronger examination answer.

model_answer:

Provide a concise improved model answer when useful.

The model answer must directly answer the given question.

Do not invent facts merely to make it look sophisticated.

============================================================
INTERNAL EVALUATION
============================================================

Before producing the JSON, internally assess:

1. What exactly is the question demanding?
2. Did the candidate understand the demand?
3. Is the answer relevant?
4. What useful content is present?
5. What analysis is present?
6. What important points are missing?
7. Are factual claims reliable?
8. Is the structure effective?
9. Is there an introduction?
10. Is there a conclusion?
11. Is the answer focused?
12. Is the word length reasonable?
13. What marks would a reasonable human examiner award?

Do NOT expose this internal reasoning.

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

Use EXACTLY these fields:

{{
    "score": 0,
    "max_score": {max_marks},
    "introduction_score": 0,
    "content_score": 0,
    "analysis_score": 0,
    "current_affairs_score": 0,
    "presentation_score": 0,
    "conclusion_score": 0,
    "strengths": [],
    "weaknesses": [],
    "missing_points": [],
    "improvement_tips": [],
    "feedback": [],
    "model_answer": "",
    "model_improvement": "",
    "evaluation_mode": "ai"
}}

============================================================
FINAL JSON RULES
============================================================

- Return JSON ONLY.
- No Markdown.
- No explanation outside JSON.
- No code fences.
- No extra fields.
- All numeric scores must be integers.
- score must be between 0 and {max_marks}.
- max_score must be exactly {max_marks}.
- No negative scores.
- No percentage in score.
- Arrays must contain strings only.
- Keep feedback concise.
- Keep feedback specific to the candidate.
- Do not fabricate facts.
- Do not fabricate statistics.
- Do not expose internal reasoning.
- Keep evaluation_mode exactly "ai".

If the answer is relevant and demonstrates reasonable
understanding, do not artificially force it into the lowest
score range.

Return valid JSON and NOTHING ELSE.
""".strip()


# ============================================================
# SIMPLE MODEL ANSWER PROMPT
# ============================================================

def build_model_answer_prompt(
    *,
    exam: str,
    question: str,
    target_words: int,
    category: Optional[str] = None,
) -> str:

    exam = normalize_text(exam).upper()
    question = normalize_text(question)

    category_text = (
        normalize_text(category)
        if category
        else "General"
    )

    return f"""
You are an expert {exam} Mains answer writer.

Write a high-quality model answer for the following question.

Exam:
{exam}

Category:
{category_text}

Question:
{question}

Target length:
Approximately {target_words} words.

Requirements:

1. Start with a concise introduction.

2. Directly address the exact demand of the question.

3. Use clear headings where appropriate.

4. Use bullet points where useful, but do not force bullets.

5. Include relevant examples.

6. Include relevant constitutional, economic, social,
   historical or governance aspects where applicable.

7. Include current affairs only when relevant.

8. Ensure balanced analysis where required.

9. End with a balanced conclusion.

10. Add a practical Way Forward where appropriate.

11. Do not invent facts or statistics.

12. Keep the answer exam-oriented and concise.

Write only the model answer.
""".strip()


# ============================================================
# ESSAY FUNCTIONS
# ============================================================

def get_essay_target_words(exam: str) -> int:

    exam = normalize_text(exam).upper()

    return ESSAY_DEFAULT_WORDS.get(
        exam,
        ESSAY_DEFAULT_WORDS["UPSC"],
    )


def get_essay_max_marks(exam: str) -> int:

    exam = normalize_text(exam).upper()

    return ESSAY_MAX_MARKS.get(
        exam,
        ESSAY_MAX_MARKS["UPSC"],
    )


def calculate_essay_structure_score(
    essay: str,
) -> int:

    essay = normalize_text(essay)

    if not essay:
        return 0

    score = 0

    if detect_introduction(essay):
        score += 3

    if detect_conclusion(essay):
        score += 3

    if detect_paragraphs(essay) >= 4:
        score += 2

    # Bullets are optional for essays.
    # Long paragraph-based essays should not be penalized.
    if detect_bullets_or_points(essay):
        score += 2

    elif detect_paragraphs(essay) >= 6:
        score += 1

    return min(score, 10)


def calculate_essay_word_score(
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

    if 120 < percentage <= 135:
        return 8

    if 50 <= percentage < 65:
        return 6

    if 135 < percentage <= 150:
        return 6

    if 35 <= percentage < 50:
        return 4

    return 2


def calculate_essay_basic_score(
    essay: str,
    exam: str,
    target_words: Optional[int] = None,
) -> Dict[str, Any]:

    essay = normalize_text(essay)

    word_count = count_words(essay)

    # --------------------------------------------------------
    # Dynamic essay target
    # --------------------------------------------------------

    if target_words is not None:

        try:
            target_words = int(target_words)

        except (TypeError, ValueError):

            target_words = get_essay_target_words(
                exam
            )

        if target_words <= 0:

            target_words = get_essay_target_words(
                exam
            )

    else:

        target_words = get_essay_target_words(
            exam
        )

    max_marks = get_essay_max_marks(
        exam
    )

    # --------------------------------------------------------
    # Empty essay
    # --------------------------------------------------------

    if word_count == 0:

        return {
            "score": 0,
            "max_score": max_marks,
            "word_count": 0,
            "target_words": target_words,
            "word_percentage": 0.0,
            "structure_score": 0,
            "word_score": 0,
            "content_score": 0,
            "introduction_present": False,
            "conclusion_present": False,
            "points_format_present": False,
            "paragraph_count": 0,
            "percentage": 0.0,
            "evaluation_mode": "basic",
        }

    structure_score = calculate_essay_structure_score(
        essay
    )

    word_score = calculate_essay_word_score(
        word_count,
        target_words,
    )

    # Basic evaluator has no semantic AI understanding.
    # Therefore use a neutral content score for non-empty essays.
    content_score = 5

    # --------------------------------------------------------
    # Basic weighting
    #
    # Structure = 40%
    # Content   = 40%
    # Words     = 20%
    # --------------------------------------------------------

    raw_score = (
        (structure_score * 0.40)
        + (content_score * 0.40)
        + (word_score * 0.20)
    )

    score = round(
        (raw_score / 10) * max_marks
    )

    score = max(
        0,
        min(score, max_marks),
    )

    percentage = (
        (score / max_marks) * 100
        if max_marks
        else 0
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
        "word_score": word_score,
        "content_score": content_score,
        "introduction_present": detect_introduction(
            essay
        ),
        "conclusion_present": detect_conclusion(
            essay
        ),
        "points_format_present": detect_bullets_or_points(
            essay
        ),
        "paragraph_count": detect_paragraphs(
            essay
        ),
        "percentage": round(
            percentage,
            2,
        ),
        "evaluation_mode": "basic",
    }


# ============================================================
# ESSAY BASIC FEEDBACK
# ============================================================

def generate_essay_basic_feedback(
    essay: str,
    target_words: int,
) -> List[str]:

    essay = normalize_text(essay)

    word_count = count_words(essay)

    if word_count == 0:

        return [
            "निबंध खाली है। कृपया पूरा निबंध लिखें।"
        ]

    feedback: List[str] = []

    percentage = calculate_word_percentage(
        word_count,
        target_words,
    )

    if percentage < 50:

        feedback.append(
            f"निबंध बहुत छोटा है। लगभग {target_words} "
            "शब्दों के आसपास विस्तार से लिखें।"
        )

    elif percentage < 80:

        feedback.append(
            f"निबंध अपेक्षित लंबाई से छोटा है। "
            f"इसे लगभग {target_words} शब्दों तक विकसित करें।"
        )

    elif percentage > 125:

        feedback.append(
            f"निबंध अपेक्षित लंबाई से काफी लंबा है। "
            "अनावश्यक दोहराव कम करें।"
        )

    else:

        feedback.append(
            "निबंध की शब्द-सीमा सामान्यतः उचित है।"
        )

    if not detect_introduction(essay):

        feedback.append(
            "निबंध की शुरुआत में विषय की वैचारिक "
            "भूमिका और संदर्भ अधिक स्पष्ट करें।"
        )

    if not detect_conclusion(essay):

        feedback.append(
            "अंत में स्पष्ट निष्कर्ष और भविष्य की राह जोड़ें।"
        )

    if detect_paragraphs(essay) < 4:

        feedback.append(
            "निबंध को अधिक स्पष्ट पैराग्राफों में "
            "विभाजित करें ताकि विचारों का प्रवाह बेहतर हो।"
        )

    return feedback


# ============================================================
# ESSAY EVALUATION PROMPT
# ============================================================

def build_essay_evaluation_prompt(
    *,
    exam: str,
    topic: str,
    essay: str,
    target_words: Optional[int] = None,
) -> str:

    exam = normalize_text(exam).upper()
    topic = normalize_text(topic)
    essay = normalize_text(essay)

    max_marks = get_essay_max_marks(
        exam
    )

    if target_words is not None:

        try:
            target_words = int(target_words)

        except (TypeError, ValueError):

            target_words = get_essay_target_words(
                exam
            )

        if target_words <= 0:

            target_words = get_essay_target_words(
                exam
            )

    else:

        target_words = get_essay_target_words(
            exam
        )

    actual_word_count = count_words(essay)

    return f"""
You are an expert evaluator for the {exam} Essay examination.

Evaluate the candidate's essay realistically and fairly according
to Indian competitive examination standards.

------------------------------------------------------------
EXAM DETAILS
------------------------------------------------------------

Exam:
{exam}

Essay Topic:
{topic}

Expected Length:
Approximately {target_words} words

Actual Candidate Word Count:
{actual_word_count}

Maximum Marks:
{max_marks}

------------------------------------------------------------
CANDIDATE ESSAY
------------------------------------------------------------

{essay}

------------------------------------------------------------
IMPORTANT EVALUATION RULES
------------------------------------------------------------

Evaluate what the candidate actually wrote.

Do NOT compare the essay against an imaginary perfect essay and
penalize every missing point.

Do NOT require statistics, quotations, schemes or famous thinkers
unless they are genuinely relevant.

Do NOT invent factual errors.

Do NOT reward an essay merely because it is long.

A shorter but focused and well-reasoned essay can receive good marks.

A long essay with repetition, irrelevant content or poor analysis
should not receive high marks.

Assess whether the candidate has understood the central theme.

Look for:

- conceptual clarity,
- relevance,
- depth,
- logical progression,
- multi-dimensional thinking,
- examples,
- balance,
- originality of thought,
- social/economic/political/historical dimensions where relevant,
- practical solutions,
- language,
- conclusion.

Do not require bullet points.

A coherent paragraph-based essay is acceptable.

------------------------------------------------------------
EVALUATION AREAS
------------------------------------------------------------

1. Understanding of topic
2. Introduction
3. Relevance
4. Depth of content
5. Logical flow
6. Multi-dimensional analysis
7. Examples
8. Current affairs
9. Balance and objectivity
10. Language and presentation
11. Conclusion
12. Overall quality

------------------------------------------------------------
WORD COUNT RULE
------------------------------------------------------------

Expected length is approximately {target_words} words.

The word count is a supporting factor, not the primary determinant.

Do NOT reduce the score drastically only because the essay is
shorter than {target_words} words.

However:

- An extremely short essay cannot demonstrate sufficient depth.
- An essay containing only a few words should receive a very low score.
- A complete, focused essay below the target may still receive
  reasonable marks.
- Excessive length with repetition should not increase marks.

------------------------------------------------------------
EMPTY / VERY SHORT ANSWER RULE
------------------------------------------------------------

If the candidate has submitted only the topic title, a few words,
or an incomplete fragment:

- score should normally be between 0 and 10,
- introduction_score should be 0,
- content_score should be 0,
- analysis_score should be 0,
- current_affairs_score should be 0,
- presentation_score should be 0 or very low,
- conclusion_score should be 0.

Do not pretend that an incomplete submission is a full essay.

------------------------------------------------------------
SCORE CALIBRATION
------------------------------------------------------------

For a 250-mark essay:

0-49:
Extremely poor / irrelevant / incomplete

50-99:
Weak

100-124:
Below average / developing

125-149:
Average / satisfactory

150-174:
Good

175-199:
Very good

200-224:
Excellent

225-250:
Exceptional / near-model quality

For a 100-mark essay:

0-19:
Extremely poor

20-39:
Weak

40-49:
Below average

50-59:
Satisfactory

60-69:
Good

70-79:
Very good

80-89:
Excellent

90-100:
Exceptional

------------------------------------------------------------
COMPONENT SCORE RULE
------------------------------------------------------------

For this {max_marks}-mark essay, component scores must use
the same 0-{max_marks} scale OR clearly represent weighted
components.

Prefer the following component allocation:

introduction_score:
0-10

content_score:
0-25

analysis_score:
0-25

current_affairs_score:
0-10

presentation_score:
0-10

conclusion_score:
0-10

The remaining marks may be reflected in the overall score based
on relevance, depth, coherence and originality.

The overall score must remain between 0 and {max_marks}.

------------------------------------------------------------
OUTPUT
------------------------------------------------------------

Return JSON ONLY:

{{
    "score": 0,
    "max_score": {max_marks},
    "introduction_score": 0,
    "content_score": 0,
    "analysis_score": 0,
    "current_affairs_score": 0,
    "presentation_score": 0,
    "conclusion_score": 0,
    "strengths": [],
    "weaknesses": [],
    "missing_points": [],
    "suggestions": [],
    "improvement_tips": [],
    "feedback": [],
    "model_answer": "",
    "model_improvement": "",
    "word_count": {actual_word_count},
    "target_words": {target_words},
    "evaluation_mode": "ai"
}}

IMPORTANT:

- score MUST be between 0 and {max_marks}.
- max_score MUST be {max_marks}.
- Never return negative marks.
- Never return marks above maximum.
- Do not return percentage as score.
- Keep component scores logically consistent.
- Feedback must be specific to this essay.
- Do not fabricate facts or statistics.
- Return valid JSON only.
""".strip()


# ============================================================
# ESSAY SUBMISSION EVALUATION
# ============================================================

def evaluate_essay(
    *,
    essay: str,
    exam: str,
    topic: str,
    target_words: Optional[int] = None,
) -> Dict[str, Any]:

    essay = normalize_text(essay)
    exam = normalize_text(exam).upper()
    topic = normalize_text(topic)

    basic = calculate_essay_basic_score(
        essay=essay,
        exam=exam,
        target_words=target_words,
    )

    actual_target = basic["target_words"]

    feedback = generate_essay_basic_feedback(
        essay=essay,
        target_words=actual_target,
    )

    result = {
        "exam": exam,
        "topic": topic,
        "essay": essay,
        **basic,
        "feedback": feedback,
        "evaluation_mode": "basic",
    }

    return result


# ============================================================
# ESSAY SUBMISSION RESULT
# ============================================================

def build_essay_submission_result(
    *,
    user_id: int,
    essay_id: int,
    essay: str,
    exam: str,
    topic: str,
    target_words: Optional[int] = None,
) -> Dict[str, Any]:

    evaluation = evaluate_essay(
        essay=essay,
        exam=exam,
        topic=topic,
        target_words=target_words,
    )

    return {
        "user_id": user_id,
        "essay_id": essay_id,
        "exam": normalize_text(exam).upper(),
        "topic": normalize_text(topic),
        "essay": normalize_text(essay),
        "target_words": evaluation["target_words"],
        "evaluation": evaluation,
    }


# ============================================================
# PUBLIC EXPORTS
# ============================================================

__all__ = [

    # Text
    "normalize_text",
    "count_words",
    "calculate_word_percentage",

    # Question
    "get_target_words",
    "get_max_marks",

    # Structure
    "get_paragraphs",
    "detect_introduction",
    "detect_conclusion",
    "detect_bullets_or_points",
    "detect_paragraphs",

    # Content
    "detect_keywords",
    "calculate_content_coverage",

    # Basic answer scoring
    "calculate_structure_score",
    "calculate_word_score",
    "generate_basic_feedback",
    "calculate_answer_score",
    "evaluate_answer",

    # AI answer evaluation
    "merge_ai_evaluation",

    # Answer submission
    "build_submission_result",

    # Answer prompts
    "build_ai_evaluation_prompt",
    "build_model_answer_prompt",

    # Essay
    "get_essay_target_words",
    "get_essay_max_marks",
    "calculate_essay_structure_score",
    "calculate_essay_word_score",
    "calculate_essay_basic_score",
    "generate_essay_basic_feedback",
    "build_essay_evaluation_prompt",
    "evaluate_essay",
    "build_essay_submission_result",
]