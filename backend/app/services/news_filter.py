from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.news_scoring import calculate_news_score

logger = logging.getLogger("app.news_filter")


# ============================================================
# CONFIGURATION
# ============================================================

SUPPORTED_EXAMS = {"UPSC", "BPSC"}

DEFAULT_EXAM = "UPSC"
DEFAULT_CATEGORY = "General"

MIN_ACCEPT_SCORE = 20
MEDIUM_SCORE = 30
HIGH_SCORE = 50
CRITICAL_SCORE = 70

MAX_FINAL_SCORE = 100


# ============================================================
# CATEGORY CONSTANTS
# ============================================================

CATEGORY_GENERAL = "General"
CATEGORY_POLITY = "Polity & Governance"
CATEGORY_ECONOMY = "Economy"
CATEGORY_ENVIRONMENT = "Environment"
CATEGORY_SCIENCE = "Science & Technology"
CATEGORY_IR = "International Relations"
CATEGORY_HISTORY = "History & Culture"
CATEGORY_GEOGRAPHY = "Geography"
CATEGORY_SOCIAL = "Social Issues"
CATEGORY_AGRICULTURE = "Agriculture"
CATEGORY_HEALTH = "Health"
CATEGORY_EDUCATION = "Education"
CATEGORY_SECURITY = "Security"
CATEGORY_DISASTER = "Disaster"
CATEGORY_ETHICS = "Ethics"


ALL_CATEGORIES = {
    CATEGORY_GENERAL,
    CATEGORY_POLITY,
    CATEGORY_ECONOMY,
    CATEGORY_ENVIRONMENT,
    CATEGORY_SCIENCE,
    CATEGORY_IR,
    CATEGORY_HISTORY,
    CATEGORY_GEOGRAPHY,
    CATEGORY_SOCIAL,
    CATEGORY_AGRICULTURE,
    CATEGORY_HEALTH,
    CATEGORY_EDUCATION,
    CATEGORY_SECURITY,
    CATEGORY_DISASTER,
    CATEGORY_ETHICS,
}


# ============================================================
# CATEGORY KEYWORDS
# ============================================================

CATEGORY_KEYWORDS: dict[str, list[str]] = {

    CATEGORY_POLITY: [
        "government",
        "governance",
        "parliament",
        "cabinet",
        "ministry",
        "minister",
        "constitution",
        "constitutional",
        "supreme court",
        "high court",
        "election",
        "elections",
        "legislation",
        "legislature",
        "bill",
        "ordinance",
        "policy",
        "administration",
        "panchayat",
        "local government",
        "federalism",
        "judiciary",
        "executive",
    ],

    CATEGORY_ECONOMY: [
        "economy",
        "economic",
        "gdp",
        "inflation",
        "rbi",
        "reserve bank",
        "monetary policy",
        "fiscal policy",
        "budget",
        "union budget",
        "tax",
        "gst",
        "banking",
        "finance",
        "financial",
        "investment",
        "exports",
        "imports",
        "trade",
        "employment",
        "unemployment",
        "manufacturing",
        "infrastructure",
        "economic growth",
        "inclusive growth",
    ],

    CATEGORY_ENVIRONMENT: [
        "environment",
        "climate",
        "climate change",
        "global warming",
        "biodiversity",
        "forest",
        "forests",
        "wildlife",
        "conservation",
        "pollution",
        "emission",
        "emissions",
        "carbon",
        "wetland",
        "ecosystem",
        "ecological",
        "renewable energy",
        "solar energy",
        "national park",
        "wildlife sanctuary",
    ],

    CATEGORY_SCIENCE: [
        "science",
        "technology",
        "space",
        "isro",
        "satellite",
        "artificial intelligence",
        "ai",
        "quantum",
        "biotechnology",
        "research",
        "innovation",
        "nuclear",
        "semiconductor",
        "digital technology",
        "cyber technology",
        "5g",
        "6g",
        "robotics",
        "genomics",
    ],

    CATEGORY_IR: [
        "international",
        "international relations",
        "foreign policy",
        "diplomacy",
        "bilateral",
        "multilateral",
        "united nations",
        "g20",
        "g7",
        "brics",
        "india-us",
        "india us",
        "india china",
        "india russia",
        "india europe",
        "india japan",
        "india australia",
        "neighbouring countries",
        "neighboring countries",
        "geopolitical",
        "strategic partnership",
    ],

    CATEGORY_HISTORY: [
        "history",
        "historical",
        "heritage",
        "culture",
        "cultural",
        "archaeology",
        "monument",
        "museum",
        "civilization",
        "festival",
        "classical dance",
        "classical music",
        "heritage site",
        "unesco",
    ],

    CATEGORY_GEOGRAPHY: [
        "geography",
        "river",
        "rivers",
        "mountain",
        "mountains",
        "plateau",
        "monsoon",
        "rainfall",
        "earthquake",
        "ocean",
        "coast",
        "coastal",
        "soil",
        "climate zone",
        "geographical",
        "watershed",
        "glacier",
        "desert",
    ],

    CATEGORY_SOCIAL: [
        "social justice",
        "social welfare",
        "poverty",
        "inequality",
        "women",
        "woman",
        "child",
        "children",
        "tribal",
        "scheduled caste",
        "scheduled tribes",
        "minority",
        "inclusion",
        "social security",
        "marginalized",
        "marginalised",
        "gender",
        "disability",
    ],

    CATEGORY_AGRICULTURE: [
        "agriculture",
        "farmer",
        "farmers",
        "farming",
        "crop",
        "crops",
        "irrigation",
        "fertilizer",
        "fertiliser",
        "agricultural",
        "minimum support price",
        "msp",
        "agri",
        "foodgrain",
        "food grains",
        "agricultural policy",
        "kisan",
        "livestock",
        "fisheries",
    ],

    CATEGORY_HEALTH: [
        "health",
        "healthcare",
        "hospital",
        "disease",
        "public health",
        "vaccine",
        "vaccination",
        "medicine",
        "medical",
        "health ministry",
        "epidemic",
        "pandemic",
        "nutrition",
        "maternal health",
        "child health",
        "health policy",
    ],

    CATEGORY_EDUCATION: [
        "education",
        "school",
        "schools",
        "college",
        "university",
        "teacher",
        "teachers",
        "professor",
        "students",
        "student",
        "exam",
        "education department",
        "higher education",
        "school education",
        "education policy",
        "ugc",
        "ncert",
    ],

    CATEGORY_SECURITY: [
        "security",
        "national security",
        "internal security",
        "terrorism",
        "terrorist",
        "militant",
        "militancy",
        "insurgency",
        "border security",
        "cyber security",
        "cybersecurity",
        "defence",
        "defense",
        "armed forces",
        "army",
        "navy",
        "air force",
        "border",
        "counter terrorism",
        "counterterrorism",
    ],

    CATEGORY_DISASTER: [
        "disaster",
        "flood",
        "floods",
        "cyclone",
        "storm",
        "drought",
        "landslide",
        "earthquake",
        "disaster management",
        "relief",
        "rescue",
        "disaster response",
        "natural disaster",
        "heatwave",
        "heat wave",
    ],

    CATEGORY_ETHICS: [
        "ethics",
        "integrity",
        "accountability",
        "transparency",
        "corruption",
        "moral",
        "values",
        "conflict of interest",
        "whistleblower",
        "ethical governance",
        "probity",
    ],
}


