"""Fetch and filter RSS feeds for digital-asset regulatory headlines (global)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import streamlit as st

from news_feeds import extract_summary, parse_entry_date

# (display name, rss url, default country/region label, is_official_gov_feed)
REGULATORY_FEEDS: list[tuple[str, str, str, bool]] = [
    ("SEC", "https://www.sec.gov/news/pressreleases.rss", "United States", True),
    ("FCA", "https://www.fca.org.uk/news/rss", "United Kingdom", True),
    ("ECB", "https://www.ecb.europa.eu/rss/press.html", "European Union", True),
    ("Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml", "United States", True),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", "Global", False),
    ("Decrypt", "https://decrypt.co/feed", "Global", False),
]

_CRYPTO_KW = re.compile(
    r"\b(bitcoin|btc\b|ethereum|eth\b|crypto|cryptocurrencies?|blockchain|"
    r"digital asset|digital currency|stablecoin|stablecoins|\bdefi\b|tokenization|\btoken\b|"
    r"\bnft\b|web3|cbdc|virtual currency|decentrali[sz]ed|altcoin|spot bitcoin|"
    r"crypto asset|digital pound|digital euro|e-money|satoshi|proof-of-stake|proof of work)\b",
    re.I,
)

_REGULATORY_KW = re.compile(
    r"\b(regulation|regulatory|enforcement|enforce\b|rulemaking|rule making|compliance|"
    r"policy framework|supervision|directive|bill\b|statute|lawsuit|litigation|"
    r"license|licence|approve|approval|reject|settlement|fine\b|penalty|sanction|"
    r"\bsec\b|cftc\b|\bfca\b|esma\b|court\b|legal action|proposed rule|investigation|"
    r"charges?\b|warning notice|AML|KYC|securities law|market abuse)\b",
    re.I,
)

# Order: more specific regions before broad ones.
_COUNTRY_FROM_TEXT: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(mica|european commission|european union|european parliament|eu regulator)\b", re.I), "European Union"),
    (re.compile(r"\b(japan|japanese|jpx|fsa\b.*japan)\b", re.I), "Japan"),
    (re.compile(r"\b(singapore|mas\b)\b", re.I), "Singapore"),
    (re.compile(r"\b(australia|asic\b|apra\b)\b", re.I), "Australia"),
    (re.compile(r"\b(canada|osc\b|canadian securities)\b", re.I), "Canada"),
    (re.compile(r"\b(india|rbi\b)\b", re.I), "India"),
    (re.compile(r"\b(south korea|korean)\b.*\b(regul|crypto|blockchain)\b", re.I), "South Korea"),
    (re.compile(r"\b(switzerland|finma\b)\b", re.I), "Switzerland"),
    (re.compile(r"\b(united kingdom|u\.k\.|britain|british|fca\b|bank of england)\b", re.I), "United Kingdom"),
    (re.compile(r"\b(united states|u\.s\.|u\.s\.a\.|american\b.*\b(sec|cftc|treasury|fed)\b|cftc\b|federal reserve)\b", re.I), "United States"),
]

_URL_COUNTRY: list[tuple[str, ...]] = [
    ("United States", ("sec.gov", "cftc.gov", "federalreserve.gov", "treasury.gov", "fincen.gov")),
    ("United Kingdom", ("fca.org.uk", "bankofengland.co.uk")),
    ("European Union", ("ecb.europa.eu", "europa.eu/commission", "esma.europa.eu")),
]


def _text_blob(title: str, summary: str) -> str:
    return f"{title} {summary}"


def _matches_digital_asset(title: str, summary: str) -> bool:
    return bool(_CRYPTO_KW.search(_text_blob(title, summary)))


def _matches_regulatory_angle(title: str, summary: str) -> bool:
    return bool(_REGULATORY_KW.search(_text_blob(title, summary)))


def _include_item(title: str, summary: str, is_gov_feed: bool) -> bool:
    if not _matches_digital_asset(title, summary):
        return False
    if is_gov_feed:
        return True
    return _matches_regulatory_angle(title, summary)


def infer_country(title: str, summary: str, link: str, feed_default: str) -> str:
    u = (link or "").lower()
    for label, needles in _URL_COUNTRY:
        if any(n in u for n in needles):
            return label
    blob = _text_blob(title, summary)
    for rx, label in _COUNTRY_FROM_TEXT:
        if rx.search(blob):
            return label
    if feed_default and feed_default != "Global":
        return feed_default
    return "Global"


def _one_entry(
    entry: Any,
    source_name: str,
    feed_default: str,
    is_gov_feed: bool,
) -> dict[str, Any] | None:
    link = getattr(entry, "link", "") or ""
    title = (getattr(entry, "title", "") or "Untitled").strip()
    if not link and not title:
        return None
    summary = extract_summary(entry)
    if not _include_item(title, summary, is_gov_feed):
        return None
    pub = parse_entry_date(entry)
    country = infer_country(title, summary, link, feed_default)
    return {
        "title": title,
        "link": link,
        "source": source_name,
        "published": pub,
        "summary": summary,
        "country": country,
    }


@st.cache_data(ttl=300, show_spinner=False)
def load_regulatory_articles() -> tuple[list[dict[str, Any]], list[str]]:
    """Load, filter, dedupe, and sort regulatory headlines (newest first)."""
    combined: list[dict[str, Any]] = []
    errors: list[str] = []
    for source_name, url, feed_default, is_gov in REGULATORY_FEEDS:
        try:
            parsed = feedparser.parse(url)
            for entry in getattr(parsed, "entries", []) or []:
                row = _one_entry(entry, source_name, feed_default, is_gov)
                if row:
                    combined.append(row)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{source_name}: {e!s}")
    combined.sort(
        key=lambda x: x["published"] if isinstance(x["published"], datetime) else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for a in combined:
        key = (a.get("link") or a.get("title") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(a)
    return unique, errors
