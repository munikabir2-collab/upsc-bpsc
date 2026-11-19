
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from dotenv import load_dotenv
from groq import AsyncGroq


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

logger = logging.getLogger("muni48.official_source_resolver")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
).strip()


# ============================================================
# CONFIGURATION
# ============================================================

PIB_BASE_URL = "https://www.pib.gov.in/"

PIB_ALL_RELEASES_URL = (
    "https://www.pib.gov.in/AllRelease.aspx?lang=1&reg=1"
)

PIB_LINKS_FILE = (
    Path(__file__).resolve().parents[2]
    / "pib_release_links.json"
)

ALLOWED_DOMAINS = (
    "gov.in",
    "nic.in",
)

REQUEST_TIMEOUT = 20.0

MAX_RESPONSE_BYTES = 2_000_000

MAX_PAGE_CHARS = 10000

MAX_PIB_CANDIDATES = 8

MIN_TITLE_SCORE = 0.38


# ============================================================
# GROQ CLIENT
# ============================================================

_groq_client: AsyncGroq | None = None

_groq_lock = asyncio.Lock()


async def _get_groq_client() -> AsyncGroq:

    global _groq_client

    if _groq_client is not None:
        return _groq_client

    async with _groq_lock:

        if _groq_client is None:

            if not GROQ_API_KEY:

                raise RuntimeError(
                    "GROQ_API_KEY is missing"
                )

            _groq_client = AsyncGroq(
                api_key=GROQ_API_KEY
            )

    return _groq_client


# ============================================================
# OFFICIAL DOMAIN VALIDATION
# ============================================================

def _is_official_domain(url: str) -> bool:

    try:

        parsed = urlparse(url)

        host = (
            parsed.hostname or ""
        ).lower().rstrip(".")

        if parsed.scheme != "https":
            return False

        if not host:
            return False

        if parsed.username or parsed.password:
            return False

        return any(
            host == domain
            or host.endswith("." + domain)
            for domain in ALLOWED_DOMAINS
        )

    except Exception:

        return False


def _is_pib_url(url: str) -> bool:

    try:

        parsed = urlparse(url)

        return (
            parsed.scheme == "https"
            and (parsed.hostname or "").lower()
            == "www.pib.gov.in"
        )

    except Exception:

        return False


# ============================================================
# SAFE HTTP REQUEST
# Redirects are validated before following them.
# ============================================================

async def _safe_get(
    client: httpx.AsyncClient,
    url: str,
    pib_only: bool = False,
) -> httpx.Response | None:

    current_url = url

    for _ in range(6):

        if not _is_official_domain(current_url):
            return None

        if pib_only and not _is_pib_url(current_url):
            return None

        response = await client.get(
            current_url,
            follow_redirects=False,
        )

        if response.status_code in (
            301,
            302,
            303,
            307,
            308,
        ):

            location = response.headers.get(
                "location"
            )

            if not location:
                return None

            next_url = urljoin(
                str(response.url),
                location,
            )

            if not _is_official_domain(next_url):
                return None

            if pib_only and not _is_pib_url(next_url):
                return None

            current_url = next_url

            continue

        response.raise_for_status()

        if len(response.content) > MAX_RESPONSE_BYTES:

            logger.warning(
                "Official page response too large"
            )

            return None

        content_type = response.headers.get(
            "content-type",
            "",
        ).lower()

        if "text/html" not in content_type:
            return None

        return response

    logger.warning(
        "Too many redirects while fetching official page"
    )

    return None


# ============================================================
# JSON EXTRACTION
# ============================================================

def _extract_json(content: str) -> dict:

    try:

        data = json.loads(content)

        if isinstance(data, dict):
            return data

    except Exception:

        pass

    return {}


# ============================================================
# PIB RELEASE LIST PARSER
# ============================================================

class _ReleaseListParser(HTMLParser):

    def __init__(self):

        super().__init__()

        self.releases = []

        self.href = None

        self.title_parts = []

    def handle_starttag(
        self,
        tag,
        attrs,
    ):

        if tag != "a":
            return

        attrs = dict(attrs)

        href = attrs.get(
            "href",
            "",
        )

        if not href:
            return

        if "PressReleseDetail.aspx" not in href:
            return

        self.href = href

        self.title_parts = []

        title = attrs.get(
            "title",
            "",
        )

        if title:
            self.title_parts.append(title)

    def handle_data(self, data):

        if self.href:

            value = data.strip()

            if value:
                self.title_parts.append(value)

    def handle_endtag(self, tag):

        if (
            tag == "a"
            and self.href
        ):

            title = " ".join(
                self.title_parts
            ).strip()

            self.releases.append({
                "title": title,
                "url": self.href,
            })

            self.href = None

            self.title_parts = []


