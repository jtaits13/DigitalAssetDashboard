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

# Multipage entry for st.switch_page from subpages.
MAIN_APP_PAGE = "streamlit_app.py"

# Pins the jpm_site_nav iframe to the viewport; inner markup lives in jpm_site_nav/build/.
# price_ticker.py aligns horizontal padding with .cd-ticker-shell.
SITE_NAV_CSS = """
<style>
iframe[title="jpm_site_nav"] {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    width: 100% !important;
    height: 5.25rem !important;
    max-height: 5.25rem !important;
    z-index: 999999;
    border: none !important;
    box-sizing: border-box;
}
.jd-site-nav-spacer {
    height: 5.25rem;
    flex-shrink: 0;
}
html {
    scroll-padding-top: 5.5rem;
}
</style>
"""


def apply_site_nav_value(val: object, *, is_landing: bool) -> None:
    """React to jpm_site_nav component return value (next rerun after a click)."""
    if not val or not isinstance(val, dict):
        return
    raw = val.get("action")
    if not isinstance(raw, str):
        return
    action = raw.strip().lower()
    if action not in ("home", "news", "market"):
        return
    if is_landing:
        if action == "home":
            st.session_state["jd_scroll_top"] = True
        elif action == "news":
            st.session_state["jd_scroll_to"] = "jd-section-news"
        elif action == "market":
            st.session_state["jd_scroll_to"] = "jd-section-market"
        return
    if action == "home":
        st.switch_page(MAIN_APP_PAGE)
    elif action == "news":
        st.query_params["jd_scroll"] = "news"
        st.switch_page(MAIN_APP_PAGE)
    elif action == "market":
        st.query_params["jd_scroll"] = "market"
        st.switch_page(MAIN_APP_PAGE)


def render_site_nav_bar(*, key: str, is_landing: bool) -> None:
    """Fixed top site nav (custom component) + spacer. Call near the top of each page."""
    st.markdown(SITE_NAV_CSS, unsafe_allow_html=True)
    from jpm_site_nav import jpm_site_nav

    val = jpm_site_nav(page_mode="landing" if is_landing else "subpage", key=key, default=None)
    apply_site_nav_value(val, is_landing=is_landing)
    st.markdown(
        '<div class="jd-site-nav-spacer" aria-hidden="true"></div>',
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
