# app/services/news_topics.py

from __future__ import annotations

from typing import Any


# ============================================================
# COMMON TOPIC KEYWORDS
# ============================================================

COMMON_TOPICS: dict[str, list[str]] = {

    "Polity & Governance": [
        "constitution",
        "constitutional",
        "parliament",
        "lok sabha",
        "rajya sabha",
        "supreme court",
        "high court",
        "judiciary",
        "fundamental rights",
        "fundamental duties",
        "directive principles",
        "governance",
        "government policy",
        "public policy",
        "administration",
        "federalism",
        "centre state relations",
        "local government",
        "panchayat",
        "municipality",
        "election commission",
        "election",
        "electoral reforms",
        "political reforms",
        "cabinet",
        "ordinance",
        "bill",
        "act",
        "amendment",
    ],

    "Economy": [
        "economy",
        "economic growth",
        "gdp",
        "gdp growth",
        "inflation",
        "deflation",
        "unemployment",
        "employment",
        "fiscal policy",
        "monetary policy",
        "budget",
        "tax",
        "taxation",
        "gst",
        "revenue",
        "fiscal deficit",
        "current account deficit",
        "trade deficit",
        "foreign exchange",
        "forex",
        "banking",
        "bank",
        "rbi",
        "reserve bank",
        "interest rate",
        "repo rate",
        "sebi",
        "stock market",
        "investment",
        "foreign direct investment",
        "fdi",
        "msme",
        "manufacturing",
        "infrastructure",
        "poverty",
        "financial inclusion",
        "digital economy",
    ],

    "Environment & Ecology": [
        "environment",
        "environmental",
        "climate change",
        "global warming",
        "biodiversity",
        "ecosystem",
        "forest",
        "wildlife",
        "national park",
        "wildlife sanctuary",
        "tiger reserve",
        "wetland",
        "ramsar",
        "pollution",
        "air pollution",
        "water pollution",
        "plastic pollution",
        "renewable energy",
        "solar energy",
        "wind energy",
        "green energy",
        "carbon emissions",
        "carbon neutrality",
        "net zero",
        "climate summit",
        "cop",
        "conservation",
        "desertification",
        "disaster management",
    ],

    "Science & Technology": [
        "science",
        "technology",
        "artificial intelligence",
        "ai",
        "machine learning",
        "robotics",
        "quantum computing",
        "quantum technology",
        "semiconductor",
        "electronics",
        "cyber security",
        "cybersecurity",
        "space",
        "isro",
        "satellite",
        "rocket",
        "space mission",
        "nuclear",
        "biotechnology",
        "biotech",
        "genome",
        "genomics",
        "nanotechnology",
        "5g",
        "6g",
        "digital technology",
        "deep tech",
    ],

    "International Relations": [
        "international relations",
        "foreign policy",
        "diplomacy",
        "bilateral relations",
        "multilateral",
        "united nations",
        "un",
        "un security council",
        "security council",
        "g20",
        "g7",
        "brics",
        "sco",
        "quad",
        "asean",
        "european union",
        "nato",
        "world bank",
        "imf",
        "international monetary fund",
        "wto",
        "world trade organization",
        "geopolitics",
        "strategic partnership",
        "defence cooperation",
    ],

    "Defence & Security": [
        "defence",
        "defense",
        "military",
        "army",
        "navy",
        "air force",
        "indian army",
        "indian navy",
        "indian air force",
        "missile",
        "drone",
        "fighter aircraft",
        "defence production",
        "defence corridor",
        "border security",
        "national security",
        "cyber security",
        "terrorism",
        "counter terrorism",
        "internal security",
        "border management",
    ],

    "Social Issues": [
        "education",
        "health",
        "healthcare",
        "public health",
        "nutrition",
        "malnutrition",
        "women empowerment",
        "women",
        "child welfare",
        "children",
        "social justice",
        "poverty",
        "inequality",
        "tribal",
        "scheduled caste",
        "scheduled tribes",
        "minority",
        "disability",
        "senior citizens",
        "skill development",
        "literacy",
    ],

    "Agriculture": [
        "agriculture",
        "farmer",
        "farmers",
        "farming",
        "crop",
        "cropping",
        "irrigation",
        "fertilizer",
        "fertiliser",
        "food security",
        "food processing",
        "minimum support price",
        "msp",
        "agricultural reform",
        "agri technology",
        "agritech",
        "organic farming",
        "natural farming",
        "horticulture",
        "animal husbandry",
        "dairy",
        "fisheries",
        "rural development",
    ],

    "History & Culture": [
        "history",
        "ancient india",
        "medieval india",
        "modern india",
        "freedom struggle",
        "independence movement",
        "heritage",
        "culture",
        "art",
        "architecture",
        "archaeology",
        "monument",
        "unesco",
        "classical dance",
        "folk dance",
        "festival",
        "literature",
        "language",
    ],

    "Geography": [
        "geography",
        "river",
        "mountain",
        "himalaya",
        "plateau",
        "plain",
        "monsoon",
        "rainfall",
        "climate",
        "earthquake",
        "flood",
        "drought",
        "cyclone",
        "natural resources",
        "mineral",
        "coast",
        "ocean",
        "groundwater",
        "water resources",
    ],
}


