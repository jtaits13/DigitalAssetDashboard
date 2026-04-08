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
    font-size: 1.2rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 0.15rem 0;
    letter-spacing: -0.02em;
    line-height: 1.25;
}
</style>
"""

# Main entry script for st.page_link from subpages (multipage app root).
MAIN_APP_PAGE = "streamlit_app.py"

# Coinbase-style strip: fixed to viewport (sticky fails inside Streamlit scroll parents).
# Subpages use st.container(key="jdnavstrip") → .st-key-jdnavstrip for fixed bar + st.page_link (SPA nav).
SITE_NAV_CSS = """
<style>
/* Horizontal inset matches CoinGecko ticker via --jd-strip-pl/pr (set in price_ticker.py). */
.jd-site-nav-fixed-wrap,
div.st-key-jdnavstrip {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    width: 100%;
    z-index: 999999;
    box-sizing: border-box;
    margin: 0;
    padding-top: 0.45rem;
    padding-bottom: 0.55rem;
    padding-left: var(--jd-strip-pl, 1rem);
    padding-right: var(--jd-strip-pr, 1rem);
    background: #f4f6f9;
    border-bottom: 1px solid #e2e8f0;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
}
.jd-site-nav-inner {
    max-width: min(1200px, 100%);
    margin: 0 auto;
}
/* Subpage: one Streamlit row = same flex + padding as .jd-site-nav on landing */
div.st-key-jdnavstrip [data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
    align-items: center !important;
    gap: 0.35rem 0.15rem !important;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.5rem 0.85rem 0.55rem 0.85rem;
    margin: 0 auto;
    max-width: min(1200px, 100%);
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    width: 100%;
    box-sizing: border-box;
}
div.st-key-jdnavstrip [data-testid="column"] {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    min-width: 0;
}
div.st-key-jdnavstrip .jd-site-brand-inline {
    font-size: 0.95rem;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.03em;
    margin-right: 1rem;
    padding-right: 1rem;
    border-right: 1px solid #e2e8f0;
    line-height: 1.35;
    display: inline-block;
}
div.st-key-jdnavstrip a[data-testid="stPageLink-NavLink"],
div.st-key-jdnavstrip [data-testid="stPageLink-NavLink"] {
    font-size: 0.88rem;
    font-weight: 600;
    color: #475569 !important;
    text-decoration: none !important;
    padding: 0.4rem 0.75rem !important;
    border-radius: 8px;
    transition: color 0.15s ease, background 0.15s ease;
}
div.st-key-jdnavstrip a[data-testid="stPageLink-NavLink"]:hover,
div.st-key-jdnavstrip [data-testid="stPageLink-NavLink"]:hover {
    color: #1E7C99 !important;
    background: rgba(30, 124, 153, 0.09);
}
div.st-key-jdnavstrip div.stPageLink {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}
.jd-site-nav-spacer {
    height: 5.25rem;
    flex-shrink: 0;
}
html {
    scroll-padding-top: 5.5rem;
}
.jd-site-nav {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.35rem 0.15rem;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 0.5rem 0.85rem 0.55rem 0.85rem;
    margin: 0;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.jd-site-nav .jd-site-brand {
    font-size: 0.95rem;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.03em;
    margin-right: 1rem;
    padding-right: 1rem;
    border-right: 1px solid #e2e8f0;
}
.jd-site-nav a.jd-site-link {
    font-size: 0.88rem;
    font-weight: 600;
    color: #475569;
    text-decoration: none;
    padding: 0.4rem 0.75rem;
    border-radius: 8px;
    transition: color 0.15s ease, background 0.15s ease;
}
.jd-site-nav a.jd-site-link:hover {
    color: #1E7C99;
    background: rgba(30, 124, 153, 0.09);
}
.jd-site-nav a.jd-site-link:active {
    color: #155e75;
}
</style>
"""


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


def render_home_top_bar(key_suffix: str = "page", *, is_landing: bool = False) -> None:
    """
    Top strip: brand + section links.

    Landing: in-page hash links. Other pages: st.page_link to home with ?jd_scroll=…
    (avoids full-page / new-tab navigation from raw <a href=\"/\"> in embedded HTML).
    """
    st.markdown(SITE_NAV_CSS, unsafe_allow_html=True)

    if is_landing:
        st.markdown(
            """
<div class="jd-site-nav-fixed-wrap">
  <div class="jd-site-nav-inner">
    <nav class="jd-site-nav" aria-label="Page sections">
      <span class="jd-site-brand">JPM Digital</span>
      <a class="jd-site-link" href="#">Home</a>
      <a class="jd-site-link" href="#jd-section-news">News</a>
      <a class="jd-site-link" href="#jd-section-market">Market Data</a>
    </nav>
  </div>
</div>
<div class="jd-site-nav-spacer" aria-hidden="true"></div>
""",
            unsafe_allow_html=True,
        )
        return

    with st.container(key="jdnavstrip"):
        c_brand, c_home, c_news, c_mkt = st.columns([2.4, 1, 1, 1.2], gap="small")
        with c_brand:
            st.markdown(
                '<span class="jd-site-brand-inline">JPM Digital</span>',
                unsafe_allow_html=True,
            )
        with c_home:
            st.page_link(MAIN_APP_PAGE, label="Home", use_container_width=True)
        with c_news:
            st.page_link(
                MAIN_APP_PAGE,
                label="News",
                query_params={"jd_scroll": "news"},
                use_container_width=True,
            )
        with c_mkt:
            st.page_link(
                MAIN_APP_PAGE,
                label="Market Data",
                query_params={"jd_scroll": "market"},
                use_container_width=True,
            )

    st.markdown(
        '<div class="jd-site-nav-spacer" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )


def article_styles_markdown() -> str:
    """Inject once per page that renders news cards."""
    return """
    <style>
    div[data-testid="stVerticalBlock"] > div:has(div.news-card) {
        gap: 0.75rem;
    }
    .news-card {
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem 1.1rem;
        background: #ffffff;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
    }
    .news-meta {
        font-size: 0.8rem;
        color: #64748b;
        margin-bottom: 0.35rem;
    }
    .news-title a {
        color: #0f172a;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.92rem;
        line-height: 1.35;
    }
    .news-title a:hover {
        color: #059669;
    }
    .news-summary {
        font-size: 0.88rem;
        color: #475569;
        line-height: 1.45;
        margin-top: 0.45rem;
    }
    .news-country {
        font-size: 0.78rem;
        color: #64748b;
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
        color: #64748b;
        margin-bottom: 0.5rem;
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
