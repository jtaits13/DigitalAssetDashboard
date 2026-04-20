"""Shared RSS fetch + dedupe for home and All Articles pages."""

from __future__ import annotations

import html as html_module
import re
from datetime import date, datetime, timezone
from html import escape
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import streamlit as st

# Match `h2.home-main-heading` on the home page (Latest Digital Asset News).
HOME_MAIN_HEADING_CSS = """
<style>
h2.home-main-heading {
    font-size: 1.06rem;
    font-weight: 650;
    color: #021D41;
    margin: 0 0 0.25rem 0;
    letter-spacing: -0.02em;
    line-height: 1.3;
}
h3.home-rwa-subheading {
    font-size: 0.98rem;
    font-weight: 650;
    color: #021D41;
    margin: 0.5rem 0 0.4rem 0;
    letter-spacing: -0.012em;
    line-height: 1.35;
}
</style>
"""

# Fixed top strip (home + subpage top bar). price_ticker.py aligns padding with .cd-ticker-shell.
SITE_NAV_CSS = """
<style>
.jd-site-nav-fixed-wrap {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    width: 100%;
    z-index: 999999;
    box-sizing: border-box;
    padding: 0.3rem 1rem 0.4rem 1rem;
    background: #F3F7FB;
    border-bottom: 1px solid #C7D8E8;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
}
.jd-site-nav-inner {
    max-width: min(1200px, 100%);
    margin: 0 auto;
}
.jd-site-nav-spacer {
    height: 4.4rem;
    flex-shrink: 0;
}
html {
    scroll-padding-top: 4.7rem;
}
.jd-site-nav {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.35rem 0.15rem;
    background: #ffffff;
    border: 1px solid #C7D8E8;
    border-radius: 10px;
    padding: 0.5rem 0.85rem 0.55rem 0.85rem;
    margin: 0;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.jd-site-nav .jd-site-brand {
    font-size: 0.95rem;
    font-weight: 800;
    color: #021D41;
    letter-spacing: -0.03em;
    margin-right: 1rem;
    padding-right: 1rem;
    border-right: 1px solid #C7D8E8;
}
.jd-site-nav a.jd-site-link {
    font-size: 0.88rem;
    font-weight: 600;
    color: #1F4C67;
    text-decoration: none;
    padding: 0.4rem 0.75rem;
    border-radius: 8px;
    transition: color 0.15s ease, background 0.15s ease;
}
.jd-site-nav a.jd-site-link:hover {
    color: #25809C;
    background: rgba(37, 128, 156, 0.12);
}
.jd-site-nav a.jd-site-link:active {
    color: #021D41;
}
/* Hover / keyboard-open dropdown (no JS; Streamlit allows injected HTML + CSS) */
.jd-site-nav-fixed-wrap,
.jd-site-nav-inner,
.jd-site-nav {
    overflow: visible;
}
.jd-nav-dd {
    position: relative;
    display: inline-block;
}
.jd-nav-dd-head.jd-site-link {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
}
.jd-nav-dd-caret {
    font-size: 0.65rem;
    opacity: 0.75;
    transform: translateY(1px);
}
.jd-nav-dd-menu {
    display: none;
    position: absolute;
    left: 0;
    top: calc(100% + 4px);
    min-width: 12.5rem;
    margin: 0;
    padding: 0.35rem 0;
    list-style: none;
    background: #ffffff;
    border: 1px solid #C7D8E8;
    border-radius: 10px;
    box-shadow: 0 6px 20px rgba(15, 23, 42, 0.12);
    z-index: 10000000;
}
.jd-nav-dd:hover .jd-nav-dd-menu,
.jd-nav-dd:focus-within .jd-nav-dd-menu {
    display: block;
}
a.jd-nav-dd-item {
    display: block;
    font-size: 0.84rem;
    font-weight: 600;
    color: #1F4C67;
    text-decoration: none;
    padding: 0.45rem 0.95rem;
    line-height: 1.35;
}
a.jd-nav-dd-item:hover {
    color: #25809C;
    background: rgba(37, 128, 156, 0.1);
}
a.jd-nav-dd-item:active {
    color: #021D41;
}
</style>
"""