# ============================================================
# EXAM KEYWORDS
# ============================================================

BPSC_KEYWORDS = [
    "bpsc",
    "bihar public service commission",
    "bihar government",
    "government of bihar",
    "bihar cabinet",
    "bihar assembly",
    "bihar budget",
    "bihar police",
    "bihar administration",
    "bihar scheme",
    "bihar yojana",
    "bihar government scheme",
    "bihar chief minister",
    "bihar cm",
    "bihar minister",
    "bihar department",
    "bihar state government",
]


UPSC_KEYWORDS = [
    "upsc",
    "union public service commission",
    "civil services",
    "civil services examination",
    "ias",
    "central government",
    "union government",
    "ministry of",
    "cabinet",
    "parliament",
    "supreme court",
    "constitutional",
    "rbi",
    "reserve bank",
    "climate change",
    "biodiversity",
    "international relations",
    "foreign policy",
    "united nations",
    "isro",
    "space mission",
    "national policy",
    "union budget",
]


BIHAR_KEYWORDS = [
    "bihar",
    "patna",
    "gaya",
    "bhagalpur",
    "muzaffarpur",
    "darbhanga",
    "purnia",
    "purnea",
    "mithila",
    "magadh",
    "nalanda",
    "vaishali",
    "bodh gaya",
    "champaran",
    "begusarai",
    "araria",
    "katihar",
    "kishanganj",
    "saharsa",
    "madhepura",
    "supaul",
    "samastipur",
    "siwan",
    "saran",
    "bhojpur",
    "rohtas",
    "buxar",
    "jamui",
    "nawada",
    "aurangabad bihar",
    "jehanabad",
    "arwal",
    "sheohar",
    "sitamarhi",
    "shivhar",
    "east champaran",
    "west champaran",
]


EMPLOYMENT_KEYWORDS = [
    "employment",
    "unemployment",
    "job",
    "jobs",
    "recruitment",
    "vacancy",
    "vacancies",
    "appointment",
    "job fair",
    "employment generation",
    "job opportunities",
    "labour reform",
    "labor reform",
]


# ============================================================
# PRIORITY KEYWORDS
# ============================================================

SECURITY_PRIORITY_KEYWORDS = (
    CATEGORY_KEYWORDS[CATEGORY_SECURITY]
)

EDUCATION_PRIORITY_KEYWORDS = (
    CATEGORY_KEYWORDS[CATEGORY_EDUCATION]
)

POLITY_PRIORITY_KEYWORDS = (
    CATEGORY_KEYWORDS[CATEGORY_POLITY]
)

AGRICULTURE_PRIORITY_KEYWORDS = (
    CATEGORY_KEYWORDS[CATEGORY_AGRICULTURE]
)


# ============================================================
# PRELIMS / MAINS KEYWORDS
# ============================================================

PRELIMS_KEYWORDS = [
    "scheme",
    "schemes",
    "government scheme",
    "welfare scheme",
    "yojana",
    "mission",
    "initiative",
    "index",
    "report",
    "rank",
    "ranking",
    "award",
    "appointment",
    "organization",
    "institution",
    "headquarters",
    "summit",
    "treaty",
    "convention",
    "species",
    "national park",
    "sanctuary",
    "river",
    "dam",
    "island",
    "space mission",
    "species",
    "constitutional amendment",
]


MAINS_KEYWORDS = [
    "policy",
    "reform",
    "governance",
    "challenges",
    "opportunities",
    "impact",
    "implications",
    "sustainable development",
    "social justice",
    "inequality",
    "climate change",
    "economic growth",
    "development",
    "federalism",
    "accountability",
    "transparency",
    "inclusive growth",
    "women empowerment",
    "structural reform",
    "governance reform",
]


BPSC_MAINS_KEYWORDS = [
    "bihar development",
    "bihar economy",
    "bihar governance",
    "bihar education",
    "bihar health",
    "bihar agriculture",
    "bihar employment",
    "bihar infrastructure",
    "bihar poverty",
    "bihar migration",
]


# ============================================================
# NOISE
# ============================================================

NOISE_KEYWORDS = [
    "celebrity",
    "bollywood gossip",
    "movie review",
    "film review",
    "entertainment",
    "viral video",
    "fashion",
    "lifestyle",
    "horoscope",
    "astrology",
    "cricket score",
    "match result",
    "football score",
    "wedding",
    "box office",
]


# ============================================================
# SAFE HELPERS
# ============================================================

def _text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


def _lower(value: Any) -> str:
    return _text(value).lower()


def _safe_int(
    value: Any,
    default: int = 0,
) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(
    value: Any,
    default: bool = False,
) -> bool:

    if isinstance(value, bool):
        return value

    if isinstance(value, str):

        value = value.strip().lower()

        if value in {
            "true",
            "1",
            "yes",
            "y",
            "on",
        }:
            return True

        if value in {
            "false",
            "0",
            "no",
            "n",
            "off",
        }:
            return False

    if isinstance(value, int):
        return bool(value)

    return default


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize_exam(
    exam: Any,
) -> Optional[str]:

    value = _lower(exam)

    if not value:
        return None

    aliases = {
        "upsc": "UPSC",
        "civil services": "UPSC",
        "civil services examination": "UPSC",
        "ias": "UPSC",

        "bpsc": "BPSC",
        "bihar public service commission": "BPSC",
    }

    normalized = aliases.get(value)

    if normalized:
        return normalized

    upper = value.upper()

    if upper in SUPPORTED_EXAMS:
        return upper

    return None


