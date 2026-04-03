"""
JPM Digital — crypto & digital asset news (RSS aggregation).
Deploy on Streamlit Community Cloud with this file as the main entrypoint.
"""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import streamlit as st

# Public RSS feeds (no API keys). Replace or extend as needed.
DEFAULT_FEEDS: list[tuple[str, str]] = [
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("The Block", "https://www.theblockcrypto.com/rss.xml"),
]


def _parse_entry_date(entry: Any) -> datetime | None:
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


@st.cache_data(ttl=300, show_spinner=False)
def fetch_feed(source_name: str, url: str) -> list[dict[str, Any]]:
    parsed = feedparser.parse(url)
    out: list[dict[str, Any]] = []
    for entry in getattr(parsed, "entries", []) or []:
        link = getattr(entry, "link", "") or ""
        title = (getattr(entry, "title", "") or "Untitled").strip()
        if not link and not title:
            continue
        out.append(
            {
                "title": title,
                "link": link,
                "source": source_name,
                "published": _parse_entry_date(entry),
            }
        )
    return out


def load_all_feeds(feeds: list[tuple[str, str]]) -> tuple[list[dict[str, Any]], list[str]]:
    combined: list[dict[str, Any]] = []
    errors: list[str] = []
    for name, url in feeds:
        try:
            combined.extend(fetch_feed(name, url))
        except Exception as e:  # noqa: BLE001 — show feed errors in UI
            errors.append(f"{name}: {e!s}")
    combined.sort(key=lambda x: x["published"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return combined, errors


def main() -> None:
    st.set_page_config(
        page_title="JPM Digital — Crypto News",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlock"] > div:has(div.news-card) {
            gap: 0.75rem;
        }
        .news-card {
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            padding: 1rem 1.1rem;
            background: rgba(255,255,255,0.03);
        }
        .news-meta {
            font-size: 0.85rem;
            opacity: 0.75;
            margin-bottom: 0.35rem;
        }
        .news-title a {
            color: #e8eef4;
            text-decoration: none;
            font-weight: 600;
            font-size: 1.05rem;
        }
        .news-title a:hover {
            color: #22c55e;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Sources")
        st.caption("RSS feeds aggregated on refresh. Add your own in the repo.")
        max_items = st.slider("Articles to show", min_value=10, max_value=80, value=30, step=5)
        refresh = st.button("Refresh feeds", use_container_width=True)

    if refresh:
        fetch_feed.clear()
        st.rerun()

    col_title, col_tag = st.columns([3, 1])
    with col_title:
        st.title("Digital asset & crypto news")
    with col_tag:
        st.caption("Aggregated headlines · RSS")

    articles, feed_errors = load_all_feeds(DEFAULT_FEEDS)

    if feed_errors:
        with st.expander("Some feeds could not be loaded", expanded=False):
            for err in feed_errors:
                st.warning(err)

    if not articles:
        st.info("No articles loaded. Check your network or RSS URLs in `streamlit_app.py`.")
        return

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for a in articles:
        key = a["link"] or a["title"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(a)
        if len(unique) >= max_items:
            break

    n_cols = 2
    rows = [unique[i : i + n_cols] for i in range(0, len(unique), n_cols)]
    for row in rows:
        cols = st.columns(n_cols)
        for col, item in zip(cols, row):
            with col:
                pub = item["published"]
                pub_s = pub.strftime("%b %d, %Y · %H:%M UTC") if pub else "Date unknown"
                title_esc = (
                    item["title"]
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                link = item["link"] or "#"
                st.markdown(
                    f"""
                    <div class="news-card">
                      <div class="news-meta">{item["source"]} · {pub_s}</div>
                      <div class="news-title"><a href="{link}" target="_blank" rel="noopener noreferrer">{title_esc}</a></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.divider()
    st.caption(
        f"Last built at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "Headlines link to original publishers."
    )


if __name__ == "__main__":
    main()
