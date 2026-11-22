
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
from pypdf import PdfReader
import re
import xml.etree.ElementTree as ET
import unicodedata
from difflib import SequenceMatcher
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from dotenv import load_dotenv
from groq import AsyncGroq, RateLimitError


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logger = logging.getLogger("muni48.official_source_resolver")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
).strip()


# ============================================================
# CONFIGURATION
# ============================================================

PIB_BASE_URL = "https://www.pib.gov.in/"

# English and Hindi PIB archives
PIB_ALL_RELEASES_URLS = (
    (
        "1",
        "https://www.pib.gov.in/AllRelease.aspx?lang=1&reg=48",
    ),
    (
        "2",
        "https://www.pib.gov.in/AllReleasem.aspx?lang=2&reg=48",
    ),
)

PIB_LINKS_FILE = (
    Path(__file__).resolve().parents[2]
    / "pib_release_links.json"
)

ALLOWED_DOMAINS = (
    "gov.in",
    "nic.in",
    "rbi.org.in",
)

REQUEST_TIMEOUT = 20.0

MAX_RESPONSE_BYTES = 2_000_000

MAX_PAGE_CHARS = 4000
MAX_GENERIC_PAGE_CHARS = 14000

MAX_SCI_PDF_BYTES = 8_000_000

MAX_SCI_PDF_PAGES = 12

MAX_PIB_CANDIDATES = 2

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
                raise RuntimeError("GROQ_API_KEY is missing")

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
        if parsed.port not in (None, 443):
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
            and parsed.port in (None, 443)
            and not parsed.username
            and not parsed.password
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
            location = response.headers.get("location")

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

async def _safe_get_sitemap(
    client: httpx.AsyncClient,
    url: str,
) -> httpx.Response | None:

    current_url = url

    for _ in range(6):

        if not _is_official_domain(current_url):
            return None

        parsed = urlparse(current_url)

        if parsed.scheme != "https":
            return None

        if parsed.username or parsed.password:
            return None

        if parsed.port not in (None, 443):
            return None

        try:
            response = await client.get(
                current_url,
                follow_redirects=False,
            )

        except httpx.HTTPError as exc:
            logger.warning(
                "Sitemap request failed: %s",
                exc,
            )
            return None

        if response.status_code in (
            301, 302, 303, 307, 308
        ):
            location = response.headers.get("location")

            if not location:
                return None

            next_url = urljoin(
                str(response.url),
                location,
            )

            if not _is_official_domain(next_url):
                return None

            current_url = next_url
            continue

        if response.status_code != 200:
            return None

        if len(response.content) > MAX_SITEMAP_BYTES:
            logger.warning(
                "Sitemap response too large"
            )
            return None

        content_type = response.headers.get(
            "content-type",
            "",
        ).lower()

        body_start = response.content.lstrip()[:100].lower()

        is_xml = (
            "xml" in content_type
            or body_start.startswith(b"<?xml")
            or body_start.startswith(b"<urlset")
            or body_start.startswith(b"<sitemapindex")
        )

        is_robots = (
            parsed.path.lower().endswith("/robots.txt")
            and (
                "text/plain" in content_type
                or "text/" in content_type
            )
        )

        if not (is_xml or is_robots):
            return None

        return response

    logger.warning(
        "Too many redirects while fetching sitemap"
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
        super().__init__(convert_charrefs=True)

        self.releases = []
        self.href = None
        self.title_parts = []

    def handle_starttag(self, tag, attrs):

        if tag.lower() != "a":
            return

        attrs = dict(attrs)

        href = str(
            attrs.get("href") or ""
        ).strip()

        if not href:
            return

        href_lower = href.lower()

        if "pressrelesedetail" not in href_lower:
            return

        self.href = href
        self.title_parts = []

        title = str(
            attrs.get("title") or ""
        ).strip()

        if title:
            self.title_parts.append(title)

    def handle_data(self, data):

        if self.href is None:
            return

        value = " ".join(
            str(data or "").split()
        )

        if value:
            self.title_parts.append(value)

    def handle_entityref(self, name):

        if self.href is None:
            return

        from html import unescape

        value = unescape(f"&{name};").strip()

        if value:
            self.title_parts.append(value)

    def handle_charref(self, name):

        if self.href is None:
            return

        from html import unescape

        value = unescape(f"&#{name};").strip()

        if value:
            self.title_parts.append(value)

    def handle_endtag(self, tag):

        if tag.lower() != "a" or self.href is None:
            return

        title = " ".join(
            self.title_parts
        ).strip()

        if title:

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

    def handle_starttag(self, tag, attrs):

        if tag != "iframe":
            return

        attrs = dict(attrs)

        if (
            attrs.get("id")
            == "ContentPlaceHolder1_iframepressrealese"
        ):
            self.frame_src = attrs.get("src")


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

    def handle_starttag(self, tag, attrs):

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

class _SCIPDFLinkParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.links = []
        self.current_href = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return

        attrs = dict(attrs)
        href = attrs.get("href")

        if href and self.current_href is None:
            self.current_href = href
            self.current_text = []

    def handle_data(self, data):
        if self.current_href is not None:
            value = " ".join(str(data or "").split())
            if value:
                self.current_text.append(value)

    def handle_endtag(self, tag):
        if tag.lower() != "a" or self.current_href is None:
            return

        title = " ".join(self.current_text).strip()

        if title:
            self.links.append({
                "title": title,
                "url": self.current_href,
            })

        self.current_href = None
        self.current_text = []

class _PIBArticleParser(HTMLParser):

    TARGET_IDS = {
        "titleh2": "Titleh2",
        "ministryname": "MinistryName",
        "prdatetime": "PrDateTime",
        "pibreleasebody": "pibReleaseBody",
        "ltrdescriptionn": "DescriptionHtml",
        "pdfdiv": "PdfDiv",
        "releaseid": "ReleaseId",
    }

    VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr",
        "img", "input", "link", "meta", "param",
        "source", "track", "wbr",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)

        self.fields = {
            value: [] for value in self.TARGET_IDS.values()
        }

        self.active = []

    def handle_starttag(self, tag, attrs):

        attrs = dict(attrs)

        for item in self.active:
            if tag not in self.VOID_TAGS:
                item["depth"] += 1

        element_id = str(attrs.get("id") or "").strip()

        normalized_id = element_id.rsplit("_", 1)[-1].lower()

        field_name = self.TARGET_IDS.get(normalized_id)

        if field_name == "DescriptionHtml" and tag.lower() == "input":
            value = attrs.get("value") or ""
            if value:
                self.fields[field_name].append(str(value))
            return

        if field_name:
            self.active.append({
                "id": field_name,
                "tag": tag,
                "depth": 1,
            })

    def handle_endtag(self, tag):

        completed = []

        for item in self.active:

            if tag not in self.VOID_TAGS:
                item["depth"] -= 1

            if (
                item["depth"] <= 0
                and item["tag"] == tag
            ):
                completed.append(item)

        for item in completed:
            self.active.remove(item)

    def handle_data(self, data):

        value = " ".join(str(data or "").split())

        if not value:
            return

        for item in self.active:
            self.fields[item["id"]].append(value)


