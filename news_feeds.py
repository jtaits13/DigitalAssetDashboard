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
    color: #0f172a;
    margin: 0 0 0.25rem 0;
    letter-spacing: -0.02em;
    line-height: 1.3;
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
    background: #f4f6f9;
    border-bottom: 1px solid #e2e8f0;
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
      <a class="jd-site-link" href="#">Home</a>
      <a class="jd-site-link" href="#jd-section-news">News</a>
      <a class="jd-site-link" href="#jd-section-market">Markets</a>
      <a class="jd-site-link" href="#jd-section-etps">Crypto ETPs</a>
      <a class="jd-site-link" href="#jd-section-rwa">RWA</a>
    </nav>
  </div>
</div>
<div class="jd-site-nav-spacer" aria-hidden="true"></div>
""",
        unsafe_allow_html=True,
    )


def render_subpage_top_bar() -> None:
    """
    Same fixed banner as the home page. Links go to the main app; News/Market add ``?jd_scroll=``
    so the home page scrolls to those sections after load.
    """
    st.markdown(SITE_NAV_CSS, unsafe_allow_html=True)
    st.markdown(
        """
<div class="jd-site-nav-fixed-wrap">
  <div class="jd-site-nav-inner">
    <nav class="jd-site-nav" aria-label="Page sections">
      <span class="jd-site-brand">JPM Digital</span>
      <a class="jd-site-link" href="/">Home</a>
      <a class="jd-site-link" href="/?jd_scroll=news">News</a>
      <a class="jd-site-link" href="/?jd_scroll=market">Markets</a>
      <a class="jd-site-link" href="/?jd_scroll=etps">Crypto ETPs</a>
      <a class="jd-site-link" href="/?jd_scroll=rwa">RWA</a>
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
        border-color: #e2e8f0 !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
        padding: 0.65rem 0.85rem 0.85rem 0.85rem !important;
    }
    .jd-home-lane-body {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }
    .jd-home-lane-body h2.home-main-heading {
        margin: 0 0 0.15rem 0;
    }
    .jd-news-column-footnote {
        font-size: 0.8rem;
        color: #64748b;
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
        '<h2 class="home-main-heading">Latest Digital Asset News</h2>',
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