def _normalize_category(
    category: Any,
) -> Optional[str]:

    value = _text(category)

    if not value:
        return None

    aliases = {
        "general": CATEGORY_GENERAL,

        "polity": CATEGORY_POLITY,
        "governance": CATEGORY_POLITY,
        "polity & governance": CATEGORY_POLITY,

        "economy": CATEGORY_ECONOMY,
        "economic": CATEGORY_ECONOMY,

        "environment": CATEGORY_ENVIRONMENT,

        "science": CATEGORY_SCIENCE,
        "science & technology": CATEGORY_SCIENCE,
        "technology": CATEGORY_SCIENCE,

        "international": CATEGORY_IR,
        "international relations": CATEGORY_IR,
        "ir": CATEGORY_IR,

        "history": CATEGORY_HISTORY,
        "history & culture": CATEGORY_HISTORY,
        "culture": CATEGORY_HISTORY,

        "geography": CATEGORY_GEOGRAPHY,

        "social": CATEGORY_SOCIAL,
        "social issues": CATEGORY_SOCIAL,

        "agriculture": CATEGORY_AGRICULTURE,

        "health": CATEGORY_HEALTH,

        "education": CATEGORY_EDUCATION,

        "security": CATEGORY_SECURITY,
        "internal security": CATEGORY_SECURITY,

        "disaster": CATEGORY_DISASTER,
        "disaster management": CATEGORY_DISASTER,

        "ethics": CATEGORY_ETHICS,
    }

    normalized = aliases.get(
        value.lower(),
        value,
    )

    if normalized in ALL_CATEGORIES:
        return normalized

    return None


# ============================================================
# TEXT
# ============================================================

def _article_text(
    article: dict[str, Any],
) -> str:

    parts = [
        _text(article.get("title")),
        _text(article.get("description")),
        _text(article.get("content")),
        _text(article.get("source")),
        _text(article.get("category")),
        _text(article.get("exam")),
    ]

    return " ".join(
        part
        for part in parts
        if part
    ).lower()


def _title_text(
    article: dict[str, Any],
) -> str:

    return _lower(
        article.get("title")
    )


def _title_description(
    article: dict[str, Any],
) -> str:

    return " ".join(
        [
            _lower(article.get("title")),
            _lower(article.get("description")),
        ]
    )


# ============================================================
# KEYWORD MATCHING
# ============================================================

def _keyword_matches(
    text: str,
    keywords: list[str],
) -> list[str]:

    if not text:
        return []

    normalized_text = text.lower()

    matches: list[str] = []

    for raw_keyword in keywords:

        keyword = _text(
            raw_keyword
        ).lower()

        if not keyword:
            continue

        if " " in keyword:

            if keyword in normalized_text:
                matches.append(keyword)

        else:

            pattern = (
                r"\b"
                + re.escape(keyword)
                + r"\b"
            )

            if re.search(
                pattern,
                normalized_text,
                flags=re.IGNORECASE,
            ):
                matches.append(keyword)

    return matches


def _has_any_keyword(
    text: str,
    keywords: list[str],
) -> bool:

    return bool(
        _keyword_matches(
            text,
            keywords,
        )
    )


# ============================================================
# CATEGORY SCORING
# ============================================================

def _category_scores(
    text: str,
) -> dict[str, int]:

    scores: dict[str, int] = {}

    for category, keywords in CATEGORY_KEYWORDS.items():

        matches = _keyword_matches(
            text,
            keywords,
        )

        score = 0

        for match in matches:

            if " " in match:
                score += 3
            else:
                score += 1

        scores[category] = score

    return scores


# ============================================================
# CATEGORY CLASSIFICATION
# ============================================================

def classify_category(
    article: dict[str, Any],
) -> str:

    if not isinstance(article, dict):
        return CATEGORY_GENERAL

    # --------------------------------------------------------
    # 1. Preserve explicit valid category
    # --------------------------------------------------------

    existing = _normalize_category(
        article.get("category")
    )

    if existing and existing != CATEGORY_GENERAL:
        return existing

    # --------------------------------------------------------
    # 2. Text
    # --------------------------------------------------------

    text = " ".join(
        [
            _lower(article.get("title")),
            _lower(article.get("description")),
            _lower(article.get("content")),
        ]
    )

    # --------------------------------------------------------
    # 3. Hard priority categories
    # --------------------------------------------------------

    if _has_any_keyword(
        text,
        SECURITY_PRIORITY_KEYWORDS,
    ):
        return CATEGORY_SECURITY

    education_matches = _keyword_matches(
        text,
        EDUCATION_PRIORITY_KEYWORDS,
    )

    if education_matches:

        if _has_any_keyword(
            text,
            [
                "teacher",
                "teachers",
                "teacher recruitment",
                "teacher vacancy",
                "teacher vacancies",
                "teacher appointment",
                "assistant professor",
                "professor",
                "education department",
            ],
        ):
            return CATEGORY_EDUCATION

    if _has_any_keyword(
        text,
        POLITY_PRIORITY_KEYWORDS,
    ):
        return CATEGORY_POLITY

    # --------------------------------------------------------
    # 4. Score categories
    # --------------------------------------------------------

    scores = _category_scores(text)

    best_category = CATEGORY_GENERAL
    best_score = 0

    for category, score in scores.items():

        if category == CATEGORY_GENERAL:
            continue

        if score > best_score:

            best_category = category
            best_score = score

    if best_score > 0:
        return best_category

    return CATEGORY_GENERAL


# ============================================================
# EXAM CLASSIFICATION
# ============================================================

def classify_exam(
    article: dict[str, Any],
) -> tuple[str, int, int]:

    text = _article_text(article)

    bpsc_matches = _keyword_matches(
        text,
        BPSC_KEYWORDS,
    )

    upsc_matches = _keyword_matches(
        text,
        UPSC_KEYWORDS,
    )

    bihar_matches = _keyword_matches(
        text,
        BIHAR_KEYWORDS,
    )

    bpsc_score = min(
        len(bpsc_matches) * 15,
        100,
    )

    upsc_score = min(
        len(upsc_matches) * 15,
        100,
    )

    existing_exam = _normalize_exam(
        article.get("exam")
    )

    # --------------------------------------------------------
    # Explicit exam should be respected
    # --------------------------------------------------------

    if existing_exam == "BPSC":

        return (
            "BPSC",
            max(bpsc_score, 20),
            upsc_score,
        )

    if existing_exam == "UPSC":

        return (
            "UPSC",
            bpsc_score,
            max(upsc_score, 20),
        )

    # --------------------------------------------------------
    # BPSC stronger
    # --------------------------------------------------------

    if bpsc_score > upsc_score and bpsc_score > 0:

        return (
            "BPSC",
            max(bpsc_score, 20),
            upsc_score,
        )

    # --------------------------------------------------------
    # UPSC stronger
    # --------------------------------------------------------

    if upsc_score > bpsc_score and upsc_score > 0:

        return (
            "UPSC",
            bpsc_score,
            max(upsc_score, 20),
        )

    # --------------------------------------------------------
    # Both matched
    # --------------------------------------------------------

    if bpsc_score > 0 and upsc_score > 0:

        if bihar_matches:

            return (
                "BPSC",
                max(bpsc_score, 25),
                upsc_score,
            )

        return (
            "UPSC",
            bpsc_score,
            max(upsc_score, 20),
        )

    # --------------------------------------------------------
    # Bihar fallback
    # --------------------------------------------------------

    if bihar_matches:

        return (
            "BPSC",
            max(bpsc_score, 20),
            upsc_score,
        )

    # --------------------------------------------------------
    # Default
    # --------------------------------------------------------

    return (
        "UPSC",
        bpsc_score,
        upsc_score,
    )


