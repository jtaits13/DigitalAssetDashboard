"""Fetch and filter Global Custodian content for crypto / digital-asset custody headlines."""

from __future__ import annotations

import html as html_module
import re
from datetime import datetime, timezone
from typing import Any
from urllib.request import Request, urlopen

import feedparser

from news_feeds import cap_market_news_per_day, extract_summary, parse_entry_date

GLOBAL_CUSTODIAN_SOURCE = "Global Custodian"
GLOBAL_CUSTODIAN_SITE = "https://www.globalcustodian.com/"

# Main site feed is only the latest ~10 posts (often awards); specialist feeds + search cover the archive.
GLOBAL_CUSTODIAN_RSS_FEEDS: list[tuple[str, bool]] = [
    # (url, trust_category — skip keyword gate; feed is already topical)
    ("https://www.globalcustodian.com/category/digital-asset-servicing/feed/", True),
    ("https://www.globalcustodian.com/digital-asset-servicing/feed/", True),
    ("https://www.globalcustodian.com/tag/digital-asset/feed/", True),
    ("https://www.globalcustodian.com/feed/", False),
]

GLOBAL_CUSTODIAN_SEARCH_QUERIES = ("digital asset", "digital asset custody")
GLOBAL_CUSTODIAN_SEARCH_MAX_PAGES = 4

CUSTODIAN_HEADLINES_PER_UTC_DAY = 5
# Site search returns multi-year archive; a 60-day window left too few items on the page.
CUSTODIAN_LOOKBACK_DAYS = 365

_CRYPTO_DA_KW = re.compile(
    r"\b(bitcoin|btc\b|ethereum|eth\b|crypto|cryptocurrencies?|blockchain|"
    r"digital\s+asset|digital\s+assets|tokenis|tokenized|tokenised|stablecoin|"
    r"\bdefi\b|DLT|distributed ledger|web3|NFT|digital\s+fund|digital\s+custod|"
    r"digital\s+asset\s+servic|zodia|wisdomtree\s+digital)\b",
    re.I,
)

_CRYPTO_DA_CATEGORIES = frozenset(
    {
        "digital asset servicing",
        "digital assets",
        "crypto",
        "blockchain",
        "tokenization",
        "tokenisation",
    }
)

_SLUG_DA_HINT = re.compile(
    r"digital-asset|digital-assets|tokenis|stablecoin|blockchain|crypto|zodia|defi",
    re.I,
)

_SKIP_TITLE = re.compile(r"\bgallery\b|\bphotos from\b", re.I)

# Hub / marketing paths surfaced on search pages — not articles.
_SKIP_PATH_SUFFIXES = frozenset(
    {
        "digital-asset-servicing",
        "digital-assets",
        "events",
        "awards",
        "custodians-assets-under-custody",
        "30-to-shape-the-future",
        "securities-review",
        "subscription-services",
        "industry-jobs",
        "thought-leadership",
        "participate",
        "directories",
        "podcasts",
    }
)

_ARTICLE_LINK_RE = re.compile(
    r'href="(https://www\.globalcustodian\.com/[a-z0-9][a-z0-9-]*/)"',
    re.I,
)

_OG_TITLE_RE = re.compile(
    r'<meta\s+[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
    re.I,
)
_OG_TITLE_RE2 = re.compile(
    r'<meta\s+[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:title["\']',
    re.I,
)
_OG_DESC_RE = re.compile(
    r'<meta\s+[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']',
    re.I,
)
_ARTICLE_TIME_RE = re.compile(
    r'<meta\s+[^>]*property=["\']article:published_time["\'][^>]*content=["\']([^"\']+)["\']',
    re.I,
)
_TITLE_TAG_RE = re.compile(r"<title[^>]*>([^<]+)</title>", re.I)

_SUBSCRIBER_MARKERS = (
    "premium content",
    "available to our digital subscribers",
    "become a subscriber",
    "already a subscriber",
    "continue reading",
    "subscriber services",
)

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_DEFAULT_UA = (
    "Mozilla/5.0 (compatible; DigitalAssetsDashboard/1.0; +https://github.com/jtaits13/DigitalAssetDashboard)"
)


