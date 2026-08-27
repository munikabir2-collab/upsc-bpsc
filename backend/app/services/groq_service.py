from __future__ import annotations

import re
from typing import Any

from app.services.groq_service import (
    generate_json,
    generate_text,
    MAX_COMPLETION_TOKENS,
)


# ============================================================
# HELPERS
# ============================================================

def _language_name(language: str) -> str:

    mapping = {
        "hi": "Hindi",
        "en": "English",
        "hinglish": "Hinglish",
    }

    return mapping.get(
        language.lower(),
        language,
    )


def _safe_string(value: Any) -> str:

    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    return value.strip()


def _safe_list(value: Any) -> list[str]:

    if not isinstance(value, list):
        return []

    result = []

    for item in value:

        if isinstance(item, str):

            item = item.strip()

            if item:
                result.append(item)

    return result


def _word_count(text: str) -> int:

    if not text:
        return 0

    return len(
        re.findall(
            r"\S+",
            text,
        )
    )


# ============================================================
# BUILD ANSWER
# ============================================================

def _build_answer(
    introduction: str,
    body: str,
    way_forward: str,
    conclusion: str,
) -> str:

    parts = []

    for part in [
        introduction,
        body,
        way_forward,
        conclusion,
    ]:

        if part:
            parts.append(part.strip())

    return "\n\n".join(parts).strip()


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

    language_name = _language_name(language)

    # --------------------------------------------------------
    # NORMALIZE WORD LIMIT
    # --------------------------------------------------------

    target_words = max(
        50,
        min(
            target_words,
            1000,
        ),
    )

    min_words = max(
        50,
        target_words - 10,
    )

    max_words = target_words + 10

    # --------------------------------------------------------
    # TOKEN BUDGET
    # --------------------------------------------------------

    if target_words <= 150:

        answer_tokens = 2500

    elif target_words <= 250:

        answer_tokens = 3000

    elif target_words <= 500:

        answer_tokens = 4000

    else:

        answer_tokens = 5000

    answer_tokens = min(
        answer_tokens,
        MAX_COMPLETION_TOKENS,
    )

    # --------------------------------------------------------
    # GENERATION PROMPT
    # --------------------------------------------------------

    prompt = f"""
You are an expert {exam} Mains answer-writing mentor.

Generate a high-quality model answer.

EXAM:
{exam}

CATEGORY:
{category}

MARKS:
{marks}

TARGET WORDS:
{target_words}

LANGUAGE:
{language_name}

QUESTION:
{question}


IMPORTANT WORD LIMIT:

The COMPLETE answer must contain between
{min_words} and {max_words} words.

Target: approximately {target_words} words.

Do NOT stop before completing the conclusion.

Do NOT truncate the answer.

Do NOT leave a sentence unfinished.


STRUCTURE:

1. Introduction
2. Analytical body
3. Way forward
4. Conclusion


CONTENT RULES:

- Directly answer the question.
- Use UPSC/BPSC Mains style.
- Use concise analytical arguments.
- Use relevant Indian examples only if you are confident they are correct.
- Use constitutional provisions only if relevant and accurate.
- Do not invent statistics.
- Do not invent schemes.
- Do not invent government departments.
- Do not use fake abbreviations.
- Do not use uncertain scheme names.
- If an example is uncertain, omit it.
- Avoid repetition.
- Use grammatically correct {language_name}.
- Do not repeat the question.


IMPORTANT:

Do NOT add labels such as:

तर्क:
निष्कर्ष:
आगे का मार्ग:
Introduction:
Body:
Way Forward:
Conclusion:

The JSON fields already represent the sections.


RETURN ONLY JSON.

Do not return markdown.
Do not return ```json.
Do not return explanations.
Do not return reasoning.

JSON:

{{
    "introduction": "...",
    "body": "...",
    "way_forward": "...",
    "conclusion": "...",
    "key_points": [
        "...",
        "...",
        "..."
    ]
}}
"""

    # --------------------------------------------------------
    # FIRST GENERATION
    # --------------------------------------------------------

    data = generate_json(
        prompt,
        max_tokens=answer_tokens,
        temperature=0.10,
    )

    if not data:

        return {
            "answer": "",
            "introduction": "",
            "body": "",
            "way_forward": "",
            "conclusion": "",
            "key_points": [],
        }

    # --------------------------------------------------------
    # EXTRACT
    # --------------------------------------------------------

    introduction = _safe_string(
        data.get("introduction")
    )

    body = _safe_string(
        data.get("body")
    )

    way_forward = _safe_string(
        data.get("way_forward")
    )

    conclusion = _safe_string(
        data.get("conclusion")
    )

    key_points = _safe_list(
        data.get("key_points")
    )[:3]

    answer = _build_answer(
        introduction,
        body,
        way_forward,
        conclusion,
    )

    word_count = _word_count(answer)

    # --------------------------------------------------------
    # SECOND PASS IF WORD COUNT IS WRONG
    # --------------------------------------------------------

    if (
        word_count < min_words
        or word_count > max_words
    ):

        correction_prompt = f"""
You are an expert {exam} Mains answer editor.

Rewrite the following answer.

Question:
{question}

Target:
{target_words} words.

Allowed range:
{min_words} to {max_words} words.

Current answer:
{answer}

STRICT REQUIREMENTS:

1. Preserve the core argument.
2. Complete the conclusion.
3. Keep the answer within {min_words}-{max_words} words.
4. Do not invent facts.
5. Do not invent schemes.
6. Do not invent statistics.
7. Remove uncertain examples.
8. Use correct {language_name}.
9. Keep UPSC/BPSC Mains style.
10. Do not add headings or labels.

Return ONLY the final answer text.

No markdown.
No JSON.
No explanation.
"""

        corrected = generate_text(
            correction_prompt,
            max_tokens=answer_tokens,
            temperature=0.05,
        )

        corrected = corrected.strip()

        if corrected:

            corrected_count = _word_count(
                corrected
            )

            if (
                min_words
                <= corrected_count
                <= max_words
            ):

                answer = corrected

    # --------------------------------------------------------
    # FINAL SAFETY
    # --------------------------------------------------------

    final_word_count = _word_count(
        answer
    )

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    return {
        "answer": answer,
        "introduction": introduction,
        "body": body,
        "way_forward": way_forward,
        "conclusion": conclusion,
        "key_points": key_points,
        "word_count": final_word_count,
    }