# ============================================================
# BIHAR CLASSIFICATION
# ============================================================

def classify_bihar(
    article: dict[str, Any],
) -> tuple[bool, int]:

    text = _article_text(article)

    matches = _keyword_matches(
        text,
        BIHAR_KEYWORDS,
    )

    score = min(
        len(matches) * 20,
        100,
    )

    existing = _safe_bool(
        article.get("bihar_relevant"),
        False,
    )

    existing_score = _safe_int(
        article.get("bihar_score"),
        0,
    )

    if matches:

        return (
            True,
            max(
                score,
                existing_score,
                20,
            ),
        )

    if existing:

        return (
            True,
            max(
                existing_score,
                20,
            ),
        )

    return (
        False,
        existing_score,
    )


# ============================================================
# EXAM RELEVANCE
# ============================================================

def _exam_relevance_points(
    article: dict[str, Any],
    exam: str,
) -> int:

    text = _article_text(article)

    score = 0

    if exam == "BPSC":

        bpsc_matches = _keyword_matches(
            text,
            BPSC_KEYWORDS,
        )

        bihar_matches = _keyword_matches(
            text,
            BIHAR_KEYWORDS,
        )

        score += min(
            len(bpsc_matches) * 12,
            40,
        )

        score += min(
            len(bihar_matches) * 5,
            25,
        )

        if _safe_bool(
            article.get("bihar_relevant"),
            False,
        ):
            score += 10

        # Bihar governance/economy/education etc.
        if _has_any_keyword(
            text,
            [
                "bihar government",
                "government of bihar",
                "bihar budget",
                "bihar assembly",
                "bihar economy",
                "bihar education",
                "bihar health",
                "bihar agriculture",
                "bihar development",
            ],
        ):
            score += 10

    else:

        upsc_matches = _keyword_matches(
            text,
            UPSC_KEYWORDS,
        )

        score += min(
            len(upsc_matches) * 10,
            40,
        )

        if _has_any_keyword(
            text,
            POLITY_PRIORITY_KEYWORDS
            + CATEGORY_KEYWORDS.get(
                CATEGORY_ECONOMY,
                [],
            )
            + CATEGORY_KEYWORDS.get(
                CATEGORY_ENVIRONMENT,
                [],
            )
            + CATEGORY_KEYWORDS.get(
                CATEGORY_SCIENCE,
                [],
            )
            + CATEGORY_KEYWORDS.get(
                CATEGORY_IR,
                [],
            )
            + CATEGORY_KEYWORDS.get(
                CATEGORY_SECURITY,
                [],
            ),
        ):
            score += 5

    return min(
        score,
        60,
    )


# ============================================================
# CATEGORY RELEVANCE
# ============================================================

def _category_relevance_points(
    article: dict[str, Any],
    category: str,
) -> int:

    text = _article_text(article)

    keywords = CATEGORY_KEYWORDS.get(
        category,
        [],
    )

    matches = _keyword_matches(
        text,
        keywords,
    )

    if not matches:
        return 0

    score = 0

    for keyword in matches:

        if " " in keyword:
            score += 5
        else:
            score += 2

    return min(
        score,
        30,
    )


# ============================================================
# BPSC BONUS
# ============================================================

def _bpsc_relevance_bonus(
    article: dict[str, Any],
) -> int:

    text = _article_text(article)

    score = 0

    if _has_any_keyword(
        text,
        BIHAR_KEYWORDS,
    ):
        score += 10

    if _has_any_keyword(
        text,
        POLITY_PRIORITY_KEYWORDS,
    ):
        score += 5

    if _has_any_keyword(
        text,
        EMPLOYMENT_KEYWORDS,
    ):
        score += 5

    if _has_any_keyword(
        text,
        BPSC_KEYWORDS,
    ):
        score += 10

    return min(
        score,
        25,
    )


# ============================================================
# IMPORTANCE
# ============================================================

def _importance_points(
    article: dict[str, Any],
) -> int:

    importance = _lower(
        article.get("importance")
    )

    if importance == "critical":
        return 10

    if importance == "high":
        return 7

    if importance == "medium":
        return 4

    return 0


# ============================================================
# EXISTING RELEVANCE
# ============================================================

def _existing_relevance_points(
    article: dict[str, Any],
) -> int:

    score = 0

    exam_relevance = _lower(
        article.get("exam_relevance")
    )

    if exam_relevance == "high":
        score += 10

    elif exam_relevance == "medium":
        score += 5

    bpsc_relevance = _lower(
        article.get("bpsc_relevance")
    )

    if bpsc_relevance == "high":
        score += 8

    elif bpsc_relevance == "medium":
        score += 4

    upsc_relevance = _lower(
        article.get("upsc_relevance")
    )

    if upsc_relevance == "high":
        score += 8

    elif upsc_relevance == "medium":
        score += 4

    return min(
        score,
        20,
    )


# ============================================================
# FALLBACK RELEVANCE SCORE
# ============================================================

def calculate_relevance_score(
    article: dict[str, Any],
    exam: str,
    category: str,
    bihar_relevant: bool,
) -> int:

    exam = (
        _normalize_exam(exam)
        or DEFAULT_EXAM
    )

    normalized_category = (
        _normalize_category(category)
        or CATEGORY_GENERAL
    )

    score = 0

    score += _exam_relevance_points(
        article,
        exam,
    )

    if bihar_relevant:

        score += (
            20
            if exam == "BPSC"
            else 10
        )

    score += _category_relevance_points(
        article,
        normalized_category,
    )

    if exam == "BPSC":

        score += _bpsc_relevance_bonus(
            article
        )

    score += _existing_relevance_points(
        article
    )

    score += _importance_points(
        article
    )

    old_score = _safe_int(
        article.get("relevance_score"),
        0,
    )

    score = max(
        score,
        min(old_score, 20),
    )

    return min(
        score,
        100,
    )


# ============================================================
# PRELIMS / MAINS
# ============================================================