# ============================================================
# TEXT NORMALIZATION
# Supports English and Hindi (Devanagari)
# ============================================================

STOP_WORDS = {
    "the", "and", "for", "from", "with",
    "that", "this", "will", "has", "have",
    "into", "its", "their", "about", "over",
    "under", "india", "indian", "shri", "smt",
    "minister", "government", "to", "of",
    "in", "on", "at", "by", "a", "an",
}

def _normalize(value: str) -> str:
    value = unicodedata.normalize(
        "NFC",
        str(value or "").lower(),
    )

    # Preserve Unicode letters, numbers and combining marks.
    normalized = "".join(
        char
        if unicodedata.category(char)[0] in {"L", "N", "M"}
        else " "
        for char in value
    )

    return " ".join(normalized.split())

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

    left = _normalize(article_title)
    right = _normalize(release_title)

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

                if isinstance(data.get(key), list):
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

            prid = _get_prid(absolute_url)

            if not prid:
                continue

            parsed = urlparse(absolute_url)

            query = parsed.query.lower()

            language = (
                "2" if re.search(
                    r"(?:^|&)lang=2(?:&|$)",
                    query,
                ) else "1"
            )

            releases.append({
                "title": str(title).strip(),
                "url": absolute_url,
                "prid": prid,
                "language": language,
            })

        return releases

    except Exception:

        logger.exception(
            "Could not read local PIB release list"
        )

        return []


# ============================================================
# FETCH LIVE PIB RELEASE LIST
# English + Hindi
# ============================================================

async def _fetch_live_releases(
    client: httpx.AsyncClient,
) -> list[dict]:

    releases = []

    for language, archive_url in PIB_ALL_RELEASES_URLS:

        try:

            response = await _safe_get(
                client,
                archive_url,
                pib_only=True,
            )

            if response is None:
                continue

            parser = _ReleaseListParser()

            parser.feed(response.text)
            parser.close()

            archive_count = 0

            for item in parser.releases:

                absolute_url = urljoin(
                    str(response.url),
                    item["url"],
                )

                if not _is_pib_url(absolute_url):
                    continue

                prid = _get_prid(absolute_url)

                if not prid:
                    continue

                releases.append({
                    "title": item["title"],
                    "url": absolute_url,
                    "prid": prid,
                    "language": language,
                })

                archive_count += 1

            logger.info(
                "PIB archive fetched: language=%s releases=%s",
                language,
                archive_count,
            )

        except Exception:

            logger.exception(
                "PIB archive unavailable: language=%s",
                language,
            )

    return releases


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
# Keep the best language/title for each PRID.
# ============================================================

