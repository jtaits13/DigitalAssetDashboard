"""Shared RSS fetch + dedupe for home and All Articles pages."""

from __future__ import annotations

import calendar
import html as html_module
import re
from datetime import date, datetime, timezone
from html import escape
from email.utils import parsedate_to_datetime
from typing import Any, Optional

import feedparser
import streamlit as st

# Match `h2.home-main-heading` on the home page (Latest Digital Asset News).
HOME_MAIN_HEADING_CSS = """
<style>
/* Slim subsection title (replaces bulky gradient shells on hub + RWA subpages) */
.jd-hub-subsection-head {
    margin: 0.4rem 0 0.55rem 0;
    padding: 0 0 0.45rem 0;
    border-bottom: 1px solid #C7D8E8;
    background: transparent;
    box-shadow: none;
}
.jd-hub-subsection-head h2.home-main-heading,
.jd-hub-subsection-head h2.home-widget-heading {
    margin: 0 !important;
    padding: 0;
}
h2.home-main-heading {
    font-size: 1.06rem;
    font-weight: 650;
    color: #021D41;
    margin: 0 0 0.25rem 0;
    letter-spacing: -0.02em;
    line-height: 1.3;
}
</style>
"""

# Hero / section blurbs that should span the main column (multipage heroes + On-chain hub intros). Default
# ``.jd-hub-dek`` in home_layout keeps a ~44rem measure for other hub lines (News, Markets, etc.).
# Lives here so home_layout stays a small, stable import on all hosts.
SUBPAGE_HERO_DEK_CSS = """
<style>
/* Wider than default .jd-hub-dek (max ~44rem) — hub section intros + multipage hero lines */
p.jd-hub-dek.jd-hub-dek-fullbleed {
    max-width: 100%;
    width: 100%;
    box-sizing: border-box;
    margin-top: 0.2rem;
    margin-bottom: 0.85rem;
    line-height: 1.55;
}
/* Hub Explore gateway cards: short intro + bullet list (home + index heroes).
   First line = .jd-hub-cta-note scale (0.78rem) — home lane “footnote” size; list one step down. */
div.jd-hub-dek.jd-hub-dek-fullbleed.jd-hub-explore-blurb {
    max-width: 100%;
    width: 100%;
    box-sizing: border-box;
    margin: 0.15rem 0 0.95rem 0;
    line-height: 1.4;
    font-size: 0.75rem;
    color: #3E6A7A;
}
div.jd-hub-dek.jd-hub-dek-fullbleed.jd-hub-explore-blurb > p:first-of-type {
    font-size: 0.78rem;
    line-height: 1.4;
    font-weight: 500;
    color: #3E6A7A;
    margin: 0 0 0.4rem 0;
    letter-spacing: -0.01em;
}
div.jd-hub-dek.jd-hub-dek-fullbleed.jd-hub-explore-blurb p {
    margin: 0 0 0.4rem 0;
}
div.jd-hub-dek.jd-hub-dek-fullbleed.jd-hub-explore-blurb p.jd-hub-explore-blurb--tail {
    font-size: 0.78rem;
    line-height: 1.4;
    margin-top: 0.45rem;
    margin-bottom: 0;
}
div.jd-hub-dek.jd-hub-dek-fullbleed.jd-hub-explore-blurb ul {
    margin: 0.1rem 0 0.2rem 0;
    padding-left: 1.2rem;
}
div.jd-hub-dek.jd-hub-dek-fullbleed.jd-hub-explore-blurb li {
    margin: 0.2rem 0;
}
</style>
"""


