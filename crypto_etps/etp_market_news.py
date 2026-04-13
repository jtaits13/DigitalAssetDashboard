"""RSS headlines filtered to crypto-related ETFs / ETPs (full ETP page pulse strip)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import streamlit as st

from news_feeds import dedupe_articles, load_all_feeds, render_article_card_html

ETP_NEWS_FEEDS: list[tuple[str, str]] = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("The Block", "https://www.theblockcrypto.com/rss.xml"),
    ("Decrypt", "https://decrypt.co/feed"),
]

# Must look like a digital-asset / crypto context (not generic equity ETFs).
_CRYPTO = re.compile(
    r"(?is)\b(?:"
    r"crypto(?:currency|currencies)?|bitcoin|\bbtc\b|ethereum|\beth\b|digital\s+assets?|"
    r"blockchain|defi|altcoin|stablecoin|solana|xrp|dogecoin|pepe|meme\s+coin|"
    r"spot\s+(?:bitcoin|ether|ethereum)|web3|\bcbdc\b|altcoins?|tokeni[sz]e"
    r")\b",
)

# ETF, ETP, or spelled-out exchange-traded fund / product.
_ETF_ETP = re.compile(
    r"(?is)\b(?:"
    r"etfs?\b|etps?\b|"
    r"exchange[\s-]traded(?:\s+funds?|\s+products?)"
    r")\b",
)


def _title_and_blob(a: dict[str, Any]) -> tuple[str, str]:
    title = (a.get("title") or "").strip()
    blob = f"{title} {a.get('summary') or ''}".strip()
    return title, blob


def is_crypto_etf_or_etp_article(a: dict[str, Any]) -> bool:
    """
    Include only if **ETF / ETP** (or spelled-out exchange-traded fund/product) appears in the
    **headline title**, and the piece still looks crypto-related (title or summary).
    """
    title, blob = _title_and_blob(a)
    if not title:
        return False
    if not _ETF_ETP.search(title):
        return False
    if not _CRYPTO.search(blob):
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
def load_etp_market_news_cached() -> list[dict[str, Any]]:
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