def _fetch_html(url: str, *, timeout: int = 12) -> str:
    req = Request(
        url,
        headers={"User-Agent": _BROWSER_UA, "Accept": "text/html,application/xhtml+xml"},
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.read(400_000).decode("utf-8", "replace")


def _entry_categories(entry: Any) -> list[str]:
    raw = getattr(entry, "tags", None) or getattr(entry, "categories", None) or []
    out: list[str] = []
    for t in raw:
        term = getattr(t, "term", None) or getattr(t, "label", None)
        if term:
            out.append(str(term).strip())
    return out


def _entry_blob(entry: Any) -> str:
    title = (getattr(entry, "title", "") or "").strip()
    summary = extract_summary(entry)
    cats = " ".join(_entry_categories(entry))
    return f"{title} {summary} {cats}"


def matches_crypto_digital_asset(entry: Any) -> bool:
    title = (getattr(entry, "title", "") or "").strip()
    if not title or _SKIP_TITLE.search(title):
        return False
    blob = _entry_blob(entry)
    if _CRYPTO_DA_KW.search(blob):
        return True
    for c in _entry_categories(entry):
        if c.lower() in _CRYPTO_DA_CATEGORIES:
            return True
    return False


def _matches_article_dict(row: dict[str, Any]) -> bool:
    title = (row.get("title") or "").strip()
    if not title or _SKIP_TITLE.search(title):
        return False
    link = (row.get("link") or "").strip()
    blob = f"{title} {row.get('summary') or ''} {row.get('category') or ''}"
    if _CRYPTO_DA_KW.search(blob):
        return True
    if link and _SLUG_DA_HINT.search(link):
        return True
    return False


def _path_slug(url: str) -> str:
    path = url.replace(GLOBAL_CUSTODIAN_SITE, "").strip("/")
    return path.split("/")[0] if path else ""


def _is_article_url(url: str) -> bool:
    if not url.startswith(GLOBAL_CUSTODIAN_SITE):
        return False
    slug = _path_slug(url)
    if not slug or slug in _SKIP_PATH_SUFFIXES:
        return False
    if "/" in url.replace(GLOBAL_CUSTODIAN_SITE, "").strip("/"):
        # Only single-segment article permalinks.
        rest = url.replace(GLOBAL_CUSTODIAN_SITE, "").strip("/")
        if rest.count("/") > 0:
            return False
    return True


def _search_page_urls(query: str, max_pages: int) -> list[str]:
    from urllib.parse import quote_plus

    q = quote_plus(query)
    pages: list[str] = []
    for n in range(1, max_pages + 1):
        if n == 1:
            pages.append(f"{GLOBAL_CUSTODIAN_SITE}?s={q}")
        else:
            pages.append(f"{GLOBAL_CUSTODIAN_SITE}page/{n}/?s={q}")
    return pages


def _discover_search_article_links() -> tuple[list[str], list[str]]:
    """Mirror GC site search (?s=digital+asset) — not available via the main RSS feed."""
    errors: list[str] = []
    seen: set[str] = set()
    links: list[str] = []
    for query in GLOBAL_CUSTODIAN_SEARCH_QUERIES:
        for page_url in _search_page_urls(query, GLOBAL_CUSTODIAN_SEARCH_MAX_PAGES):
            try:
                html = _fetch_html(page_url)
            except Exception as exc:
                errors.append(f"GC search page {page_url}: {exc}")
                continue
            found_on_page = 0
            for m in _ARTICLE_LINK_RE.finditer(html):
                url = m.group(1)
                if not _is_article_url(url) or url in seen:
                    continue
                seen.add(url)
                links.append(url)
                found_on_page += 1
            if found_on_page == 0 and "page/" in page_url:
                break
    return links, errors


def _meta_content(html: str, pattern: re.Pattern[str], alt: re.Pattern[str] | None = None) -> str:
    m = pattern.search(html)
    if m:
        return html_module.unescape(m.group(1).strip())
    if alt:
        m2 = alt.search(html)
        if m2:
            return html_module.unescape(m2.group(1).strip())
    return ""


def _parse_published_iso(raw: str) -> datetime | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _article_from_url(url: str) -> dict[str, Any] | None:
    try:
        html = _fetch_html(url)
    except Exception:
        return None
    title = _meta_content(html, _OG_TITLE_RE, _OG_TITLE_RE2)
    if not title:
        m = _TITLE_TAG_RE.search(html)
        title = html_module.unescape(m.group(1).strip()) if m else ""
        title = re.sub(r"\s*[-|]\s*Global Custodian\s*$", "", title, flags=re.I).strip()
    summary = _meta_content(html, _OG_DESC_RE)
    published = _parse_published_iso(_meta_content(html, _ARTICLE_TIME_RE))
    if not title:
        return None
    access = _guess_access_from_summary(summary)
    if access == "unknown" and summary:
        s = summary.lower()
        if any(m in s for m in _SUBSCRIBER_MARKERS):
            access = "subscriber"
    return {
        "title": title,
        "link": url,
        "source": GLOBAL_CUSTODIAN_SOURCE,
        "published": published or datetime.now(timezone.utc),
        "summary": summary,
        "country": "",
        "category": "",
        "access": access,
    }


def _guess_access_from_summary(summary: str) -> str:
    s = (summary or "").lower()
    if any(m in s for m in _SUBSCRIBER_MARKERS):
        return "subscriber"
    if len((summary or "").strip()) > 200:
        return "free"
    return "unknown"


def detect_article_access(link: str, *, rss_summary: str = "") -> str:
    """Return ``free``, ``subscriber``, or ``unknown`` (best-effort HTML check)."""
    link = (link or "").strip()
    if not link:
        return "unknown"
    try:
        html = _fetch_html(link, timeout=10).lower()
    except Exception:
        if rss_summary and len(rss_summary) > 120:
            return "free"
        return "unknown"
    if any(m in html for m in _SUBSCRIBER_MARKERS):
        if "login" in html and "premium" in html:
            return "subscriber"
        if "continue reading" in html and "subscriber" in html:
            return "subscriber"
        if "premium content" in html:
            return "subscriber"
    if 'class="paywall' in html or "data-paywall" in html:
        return "subscriber"
    return "free"


def _parse_gc_entry(entry: Any) -> dict[str, Any] | None:
    link = (getattr(entry, "link", "") or "").strip()
    title = (getattr(entry, "title", "") or "Untitled").strip()
    if not link and not title:
        return None
    summary = extract_summary(entry)
    published = parse_entry_date(entry)
    cats = _entry_categories(entry)
    category = cats[0] if cats else ""
    access = _guess_access_from_summary(summary)
    return {
        "title": title,
        "link": link,
        "source": GLOBAL_CUSTODIAN_SOURCE,
        "published": published,
        "summary": summary,
        "country": "",
        "category": category,
        "access": access,
    }


def _load_rss_candidates() -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    candidates: list[dict[str, Any]] = []
    for feed_url, trust_category in GLOBAL_CUSTODIAN_RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
        except Exception as exc:
            errors.append(f"Global Custodian RSS {feed_url}: {exc}")
            continue
        if getattr(parsed, "bozo_exception", None):
            errors.append(f"Global Custodian RSS parse {feed_url}: {parsed.bozo_exception}")
        for entry in getattr(parsed, "entries", []) or []:
            if not trust_category and not matches_crypto_digital_asset(entry):
                continue
            row = _parse_gc_entry(entry)
            if row:
                candidates.append(row)
    return candidates, errors


def load_custodian_articles(
    *,
    per_day_cap: int = CUSTODIAN_HEADLINES_PER_UTC_DAY,
    include_search: bool = True,
) -> tuple[list[dict[str, Any]], list[str]]:
    """GC RSS (topic feeds + filtered main feed) plus site search discovery."""
    errors: list[str] = []
    candidates, rss_errs = _load_rss_candidates()
    errors.extend(rss_errs)

    if include_search:
        search_links, search_errs = _discover_search_article_links()
        errors.extend(search_errs)
        existing = {a.get("link") for a in candidates if a.get("link")}
        for url in search_links:
            if url in existing:
                continue
            row = _article_from_url(url)
            if not row or not _matches_article_dict(row):
                continue
            candidates.append(row)
            existing.add(url)

    # Dedupe by link
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for row in candidates:
        key = (row.get("link") or row.get("title") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(row)

    def _pub_key(r: dict[str, Any]) -> datetime:
        p = r.get("published")
        if isinstance(p, datetime):
            return p if p.tzinfo else p.replace(tzinfo=timezone.utc)
        return datetime.min.replace(tzinfo=timezone.utc)

    unique.sort(key=_pub_key, reverse=True)

    if per_day_cap <= 0:
        return unique, errors

    return cap_market_news_per_day(unique, per_day_cap), errors