def _rank_releases(
    article_title: str,
    releases: list[dict],
) -> list[dict]:

    best_by_prid = {}

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

        if not prid:
            continue

        score = _title_score(
            article_title,
            title,
        )

        if score < MIN_TITLE_SCORE:
            continue

        candidate = {
            "title": title,
            "url": url,
            "prid": prid,
            "language": str(
                item.get("language") or "1"
            ),
            "score": score,
        }

        previous = best_by_prid.get(prid)

        if (
            previous is None
            or score > previous["score"]
        ):
            best_by_prid[prid] = candidate

    ranked = sorted(
        best_by_prid.values(),
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
        max_completion_tokens=1024,
        reasoning_effort="low",
        include_reasoning=False,
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
                    "Return exactly one valid JSON object with these two keys: "
                    "is_government_claim (boolean) and claim (string). "
                    "Example: {\"is_government_claim\": true, \"claim\": \"...\"}. "
                    "If no specific government claim exists, return "
                    "{\"is_government_claim\": false, \"claim\": \"\"}. "
                    "Do not include markdown, explanations, or extra keys. "
                    "Do not invent facts."
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

    if not response.choices:
        logger.warning(
            "Groq claim extraction returned no choices"
        )
        return {}

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
# FETCH REAL PIB ARTICLE
# Supports English and Hindi
# ============================================================

async def _fetch_pib_article(
    client: httpx.AsyncClient,
    prid: str,
    language: str = "1",
) -> tuple[str, str] | None:

    if not str(prid).isdigit():
        return None

    if language not in {"1", "2"}:
        return None

    if language == "2":

        article_url = (
            f"{PIB_BASE_URL}PressReleseDetailm.aspx"
            f"?PRID={prid}&reg=48&lang=2"
        )

    else:

        article_url = (
            f"{PIB_BASE_URL}PressReleasePage.aspx"
            f"?PRID={prid}&reg=48&lang=1"
        )

    try:

        article_response = await _safe_get(
            client,
            article_url,
            pib_only=True,
        )

        if article_response is None:
            logger.warning(
                "PIB article unavailable: PRID=%s language=%s",
                prid,
                language,
            )
            return None

        final_url = str(article_response.url)

        if not _is_pib_url(final_url):

            logger.warning(
                "PIB article URL validation failed: %s",
                final_url,
            )

            return None

        parser = _PIBArticleParser()

        parser.feed(
            article_response.text[:MAX_RESPONSE_BYTES]
        )

        parser.close()

        def field_text(field_name: str) -> str:

            return " ".join(
                parser.fields.get(field_name, [])
            ).strip()

        title = field_text("Titleh2")

        ministry = field_text("MinistryName")

        posted_on = " ".join(
            field_text("PrDateTime").split()
        )

        if posted_on.lower().startswith("posted on:"):

            posted_on = posted_on.split(
                ":",
                1,
            )[1].strip()

        # PIB stores the complete article in an HTML-encoded
        # hidden input on some Hindi and English release pages.
        description_html = unescape(
            field_text("DescriptionHtml")
        )

        body = ""

        if description_html:
            body_parser = _PIBArticleParser()
            body_parser.feed(
                '<div id="pibReleaseBody">'
                + description_html
                + '</div>'
            )
            body_parser.close()

            body = " ".join(
                body_parser.fields.get("pibReleaseBody", [])
            ).strip()

        # Fallback for PIB layouts that expose article text
        # inside the hidden PDF/print container.
        if len(body) < 150:
            body = field_text("PdfDiv")

        # Keep support for older PIB page layouts.
        if len(body) < 150:
            body = field_text("pibReleaseBody")

        release_id_text = field_text("ReleaseId")

        release_digits = "".join(
            char
            for char in release_id_text
            if char.isdigit()
        )

        # Fallback for PIB layouts where Release ID
        # is visible as ordinary page text.
        if not release_digits:
            release_match = re.search(
                r"(?:Official\s+)?Release\s*ID\s*[:?]?\s*(\d+)",
                article_response.text,
                flags=re.IGNORECASE,
            )

            if release_match:
                release_digits = release_match.group(1)
                release_id_text = release_match.group(0)

        if release_digits != str(prid):
            logger.warning(
                "PIB Release ID mismatch: requested=%s received=%s",
                prid,
                release_id_text,
            )
            return None

        if not title or len(body) < 150:

            logger.warning(
                "PIB article content incomplete: PRID=%s",
                prid,
            )

            return None

        body = body[:MAX_PAGE_CHARS]

        article_text = (
            f"Page title: {title}\n"
            f"Ministry: {ministry}\n"
            f"Posted on: {posted_on}\n"
            f"Release ID: {prid}\n"
            f"Article content:\n{body}"
        )

        logger.info(
            "PIB article fetched: PRID=%s language=%s title=%s",
            prid,
            language,
            title[:120],
        )

        return final_url, article_text

    except Exception:

        logger.exception(
            "PIB article fetch failed: PRID=%s language=%s",
            prid,
            language,
        )

        return None

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
        max_completion_tokens=1024,
        reasoning_effort="low",
        include_reasoning=False,
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

    if not result.choices:
        logger.warning(
            "Groq PIB verification returned no choices"
        )
        return False

    data = _extract_json(
        result.choices[0].message.content or "{}"
    )

    return data.get("matches") is True


# ============================================================
# GENERIC OFFICIAL GOVERNMENT SOURCE FALLBACK
# No Tavily or additional API key required.
# ============================================================

OFFICIAL_SITEMAP_DOMAINS = (
    "upsc.gov.in",
    "bpsc.bihar.gov.in",
    "education.gov.in",
    "mha.gov.in",
    "pmo.gov.in",
    "cag.gov.in",
    "sebi.gov.in",
    "rbi.org.in",
    "sci.gov.in",
)

MAX_SITEMAP_BYTES = 2_000_000
MAX_SITEMAP_FILES = 4
MAX_SITEMAP_URLS = 500
MAX_GENERIC_CANDIDATES = 5





def _has_any(text: str, words) -> bool:
    import re
    for w in words:
        if w.isascii():
            if re.search(r"\b" + re.escape(w) + r"\b", text):
                return True
        elif w in text:
            return True
    return False
def _generic_domains_for_claim(
    article: dict,
    claim: str,
) -> tuple[str, ...]:

    text = _normalize(
        str(article.get("title") or "")
        + " "
        + str(claim or "")
    )

    domains = []

    # UPSC
    if _has_any(text, (
        "upsc",
        "union public service",
        "civil services examination",
        "संघ लोक सेवा आयोग",
        "सिविल सेवा परीक्षा",
    )):
        domains.append("upsc.gov.in")

    # BPSC
    if _has_any(text, (
        "bpsc",
        "bihar public service",
        "बिहार लोक सेवा आयोग",
    )):
        domains.append("bpsc.bihar.gov.in")

    # CAG
    if _has_any(text, (
        "cag",
        "comptroller and auditor general",
        "comptroller auditor general",
        "नियंत्रक एवं महालेखा परीक्षक",
        "कैग",
    )):
        domains.append("cag.gov.in")

    # SEBI
    if _has_any(text, (
        "sebi",
        "securities and exchange board",
        "भारतीय प्रतिभूति और विनिमय बोर्ड",
    )):
        domains.append("sebi.gov.in")

    # RBI
    if _has_any(text, (
        "rbi",
        "reserve bank of india",
        "भारतीय रिजर्व बैंक",
        "भारतीय रिज़र्व बैंक",
    )):
        domains.append("rbi.org.in")

    # Supreme Court
    if _has_any(text, (
        "supreme court of india",
        "supreme court",
        "भारत का सर्वोच्च न्यायालय",
        "सर्वोच्च न्यायालय",
    )):
        domains.append("sci.gov.in")

    # Education
    if _has_any(text, (
        "education",
        "school",
        "university",
        "शिक्षा",
        "विद्यालय",
        "विश्वविद्यालय",
    )):
        domains.append("education.gov.in")

    # Home Ministry
    if _has_any(text, (
        "home ministry",
        "home affairs",
        "security",
        "गृह मंत्रालय",
        "गृह विभाग",
    )):
        domains.append("mha.gov.in")

    # Prime Minister / Cabinet
    if _has_any(text, (
        "prime minister",
        "cabinet",
        "प्रधानमंत्री",
        "मंत्रिमंडल",
    )):
        domains.append("pmo.gov.in")

    # Never use a generic portal as an automatic fallback.
    return tuple(dict.fromkeys(domains))



def _extract_sitemap_locations(
    content: bytes,
) -> tuple[list[str], list[str]]:

    sitemap_urls = []
    page_urls = []

    try:
        root = ET.fromstring(content)

        for element in root.iter():

            if not element.tag.lower().endswith("loc"):
                continue

            value = (element.text or "").strip()

            if not value:
                continue

            if not _is_official_domain(value):
                continue

            path = urlparse(value).path.lower()

            if (
                path.endswith(".xml")
                or "sitemap" in path
            ):
                sitemap_urls.append(value)
            else:
                page_urls.append(value)

    except Exception:
        logger.debug(
            "Could not parse sitemap XML",
            exc_info=True,
        )

    return sitemap_urls, page_urls


async def _discover_official_sitemap_urls(
    client: httpx.AsyncClient,
    domain: str,
) -> list[str]:
    for host in (f"www.{domain}", domain):
        urls = await _discover_official_sitemap_urls_for_host(
            client,
            domain,
            host,
        )
        if urls:
            return urls
    return []


async def _discover_official_sitemap_urls_for_host(
    client: httpx.AsyncClient,
    domain: str,
    host: str,
) -> list[str]:

    base_url = f"https://{host}/"

    def belongs_to_domain(url: str) -> bool:

        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()

        return (
            parsed.scheme == "https"
            and not parsed.username
            and not parsed.password
            and parsed.port in (None, 443)
            and (
                host == domain
                or host.endswith("." + domain)
            )
        )

    sitemap_queue = []
    discovered_pages = []

    # First discover sitemap declarations in robots.txt.
    robots_response = await _safe_get_sitemap(
        client,
        urljoin(base_url, "robots.txt"),
    )

    if robots_response is not None:

        for line in robots_response.text.splitlines():

            if line.lower().startswith("sitemap:"):

                sitemap_url = line.split(":", 1)[1].strip()

                if belongs_to_domain(sitemap_url):
                    sitemap_queue.append(sitemap_url)

    # Standard sitemap locations.
    sitemap_queue.extend([
        urljoin(base_url, "sitemap.xml"),
        urljoin(base_url, "sitemap_index.xml"),
    ])

    visited_sitemaps = set()

    while (
        sitemap_queue
        and len(visited_sitemaps) < MAX_SITEMAP_FILES
        and len(discovered_pages) < MAX_SITEMAP_URLS
    ):

        sitemap_url = sitemap_queue.pop(0)

        if sitemap_url in visited_sitemaps:
            continue

        visited_sitemaps.add(sitemap_url)

        response = await _safe_get_sitemap(
            client,
            sitemap_url,
        )

        if response is None:
            continue

        nested, pages = _extract_sitemap_locations(
            response.content
        )

        for nested_url in nested:

            if (
                belongs_to_domain(nested_url)
                and nested_url not in visited_sitemaps
                and len(visited_sitemaps)
                + len(sitemap_queue)
                < MAX_SITEMAP_FILES
            ):
                sitemap_queue.append(nested_url)

        remaining = MAX_SITEMAP_URLS - len(discovered_pages)

        if remaining > 0:
            for page_url in pages:
                if belongs_to_domain(page_url):
                    discovered_pages.append(page_url)

                    if len(discovered_pages) >= MAX_SITEMAP_URLS:
                        break

    # Only URLs belonging to the domain being searched.
    result = []

    for url in discovered_pages:

        parsed_url = urlparse(url)
        host = (parsed_url.hostname or "").lower()
        path = parsed_url.path.lower()

        # Skip static media and frontend assets.
        blocked_extensions = (
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            ".svg",
            ".ico",
            ".avif",
            ".css",
            ".js",
            ".woff",
            ".woff2",
            ".ttf",
            ".eot",
            ".mp3",
            ".mp4",
            ".webm",
        )

        if path.endswith(blocked_extensions):
            continue

        # Reject homepage and root URLs.
        if path in ("", "/"):
            continue

        # Accept only pages from the searched official domain.
        if host == domain or host.endswith("." + domain):
            result.append(url)

    return list(dict.fromkeys(result))[:MAX_SITEMAP_URLS]
async def _fetch_generic_official_page(
    client: httpx.AsyncClient,
    url: str,
) -> tuple[str, str] | None:

    response = await _safe_get(
        client,
        url,
    )

    if response is None:
        return None

    # Validate the final URL after redirects.
    final_url = str(response.url)

    if not _is_official_domain(final_url):
        return None

    parsed_url = urlparse(final_url)

    if parsed_url.scheme != "https":
        return None

    if parsed_url.username or parsed_url.password:
        return None

    if parsed_url.port not in (None, 443):
        return None

    parser = _ArticleParser()

    try:
        parser.feed(
            response.text[:MAX_RESPONSE_BYTES]
        )
        parser.close()

    except Exception:
        return None

    title = " ".join(parser.title_parts).strip()
    body = " ".join(parser.text_parts).strip()

    if not title or len(body) < 200:
        return None

    # Reject pages with generic or missing titles.
    normalized_title = _normalize(title)

    if normalized_title in (
        "",
        "home",
        "homepage",
        "welcome",
        "official website",
        "government of india",
    ):
        return None

    content = (
        f"Official page title: {title}\n"
        f"Official page URL: {final_url}\n"
        f"Official page content:\n{body[:MAX_PAGE_CHARS]}"
    )

    return final_url, content


def _relevant_excerpt(
    page_text: str,
    claim: str,
    limit: int,
) -> str:
    """Keep the page header, then the paragraphs most relevant to the claim."""

    if len(page_text) <= limit:
        return page_text

    head = page_text[:1500]
    rest = page_text[1500:]

    words = {
        w for w in re.findall(r"[a-z0-9]{4,}", claim.lower())
    }

    paragraphs = [
        para.strip()
        for para in re.split(r"\n\s*\n|(?<=\.)\s*\n", rest)
        if para.strip()
    ]

    scored = []
    for index, para in enumerate(paragraphs):
        low = para.lower()
        score = sum(1 for w in words if w in low)
        scored.append((score, index, para))

    budget = limit - len(head) - 50
    chosen = []

    for score, index, para in sorted(scored, key=lambda t: (-t[0], t[1])):
        if score == 0 or budget <= 0:
            break
        chosen.append((index, para[:900]))
        budget -= len(para[:900]) + 2

    chosen.sort()

    return head + "\n...\n" + "\n\n".join(t for _, t in chosen)


async def _verify_generic_official_page(
    article: dict,
    claim: str,
    page_content: str,
) -> bool:

    # Basic evidence checks before using AI.
    if not claim or len(claim.strip()) < 20:
        return False

    if not page_content or len(page_content.strip()) < 200:
        return False

    page_text = page_content.strip()

    # The page must contain a real title and its official URL.
    if "Official page title:" not in page_text:
        return False

    if "Official page URL:" not in page_text:
        return False

    groq = await _get_groq_client()

    result = await groq.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0,
        max_completion_tokens=700,
        reasoning_effort="low",
        include_reasoning=False,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict Indian government source verifier. "
                    "Your task is to verify whether an official government "
                    "webpage provides direct evidence for the exact factual "
                    "claim in a news article. "
                    "A shared topic, ministry, person, department, or "
                    "keyword is NOT evidence. "
                    "Check whether the page itself supports the specific "
                    "event, announcement, decision, order, report, date, "
                    "or numerical fact stated in the claim. "
                    "Do not use outside knowledge. "
                    "Do not assume that a page is relevant merely because "
                    "it belongs to the correct government department. "
                    "If the page is a homepage, general information page, "
                    "unrelated notice, search result, or does not contain "
                    "direct supporting evidence, return matches false. "
                    "A consultation paper, draft or proposal published by the official body counts as direct evidence for a news claim that reports that proposal, even if the news wording says plans, proposes or introduced. "
                    "Ignore small wording differences in verbs and job titles; check the subject, the institution and the key figures. "
                    "If any important part of the claim is unsupported, "
                    "return matches false. "
                    'Return JSON only: {"matches": true} or '
                    '{"matches": false}.'
                ),
            },
            {
                "role": "user",
                "content": (
                    "NEWS TITLE:\n"
                    + str(article.get("title") or "")[:500]
                    + "\n\nNEWS DESCRIPTION:\n"
                    + str(
                        article.get("description")
                        or article.get("content")
                        or ""
                    )[:1500]
                    + "\n\nEXTRACTED GOVERNMENT CLAIM:\n"
                    + claim[:1500]
                    + "\n\nOFFICIAL GOVERNMENT PAGE:\n"
                    + _relevant_excerpt(page_text, claim, MAX_GENERIC_PAGE_CHARS)
                ),
            },
        ],
    )

    if not result.choices:
        return False

    raw = (result.choices[0].message.content or "").lower()

    # Plain-text parse: JSON mode is off, so look for the verdict.
    if re.search(r'"matches"\s*:\s*true', raw):
        return True

    return False