# ============================================================
# PIB IFRAME PARSER
# ============================================================

class _FrameParser(HTMLParser):

    def __init__(self):

        super().__init__()

        self.frame_src = None

    def handle_starttag(
        self,
        tag,
        attrs,
    ):

        if tag != "iframe":
            return

        attrs = dict(attrs)

        if (
            attrs.get("id")
            == "ContentPlaceHolder1_iframepressrealese"
        ):

            self.frame_src = attrs.get(
                "src"
            )


# ============================================================
# ARTICLE CONTENT PARSER
# ============================================================

class _ArticleParser(HTMLParser):

    BLOCKED_TAGS = {
        "script",
        "style",
        "noscript",
        "svg",
        "header",
        "footer",
    }

    def __init__(self):

        super().__init__()

        self.text_parts = []

        self.title_parts = []

        self.blocked = 0

        self.in_title = False

    def handle_starttag(
        self,
        tag,
        attrs,
    ):

        if tag == "title":
            self.in_title = True

        if tag in self.BLOCKED_TAGS:
            self.blocked += 1

    def handle_endtag(self, tag):

        if tag == "title":
            self.in_title = False

        if tag in self.BLOCKED_TAGS:

            self.blocked = max(
                0,
                self.blocked - 1,
            )

    def handle_data(self, data):

        value = data.strip()

        if not value:
            return

        if self.in_title:
            self.title_parts.append(value)

        if not self.blocked:
            self.text_parts.append(value)


# ============================================================
# TEXT NORMALIZATION
# ============================================================

STOP_WORDS = {
    "the",
    "and",
    "for",
    "from",
    "with",
    "that",
    "this",
    "will",
    "has",
    "have",
    "into",
    "its",
    "their",
    "about",
    "over",
    "under",
    "india",
    "indian",
    "shri",
    "smt",
    "minister",
    "government",
    "to",
    "of",
    "in",
    "on",
    "at",
    "by",
    "a",
    "an",
}


def _normalize(value: str) -> str:

    value = str(
        value or ""
    ).lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    return " ".join(
        value.split()
    )


def _tokens(value: str) -> set[str]:

    return {
        word
        for word in _normalize(value).split()
        if len(word) > 2
        and word not in STOP_WORDS
    }


def _title_score(
    article_title: str,
    release_title: str,
) -> float:

    left = _normalize(
        article_title
    )

    right = _normalize(
        release_title
    )

    if not left or not right:
        return 0.0

    sequence_score = SequenceMatcher(
        None,
        left,
        right,
    ).ratio()

    left_tokens = _tokens(left)

    right_tokens = _tokens(right)

    if not left_tokens or not right_tokens:
        return sequence_score

    overlap = (
        len(left_tokens & right_tokens)
        / len(left_tokens)
    )

    return max(
        sequence_score,
        overlap,
    )


# ============================================================
# LOAD LOCAL PIB RELEASE JSON
# ============================================================

def _load_local_releases() -> list[dict]:

    if not PIB_LINKS_FILE.exists():
        return []

    try:

        data = json.loads(
            PIB_LINKS_FILE.read_text(
                encoding="utf-8-sig"
            )
        )

        if isinstance(data, dict):

            for key in (
                "releases",
                "items",
                "results",
                "data",
            ):

                if isinstance(
                    data.get(key),
                    list,
                ):

                    data = data[key]

                    break

        if not isinstance(data, list):
            return []

        releases = []

        for item in data:

            if not isinstance(item, dict):
                continue

            title = (
                item.get("title")
                or item.get("name")
                or item.get("text")
                or ""
            )

            url = (
                item.get("url")
                or item.get("link")
                or item.get("href")
                or ""
            )

            if not title or not url:
                continue

            absolute_url = urljoin(
                PIB_BASE_URL,
                str(url),
            )

            if not _is_pib_url(absolute_url):
                continue

            if "PRID=" not in absolute_url.upper():
                continue

            releases.append({
                "title": str(title).strip(),
                "url": absolute_url,
            })

        return releases

    except Exception:

        logger.exception(
            "Could not read local PIB release list"
        )

        return []