# ============================================================
# UPSC SPECIFIC TOPICS
# ============================================================

UPSC_TOPICS: dict[str, dict[str, Any]] = {

    "Indian Polity": {
        "keywords": [
            "constitution",
            "parliament",
            "supreme court",
            "fundamental rights",
            "directive principles",
            "federalism",
            "governance",
            "election commission",
            "constitutional amendment",
            "judicial review",
            "centre state relations",
            "local governance",
            "panchayati raj",
        ],
        "prelims": [
            "Indian Constitution",
            "Parliament",
            "Constitutional Bodies",
            "Judiciary",
            "Fundamental Rights",
            "Directive Principles",
            "Local Government",
        ],
        "mains": [
            "GS-II",
            "Indian Polity",
            "Governance",
            "Constitution",
            "Federalism",
            "Judiciary",
        ],
    },

    "Indian Economy": {
        "keywords": [
            "gdp",
            "inflation",
            "fiscal deficit",
            "monetary policy",
            "rbi",
            "banking",
            "budget",
            "gst",
            "taxation",
            "employment",
            "unemployment",
            "investment",
            "fdi",
            "msme",
            "manufacturing",
            "infrastructure",
        ],
        "prelims": [
            "Indian Economy",
            "Banking",
            "Inflation",
            "Fiscal Policy",
            "Monetary Policy",
            "Budget",
            "Taxation",
        ],
        "mains": [
            "GS-III",
            "Indian Economy",
            "Growth & Development",
            "Fiscal Policy",
            "Inclusive Growth",
        ],
    },

    "Environment & Ecology": {
        "keywords": [
            "climate change",
            "biodiversity",
            "ecosystem",
            "wildlife",
            "forest",
            "wetland",
            "ramsar",
            "pollution",
            "renewable energy",
            "carbon emissions",
            "net zero",
            "conservation",
        ],
        "prelims": [
            "Environment",
            "Ecology",
            "Biodiversity",
            "Protected Areas",
            "Climate Change",
            "International Environmental Conventions",
        ],
        "mains": [
            "GS-III",
            "Environment",
            "Ecology",
            "Climate Change",
            "Biodiversity",
        ],
    },

    "Science & Technology": {
        "keywords": [
            "artificial intelligence",
            "quantum technology",
            "semiconductor",
            "isro",
            "space mission",
            "satellite",
            "biotechnology",
            "genomics",
            "cybersecurity",
            "robotics",
            "nuclear technology",
        ],
        "prelims": [
            "Science & Technology",
            "Space Technology",
            "Biotechnology",
            "Artificial Intelligence",
            "Cyber Security",
        ],
        "mains": [
            "GS-III",
            "Science & Technology",
            "Emerging Technologies",
            "Cyber Security",
        ],
    },

    "International Relations": {
        "keywords": [
            "foreign policy",
            "diplomacy",
            "united nations",
            "g20",
            "brics",
            "sco",
            "quad",
            "asean",
            "wto",
            "imf",
            "world bank",
            "geopolitics",
            "bilateral relations",
        ],
        "prelims": [
            "International Organisations",
            "International Groupings",
            "India and World",
        ],
        "mains": [
            "GS-II",
            "International Relations",
            "India and its Neighbourhood",
            "International Institutions",
        ],
    },

    "Defence & Internal Security": {
        "keywords": [
            "defence",
            "military",
            "missile",
            "army",
            "navy",
            "air force",
            "border security",
            "terrorism",
            "cyber security",
            "internal security",
        ],
        "prelims": [
            "Defence Technology",
            "Military Exercises",
            "Missile Systems",
            "National Security",
        ],
        "mains": [
            "GS-III",
            "Internal Security",
            "Defence",
            "Border Management",
            "Cyber Security",
        ],
    },

    "Social Issues": {
        "keywords": [
            "education",
            "health",
            "nutrition",
            "women empowerment",
            "poverty",
            "inequality",
            "social justice",
            "skill development",
            "literacy",
        ],
        "prelims": [
            "Government Schemes",
            "Social Sector",
            "Health",
            "Education",
            "Women and Children",
        ],
        "mains": [
            "GS-II",
            "Social Justice",
            "Health",
            "Education",
            "Women Empowerment",
        ],
    },

    "Agriculture": {
        "keywords": [
            "agriculture",
            "farmer",
            "msp",
            "irrigation",
            "food security",
            "fertilizer",
            "crop",
            "agritech",
            "animal husbandry",
            "fisheries",
        ],
        "prelims": [
            "Agriculture",
            "Crops",
            "Irrigation",
            "MSP",
            "Food Security",
        ],
        "mains": [
            "GS-III",
            "Agriculture",
            "Food Security",
            "Irrigation",
            "Agricultural Reforms",
        ],
    },
}


