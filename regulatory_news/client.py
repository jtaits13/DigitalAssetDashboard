"""Fetch and filter RSS feeds for digital-asset regulatory headlines (global)."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import feedparser
import streamlit as st

from news_feeds import cap_market_news_per_day, extract_summary, parse_entry_date

# Ranked cap per UTC calendar day (same scoring heuristic as market-news ``cap_market_news_per_day``).
REGULATORY_HEADLINES_PER_UTC_DAY = 5

# (display name, rss url, default country/region label, is_official_gov_feed)
#
# Official feeds still require a crypto / digital-asset keyword match (see ``_CRYPTO_KW``) so generic macro releases
# stay out. Supplemental Google News feeds are ``is_gov=False``: crypto + regulatory/policy keyword required.
REGULATORY_FEEDS: list[tuple[str, str, str, bool]] = [
    ("SEC", "https://www.sec.gov/news/pressreleases.rss", "United States", True),
    (
        "Federal Register (SEC releases)",
        "https://www.federalregister.gov/articles/search.rss?conditions%5Bagency_ids%5D%5B%5D=466&order=newest",
        "United States",
        True,
    ),
    (
        "CFTC (Federal Register · proposed rules)",
        "https://comments.cftc.gov/handlers/RSSHandler.ashx?type=Releases&category=Proposed%20Rule",
        "United States",
        True,
    ),
    (
        "CFTC (Federal Register · final rules)",
        "https://comments.cftc.gov/handlers/RSSHandler.ashx?type=Releases&category=Final%20Rule",
        "United States",
        True,
    ),
    ("FCA", "https://www.fca.org.uk/news/rss", "United Kingdom", True),
    ("ECB", "https://www.ecb.europa.eu/rss/press.html", "European Union", True),
    ("Federal Reserve", "https://www.federalreserve.gov/feeds/press_all.xml", "United States", True),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", "Global", False),
    ("Decrypt", "https://decrypt.co/feed", "Global", False),
    (
        "Google News (US · SEC crypto policy)",
        "https://news.google.com/rss/search?q=SEC+cryptocurrency+regulation+United+States&hl=en-US&gl=US&ceid=US:en",
        "United States",
        False,
    ),
    (
        "Google News (US · digital asset legislation)",
        "https://news.google.com/rss/search?q=digital+asset+crypto+bill+Congress+Senate&hl=en-US&gl=US&ceid=US:en",
        "United States",
        False,
    ),
    (
        "Google News (US · stablecoin Treasury)",
        "https://news.google.com/rss/search?q=stablecoin+regulation+US+Treasury+FinCEN&hl=en-US&gl=US&ceid=US:en",
        "United States",
        False,
    ),
    (
        "Google News (US · CFTC crypto commodities)",
        "https://news.google.com/rss/search?q=CFTC+cryptocurrency+digital+commodity+bitcoin&hl=en-US&gl=US&ceid=US:en",
        "United States",
        False,
    ),
    (
        "Google News (US · banking OCC custody)",
        "https://news.google.com/rss/search?q=OCC+bank+crypto+custody+digital+asset+United+States&hl=en-US&gl=US&ceid=US:en",
        "United States",
        False,
    ),
]

_CRYPTO_KW = re.compile(
    r"\b(bitcoin|btc\b|ethereum|eth\b|crypto|cryptocurrencies?|blockchain|"
    r"digital asset|digital assets|digital currency|stablecoin|stablecoins|\bdefi\b|tokenization|\btoken\b|"
    r"\bnft\b|web3|cbdc|virtual currency|decentrali[sz]ed|altcoin|spot bitcoin|digital commodities?|"
    r"crypto asset|digital pound|digital euro|e-money|satoshi|proof-of-stake|proof of work|\betf\b|\betps?\b)\b",
    re.I,
)

_REGULATORY_KW = re.compile(
    r"\b(regulation|regulatory|enforcement|enforce\b|rulemaking|rule making|compliance|"
    r"policy|policies|policy framework|guidance|guidelines|interpretive|oversight|supervision|directive|"
    r"legislation|legislative|statute|bill\b|congress|senate|house of representatives|\bhouse\b.*\bcommittee\b|"
    r"hearing|markup|executive order|working group|market structure|framework|"
    r"lawsuit|litigation|license|licence|approve|approval|reject|settlement|fine\b|penalty|sanction|"
    r"\bsec\b|cftc\b|\bfincen\b|\bocc\b|\bfdic\b|\btreasury\b|\bfca\b|esma\b|court\b|legal action|"
    r"proposed rule|final rule|notice of proposed rulemaking|\bnprm\b|investigation|"
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
    (
        "United States",
        (
            "sec.gov",
            "cftc.gov",
            "federalreserve.gov",
            "treasury.gov",
            "fincen.gov",
            "federalregister.gov",
            "comments.cftc.gov",
            "occ.gov",
            "fdic.gov",
        ),
    ),
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


def _load_one_regulatory_source(
    source_name: str,
    url: str,
    feed_default: str,
    is_gov: bool,
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        parsed = feedparser.parse(url)
        out: list[dict[str, Any]] = []
        for entry in getattr(parsed, "entries", []) or []:
            row = _one_entry(entry, source_name, feed_default, is_gov)
            if row:
                out.append(row)
        return out, None
    except Exception as e:  # noqa: BLE001
        return [], f"{source_name}: {e!s}"


@st.cache_data(ttl=300, show_spinner=False)
def load_regulatory_articles() -> tuple[list[dict[str, Any]], list[str]]:
    """Load, filter, dedupe, cap at ``REGULATORY_HEADLINES_PER_UTC_DAY`` ranked items per UTC day, sort newest first."""
    combined: list[dict[str, Any]] = []
    errors: list[str] = []
    feeds = REGULATORY_FEEDS
    n = len(feeds)
    if n == 0:
        return combined, errors
    if n == 1:
        (source_name, url, feed_default, is_gov) = feeds[0]
        rows, err = _load_one_regulatory_source(source_name, url, feed_default, is_gov)
        combined.extend(rows)
        if err:
            errors.append(err)
    else:
        max_w = min(12, n)
        with ThreadPoolExecutor(max_workers=max_w) as ex:
            futs = {
                ex.submit(_load_one_regulatory_source, sn, url, fd, is_gov): sn
                for (sn, url, fd, is_gov) in feeds
            }
            for fut in as_completed(futs):
                rows, err = fut.result()
                combined.extend(rows)
                if err:
                    errors.append(err)
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

    capped = cap_market_news_per_day(unique, max_per_day=REGULATORY_HEADLINES_PER_UTC_DAY)
    capped.sort(
        key=lambda x: x["published"]
        if isinstance(x["published"], datetime)
        else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return capped, errors
