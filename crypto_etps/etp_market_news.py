"""RSS-driven crypto / digital-asset ETP market headlines for the home ETP column."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import streamlit as st

from news_feeds import dedupe_articles, load_all_feeds, render_article_card_html

# Major outlets that routinely cover ETF filings, launches, and flows.
ETP_NEWS_FEEDS: list[tuple[str, str]] = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("The Block", "https://www.theblockcrypto.com/rss.xml"),
    ("Decrypt", "https://decrypt.co/feed"),
]

_ETP_PULSE = re.compile(
    r"(?is)\b(?:"
    r"etf\b|etps?\b|spot\s+bitcoin|spot\s+ether|bitcoin\s+etf|ethereum\s+etf|crypto\s+etf|"
    r"digital\s+asset\s+etf|exchange[\s-]traded|grayscale|blackrock|ishares|invesco|"
    r"filing|s-1\b|registration\s+statement|prospectus|\bsec\b|"
    r"inflow|outflow|net\s+flow|creation\s+unit|aum\b|assets\s+under\s+management|"
    r"launch(?:es|ed|ing)?|list(?:s|ed|ing)?|"
    r"morgan\s+stanley|fidelity|franklin\s+templeton|canary|hashdex|vaneck|wisdomtree|"
    r"pepe\s+etf|meme\s+coin\s+etf|solana\s+etf|xrp\s+etf"
    r")\b",
)


def _blob(a: dict[str, Any]) -> str:
    return f"{a.get('title') or ''} {a.get('summary') or ''}"


def pick_etp_market_articles(
    articles: list[dict[str, Any]],
    *,
    limit: int = 6,
    scan_cap: int = 180,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for a in articles[:scan_cap]:
        if _ETP_PULSE.search(_blob(a)):
            out.append(a)
            if len(out) >= limit:
                break
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def load_etp_market_news_cached() -> list[dict[str, Any]]:
    combined, _errors = load_all_feeds(ETP_NEWS_FEEDS)
    combined = dedupe_articles(combined, max_items=None)
    combined.sort(
        key=lambda x: x["published"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return pick_etp_market_articles(combined, limit=6)


def build_etp_market_news_box_html(articles: list[dict[str, Any]]) -> str:
    parts = [
        '<div class="jd-home-lane-body etp-news-stack">',
        '<h3 class="home-main-heading" style="font-size:1rem;margin:0 0 0.35rem 0;">'
        "ETF &amp; ETP market pulse</h3>",
        '<p class="jd-news-column-footnote" style="margin:0 0 0.65rem 0;">'
        "Filings, launches, flows, and fund news (filtered from major crypto RSS).</p>",
    ]
    if not articles:
        parts.append(
            '<p class="jd-news-column-footnote">No ETP-focused headlines matched filters yet. '
            "Try <strong>Refresh feeds</strong> in the sidebar.</p>"
        )
    else:
        for item in articles:
            parts.append(render_article_card_html(item))
    parts.append("</div>")
    return "".join(parts)