# ============================================================
# BPSC SPECIFIC TOPICS
# ============================================================

BPSC_TOPICS: dict[str, dict[str, Any]] = {

    "Bihar History": {
        "keywords": [
            "bihar history",
            "magadha",
            "maurya",
            "gupta",
            "nalanda",
            "vikramshila",
            "bodh gaya",
            "vaishali",
            "pataliputra",
            "chandragupta maurya",
            "ashoka",
            "bihar freedom movement",
            "champaran movement",
            "champaran",
            "rajendra prasad",
            "jayaprakash narayan",
        ],
        "prelims": [
            "Ancient Bihar",
            "Medieval Bihar",
            "Modern Bihar",
            "Bihar Freedom Movement",
            "Important Personalities",
        ],
        "mains": [
            "Bihar History",
            "Bihar Freedom Movement",
            "Bihar Personalities",
            "Social and Cultural History of Bihar",
        ],
    },

    "Bihar Geography": {
        "keywords": [
            "bihar geography",
            "ganga",
            "kosi",
            "gandak",
            "son river",
            "bagmati",
            "kamla river",
            "flood in bihar",
            "bihar flood",
            "bihar rainfall",
            "bihar climate",
            "bihar soil",
            "bihar irrigation",
            "bihar agriculture",
        ],
        "prelims": [
            "Rivers of Bihar",
            "Climate of Bihar",
            "Soils of Bihar",
            "Agriculture of Bihar",
            "Floods",
            "Natural Resources",
        ],
        "mains": [
            "Bihar Geography",
            "Flood Management",
            "Water Resources",
            "Agriculture",
            "Climate",
        ],
    },

    "Bihar Economy": {
        "keywords": [
            "bihar economy",
            "bihar budget",
            "bihar gdp",
            "bihar growth",
            "bihar development",
            "bihar industry",
            "bihar manufacturing",
            "bihar employment",
            "bihar unemployment",
            "bihar agriculture",
            "bihar infrastructure",
            "bihar investment",
            "bihar msme",
            "bihar startup",
            "bihar tourism",
        ],
        "prelims": [
            "Bihar Economy",
            "Bihar Budget",
            "Bihar Agriculture",
            "Bihar Industry",
            "Bihar Infrastructure",
        ],
        "mains": [
            "Bihar Economy",
            "Economic Development",
            "Agriculture",
            "Industrial Development",
            "Employment",
            "Infrastructure",
        ],
    },

    "Bihar Polity & Governance": {
        "keywords": [
            "bihar government",
            "bihar cabinet",
            "bihar assembly",
            "bihar legislature",
            "bihar election",
            "bihar administration",
            "bihar panchayat",
            "bihar municipality",
            "bihar chief minister",
            "nitish kumar",
            "governance in bihar",
            "bihar policy",
        ],
        "prelims": [
            "Bihar Government",
            "Bihar Legislature",
            "Bihar Administration",
            "Panchayati Raj",
            "Bihar Elections",
        ],
        "mains": [
            "Bihar Governance",
            "Bihar Administration",
            "Panchayati Raj",
            "State Politics",
        ],
    },

    "Bihar Schemes & Welfare": {
        "keywords": [
            "bihar scheme",
            "bihar yojana",
            "bihar government scheme",
            "bihar welfare scheme",
            "student scheme bihar",
            "women scheme bihar",
            "farmer scheme bihar",
            "employment scheme bihar",
            "education scheme bihar",
            "health scheme bihar",
            "bihar scholarship",
            "bihar skill development",
        ],
        "prelims": [
            "Bihar Government Schemes",
            "Welfare Schemes",
            "Education Schemes",
            "Women Welfare",
            "Farmer Welfare",
        ],
        "mains": [
            "Social Welfare in Bihar",
            "Government Schemes",
            "Education",
            "Women Empowerment",
            "Employment",
        ],
    },

    "Bihar Agriculture": {
        "keywords": [
            "bihar agriculture",
            "bihar farmer",
            "bihar farming",
            "bihar crop",
            "bihar irrigation",
            "bihar fertilizer",
            "bihar horticulture",
            "bihar fisheries",
            "bihar dairy",
            "agriculture in bihar",
            "maize bihar",
            "rice bihar",
            "wheat bihar",
            "litchi bihar",
        ],
        "prelims": [
            "Agriculture of Bihar",
            "Major Crops",
            "Irrigation",
            "Horticulture",
            "Fisheries",
        ],
        "mains": [
            "Agriculture in Bihar",
            "Agricultural Development",
            "Irrigation",
            "Food Processing",
            "Rural Economy",
        ],
    },

    "Bihar Education & Health": {
        "keywords": [
            "bihar education",
            "bihar school",
            "bihar university",
            "bihar college",
            "bihar literacy",
            "bihar health",
            "bihar hospital",
            "bihar healthcare",
            "bihar medical",
            "bihar nutrition",
            "bihar teacher",
            "bihar education department",
        ],
        "prelims": [
            "Education in Bihar",
            "Health in Bihar",
            "Literacy",
            "Educational Institutions",
        ],
        "mains": [
            "Education in Bihar",
            "Health in Bihar",
            "Human Development",
            "Social Sector",
        ],
    },

    "Bihar Environment & Disaster": {
        "keywords": [
            "bihar flood",
            "bihar drought",
            "bihar cyclone",
            "bihar earthquake",
            "bihar disaster",
            "bihar environment",
            "bihar pollution",
            "bihar forest",
            "bihar wildlife",
            "ganga bihar",
            "kosi flood",
            "gandak flood",
        ],
        "prelims": [
            "Bihar Environment",
            "Rivers",
            "Floods",
            "Disaster Management",
            "Forests and Wildlife",
        ],
        "mains": [
            "Disaster Management in Bihar",
            "Flood Management",
            "Environmental Issues",
            "Climate Change",
        ],
    },
}


