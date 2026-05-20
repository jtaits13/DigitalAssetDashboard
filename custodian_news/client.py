"""Fetch and filter Global Custodian RSS for crypto / digital-asset custody headlines."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.request import Request, urlopen

import feedparser

from news_feeds import cap_market_news_per_day, extract_summary, parse_entry_date

GLOBAL_CUSTODIAN_RSS = "https://www.globalcustodian.com/feed/"
GLOBAL_CUSTODIAN_SOURCE = "Global Custodian"

CUSTODIAN_HEADLINES_PER_UTC_DAY = 5
CUSTODIAN_LOOKBACK_DAYS = 60

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

_SKIP_TITLE = re.compile(r"\bgallery\b|\bphotos from\b", re.I)

_SUBSCRIBER_MARKERS = (
    "premium content",
    "available to our digital subscribers",
    "become a subscriber",
    "already a subscriber",
    "continue reading",
    "subscriber services",
)

_DEFAULT_UA = (
    "Mozilla/5.0 (compatible; DigitalAssetsDashboard/1.0; +https://github.com/jtaits13/DigitalAssetDashboard)"
)


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
        req = Request(
            link,
            headers={"User-Agent": _DEFAULT_UA, "Accept": "text/html"},
        )
        with urlopen(req, timeout=10) as resp:
            html = resp.read(350_000).decode("utf-8", "replace").lower()
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


def load_custodian_articles(
    *,
    per_day_cap: int = CUSTODIAN_HEADLINES_PER_UTC_DAY,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Fetch GC RSS, filter to crypto/digital-asset stories, rank-cap by UTC day."""
    errors: list[str] = []
    try:
        parsed = feedparser.parse(GLOBAL_CUSTODIAN_RSS)
    except Exception as exc:
        return [], [f"Global Custodian RSS: {exc}"]

    if getattr(parsed, "bozo_exception", None):
        errors.append(f"Global Custodian RSS parse: {parsed.bozo_exception}")

    candidates: list[dict[str, Any]] = []
    for entry in getattr(parsed, "entries", []) or []:
        if not matches_crypto_digital_asset(entry):
            continue
        row = _parse_gc_entry(entry)
        if row:
            candidates.append(row)

    def _pub_key(row: dict[str, Any]) -> datetime:
        p = row.get("published")
        if isinstance(p, datetime):
            return p if p.tzinfo else p.replace(tzinfo=timezone.utc)
        return datetime.min.replace(tzinfo=timezone.utc)

    candidates.sort(key=_pub_key, reverse=True)

    if per_day_cap <= 0:
        return candidates, errors

    return cap_market_news_per_day(candidates, per_day_cap), errors