def classify_prelims_mains(
    article: dict[str, Any],
) -> tuple[bool, bool]:

    text = _title_description(article)
    full_text = _article_text(article)

    prelims_matches = _keyword_matches(
        text,
        PRELIMS_KEYWORDS,
    )

    if not prelims_matches:

        prelims_matches = _keyword_matches(
            full_text,
            PRELIMS_KEYWORDS,
        )

    mains_matches = _keyword_matches(
        text,
        MAINS_KEYWORDS,
    )

    if not mains_matches:

        mains_matches = _keyword_matches(
            full_text,
            MAINS_KEYWORDS,
        )

    exam = _normalize_exam(
        article.get("exam")
    )

    if exam == "BPSC":

        bpsc_mains_matches = _keyword_matches(
            full_text,
            BPSC_MAINS_KEYWORDS,
        )

        mains_matches.extend(
            bpsc_mains_matches
        )

    category = _normalize_category(
        article.get("category")
    )

    if (
        _safe_bool(
            article.get("bihar_relevant"),
            False,
        )
        and category in {
            CATEGORY_POLITY,
            CATEGORY_ECONOMY,
            CATEGORY_EDUCATION,
            CATEGORY_SECURITY,
            CATEGORY_ENVIRONMENT,
            CATEGORY_AGRICULTURE,
            CATEGORY_HEALTH,
        }
    ):
        prelims_matches.append(
            "bihar-current-affair"
        )

    if _has_any_keyword(
        full_text,
        [
            "scheme",
            "schemes",
            "government scheme",
            "welfare scheme",
            "yojana",
        ],
    ):
        prelims_matches.append("scheme")

    if _has_any_keyword(
        full_text,
        EMPLOYMENT_KEYWORDS,
    ):
        mains_matches.append("employment")

    return (
        bool(prelims_matches),
        bool(mains_matches),
    )


# ============================================================
# NOISE DETECTION
# ============================================================

def detect_noise(
    article: dict[str, Any],
) -> bool:

    text = _article_text(article)

    matches = _keyword_matches(
        text,
        NOISE_KEYWORDS,
    )

    if not matches:
        return False

    # Strong exam relevance overrides noise.
    exam = _normalize_exam(
        article.get("exam")
    )

    important_exam_matches = _keyword_matches(
        text,
        BPSC_KEYWORDS
        + UPSC_KEYWORDS
        + BIHAR_KEYWORDS,
    )

    if important_exam_matches:
        return False

    if exam in SUPPORTED_EXAMS:
        relevance_score = _safe_int(
            article.get("relevance_score"),
            0,
        )

        if relevance_score >= 30:
            return False

    if _has_any_keyword(
        text,
        POLITY_PRIORITY_KEYWORDS,
    ):
        return False

    if _has_any_keyword(
        text,
        [
            "government",
            "ministry",
            "policy",
            "scheme",
            "parliament",
            "supreme court",
            "high court",
        ],
    ):
        return False

    return True


# ============================================================
# PROVIDER SCORE
# ============================================================

def calculate_provider_bonus(
    article: dict[str, Any],
) -> int:

    query_score = max(
        _safe_int(
            article.get("query_score"),
            0,
        ),
        0,
    )

    engine_score = max(
        _safe_int(
            article.get("engine_score"),
            0,
        ),
        0,
    )

    freshness_score = max(
        _safe_int(
            article.get("freshness_score"),
            0,
        ),
        0,
    )

    provider_score = (
        query_score
        + engine_score
        + freshness_score
    )

    return min(
        provider_score,
        25,
    )


# ============================================================
# FINAL SCORE
# ============================================================

def calculate_final_score(
    article: dict[str, Any],
    relevance_score: int,
) -> int:

    provider_bonus = calculate_provider_bonus(
        article
    )

    return min(
        max(
            relevance_score,
            0,
        )
        + provider_bonus,
        MAX_FINAL_SCORE,
    )


# ============================================================
# LABELS
# ============================================================

def relevance_label(
    score: int,
) -> str:

    score = _safe_int(
        score,
        0,
    )

    if score >= HIGH_SCORE:
        return "High"

    if score >= MEDIUM_SCORE:
        return "Medium"

    return "Low"


def importance_label(
    score: int,
) -> str:

    score = _safe_int(
        score,
        0,
    )

    if score >= CRITICAL_SCORE:
        return "Critical"

    if score >= HIGH_SCORE:
        return "High"

    if score >= MEDIUM_SCORE:
        return "Medium"

    return "Low"


# ============================================================
# CLASSIFY ARTICLE
# ============================================================