# ============================================================
# FETCH LIVE PIB RELEASE LIST
# ============================================================

async def _fetch_live_releases(
    client: httpx.AsyncClient,
) -> list[dict]:

    try:

        response = await _safe_get(
            client,
            PIB_ALL_RELEASES_URL,
            pib_only=True,
        )

        if response is None:
            return []

        parser = _ReleaseListParser()

        parser.feed(
            response.text
        )

        releases = []

        for item in parser.releases:

            absolute_url = urljoin(
                str(response.url),
                item["url"],
            )

            if not _is_pib_url(absolute_url):
                continue

            if "PRID=" not in absolute_url.upper():
                continue

            releases.append({
                "title": item["title"],
                "url": absolute_url,
            })

        return releases

    except Exception as exc:

        logger.warning(
            "PIB release list unavailable: %s",
            type(exc).__name__,
        )

        return []


# ============================================================
# EXTRACT PRID
# ============================================================

def _get_prid(url: str) -> str | None:

    match = re.search(
        r"[?&]PRID=(\d+)",
        url,
        flags=re.IGNORECASE,
    )

    return (
        match.group(1)
        if match
        else None
    )


# ============================================================
# RANK PIB RELEASES BY TITLE
# ============================================================

def _rank_releases(
    article_title: str,
    releases: list[dict],
) -> list[dict]:

    ranked = []

    seen = set()

    for item in releases:

        title = str(
            item.get("title") or ""
        ).strip()

        url = str(
            item.get("url") or ""
        ).strip()

        if not title or not _is_pib_url(url):
            continue

        prid = _get_prid(url)

        if not prid or prid in seen:
            continue

        seen.add(prid)

        score = _title_score(
            article_title,
            title,
        )

        if score >= MIN_TITLE_SCORE:

            ranked.append({
                "title": title,
                "url": url,
                "prid": prid,
                "score": score,
            })

    ranked.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return ranked[:MAX_PIB_CANDIDATES]


# ============================================================
# EXTRACT GOVERNMENT CLAIM USING GROQ
# ============================================================

async def _extract_claim(
    article: dict,
) -> dict:

    client = await _get_groq_client()

    title = str(
        article.get("title") or ""
    )[:500]

    description = str(
        article.get("description")
        or article.get("content")
        or ""
    )[:2500]

    if not title and not description:
        return {}

    response = await client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0,
        response_format={
            "type": "json_object"
        },
        messages=[
            {
                "role": "system",
                "content": (
                    "Identify a specific factual claim about an "
                    "Indian government action, scheme, policy, "
                    "notification, institution or announcement. "
                    "Return JSON with is_government_claim boolean "
                    "and claim string. Do not invent facts. "
                    "If no specific government claim exists, "
                    "return false and an empty claim."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Title: {title}\n"
                    f"Description: {description}"
                ),
            },
        ],
    )

    data = _extract_json(
        response.choices[0].message.content or "{}"
    )

    if data.get("is_government_claim") is not True:
        return {}

    claim = str(
        data.get("claim") or ""
    ).strip()

    if not claim:
        return {}

    return {
        "claim": claim[:1500]
    }


# ============================================================
# FETCH REAL PIB ARTICLE FROM IFRAME
# ============================================================

async def _fetch_pib_article(
    client: httpx.AsyncClient,
    prid: str,
) -> tuple[str, str] | None:

    if not prid.isdigit():
        return None

    outer_url = (
        f"{PIB_BASE_URL}PressReleaseDetail.aspx"
        f"?PRID={prid}&reg=48&lang=1"
    )

    outer_response = await _safe_get(
        client,
        outer_url,
        pib_only=True,
    )

    if outer_response is None:
        return None

    frame_parser = _FrameParser()

    frame_parser.feed(
        outer_response.text
    )

    if not frame_parser.frame_src:

        logger.warning(
            "PIB iframe not found for PRID %s",
            prid,
        )

        return None

    iframe_url = urljoin(
        str(outer_response.url),
        frame_parser.frame_src,
    )

    if not _is_pib_url(iframe_url):
        return None

    article_response = await _safe_get(
        client,
        iframe_url,
        pib_only=True,
    )

    if article_response is None:
        return None

    parser = _ArticleParser()

    parser.feed(
        article_response.text[:MAX_RESPONSE_BYTES]
    )

    title = " ".join(
        parser.title_parts
    ).strip()

    page_text = " ".join(
        parser.text_parts
    ).strip()

    if len(page_text) > MAX_PAGE_CHARS:
        page_text = page_text[-MAX_PAGE_CHARS:]

    if len(page_text) < 150:

        logger.warning(
            "PIB article content too short for PRID %s",
            prid,
        )

        return None

    final_url = str(
        article_response.url
    )

    if not _is_pib_url(final_url):
        return None

    return (
        final_url,
        (
            f"Page title: {title}\n"
            f"Article content:\n{page_text}"
        ),
    )