def render_home_top_bar(key_suffix: str = "page", *, is_landing: bool = False) -> None:
    """
    Fixed top bar + spacer on the landing page (in-page anchors).
    Subpages use ``render_subpage_top_bar()`` instead.
    """
    if not is_landing:
        return

    st.markdown(SITE_NAV_CSS, unsafe_allow_html=True)
    st.markdown(
        """
<div class="jd-site-nav-fixed-wrap">
  <div class="jd-site-nav-inner">
    <nav class="jd-site-nav" aria-label="Page sections">
      <span class="jd-site-brand">JPM Digital</span>
      <a class="jd-site-link" href="/?jd_scroll=top">Home</a>
      <a class="jd-site-link" href="#jd-section-news">News</a>
      <a class="jd-site-link" href="#jd-section-etps">Digital Asset ETPs</a>
      <div class="jd-nav-dd" role="group" aria-label="RWA subsections">
        <a class="jd-site-link jd-nav-dd-head" href="#jd-section-rwa">RWA <span class="jd-nav-dd-caret" aria-hidden="true">▾</span></a>
        <ul class="jd-nav-dd-menu" role="menu">
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="#jd-rwa-market">Market overview</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="#jd-rwa-stablecoins">Stablecoins</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="#jd-rwa-treasuries">US Treasuries</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="#jd-rwa-tokenized-stocks">Tokenized stocks</a></li>
        </ul>
      </div>
    </nav>
  </div>
</div>
<div class="jd-site-nav-spacer" aria-hidden="true"></div>
""",
        unsafe_allow_html=True,
    )


def render_subpage_top_bar() -> None:
    """
    Same fixed banner as the home page. Links go to the main app; News adds ``?jd_scroll=``
    so the home page scrolls to that section after load.
    """
    st.markdown(SITE_NAV_CSS, unsafe_allow_html=True)
    st.markdown(
        """
<div class="jd-site-nav-fixed-wrap">
  <div class="jd-site-nav-inner">
    <nav class="jd-site-nav" aria-label="Page sections">
      <span class="jd-site-brand">JPM Digital</span>
      <a class="jd-site-link" href="/?jd_scroll=top">Home</a>
      <a class="jd-site-link" href="/?jd_scroll=news">News</a>
      <a class="jd-site-link" href="/?jd_scroll=etps">Digital Asset ETPs</a>
      <div class="jd-nav-dd" role="group" aria-label="RWA pages">
        <a class="jd-site-link jd-nav-dd-head" href="/?jd_scroll=rwa">RWA <span class="jd-nav-dd-caret" aria-hidden="true">▾</span></a>
        <ul class="jd-nav-dd-menu" role="menu">
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="/RWA_League">Market overview</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="/RWA_Stablecoins">Stablecoins</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="/RWA_US_Treasuries">US Treasuries</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="/RWA_Tokenized_Stocks">Tokenized stocks</a></li>
        </ul>
      </div>
    </nav>
  </div>
</div>
<div class="jd-site-nav-spacer" aria-hidden="true"></div>
""",
        unsafe_allow_html=True,
    )


DEFAULT_FEEDS: list[tuple[str, str]] = [
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("The Block", "https://www.theblockcrypto.com/rss.xml"),
]