def classify_news(
    article: dict[str, Any],
) -> dict[str, Any]:

    if not isinstance(article, dict):
        return {}

    result = dict(article)

    # --------------------------------------------------------
    # Normalize text
    # --------------------------------------------------------

    for field in [
        "title",
        "description",
        "content",
        "source",
    ]:

        result[field] = _text(
            result.get(field)
        )

    # --------------------------------------------------------
    # Exam
    # --------------------------------------------------------

    exam, bpsc_score, upsc_score = classify_exam(
        result
    )

    result["exam"] = exam

    result["bpsc_score"] = max(
        bpsc_score,
        _safe_int(
            result.get("bpsc_score"),
            0,
        ),
    )

    result["upsc_score"] = max(
        upsc_score,
        _safe_int(
            result.get("upsc_score"),
            0,
        ),
    )

    # --------------------------------------------------------
    # Category
    # --------------------------------------------------------

    category = classify_category(
        result
    )

    result["category"] = category

    # --------------------------------------------------------
    # Bihar
    # --------------------------------------------------------

    (
        bihar_relevant,
        bihar_score,
    ) = classify_bihar(
        result
    )

    result["bihar_relevant"] = (
        bihar_relevant
    )

    result["bihar_score"] = (
        bihar_score
    )

    # --------------------------------------------------------
    # News scoring engine
    # --------------------------------------------------------

    scoring_succeeded = False

    try:

        scoring = calculate_news_score(
            result,
            exam=exam,
        )

        if isinstance(scoring, dict):

            result.update(scoring)
            scoring_succeeded = True

    except Exception:

        logger.exception(
            "calculate_news_score failed"
        )

    # --------------------------------------------------------
    # Fallback relevance
    # --------------------------------------------------------

    relevance_score = _safe_int(
        result.get("relevance_score"),
        0,
    )

    fallback_relevance = calculate_relevance_score(
        result,
        exam=exam,
        category=category,
        bihar_relevant=bihar_relevant,
    )

    # Never allow an invalid/zero scoring-engine
    # result to destroy useful classifier relevance.
    if relevance_score <= 0:

        relevance_score = fallback_relevance

    elif not scoring_succeeded:

        relevance_score = max(
            relevance_score,
            fallback_relevance,
        )

    result["relevance_score"] = min(
        max(relevance_score, 0),
        100,
    )

    # --------------------------------------------------------
    # Final score
    # --------------------------------------------------------

    existing_final = _safe_int(
        result.get("final_score"),
        0,
    )

    fallback_final = calculate_final_score(
        result,
        result["relevance_score"],
    )

    if existing_final <= 0:

        final_score = fallback_final

    else:

        final_score = max(
            existing_final,
            min(
                fallback_final,
                100,
            ),
        )

    result["final_score"] = min(
        max(final_score, 0),
        MAX_FINAL_SCORE,
    )

    # --------------------------------------------------------
    # Prelims / Mains
    # --------------------------------------------------------

    (
        prelims_relevant,
        mains_relevant,
    ) = classify_prelims_mains(
        result
    )

    result["prelims_relevant"] = (
        prelims_relevant
    )

    result["mains_relevant"] = (
        mains_relevant
    )

    # --------------------------------------------------------
    # Syllabus
    # --------------------------------------------------------

    existing_syllabus = result.get(
        "syllabus"
    )

    if not isinstance(
        existing_syllabus,
        dict,
    ):
        existing_syllabus = {}

    prelims_syllabus = existing_syllabus.get(
        "prelims",
        [],
    )

    mains_syllabus = existing_syllabus.get(
        "mains",
        [],
    )

    if not isinstance(
        prelims_syllabus,
        list,
    ):
        prelims_syllabus = []

    if not isinstance(
        mains_syllabus,
        list,
    ):
        mains_syllabus = []

    prelims_syllabus = list(
        dict.fromkeys(
            prelims_syllabus
        )
    )

    mains_syllabus = list(
        dict.fromkeys(
            mains_syllabus
        )
    )

    if prelims_relevant:

        if category not in prelims_syllabus:
            prelims_syllabus.append(
                category
            )

    if mains_relevant:

        if category not in mains_syllabus:
            mains_syllabus.append(
                category
            )

    result["syllabus"] = {
        "prelims": prelims_syllabus,
        "mains": mains_syllabus,
    }

    # --------------------------------------------------------
    # Relevance
    # --------------------------------------------------------

    result["exam_relevance"] = relevance_label(
        result["relevance_score"]
    )

    # --------------------------------------------------------
    # Exam-specific relevance
    # --------------------------------------------------------

    if exam == "BPSC":

        if (
            bihar_relevant
            and result["relevance_score"] >= 40
        ):
            result["bpsc_relevance"] = "High"

        elif result["relevance_score"] >= 30:
            result["bpsc_relevance"] = "High"

        elif result["relevance_score"] >= 20:
            result["bpsc_relevance"] = "Medium"

        else:
            result["bpsc_relevance"] = "Low"

        result["upsc_relevance"] = "Low"

    else:

        if result["relevance_score"] >= 40:
            result["upsc_relevance"] = "High"

        elif result["relevance_score"] >= 20:
            result["upsc_relevance"] = "Medium"

        else:
            result["upsc_relevance"] = "Low"

        result["bpsc_relevance"] = "Low"

    # --------------------------------------------------------
    # Importance
    # --------------------------------------------------------

    result["importance"] = importance_label(
        result["final_score"]
    )

    # --------------------------------------------------------
    # Noise
    # --------------------------------------------------------

    result["is_noise"] = detect_noise(
        result
    )

    # --------------------------------------------------------
    # Provider scores
    # --------------------------------------------------------

    result["query_score"] = _safe_int(
        result.get("query_score"),
        0,
    )

    result["engine_score"] = _safe_int(
        result.get("engine_score"),
        0,
    )

    result["freshness_score"] = _safe_int(
        result.get("freshness_score"),
        0,
    )

    return result


# ============================================================
# CLASSIFY LIST
# ============================================================