async def _safe_get_sci_pdf(
    client: httpx.AsyncClient,
    url: str,
) -> tuple[str, bytes] | None:

    current_url = url
    parsed = urlparse(current_url)

    # Convert SCI HTML PDF viewer URL to actual PDF endpoint.
    if parsed.path.rstrip("/") == "/view-pdf":
        current_url = parsed._replace(
            path="/sci-get-pdf/"
        ).geturl()

    for _ in range(6):

        if not _is_official_domain(current_url):
            return None

        parsed = urlparse(current_url)

        if (
            parsed.scheme != "https"
            or parsed.hostname not in (
                "sci.gov.in",
                "www.sci.gov.in",
            )
            or parsed.port not in (None, 443)
            or parsed.username
            or parsed.password
            or parsed.path.rstrip("/") != "/sci-get-pdf"
        ):
            return None

        response = await client.get(
            current_url,
            follow_redirects=False,
        )

        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("location")

            if not location:
                return None

            current_url = urljoin(
                str(response.url),
                location,
            )
            continue

        response.raise_for_status()

        if len(response.content) > MAX_SCI_PDF_BYTES:
            logger.warning("Supreme Court PDF too large")
            return None

        pdf_start = response.content[:1024].lstrip()

        if not pdf_start.startswith(b"%PDF-"):
            logger.warning(
                "Supreme Court endpoint did not return a PDF: %s",
                current_url,
            )
            return None

        return str(response.url), response.content

    logger.warning("Too many redirects while fetching SCI PDF")
    return None