# ============================================================
# BIHAR LOCATIONS
# ============================================================

BIHAR_LOCATIONS = {
    "bihar",
    "patna",
    "gaya",
    "nalanda",
    "rajgir",
    "vaishali",
    "muzaffarpur",
    "bhagalpur",
    "darbhanga",
    "purnia",
    "katihar",
    "begusarai",
    "munger",
    "bhojpur",
    "ara",
    "rohtas",
    "sasaram",
    "aurangabad",
    "jehanabad",
    "arwal",
    "nawada",
    "sheikhpura",
    "lakhisarai",
    "jamui",
    "khagaria",
    "saharsa",
    "madhepura",
    "supaul",
    "araria",
    "kishanganj",
    "samastipur",
    "sitamarhi",
    "sheohar",
    "madhubani",
    "darbhanga",
    "saran",
    "chapra",
    "siwan",
    "gopalganj",
    "east champaran",
    "motihari",
    "west champaran",
    "bettiah",
}


# ============================================================
# GOVERNMENT / INSTITUTION KEYWORDS
# ============================================================

GOVERNMENT_INSTITUTIONS = {
    "government",
    "ministry",
    "department",
    "commission",
    "authority",
    "parliament",
    "assembly",
    "supreme court",
    "high court",
    "rbi",
    "sebi",
    "niti aayog",
    "isro",
    "drdo",
    "upsc",
    "bpsc",
    "pib",
}