# ============================================================
# STRICT GROQ ARTICLE VERIFICATION
# ============================================================

async def _verify_pib_article(
    article: dict,
    claim: str,
    pib_title: str,
    pib_content: str,
) -> bool:

    groq = await _get_groq_client()

    news_title = str(
        article.get("title") or ""
    )[:500]

    news_description = str(
        article.get("description")
        or article.get("content")
        or ""
    )[:1500]

    result = await groq.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0,
        response_format={
            "type": "json_object"
        },
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict government source verifier. "
                    "Check whether this exact PIB article supports "
                    "the factual government claim in the news. "
                    "A shared topic, person, ministry or keyword "
                    "is NOT sufficient. The article must support "
                    "the same announcement or factual event. "
                    "If evidence is incomplete or ambiguous, return "
                    '{"matches": false}. Return JSON only.'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"NEWS TITLE:\n{news_title}\n\n"
                    f"NEWS DESCRIPTION:\n{news_description}\n\n"
                    f"EXTRACTED CLAIM:\n{claim}\n\n"
                    f"PIB RELEASE TITLE:\n{pib_title}\n\n"
                    f"PIB ARTICLE CONTENT:\n{pib_content}"
                ),
            },
        ],
    )

    data = _extract_json(
        result.choices[0].message.content or "{}"
    )

    return data.get("matches") is True


# ============================================================
# MAIN RESOLVER
# ============================================================

async def resolve_official_source(
    article: dict,
) -> str | None:

    """
    Return a verified article-specific PIB source URL.

    Returns None if:
    - No specific government claim exists.
    - No PIB title match is found.
    - The PIB article iframe is unavailable.
    - The article content cannot be extracted.
    - Groq cannot verify the exact claim.
    """

    if not isinstance(article, dict):
        return None

    article_title = str(
        article.get("title") or ""
    ).strip()

    if len(article_title) < 8:
        return None

    try:

        # ----------------------------------------------------
        # 1. Extract government claim.
        # ----------------------------------------------------

        extracted = await _extract_claim(
            article
        )

        if not extracted:
            return None

        # ----------------------------------------------------
        # 2. Create HTTP client.
        # ----------------------------------------------------

        timeout = httpx.Timeout(
            timeout=REQUEST_TIMEOUT,
            connect=7.0,
        )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; Muni48SourceVerifier/1.0)"
            ),
            "Accept": (
                "text/html,application/xhtml+xml"
            ),
        }

        async with httpx.AsyncClient(
            timeout=timeout,
            headers=headers,
            follow_redirects=False,
            max_redirects=0,
        ) as client:

            # ------------------------------------------------
            # 3. Load live and local PIB releases.
            # ------------------------------------------------

            live_releases = await _fetch_live_releases(
                client
            )

            local_releases = _load_local_releases()

            combined = (
                live_releases + local_releases
            )

            if not combined:

                logger.info(
                    "No PIB releases available"
                )

                return None

            # ------------------------------------------------
            # 4. Match article title to PIB release titles.
            # ------------------------------------------------

            candidates = _rank_releases(
                article_title,
                combined,
            )

            if not candidates:

                logger.info(
                    "No PIB title match: %s",
                    article_title[:120],
                )

                return None

            # ------------------------------------------------
            # 5. Fetch iframe content and verify.
            # ------------------------------------------------

            for candidate in candidates:

                pib_article = await _fetch_pib_article(
                    client,
                    candidate["prid"],
                )

                if not pib_article:
                    continue

                official_url, pib_content = pib_article

                matched = await _verify_pib_article(
                    article=article,
                    claim=extracted["claim"],
                    pib_title=candidate["title"],
                    pib_content=pib_content,
                )

                if matched:

                    logger.info(
                        "Verified PIB source PRID=%s",
                        candidate["prid"],
                    )

                    return official_url

        return None

    except Exception as exc:

        logger.warning(
            "Official source resolver unavailable: %s",
            type(exc).__name__,
        )

        return None