async def _resolve_sci_pdf_source(
    client: httpx.AsyncClient,
    article: dict,
    claim: str,
) -> str | None:

    homepage_url = "https://www.sci.gov.in/"

    homepage = await _safe_get(
        client,
        homepage_url,
    )

    if homepage is None:
        logger.warning("Supreme Court homepage fetch failed")
        return None

    parser = _SCIPDFLinkParser()
    parser.feed(homepage.text[:MAX_RESPONSE_BYTES])

    candidates = []

    article_title = str(article.get("title") or "")

    for item in parser.links:

        pdf_url = urljoin(
            str(homepage.url),
            item["url"],
        )

        parsed = urlparse(pdf_url)

        if (
            parsed.scheme != "https"
            or parsed.hostname not in (
                "sci.gov.in",
                "www.sci.gov.in",
            )
            or parsed.path.rstrip("/") != "/view-pdf"
            or not _is_official_domain(pdf_url)
        ):
            continue

        title = item["title"]

        score = max(
            _title_score(article_title, title),
            _title_score(claim, title),
        )

        if score >= 0.12:
            candidates.append({
                "url": pdf_url,
                "title": title,
                "score": score,
            })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    candidates = candidates[:MAX_GENERIC_CANDIDATES]

    logger.info(
        "Supreme Court PDF candidates shortlisted: %s",
        len(candidates),
    )

    for candidate in candidates:

        logger.info(
            "Checking Supreme Court PDF: %s",
            candidate["url"],
        )

        result = await _safe_get_sci_pdf(
            client,
            candidate["url"],
        )

        if result is None:
            continue

        pdf_url, pdf_bytes = result

        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))

            if reader.is_encrypted:
                logger.info("Skipping encrypted SCI PDF")
                continue

            page_text = []

            for page in reader.pages[:MAX_SCI_PDF_PAGES]:
                text = page.extract_text() or ""

                if text.strip():
                    page_text.append(text)

            extracted_text = "\n".join(page_text).strip()

        except Exception:
            logger.exception(
                "Supreme Court PDF text extraction failed"
            )
            continue

        if len(extracted_text) < 200:
            logger.info(
                "SCI PDF has insufficient extractable text: %s",
                pdf_url,
            )
            continue

        page_content = (
            "Official page title: "
            + candidate["title"]
            + "\nOfficial page URL: "
            + pdf_url
            + "\nOfficial page content:\n"
            + extracted_text[:MAX_PAGE_CHARS]
        )

        matched = await _verify_generic_official_page(
            article=article,
            claim=claim,
            page_content=page_content,
        )

        logger.info(
            "Supreme Court PDF verification: matched=%s url=%s",
            matched,
            pdf_url,
        )

        if matched:
            logger.info(
                "Verified Supreme Court PDF source: %s",
                pdf_url,
            )
            return pdf_url

    return None