# ============================================================
# TOPIC ALIASES
# ============================================================

TOPIC_ALIASES = {

    "Artificial Intelligence": [
        "artificial intelligence",
        "ai",
        "generative ai",
        "gen ai",
        "machine learning",
        "deep learning",
    ],

    "Climate Change": [
        "climate change",
        "global warming",
        "climate crisis",
        "climate emergency",
    ],

    "Renewable Energy": [
        "renewable energy",
        "green energy",
        "clean energy",
        "solar energy",
        "wind energy",
    ],

    "Fiscal Policy": [
        "fiscal policy",
        "government spending",
        "public expenditure",
        "fiscal deficit",
    ],

    "Monetary Policy": [
        "monetary policy",
        "repo rate",
        "reverse repo",
        "interest rate",
        "rbi policy",
    ],

    "Bihar Government": [
        "bihar government",
        "government of bihar",
        "bihar govt",
        "state government",
    ],

    "Bihar Economy": [
        "bihar economy",
        "economy of bihar",
        "bihar economic growth",
        "bihar development",
    ],

    "Bihar Agriculture": [
        "bihar agriculture",
        "agriculture in bihar",
        "bihar farming",
        "bihar farmers",
    ],

    "Bihar Flood": [
        "bihar flood",
        "flood in bihar",
        "floods in bihar",
        "kosi flood",
        "gandak flood",
        "ganga flood",
    ],

    "Bihar Education": [
        "bihar education",
        "education in bihar",
        "bihar schools",
        "bihar universities",
    ],

    "Bihar Health": [
        "bihar health",
        "health in bihar",
        "bihar healthcare",
        "bihar hospitals",
    ],
}


# ============================================================
# HELPERS
# ============================================================

def get_all_keywords(
    exam: str | None = None,
) -> set[str]:

    keywords: set[str] = set()

    keywords.update(
        keyword.lower()
        for topic in COMMON_TOPICS.values()
        for keyword in topic
    )

    if exam:

        exam = exam.upper()

        if exam == "UPSC":

            for topic in UPSC_TOPICS.values():
                keywords.update(
                    keyword.lower()
                    for keyword in topic[
                        "keywords"
                    ]
                )

        elif exam == "BPSC":

            for topic in BPSC_TOPICS.values():
                keywords.update(
                    keyword.lower()
                    for keyword in topic[
                        "keywords"
                    ]
                )

    return keywords


def get_topics_for_exam(
    exam: str | None,
) -> dict[str, dict[str, Any]]:

    if not exam:
        return {
            **UPSC_TOPICS,
            **BPSC_TOPICS,
        }

    exam = exam.upper()

    if exam == "UPSC":
        return UPSC_TOPICS

    if exam == "BPSC":
        return BPSC_TOPICS

    return {}


def get_topic_keywords(
    topic_name: str,
    exam: str | None = None,
) -> list[str]:

    topics = get_topics_for_exam(
        exam
    )

    topic = topics.get(
        topic_name
    )

    if not topic:
        return []

    return list(
        topic.get(
            "keywords",
            [],
        )
    )


def get_topic_syllabus(
    topic_name: str,
    exam: str,
) -> dict[str, list[str]]:

    topics = get_topics_for_exam(
        exam
    )

    topic = topics.get(
        topic_name
    )

    if not topic:
        return {
            "prelims": [],
            "mains": [],
        }

    return {
        "prelims": list(
            topic.get(
                "prelims",
                [],
            )
        ),
        "mains": list(
            topic.get(
                "mains",
                [],
            )
        ),
    }


def get_bihar_keywords() -> set[str]:

    keywords: set[str] = set()

    keywords.update(
        BIHAR_LOCATIONS
    )

    keywords.update(
        keyword.lower()
        for topic in BPSC_TOPICS.values()
        for keyword in topic[
            "keywords"
        ]
    )

    return keywords