def parse_entry_date(entry: Any) -> datetime | None:
    """Parse published/updated date from a feedparser entry (UTC)."""
    if getattr(entry, "published_parsed", None):
        t = entry.published_parsed
        try:
            return datetime(*t[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    if getattr(entry, "updated_parsed", None):
        t = entry.updated_parsed
        try:
            return datetime(*t[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (TypeError, ValueError):
            pass
    return None


def _html_to_text(raw: str) -> str:
    raw = html_module.unescape(raw)
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def _first_sentence(text: str, max_len: int = 320) -> str:
    text = text.strip()
    if not text:
        return ""
    m = re.match(r"^(.+?[.!?])(?:\s|$)", text)
    if m:
        one = m.group(1).strip()
        if len(one) <= max_len:
            return one
    if len(text) <= max_len:
        return text
    cut = text[: max_len + 1].rsplit(" ", 1)[0]
    return cut + "…"


def extract_summary(entry: Any) -> str:
    body = ""
    if getattr(entry, "summary_detail", None):
        sd = entry.summary_detail
        if isinstance(sd, list) and sd:
            body = sd[0].get("value", "") if isinstance(sd[0], dict) else str(sd[0])
        elif isinstance(sd, dict):
            body = sd.get("value", "") or ""
        else:
            body = str(sd)
    if not body and getattr(entry, "summary", None):
        body = str(entry.summary)
    if not body and getattr(entry, "description", None):
        body = str(entry.description)
    if not body and getattr(entry, "subtitle", None):
        body = str(entry.subtitle)
    if not body and getattr(entry, "content", None):
        c = entry.content
        if isinstance(c, list) and c and isinstance(c[0], dict):
            body = c[0].get("value", "") or ""

    plain = _html_to_text(body)
    plain = _first_sentence(plain)
    title = (getattr(entry, "title", None) or "").strip()
    if plain and title:
        tl, pl = title.lower(), plain.lower()
        if pl.startswith(tl):
            plain = plain[len(title) :].lstrip(" —:-\t")
    if plain and title and plain.strip().lower() == title.lower():
        return ""
    return plain


@st.cache_data(ttl=300, show_spinner=False)
def fetch_feed(source_name: str, url: str) -> list[dict[str, Any]]:
    parsed = feedparser.parse(url)
    out: list[dict[str, Any]] = []
    for entry in getattr(parsed, "entries", []) or []:
        link = getattr(entry, "link", "") or ""
        title = (getattr(entry, "title", "") or "Untitled").strip()
        if not link and not title:
            continue
        summary = extract_summary(entry)
        out.append(
            {
                "title": title,
                "link": link,
                "source": source_name,
                "published": parse_entry_date(entry),
                "summary": summary,
            }
        )
    return out


def load_all_feeds(feeds: list[tuple[str, str]]) -> tuple[list[dict[str, Any]], list[str]]:
    combined: list[dict[str, Any]] = []
    errors: list[str] = []
    for name, url in feeds:
        try:
            combined.extend(fetch_feed(name, url))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {e!s}")
    combined.sort(
        key=lambda x: x["published"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return combined, errors


def dedupe_articles(articles: list[dict[str, Any]], max_items: int | None = None) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for a in articles:
        key = a["link"] or a["title"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(a)
        if max_items is not None and len(unique) >= max_items:
            break
    return unique


def filter_headlines_by_keyword(articles: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """
    Keep items where every whitespace-separated token appears in title, summary,
    source, link, or country (case-insensitive). Empty or whitespace-only query
    returns a shallow copy of the input order.
    """
    tokens = [t.lower() for t in query.split() if t.strip()]
    if not tokens:
        return list(articles)
    out: list[dict[str, Any]] = []
    for a in articles:
        blob = " ".join(
            str(x or "")
            for x in (
                a.get("title"),
                a.get("summary"),
                a.get("source"),
                a.get("link"),
                a.get("country"),
            )
        ).lower()
        if all(tok in blob for tok in tokens):
            out.append(a)
    return out


def article_styles_markdown() -> str:
    """Inject once per page that renders news cards."""
    return """
    <style>
    div[data-testid="stVerticalBlock"] > div:has(div.news-card) {
        gap: 0.75rem;
    }
    .news-card {
        border: 1px solid #C7D8E8;
        border-radius: 10px;
        padding: 1rem 1.1rem;
        background: #ffffff;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
    }
    .news-meta {
        font-size: 0.8rem;
        color: #3E6A7A;
        margin-bottom: 0.35rem;
    }
    .news-title a {
        color: #021D41;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.92rem;
        line-height: 1.35;
    }
    .news-title a:hover {
        color: #25809C;
    }
    .news-summary {
        font-size: 0.88rem;
        color: #1F4C67;
        line-height: 1.45;
        margin-top: 0.45rem;
    }
    .news-country {
        font-size: 0.78rem;
        color: #3E6A7A;
        margin-top: 0.35rem;
        line-height: 1.35;
    }
    .day-sep {
        margin: 1.25rem 0 0.75rem 0;
        padding-top: 0.75rem;
        border-top: 1px solid #cbd5e1;
    }
    .day-label {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #3E6A7A;
        margin-bottom: 0.5rem;
    }
    /* Home: News & Regulatory — bordered st.container(border=True) lanes, equal height */
    div[data-testid="stHorizontalBlock"]:has([data-testid="stVerticalBlockBorderWrapper"]) {
        align-items: stretch !important;
    }
    div[data-testid="column"]:has([data-testid="stVerticalBlockBorderWrapper"]) {
        display: flex !important;
        flex-direction: column !important;
        align-self: stretch !important;
    }
    div[data-testid="column"]:has([data-testid="stVerticalBlockBorderWrapper"])
        > div[data-testid="stVerticalBlockBorderWrapper"] {
        flex: 1 1 auto !important;
        width: 100% !important;
        min-height: 100% !important;
        border-radius: 12px !important;
        background: #ffffff !important;
        border-color: #C7D8E8 !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
        padding: 0.65rem 0.85rem 0.85rem 0.85rem !important;
    }
    .jd-home-lane-body {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }
    .jd-home-lane-body h2.home-lane-heading {
        margin: 0 0 0.15rem 0;
    }
    .jd-news-column-footnote {
        font-size: 0.8rem;
        color: #3E6A7A;
        margin: 0;
        line-height: 1.45;
    }
    [data-testid="stVerticalBlockBorderWrapper"] .news-card {
        box-shadow: none;
        border-color: #eef2f7;
    }
    /* Bordered lane: avoid dead air between HTML lane + primary button when column height stretches */
    [data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlock"] {
        justify-content: flex-start !important;
        align-content: flex-start !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]
        .stElementContainer:has([data-testid="stMarkdownContainer"]) {
        margin-bottom: 0 !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] .stElementContainer:has(.stButton) {
        margin-top: 0 !important;
    }
    </style>
    """


def format_article_day_label(published: datetime | None) -> str:
    if not published:
        return "Date not listed"
    return published.astimezone(timezone.utc).strftime("%A, %B %d, %Y")


def article_day_key(published: datetime | None) -> date | None:
    if not published:
        return None
    return published.astimezone(timezone.utc).date()


def build_home_news_lane_body_html(
    top: list[dict[str, Any]],
    *,
    show_footnote: bool,
) -> str:
    """Heading + cards (+ optional footnote) for inside ``st.container(border=True)`` — no outer shell."""
    parts = [
        '<div class="jd-home-lane-body">',
        '<h2 class="home-lane-heading">Latest Digital Asset News</h2>',
    ]
    for item in top:
        parts.append(render_article_card_html(item))
    if show_footnote:
        parts.append(
            '<p class="jd-news-column-footnote">Showing the most recent headlines from the combined RSS list.</p>'
        )
    parts.append("</div>")
    return "".join(parts)


def render_article_card_html(item: dict[str, Any]) -> str:
    pub = item.get("published")
    pub_s = pub.strftime("%b %d, %Y · %H:%M UTC") if isinstance(pub, datetime) else "Date unknown"
    title_esc = escape(item.get("title") or "Untitled")
    link = item.get("link") or "#"
    href = escape(str(link), quote=True)
    summary = (item.get("summary") or "").strip()
    sum_html = ""
    if summary:
        sum_html = f'<div class="news-summary">{escape(summary)}</div>'
    return (
        f'<div class="news-card">'
        f'<div class="news-meta">{escape(str(item.get("source", "")))} · {escape(pub_s)}</div>'
        f'<div class="news-title"><a href="{href}" target="_blank" rel="noopener noreferrer">{title_esc}</a></div>'
        f"{sum_html}"
        f"</div>"
    )


# --- ETF / ETP pulse (RSS headlines: crypto context + ETF/ETP in title only) -----------------

ETP_NEWS_FEEDS: list[tuple[str, str]] = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("The Block", "https://www.theblockcrypto.com/rss.xml"),
    ("Decrypt", "https://decrypt.co/feed"),
]

_CRYPTO_ETF = re.compile(
    r"(?is)\b(?:"
    r"crypto(?:currency|currencies)?|bitcoin|\bbtc\b|ethereum|\beth\b|digital\s+assets?|"
    r"blockchain|defi|altcoin|stablecoin|solana|xrp|dogecoin|pepe|meme\s+coin|"
    r"spot\s+(?:bitcoin|ether|ethereum)|web3|\bcbdc\b|altcoins?|tokeni[sz]e"
    r")\b",
)

_RE_ETF_TOKENS = re.compile(
    r"(?is)(?<![a-z0-9])(?:etf|etfs|etp|etps)(?![a-z0-9])",
)
_RE_EXCHANGE_TRADED = re.compile(
    r"(?is)exchange\s*[-]?\s*traded\s+(?:fund|funds|product|products)\b",
)


def _normalize_headline_for_etp(raw: str) -> str:
    t = html_module.unescape(raw or "")
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def title_mentions_etf_or_etp_vehicle(title: str) -> bool:
    t = _normalize_headline_for_etp(title).lower()
    if not t:
        return False
    if _RE_ETF_TOKENS.search(t):
        return True
    if _RE_EXCHANGE_TRADED.search(t):
        return True
    return False


def _title_and_blob_etp(a: dict[str, Any]) -> tuple[str, str]:
    title = (a.get("title") or "").strip()
    blob = f"{title} {a.get('summary') or ''}".strip()
    return title, blob


def is_crypto_etf_or_etp_article(a: dict[str, Any]) -> bool:
    title, blob = _title_and_blob_etp(a)
    if not title:
        return False
    if not title_mentions_etf_or_etp_vehicle(title):
        return False
    if not _CRYPTO_ETF.search(blob):
        return False
    return True


def pick_crypto_etf_headlines(
    articles: list[dict[str, Any]],
    *,
    limit: int = 8,
    scan_cap: int = 200,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for a in articles[:scan_cap]:
        if is_crypto_etf_or_etp_article(a):
            out.append(a)
            if len(out) >= limit:
                break
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def load_etp_market_news_cached(_filter_rev: int = 5) -> list[dict[str, Any]]:
    """Bump ``_filter_rev`` default when headline-matching rules change (invalidates Streamlit cache)."""
    _ = _filter_rev
    combined, _errors = load_all_feeds(ETP_NEWS_FEEDS)
    combined = dedupe_articles(combined, max_items=None)
    combined.sort(
        key=lambda x: x["published"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return pick_crypto_etf_headlines(combined, limit=8)


def build_etp_market_news_box_html(articles: list[dict[str, Any]]) -> str:
    parts = [
        '<div class="jd-home-lane-body etp-news-pulse">',
        '<h3 class="home-main-heading" style="font-size:1.05rem;margin:0 0 0.35rem 0;">'
        "ETF &amp; ETP pulse</h3>",
        '<p class="jd-news-column-footnote" style="margin:0 0 0.75rem 0;">'
        "Crypto and digital-asset stories from major RSS where the <strong>headline</strong> includes "
        "<strong>ETF</strong>, <strong>ETP</strong>, or an <strong>exchange-traded</strong> fund/product phrase; "
        "summary-only mentions are excluded.</p>",
    ]
    if not articles:
        parts.append(
            '<p class="jd-news-column-footnote">No matching headlines right now. '
            "Try <strong>Refresh feeds</strong> on the home page.</p>"
        )
    else:
        for item in articles:
            parts.append(render_article_card_html(item))
    parts.append("</div>")
    return "".join(parts)