OFFICIAL_LISTING_PAGES = {
    "sebi.gov.in": (
        "https://" + "www." + "sebi.gov.in"
        + "/sebiweb/home/HomeAction.do?doListingAll=yes",
    ),
}

LISTING_PATH_HINTS = (
    "/media-and-notifications/",
    "/legal/",
    "/reports-and-statistics/",
)


async def _discover_listing_urls(
    client: httpx.AsyncClient,
    domain: str,
) -> list[str]:
    """Collect recent item links from an official listing page."""

    found: list[str] = []

    for page_url in OFFICIAL_LISTING_PAGES.get(domain, ()):

        response = await _safe_get(client, page_url)

        if response is None:
            logger.info("Listing page fetch failed: %s", page_url)
            continue

        for href in re.findall(
            r'href="([^"]+\.html)"',
            response.text[:MAX_RESPONSE_BYTES],
        ):
            full = urljoin(page_url, href)
            parsed = urlparse(full)
            host = (parsed.hostname or "").lower()

            if (
                parsed.scheme == "https"
                and (host == domain or host.endswith("." + domain))
                and any(h in parsed.path for h in LISTING_PATH_HINTS)
                and full not in found
            ):
                found.append(full)

    logger.info(
        "Listing discovery: domain=%s items=%s", domain, len(found)
    )
    return found[:200]