def app_shared_layout_css() -> str:
    """
    ``HOME_MAIN_HEADING_CSS`` plus ``HOME_PAGE_LAYOUT_CSS`` — same typography, section rhythm,
    dividers, and ticker spacing as the hub. Use on ``streamlit_app`` and every multipage view.
    """
    from home_layout import HOME_PAGE_LAYOUT_CSS

    return HOME_MAIN_HEADING_CSS + HOME_PAGE_LAYOUT_CSS + SUBPAGE_HERO_DEK_CSS


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
a.jd-nav-dd-item.jd-nav-dd-sub {
    padding-left: 1.5rem;
    font-weight: 500;
    color: #3E6A7A;
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
      <a class="jd-site-link" href="#jd-section-markets-funds">Markets &amp; Funds</a>
      <div class="jd-nav-dd" role="group" aria-label="On-chain Data subsections">
        <a class="jd-site-link jd-nav-dd-head" href="#jd-section-onchain">On-chain Data <span class="jd-nav-dd-caret" aria-hidden="true">▾</span></a>
        <ul class="jd-nav-dd-menu" role="menu">
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="#jd-rwa-market">Global Market overview</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="#jd-rwa-explore-asset-type">Explore by Asset Type</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="#jd-rwa-explore-market-participant">Explore by Market Participant</a></li>
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
      <a class="jd-site-link" href="/?jd_scroll=markets_funds">Markets &amp; Funds</a>
      <div class="jd-nav-dd" role="group" aria-label="On-chain Data pages">
        <a class="jd-site-link jd-nav-dd-head" href="/?jd_scroll=onchain">On-chain Data <span class="jd-nav-dd-caret" aria-hidden="true">▾</span></a>
        <ul class="jd-nav-dd-menu" role="menu">
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="/RWA_Stablecoins">Stablecoins</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="/RWA_US_Treasuries">US Treasuries</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="/RWA_Tokenized_Stocks">Tokenized stocks</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="/RWA_Explore_By_Asset_Type">Explore by Asset Type</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="/RWA_Explore_By_Market_Participant">Explore by Market Participant</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="/RWA_Participants_Networks">Participants — Networks</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="/RWA_Participants_Platforms">Participants — Platforms</a></li>
          <li role="none"><a class="jd-nav-dd-item" role="menuitem" href="/RWA_Participants_Asset_Managers">Participants — Asset Managers</a></li>
        </ul>
      </div>
    </nav>
  </div>
</div>
<div class="jd-site-nav-spacer" aria-hidden="true"></div>
""",
        unsafe_allow_html=True,
    )


_SUBPAGE_SIDEBAR_REFRESH_NOTE = (
    "Use **Refresh all data** on the home page to reload RSS, prices, ETPs, regulatory feeds, "
    "and all RWA.xyz embed caches."
)


def render_subpage_sidebar(*, key_prefix: str, current: str) -> None:
    """
    Left navigation on multipage views — same structure as the home sidebar (brand + **Pages**),
    without the refresh button (users return to the landing page to refresh).

    ``key_prefix`` must be unique per page module (e.g. ``all_articles``) so widget keys stay isolated.

    ``current`` marks the active destination: ``articles``, ``regulatory``, ``etp``, ``etf_news``,
    ``rwa_explore_asset_type``, ``rwa_explore_market_participant``, ``rwa_participants_networks``, ``rwa_participants_platforms``, ``rwa_participants_asset_managers``, ``rwa_stablecoins``, ``rwa_treasuries``, ``rwa_tokenized_stocks``.
    """
    with st.sidebar:
        st.markdown("### JPM Digital")
        st.caption("Markets, policy, and on-chain market data.")
        st.divider()
        st.markdown("**Pages**")
        if st.button(
            "Home",
            key=f"{key_prefix}_sb_landing",
            use_container_width=True,
            type="secondary",
        ):
            st.switch_page("streamlit_app.py")

        nav: list[tuple[str, str, str]] = [
            ("All articles", "pages/All_Articles.py", "articles"),
            ("Regulatory headlines", "pages/All_Regulatory.py", "regulatory"),
            ("U.S. Digital Asset ETPs", "pages/US_Crypto_ETPs.py", "etp"),
            ("ETF & ETP market news", "pages/All_ETF_News.py", "etf_news"),
            ("RWA Stablecoins", "pages/RWA_Stablecoins.py", "rwa_stablecoins"),
            ("RWA US Treasuries", "pages/RWA_US_Treasuries.py", "rwa_treasuries"),
            ("RWA Tokenized Stocks", "pages/RWA_Tokenized_Stocks.py", "rwa_tokenized_stocks"),
            ("Explore by Asset Type", "pages/RWA_Explore_By_Asset_Type.py", "rwa_explore_asset_type"),
            ("Explore by Market Participant", "pages/RWA_Explore_By_Market_Participant.py", "rwa_explore_market_participant"),
            ("Participants — Networks", "pages/RWA_Participants_Networks.py", "rwa_participants_networks"),
            ("Participants — Platforms", "pages/RWA_Participants_Platforms.py", "rwa_participants_platforms"),
            ("Participants — Asset Managers", "pages/RWA_Participants_Asset_Managers.py", "rwa_participants_asset_managers"),
        ]
        for label, page, slug in nav:
            if st.button(
                label,
                key=f"{key_prefix}_sb_{slug}",
                use_container_width=True,
                type="primary" if current == slug else "secondary",
            ):
                st.switch_page(page)

        st.divider()
        st.caption(_SUBPAGE_SIDEBAR_REFRESH_NOTE)


DEFAULT_FEEDS: list[tuple[str, str]] = [
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("The Block", "https://www.theblockcrypto.com/rss.xml"),
]

# Extra ETF/ETP-dedicated + broader crypto/finance sources (checked with feedparser). Appended to :data:`DEFAULT_FEEDS`
# for the pulse + All ETF news only (home / All articles still use ``DEFAULT_FEEDS``).
#
# **Why date gaps happen:** each outlet’s RSS is only its latest N posts; older URLs fall off the feed entirely.
# Google News search RSS returns ~100 headlines per query and often spans more calendar time, which helps fill
# holes—but this is still not a full archive (subject to Google’s terms for the feed URL).
ETP_SUPPLEMENT_FEEDS: list[tuple[str, str]] = [
    ("ETF Trends (VettaFi)", "https://www.etftrends.com/feed/"),
    ("Benzinga ETFs", "https://www.benzinga.com/topic/etfs/feed"),
    ("ETFdb", "https://www.etfdb.com/feed/"),
    (
        "GlobeNewswire (ETF)",
        "https://www.globenewswire.com/RssFeed/subjectcode/23-Exchange%20Traded%20Funds-25/feedTitle/"
        "GlobeNewswire%20-%20Company%20Announcements%20on%20Exchange%20Traded%20Funds",
    ),
    # Aggregated search: more items + longer tail than single-site RSS (still capped ~100/query).
    ("Google News (crypto ETF)", "https://news.google.com/rss/search?q=crypto+ETF&hl=en-US&gl=US&ceid=US:en"),
    (
        "Google News (spot Bitcoin ETF)",
        "https://news.google.com/rss/search?q=spot+bitcoin+ETF&hl=en-US&gl=US&ceid=US:en",
    ),
    (
        "Google News (crypto ETP / ETF)",
        "https://news.google.com/rss/search?q=crypto+exchange+traded+fund&hl=en-US&gl=US&ceid=US:en",
    ),
    ("Yahoo Finance (headlines)", "https://finance.yahoo.com/news/rssindex"),
    ("Blockworks", "https://blockworks.co/feed"),
]

ETP_NEWS_FEEDS: list[tuple[str, str]] = list(DEFAULT_FEEDS) + ETP_SUPPLEMENT_FEEDS


def parse_entry_date(entry: Any) -> Optional[datetime]:
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


def dedupe_articles(articles: list[dict[str, Any]], max_items: Optional[int] = None) -> list[dict[str, Any]]:
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


def hub_news_panel_header_html(*, eyebrow: str, title: str, heading_id: Optional[str] = None) -> str:
    """Shared lane chrome: eyebrow label + panel title (both hub columns use this)."""
    id_attr = f' id="{escape(heading_id)}"' if heading_id else ""
    return (
        '<header class="jd-hub-news-panel-header">'
        f'<span class="jd-hub-news-eyebrow">{escape(eyebrow)}</span>'
        f'<p class="jd-hub-news-panel-title" role="heading" aria-level="2"{id_attr}>{escape(title)}</p>'
        "</header>"
    )


def render_hub_news_lane_item_html(
    item: dict[str, Any],
    index: int,
    *,
    show_country: bool = False,
) -> str:
    """One headline row inside the home hub panels (index + meta + optional region chip + title)."""
    pub = item.get("published")
    if isinstance(pub, datetime):
        pub_s = pub.astimezone(timezone.utc).strftime("%b %d · %H:%M UTC")
    else:
        pub_s = "—"
    title_esc = escape(item.get("title") or "Untitled")
    link = item.get("link") or "#"
    href = escape(str(link), quote=True)
    src = (item.get("source") or "").strip()
    meta_line = f"{escape(src)} · {escape(pub_s)}" if src else escape(pub_s)
    chip_html = ""
    if show_country:
        c = escape(str(item.get("country") or "Global"))
        chip_html = f'<span class="jd-hub-news-chip">{c}</span>'
    idx = max(1, min(99, index))
    return (
        f'<li class="jd-hub-news-item" data-index="{idx}">'
        f'<span class="jd-hub-news-item-idx" aria-hidden="true">{idx:02d}</span>'
        '<div class="jd-hub-news-item-body">'
        f'<div class="jd-hub-news-meta">{meta_line}</div>'
        f'<div class="jd-hub-news-chips">{chip_html}</div>'
        f'<a class="jd-hub-news-title" href="{href}" target="_blank" rel="noopener noreferrer">{title_esc}</a>'
        "</div>"
        "</li>"
    )


def article_styles_markdown() -> str:
    """Inject once per page that renders news cards."""
    return """
    <style>
    div[data-testid="stVerticalBlock"] > div:has(div.news-card) {
        gap: 0.75rem;
    }
    /* Home hub: News & Regulatory panels — align with home-band / widget / subsection rhythm */
    .jd-hub-news-panel {
        display: flex;
        flex-direction: column;
        gap: 0;
        box-sizing: border-box;
        width: 100%;
        height: 100%;
        /* Floor + stretch: both lanes share height; list flexes when one side is shorter on text. */
        min-height: 17.5rem;
        padding: 0.55rem 0.65rem 0.5rem;
        border-radius: 12px;
        background: #ffffff;
        border: 1px solid #C7D8E8;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    }
    .jd-hub-news-panel-header {
        margin: 0 0 0.45rem 0;
        padding: 0 0 0.45rem 0;
        border-bottom: 1px solid #C7D8E8;
    }
    .jd-hub-news-eyebrow {
        display: block;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #25809C;
        margin-bottom: 0.22rem;
    }
    /*
     * Match hub section bands (.home-band-label.teal in home_layout.py).
     * Use <p role="heading"> — Streamlit applies large theme styles to raw <h2> in markdown.
     */
    .jd-hub-news-panel .jd-hub-news-panel-title,
    [data-testid="stMarkdownContainer"] .jd-hub-news-panel-title {
        font-size: 1.3rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.024em !important;
        line-height: 1.22 !important;
        color: #021D41 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .jd-hub-news-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0;
        flex: 1 1 auto;
        min-height: 0;
        align-self: stretch;
    }
    .jd-hub-news-item {
        display: grid;
        grid-template-columns: 1.75rem minmax(0, 1fr);
        gap: 0.45rem 0.55rem;
        align-items: start;
        padding: 0.5rem 0.1rem;
        margin: 0;
        border-radius: 0;
        border: none;
        border-bottom: 1px solid #dce7f0;
        transition: background 0.1s ease;
        /* Meta + chip row + 2-line title (both lanes use same row rhythm). */
        min-height: 5.35rem;
        box-sizing: border-box;
    }
    .jd-hub-news-item:last-child {
        border-bottom: none;
        padding-bottom: 0.15rem;
    }
    .jd-hub-news-item:hover {
        background: #F3F7FB;
        box-shadow: none;
    }
    .jd-hub-news-item-idx {
        font-size: 0.68rem;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
        color: #8CB9C9;
        line-height: 1.4;
        padding-top: 0.1rem;
        text-align: right;
        user-select: none;
    }
    .jd-hub-news-item-body {
        min-width: 0;
    }
    .jd-hub-news-meta {
        font-size: 0.78rem;
        font-weight: 500;
        color: #3E6A7A;
        line-height: 1.4;
        margin: 0 0 0.18rem 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    /* Always reserve one chip line so Market rows match Regulatory (region pill). */
    .jd-hub-news-chips {
        margin: 0 0 0.18rem 0;
        min-height: 1.36rem;
        line-height: 1.36rem;
    }
    .jd-hub-news-chip {
        display: inline-block;
        font-size: 0.62rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #1F4C67;
        background: #F3F7FB;
        border: 1px solid #C7D8E8;
        border-radius: 999px;
        padding: 0.1rem 0.38rem;
        line-height: 1.25;
    }
    .jd-hub-news-title {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        font-size: 0.92rem;
        font-weight: 600;
        line-height: 1.35;
        color: #021D41;
        text-decoration: none;
    }
    .jd-hub-news-title:hover {
        color: #25809C;
        text-decoration: none;
    }
    .jd-hub-news-footnote {
        margin-top: auto;
        padding-top: 0.4rem;
        margin-bottom: 0;
        font-size: 0.78rem;
        line-height: 1.4;
        color: #3E6A7A;
        border-top: 1px solid #dce7f0;
    }
    .jd-hub-news-empty {
        margin: 0.4rem 0 0 0;
        font-size: 0.8125rem;
        line-height: 1.5;
        color: #3E6A7A;
    }
    .jd-hub-news-panel--empty .jd-hub-news-list {
        min-height: 0;
    }
    .jd-hub-news-panel--empty .jd-hub-news-empty {
        flex: 1 1 auto;
        margin-top: 0.25rem;
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
        border-top: 1px solid #dce7f0;
    }
    .day-label {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #3E6A7A;
        margin-bottom: 0.5rem;
    }
    /* Home: News & Regulatory — equal-height columns (st.columns(..., border=True)) */
    div[data-testid="stHorizontalBlock"]:has(.jd-hub-news-panel) {
        display: flex !important;
        flex-direction: row !important;
        align-items: stretch !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.jd-hub-news-panel) > div[data-testid="column"] {
        flex: 1 1 0 !important;
        min-width: 0 !important;
        display: flex !important;
        flex-direction: column !important;
        align-self: stretch !important;
    }
    div[data-testid="column"]:has(.jd-hub-news-panel) {
        display: flex !important;
        flex-direction: column !important;
        align-self: stretch !important;
    }
    /* Hide Streamlit's column border chrome; we only use border=True for equal cell height. */
    div[data-testid="stHorizontalBlock"]:has(.jd-hub-news-panel)
        > div[data-testid="column"]
        > div[data-testid="stVerticalBlockBorderWrapper"] {
        flex: 1 1 auto !important;
        width: 100% !important;
        min-height: 0 !important;
        display: flex !important;
        flex-direction: column !important;
        background: transparent !important;
        border-color: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    /* Primary vertical stack: lane markdown + optional button + note */
    div[data-testid="stHorizontalBlock"]:has(.jd-hub-news-panel)
        > div[data-testid="column"]:has(.jd-hub-news-panel)
        > div[data-testid="stVerticalBlockBorderWrapper"]
        > div[data-testid="stVerticalBlock"],
    div[data-testid="column"]:has(.jd-hub-news-panel) > div[data-testid="stVerticalBlock"] {
        flex: 1 1 auto !important;
        width: 100% !important;
        min-height: 0 !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 0.45rem !important;
    }
    div[data-testid="column"]:has(.jd-hub-news-panel)
        div[data-testid="stElementContainer"]:has(.jd-hub-news-panel) {
        flex: 1 1 auto !important;
        min-height: 0 !important;
    }
    div[data-testid="column"]:has(.jd-hub-news-panel)
        div[data-testid="stElementContainer"]:has(.stButton) {
        margin-top: auto !important;
        flex: 0 0 auto !important;
    }
    div[data-testid="column"]:has(.jd-hub-news-panel)
        div[data-testid="stElementContainer"]:has(.jd-hub-news-panel)
        [data-testid="stMarkdownContainer"] {
        flex: 1 1 auto !important;
        display: flex !important;
        flex-direction: column !important;
        min-height: 0 !important;
    }
    div[data-testid="column"]:has(.jd-hub-news-panel)
        div[data-testid="stElementContainer"]:has(.jd-hub-news-panel)
        [data-testid="stMarkdownContainer"]
        > div {
        flex: 1 1 auto !important;
        display: flex !important;
        flex-direction: column !important;
        min-height: 0 !important;
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
    /* Bordered stacks that use .news-card (not hub news columns). */
    [data-testid="stVerticalBlockBorderWrapper"]:has(.news-card) div[data-testid="stVerticalBlock"] {
        justify-content: flex-start !important;
        align-content: flex-start !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.news-card)
        .stElementContainer:has([data-testid="stMarkdownContainer"]) {
        margin-bottom: 0 !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:has(.news-card) .stElementContainer:has(.stButton) {
        margin-top: 0 !important;
    }
    div[data-testid="column"]:has(.jd-hub-news-panel)
        .stElementContainer:has([data-testid="stMarkdownContainer"]) {
        margin-bottom: 0 !important;
    }
    /* U.S. crypto ETP full page: half-width column — do not force hub panel min height */
    .jd-etp-pulse-rail {
        width: 100%;
        min-width: 0;
    }
    .jd-etp-pulse-rail .jd-hub-news-panel {
        min-height: 0;
    }
    </style>
    """


def format_article_day_label(published: Optional[datetime]) -> str:
    if not published:
        return "Date not listed"
    return published.astimezone(timezone.utc).strftime("%A, %B %d, %Y")


def article_day_key(published: Optional[datetime]) -> Optional[date]:
    if not published:
        return None
    return published.astimezone(timezone.utc).date()


def build_home_news_lane_body_html(
    top: list[dict[str, Any]],
    *,
    show_footnote: bool,
) -> str:
    """Hub left column: panel shell, numbered rows, optional footnote (no summaries)."""
    hid = "jd-hub-news-market-h2"
    parts: list[str] = [
        f'<section class="jd-hub-news-panel" aria-labelledby="{hid}">',
        hub_news_panel_header_html(
            eyebrow="Market feed",
            title="Latest Digital Asset News",
            heading_id=hid,
        ),
        '<ol class="jd-hub-news-list" role="list">',
    ]
    for i, item in enumerate(top, start=1):
        parts.append(render_hub_news_lane_item_html(item, i, show_country=False))
    parts.append("</ol>")
    if show_footnote:
        parts.append(
            '<p class="jd-hub-news-footnote">Most recent stories from the combined RSS list.</p>'
        )
    parts.append("</section>")
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


# --- ETF / ETP market lane (``ETP_NEWS_FEEDS`` = ``DEFAULT_FEEDS`` + :data:`ETP_SUPPLEMENT_FEEDS`); bump ``_filter_rev`` when this changes.

# Shown in the U.S. ETPs "Market pulse" box (full list still uses :func:`load_all_etf_etp_news_cached`).
ETP_PULSE_PREVIEW_COUNT = 4

# ETF / ETP lane: drop items older than this many **calendar** months (rolling, UTC calendar dates).
ETF_NEWS_RECENCY_MONTHS = 3


def _etf_news_cutoff_date_utc() -> date:
    """First calendar date (UTC) still included in the ETF news window (inclusive)."""
    now = datetime.now(timezone.utc)
    y, m = now.year, now.month
    m -= ETF_NEWS_RECENCY_MONTHS
    while m < 1:
        m += 12
        y -= 1
    last_day = calendar.monthrange(y, m)[1]
    d = min(now.day, last_day)
    return date(y, m, d)


def _etf_news_item_within_recency(a: dict[str, Any]) -> bool:
    pub = a.get("published")
    if not isinstance(pub, datetime):
        return False
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    else:
        pub = pub.astimezone(timezone.utc)
    return pub.date() >= _etf_news_cutoff_date_utc()


_RE_ETF_MARKET_LANE = re.compile(
    r"""(?is)
    # A) ETF/ETP / exchange-traded / flows — not generic "listing" / "ticker" / bare "spot"
    (?:\b(?:etf|etps?|etns?|etv|exchange[-\s]traded(?:\s+(?:funds?|products?|notes?|vehicles?))?|spot\s*etf|AUM|inflow|outflow)\b
        [\s\S]{0,1000}?
        \b(?:crypto|cryptocurren\w*|bitcoin|btc(?!ore)|\beth\b(?!s)|\bethereum\b|ether(?!eum\W*classic|net)|defi\w*?|blockchain|web3|xrp\w*|
        sol(?!d|f)|doge(?!r)|on[-\s]chain|digital\W*assets?|gbtc|ibit|fbtc|etha|qbtc|bito|eeth|stake[sd]?\W*et[fh]|
        stablecoin|altcoin|token\w*|layer|meme\W*coin|cbdc|grayscale|bitwise|vaneck|wisdomtree|ark|21\W*shares|hashdex|galaxy|invesco|franklin)
    # B) Digital-asset (incl. stablecoin) or issuer, then strong ETF/ETP / flow terms (no "funds"/"listing" alone)
    |(?:\b(?:crypto|cryptocurren\w*|bitcoin|btc(?!ore)|\beth\b(?!s)|\bethereum\b|defi\w*?|blockchain|web3|xrp\w*|sol(?!d)|gbtc|ibit|fbtc|spot\W*btc|spot\W*eth(?!s)|
        on[-\s]chain|digital\W*assets?|grayscale|bitwise|vaneck|wisdomtree|ark|21\W*shares|hashdex|galaxy|stablecoin|meme|defi\w*?\b|layer)
        [\s\S]{0,1000}?
        \b(?:etf|etps?|etns?|etv|exchange[-\s]traded|AUM|inflow|outflow|spot\W*etf|spot\W*ether|spot\W*bitcoin|holdings))
    # C) Tight: known product tickers / spot pairings
    |(?:\b(?:gbtc|ibit|fbtc|etha|qbtc|bito|eeth|gder|feth)\b|spot\W+btc|spot\W+eth|spot\W+ether|spot\W+bitcoin|spot\W+ethereum|spot\W+xrp|spot\W+sol|spot\W+crypto|spot\W+defi)
    # D) Phrase: "X ETF" with digital asset X
    |(?:\b(?:bitcoin|btc|eth|ether|xrp|sol|defi\w*?|blockchain\w*?|meme\w*?|stablecoin\w*?|on[-\s]chain\w*?|digital\w*?|crypto\w*?)\W*[-–—,]?\W*et[fh]s?)\b
    |(?:\bet[fh]p?s?\W*[-–—,]?\W*(?:for|in|on|exposure|tracking|tender)\W+[\s\S]{0,80}?(?:bitcoin|btc|eth|xrp|sol|defi\w*?|blockchain\w*?|crypto\w*?|digital\w*?))
    )""",
    re.VERBOSE,
)


def _normalize_headline_for_etp(raw: str) -> str:
    t = html_module.unescape(raw or "")
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _etf_market_feed_text(a: dict[str, Any]) -> str:
    return _normalize_headline_for_etp(f"{a.get('title') or ''} {a.get('summary') or ''}").lower()


def is_etf_market_feed_item(a: dict[str, Any]) -> bool:
    """
    Heuristic: title + summary should read **ETF/ETP / exchange-traded product**-oriented in the
    digital-asset space (ticker/spot-ETF branch still catches spot-product headlines without the word *ETF*).
    """
    t = _etf_market_feed_text(a)
    if not t or len(t) < 4:
        return False
    return _RE_ETF_MARKET_LANE.search(t) is not None


def pick_etf_market_feed(
    articles: list[dict[str, Any]],
    *,
    limit: Optional[int] = None,
    scan_cap: Optional[int] = None,
) -> list[dict[str, Any]]:
    """``limit=None`` and ``scan_cap=None`` = all items in ``articles`` (full scan)."""
    n = len(articles)
    take = n if scan_cap is None else min(n, max(0, scan_cap))
    out: list[dict[str, Any]] = []
    for a in articles[:take]:
        if is_etf_market_feed_item(a):
            out.append(a)
            if limit is not None and len(out) >= limit:
                break
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def load_all_etf_etp_news_cached(
    _filter_rev: int = 13,
) -> tuple[list[dict[str, Any]], list[str]]:
    """ETP lane: :data:`ETP_NEWS_FEEDS`, deduped, :func:`is_etf_market_feed_item`, then last :data:`ETF_NEWS_RECENCY_MONTHS` months (UTC)."""
    _ = _filter_rev
    combined, errors = load_all_feeds(ETP_NEWS_FEEDS)
    combined = dedupe_articles(combined, max_items=None)
    combined.sort(
        key=lambda x: x["published"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    out = pick_etf_market_feed(combined, limit=None, scan_cap=None)
    out = [a for a in out if _etf_news_item_within_recency(a)]
    return out, errors


def load_etp_market_news_cached(_filter_rev: int = 13) -> list[dict[str, Any]]:
    """First :data:`ETP_PULSE_PREVIEW_COUNT` items for the U.S. ETPs Market pulse (shared cache with :func:`load_all_etf_etp_news_cached`)."""
    articles, _ = load_all_etf_etp_news_cached(_filter_rev=_filter_rev)
    return articles[:ETP_PULSE_PREVIEW_COUNT]


def build_etp_market_news_box_html(articles: list[dict[str, Any]]) -> str:
    """ETF/ETP RSS pulse: same ``jd-hub-news-panel`` + numbered rows as the home regulatory column."""
    hid = "jd-etp-pulse-h2"
    panel_cls = "jd-hub-news-panel jd-hub-news-panel--empty" if not articles else "jd-hub-news-panel"
    out: list[str] = [
        '<div class="jd-etp-pulse-rail">',
        f'<section class="{panel_cls}" aria-labelledby="{escape(hid)}">',
        hub_news_panel_header_html(eyebrow="ETF & ETP", title="Market Pulse", heading_id=hid),
    ]
    if not articles:
        out.append(
            '<p class="jd-hub-news-empty">No matching headlines right now. Try '
            "<strong>Refresh all data</strong> on the home page to reload RSS.</p>"
        )
    else:
        out.append('<ol class="jd-hub-news-list" role="list">')
        for i, item in enumerate(articles, start=1):
            out.append(render_hub_news_lane_item_html(item, i, show_country=False))
        out.append("</ol>")
    out.append(
        '<p class="jd-hub-news-footnote">'
        "Items favor <strong>ETF / ETP / exchange-traded</strong> and flow language (AUM, inflows) in the <strong>digital-asset</strong> "
        "title and summary — not general crypto policy unless it also ties to those products. Same pool as <strong>All ETF news</strong>. "
        "Only the <strong>last three calendar months</strong> (UTC) are shown. Feeds are still RSS / capped Google News, not a full archive."
        "</p>"
    )
    out.append("</section></div>")
    return "".join(out)