def classify_news_list(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    if not articles:
        return []

    classified: list[dict[str, Any]] = []

    for article in articles:

        try:

            item = classify_news(
                article
            )

            if item:
                classified.append(item)

        except Exception:

            logger.exception(
                "Failed to classify article: %s",
                (
                    article.get("title")
                    if isinstance(article, dict)
                    else None
                ),
            )

    return classified


# ============================================================
# MATCH EXAM
# ============================================================

def _matches_exam(
    article: dict[str, Any],
    exam: Optional[str],
) -> bool:

    if not exam:
        return True

    normalized_exam = _normalize_exam(
        exam
    )

    if not normalized_exam:
        return True

    article_exam = _normalize_exam(
        article.get("exam")
    )

    text = _article_text(article)

    relevance_score = _safe_int(
        article.get("relevance_score"),
        0,
    )

    # --------------------------------------------------------
    # BPSC
    # --------------------------------------------------------

    if normalized_exam == "BPSC":

        if article_exam == "BPSC":
            return True

        if _has_any_keyword(
            text,
            BPSC_KEYWORDS,
        ):
            return True

        if _safe_bool(
            article.get("bihar_relevant"),
            False,
        ):
            return True

        if _has_any_keyword(
            text,
            BIHAR_KEYWORDS,
        ):
            return True

        if (
            relevance_score >= 20
            and _has_any_keyword(
                text,
                POLITY_PRIORITY_KEYWORDS
                + EMPLOYMENT_KEYWORDS,
            )
            and _has_any_keyword(
                text,
                BIHAR_KEYWORDS,
            )
        ):
            return True

        return False

    # --------------------------------------------------------
    # UPSC
    # --------------------------------------------------------

    if normalized_exam == "UPSC":

        if article_exam == "UPSC":
            return True

        if _has_any_keyword(
            text,
            UPSC_KEYWORDS,
        ):
            return True

        if relevance_score >= 20:
            return True

        if _has_any_keyword(
            text,
            POLITY_PRIORITY_KEYWORDS
            + CATEGORY_KEYWORDS.get(
                CATEGORY_ECONOMY,
                [],
            )
            + CATEGORY_KEYWORDS.get(
                CATEGORY_ENVIRONMENT,
                [],
            )
            + CATEGORY_KEYWORDS.get(
                CATEGORY_SCIENCE,
                [],
            )
            + CATEGORY_KEYWORDS.get(
                CATEGORY_IR,
                [],
            )
            + CATEGORY_KEYWORDS.get(
                CATEGORY_SECURITY,
                [],
            ),
        ):
            return True

        return False

    return False


# ============================================================
# MATCH CATEGORY
# ============================================================

def _matches_category(
    article: dict[str, Any],
    category: Optional[str],
) -> bool:

    if not category:
        return True

    normalized_category = _normalize_category(
        category
    )

    if not normalized_category:
        return True

    article_category = _normalize_category(
        article.get("category")
    )

    if article_category == normalized_category:
        return True

    calculated_category = classify_category(
        article
    )

    return (
        calculated_category
        == normalized_category
    )


# ============================================================
# MATCH BIHAR
# ============================================================

def _matches_bihar(
    article: dict[str, Any],
) -> bool:

    if _safe_bool(
        article.get("bihar_relevant"),
        False,
    ):
        return True

    text = _article_text(article)

    return _has_any_keyword(
        text,
        BIHAR_KEYWORDS,
    )


# ============================================================
# MATCH LANGUAGE
# ============================================================

def _matches_language(
    article: dict[str, Any],
    language: Optional[str],
) -> bool:

    if not language:
        return True

    requested = _lower(
        language
    )

    actual = _lower(
        article.get("language")
    )

    # Provider may not provide language.
    if not actual:
        return True

    aliases = {
        "english": "en",
        "en": "en",

        "hindi": "hi",
        "hi": "hi",

        "bengali": "bn",
        "bn": "bn",

        "marathi": "mr",
        "mr": "mr",

        "tamil": "ta",
        "ta": "ta",

        "telugu": "te",
        "te": "te",
    }

    requested = aliases.get(
        requested,
        requested,
    )

    actual = aliases.get(
        actual,
        actual,
    )

    return requested == actual


# ============================================================
# FILTER NEWS
# ============================================================

def filter_news(
    articles: list[dict[str, Any]],
    min_score: int = MIN_ACCEPT_SCORE,
    exam: Optional[str] = None,
    category: Optional[str] = None,
    bihar_only: bool = False,
    language: Optional[str] = None,
    already_classified: bool = False,
) -> list[dict[str, Any]]:

    if not articles:
        return []

    normalized_exam = (
        _normalize_exam(exam)
        if exam
        else None
    )

    normalized_category = (
        _normalize_category(category)
        if category
        else None
    )

    output: list[dict[str, Any]] = []

    for original_article in articles:

        if not isinstance(
            original_article,
            dict,
        ):
            continue

        # ----------------------------------------------------
        # Classification
        # ----------------------------------------------------

        if already_classified:

            article = dict(
                original_article
            )

            required_fields = {
                "final_score",
                "relevance_score",
                "category",
                "exam",
                "bihar_relevant",
                "prelims_relevant",
                "mains_relevant",
            }

            if not required_fields.issubset(
                article.keys()
            ):
                article = classify_news(
                    article
                )

        else:

            article = classify_news(
                original_article
            )

        if not article:
            continue

        # ----------------------------------------------------
        # Noise
        # ----------------------------------------------------

        if _safe_bool(
            article.get("is_noise"),
            False,
        ):
            continue

        # ----------------------------------------------------
        # Language
        # ----------------------------------------------------

        if not _matches_language(
            article,
            language,
        ):
            continue

        # ----------------------------------------------------
        # Exam
        # ----------------------------------------------------

        if not _matches_exam(
            article,
            normalized_exam,
        ):
            continue

        # ----------------------------------------------------
        # Category
        # ----------------------------------------------------

        if not _matches_category(
            article,
            normalized_category,
        ):
            continue

        # ----------------------------------------------------
        # Bihar
        # ----------------------------------------------------

        if bihar_only:

            if not _matches_bihar(
                article
            ):
                continue

        # ----------------------------------------------------
        # Score
        # ----------------------------------------------------

        final_score = _safe_int(
            article.get("final_score"),
            0,
        )

        relevance_score = _safe_int(
            article.get("relevance_score"),
            0,
        )

        effective_score = max(
            final_score,
            relevance_score,
        )

        if effective_score < min_score:
            continue

        output.append(
            article
        )

    return output


# ============================================================
# PUBLISHED TIMESTAMP
# ============================================================

def _published_timestamp(
    article: dict[str, Any],
) -> float:

    value = article.get(
        "published_at"
    )

    if isinstance(
        value,
        datetime,
    ):

        dt = value

    elif isinstance(
        value,
        str,
    ):

        raw = value.strip()

        if not raw:
            return 0.0

        try:

            if raw.endswith("Z"):
                raw = (
                    raw[:-1]
                    + "+00:00"
                )

            dt = datetime.fromisoformat(
                raw
            )

        except ValueError:
            return 0.0

    else:
        return 0.0

    if dt.tzinfo is None:

        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.timestamp()


# ============================================================
# RANK NEWS
# ============================================================

def rank_news(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    if not articles:
        return []

    def sort_key(
        article: dict[str, Any],
    ):

        final_score = _safe_int(
            article.get("final_score"),
            0,
        )

        relevance_score = _safe_int(
            article.get("relevance_score"),
            0,
        )

        importance = _lower(
            article.get("importance")
        )

        importance_score = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
        }.get(
            importance,
            0,
        )

        bihar_score = _safe_int(
            article.get("bihar_score"),
            0,
        )

        return (
            final_score,
            relevance_score,
            importance_score,
            bihar_score,
            _published_timestamp(article),
        )

    return sorted(
        articles,
        key=sort_key,
        reverse=True,
    )


# ============================================================
# URL NORMALIZATION
# ============================================================

def _normalize_url(
    value: Any,
) -> str:

    url = _text(value).lower()

    if not url:
        return ""

    url = re.sub(
        r"[?&](utm_[^=&]+|fbclid|gclid)=[^&]*",
        "",
        url,
    )

    url = re.sub(
        r"[?&]$",
        "",
        url,
    )

    return url.rstrip(
        " /.,;:"
    )


# ============================================================
# TITLE NORMALIZATION
# ============================================================

def _normalize_title(
    value: Any,
) -> str:

    text = _lower(value)

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# ============================================================
# DEDUP KEY
# ============================================================

def article_dedup_key(
    article: dict[str, Any],
) -> str:

    url = _normalize_url(
        article.get("url")
    )

    if url:
        return "url:" + url

    title = _normalize_title(
        article.get("title")
    )

    if title:
        return "title:" + title

    article_id = _text(
        article.get("id")
    )

    if article_id:
        return "id:" + article_id

    return ""


# ============================================================
# DEDUPLICATE
# ============================================================

def deduplicate_news(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    if not articles:
        return []

    unique: list[dict[str, Any]] = []
    seen: set[str] = set()

    for article in articles:

        if not isinstance(
            article,
            dict,
        ):
            continue

        key = article_dedup_key(
            article
        )

        if not key:

            unique.append(
                article
            )

            continue

        if key in seen:
            continue

        seen.add(key)

        unique.append(
            article
        )

    return unique


# ============================================================
# DISTRIBUTION
# ============================================================

def category_distribution(
    articles: list[dict[str, Any]],
) -> dict[str, int]:

    distribution: dict[str, int] = {}

    for article in articles:

        category = (
            _normalize_category(
                article.get("category")
            )
            or CATEGORY_GENERAL
        )

        distribution[category] = (
            distribution.get(category, 0)
            + 1
        )

    return distribution


def exam_distribution(
    articles: list[dict[str, Any]],
) -> dict[str, int]:

    distribution: dict[str, int] = {}

    for article in articles:

        exam = _normalize_exam(
            article.get("exam")
        )

        if exam not in SUPPORTED_EXAMS:
            exam = DEFAULT_EXAM

        distribution[exam] = (
            distribution.get(exam, 0)
            + 1
        )

    return distribution


def score_distribution(
    articles: list[dict[str, Any]],
) -> dict[str, int]:

    distribution = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for article in articles:

        score = _safe_int(
            article.get("final_score"),
            0,
        )

        if score >= CRITICAL_SCORE:
            distribution["critical"] += 1

        elif score >= HIGH_SCORE:
            distribution["high"] += 1

        elif score >= MEDIUM_SCORE:
            distribution["medium"] += 1

        else:
            distribution["low"] += 1

    return distribution


# ============================================================
# DEBUG
# ============================================================

def debug_article(
    article: dict[str, Any],
) -> dict[str, Any]:

    classified = classify_news(
        article
    )

    return {
        "title": classified.get("title"),
        "exam": classified.get("exam"),
        "category": classified.get("category"),

        "bihar_relevant": classified.get(
            "bihar_relevant"
        ),

        "bihar_score": classified.get(
            "bihar_score"
        ),

        "bpsc_score": classified.get(
            "bpsc_score"
        ),

        "upsc_score": classified.get(
            "upsc_score"
        ),

        "relevance_score": classified.get(
            "relevance_score"
        ),

        "final_score": classified.get(
            "final_score"
        ),

        "exam_relevance": classified.get(
            "exam_relevance"
        ),

        "bpsc_relevance": classified.get(
            "bpsc_relevance"
        ),

        "upsc_relevance": classified.get(
            "upsc_relevance"
        ),

        "prelims_relevant": classified.get(
            "prelims_relevant"
        ),

        "mains_relevant": classified.get(
            "mains_relevant"
        ),

        "importance": classified.get(
            "importance"
        ),

        "is_noise": classified.get(
            "is_noise"
        ),

        "query_score": classified.get(
            "query_score"
        ),

        "engine_score": classified.get(
            "engine_score"
        ),

        "freshness_score": classified.get(
            "freshness_score"
        ),
    }


# ============================================================
# VALIDATE
# ============================================================

def validate_article(
    article: dict[str, Any],
) -> bool:

    if not isinstance(
        article,
        dict,
    ):
        return False

    title = _text(
        article.get("title")
    )

    description = _text(
        article.get("description")
    )

    content = _text(
        article.get("content")
    )

    return bool(
        title
        or description
        or content
    )


# ============================================================
# CLEAN
# ============================================================

def clean_article(
    article: dict[str, Any],
) -> dict[str, Any]:

    if not isinstance(
        article,
        dict,
    ):
        return {}

    result = dict(article)

    for field in [
        "title",
        "description",
        "content",
        "source",
        "url",
        "image_url",
        "language",
    ]:

        if field in result:

            result[field] = _text(
                result[field]
            )

    return result


# ============================================================
# PROCESS NEWS
# ============================================================

def process_news(
    articles: list[dict[str, Any]],
    exam: Optional[str] = None,
    category: Optional[str] = None,
    bihar_only: bool = False,
    min_score: int = MIN_ACCEPT_SCORE,
    language: Optional[str] = None,
) -> list[dict[str, Any]]:

    if not articles:
        return []

    cleaned: list[dict[str, Any]] = []

    for article in articles:

        if not validate_article(article):
            continue

        cleaned.append(
            clean_article(article)
        )

    classified = classify_news_list(
        cleaned
    )

    classified = deduplicate_news(
        classified
    )

    filtered = filter_news(
        classified,
        min_score=min_score,
        exam=exam,
        category=category,
        bihar_only=bihar_only,
        language=language,
        already_classified=True,
    )

    return rank_news(
        filtered
    )


# ============================================================
# BEST CATEGORY
# ============================================================

def get_best_category(
    article: dict[str, Any],
) -> str:

    explicit = _normalize_category(
        article.get("category")
    )

    if explicit and explicit != CATEGORY_GENERAL:
        return explicit

    text = _article_text(
        article
    )

    scores = _category_scores(
        text
    )

    explicit_scores = {
        category: score
        for category, score in scores.items()
        if category != CATEGORY_GENERAL
    }

    if not explicit_scores:
        return CATEGORY_GENERAL

    best_category = max(
        explicit_scores,
        key=explicit_scores.get,
    )

    if explicit_scores[best_category] <= 0:
        return CATEGORY_GENERAL

    return best_category


# ============================================================
# CATEGORY MATCHES
# ============================================================

def get_category_matches(
    article: dict[str, Any],
    category: str,
) -> list[str]:

    normalized_category = (
        _normalize_category(category)
        or CATEGORY_GENERAL
    )

    text = _article_text(
        article
    )

    return _keyword_matches(
        text,
        CATEGORY_KEYWORDS.get(
            normalized_category,
            [],
        ),
    )


# ============================================================
# BPSC MATCHES
# ============================================================

def get_bpsc_matches(
    article: dict[str, Any],
) -> list[str]:

    return _keyword_matches(
        _article_text(article),
        BPSC_KEYWORDS,
    )


# ============================================================
# UPSC MATCHES
# ============================================================

def get_upsc_matches(
    article: dict[str, Any],
) -> list[str]:

    return _keyword_matches(
        _article_text(article),
        UPSC_KEYWORDS,
    )


# ============================================================
# BIHAR MATCHES
# ============================================================

def get_bihar_matches(
    article: dict[str, Any],
) -> list[str]:

    return _keyword_matches(
        _article_text(article),
        BIHAR_KEYWORDS,
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [

    # Main classification
    "classify_news",
    "classify_news_list",
    "classify_category",
    "classify_exam",
    "classify_bihar",

    # Scoring
    "calculate_relevance_score",
    "calculate_final_score",
    "calculate_provider_bonus",

    # Filtering
    "filter_news",
    "process_news",
    "rank_news",

    # Deduplication
    "deduplicate_news",
    "article_dedup_key",

    # Classification
    "classify_prelims_mains",
    "detect_noise",
    "relevance_label",
    "importance_label",

    # Debug
    "debug_article",
    "validate_article",
    "clean_article",

    # Distribution
    "category_distribution",
    "exam_distribution",
    "score_distribution",

    # Matching
    "get_best_category",
    "get_category_matches",
    "get_bpsc_matches",
    "get_upsc_matches",
    "get_bihar_matches",

    # Constants
    "CATEGORY_KEYWORDS",
    "BPSC_KEYWORDS",
    "UPSC_KEYWORDS",
    "BIHAR_KEYWORDS",
    "EMPLOYMENT_KEYWORDS",
]