async def _append_linked_pdf_text(
    client: httpx.AsyncClient,
    page_url: str,
    page_content: str,
) -> str:
    """Append text of a PDF embedded via a viewer link (web/?file=...pdf)."""

    try:
        response = await _safe_get(client, page_url)

        if response is None:
            return page_content

        match = re.search(
            r"file=(https?://[^'\"&\s]+\.pdf)",
            response.text[:MAX_RESPONSE_BYTES],
        )

        if not match:
            return page_content

        current = match.group(1)
        pdf_bytes = None

        for _ in range(3):

            if not _is_official_domain(current):
                return page_content

            pdf_response = await client.get(current)

            if pdf_response.is_redirect:
                location = pdf_response.headers.get("location")
                if not location:
                    return page_content
                current = urljoin(current, location)
                continue

            if pdf_response.status_code != 200:
                return page_content

            pdf_bytes = pdf_response.content
            break

        if (
            not pdf_bytes
            or len(pdf_bytes) > 15_000_000
            or not pdf_bytes[:1024].lstrip().startswith(b"%PDF-")
        ):
            return page_content

        def _extract() -> str:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            return "\n".join(
                (pg.extract_text() or "")
                for pg in reader.pages[:25]
            )

        text = (await asyncio.to_thread(_extract)).strip()

        if not text:
            return page_content

        logger.info(
            "Linked PDF text appended: %s chars=%s",
            current,
            len(text),
        )

        return (
            page_content
            + "\n\nLinked official PDF text:\n"
            + text[:60000]
        )

    except Exception:
        logger.warning(
            "Linked PDF extraction failed: %s",
            page_url,
            exc_info=True,
        )
        return page_content


def _is_recent_dated_url(url: str, max_days: int = 100) -> bool:
    """True when the path has /mmm-yyyy/ and that month is recent."""

    from datetime import datetime

    months = "jan feb mar apr may jun jul aug sep oct nov dec".split()
    match = re.search(
        r"/(" + "|".join(months) + r")-(\d{4})/",
        urlparse(url).path.lower(),
    )

    if not match:
        return False

    month = months.index(match.group(1)) + 1
    item_date = datetime(int(match.group(2)), month, 1)

    return (datetime.utcnow() - item_date).days <= max_days


async def _resolve_generic_official_source(
    client: httpx.AsyncClient,
    article: dict,
    claim: str,
) -> str | None:

    domains = _generic_domains_for_claim(
        article,
        claim,
    )

    article_title = str(
        article.get("title") or ""
    )

    logger.info(
        "Generic source domains selected: %s",
        domains,
    )

    if not domains:
        logger.info(
            "No official domain matched the article"
        )
        return None

    candidates = []

    for domain in domains:
        if domain == "sci.gov.in":

            sci_source = await _resolve_sci_pdf_source(
                client=client,
                article=article,
                claim=claim,
            )

            if sci_source:
                return sci_source

            logger.info(
                "No verified Supreme Court PDF source found"
            )
            continue
        urls = await _discover_official_sitemap_urls(
            client,
            domain,
        )
        urls = list(dict.fromkeys(
            list(await _discover_listing_urls(client, domain)) + list(urls)
        ))

        logger.info(
            "Official sitemap discovery: domain=%s pages=%s",
            domain,
            len(urls),
        )

        for url in urls:

            if (
                domain in OFFICIAL_LISTING_PAGES
                and not _is_recent_dated_url(url)
            ):
                continue

            path_text = (
                urlparse(url).path
                .replace("/", " ")
                .replace("-", " ")
                .replace("_", " ")
            )

            score = max(
                _title_score(article_title, path_text),
                _title_score(claim, path_text),
            )

            search_text = (
                article_title + " "
                + claim + " "
                + str(
                    article.get("description")
                    or article.get("content")
                    or ""
                )
            ).lower()

            is_exam_calendar_news = (
                "exam calendar" in search_text
                or "examination calendar" in search_text
                or "exam date" in search_text
                or "परीक्षा कैलेंडर" in search_text
            )

            is_exam_calendar_page = (
                "exam-calendar" in urlparse(url).path.lower()
                or "exam calendar" in path_text.lower()
            )

            if (
                is_exam_calendar_news
                and is_exam_calendar_page
            ):
                score += 1.0

            if score >= 0.12:
                candidates.append({
                    "url": url,
                    "score": score,
                })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    candidates = candidates[:MAX_GENERIC_CANDIDATES]

    logger.info(
        "Generic official candidates shortlisted: %s",
        len(candidates),
    )

    for candidate in candidates:

        logger.info(
            "Checking official candidate: %s",
            candidate["url"],
        )

        page = await _fetch_generic_official_page(
            client,
            candidate["url"],
        )

        if page is None:
            logger.info(
                "Official candidate page fetch failed: %s",
                candidate["url"],
            )
            continue

        official_url, page_content = page

        if not _is_official_domain(official_url):
            continue

        page_content = await _append_linked_pdf_text(
            client,
            official_url,
            page_content,
        )

        try:
            matched = await _verify_generic_official_page(
                article=article,
                claim=claim,
                page_content=page_content,
            )
        except RateLimitError:
            raise
        except Exception:
            logger.warning(
                "Generic verification failed; skipping candidate: %s",
                official_url,
                exc_info=True,
            )
            continue

        logger.info(
            "Official candidate verification: matched=%s url=%s",
            matched,
            official_url,
        )

        if matched:
            logger.info(
                "Verified generic government source: %s",
                official_url,
            )
            return official_url

    logger.info(
        "No verified generic government source found"
    )

    return None

# ============================================================
# MAIN RESOLVER
# ============================================================

# ============================================================
# MAIN RESOLVER
# PIB first, then verified generic official source fallback.
# ============================================================

async def resolve_official_source(
    article: dict,
) -> str | None:
    """
    Return an article-specific verified Indian government source.

    Search order:
    1. PIB English and Hindi archives.
    2. Bounded official government sitemap fallback.

    Returns None when no exact official source is verified.
    """

    if not isinstance(article, dict):
        return None

    article_title = str(
        article.get("title") or ""
    ).strip()

    if len(article_title) < 8:
        return None

    try:
        try:
            extracted = await _extract_claim(article)

        except RateLimitError:
            raise

        except Exception:
            logger.warning(
                "Groq claim extraction failed; "
                "using article text fallback: %s",
                article_title[:120],
                exc_info=True,
            )
            extracted = {}

        if not isinstance(extracted, dict):
            extracted = {}

        claim = str(
            extracted.get("claim") or ""
        ).strip()

        if not claim:
            description = str(
                article.get("description")
                or article.get("content")
                or ""
            ).strip()

            claim = (
                article_title + "\n" + description
            ).strip()[:1500]

            logger.info(
                "Groq claim unavailable; "
                "using article text for strict verification: %s",
                article_title[:120],
            )

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
                "text/html,application/xhtml+xml,"
                "application/xml,text/xml,text/plain"
            ),
        }

        async with httpx.AsyncClient(
            timeout=timeout,
            headers=headers,
            follow_redirects=False,
            max_redirects=0,
        ) as client:

            # FIRST: PIB ENGLISH + HINDI ARCHIVES

            live_releases = await _fetch_live_releases(
                client
            )

            local_releases = _load_local_releases()

            combined = (
                live_releases + local_releases
            )

            candidates = _rank_releases(
                article_title,
                combined,
            )

            if not combined:
                logger.info(
                    "No PIB releases available; "
                    "trying generic official sources"
                )

            elif not candidates:
                logger.info(
                    "No PIB title match; "
                    "trying generic official sources"
                )

            else:
                for candidate in candidates:

                    pib_article = await _fetch_pib_article(
                        client,
                        candidate["prid"],
                        candidate["language"],
                    )

                    if not pib_article:
                        continue

                    official_url, pib_content = pib_article

                    matched = await _verify_pib_article(
                        article=article,
                        claim=claim,
                        pib_title=candidate["title"],
                        pib_content=pib_content,
                    )

                    if matched:
                        logger.info(
                            "Verified PIB source "
                            "PRID=%s language=%s",
                            candidate["prid"],
                            candidate["language"],
                        )

                        return official_url

            # SECOND: GENERIC OFFICIAL GOVERNMENT SOURCES

            generic_url = await _resolve_generic_official_source(
                client=client,
                article=article,
                claim=claim,
            )

            if (
                generic_url
                and _is_official_domain(generic_url)
            ):
                return generic_url

        logger.info(
            "No exact official government source verified: %s",
            article_title[:120],
        )

        return None


    except RateLimitError:
        logger.warning(
            "Groq rate limit reached; source check will be retried later"
        )
        raise

    except Exception:
        logger.exception(
            "Official source resolver failed"
        )
        return None