"""
Streamlit ↔ GitHub Pages (static_home) parity: shared nav, CSS, and home zone chrome.

Loads the same stylesheets as ``static_home/index.html`` and mirrors layout structure.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import streamlit as st

_REPO = Path(__file__).resolve().parent
_STATIC = _REPO / "static_home"

HOME_NEWS_LIMIT = 4
HOME_PREVIEW_ROWS = 5

# Streamlit multipage routes (filename stem → path)
PAGES = {
    "home": "streamlit_app.py",
    "tmmf": "pages/RWA_Tokenized_MMF.py",
    "stablecoins": "pages/RWA_Stablecoins.py",
    "rwa_global": "pages/RWA_Global_Market_Overview.py",
    "explore_asset": "pages/RWA_Explore_By_Asset_Type.py",
    "explore_participant": "pages/RWA_Explore_By_Market_Participant.py",
    "treasuries": "pages/RWA_US_Treasuries.py",
    "stocks": "pages/RWA_Tokenized_Stocks.py",
    "networks": "pages/RWA_Participants_Networks.py",
    "platforms": "pages/RWA_Participants_Platforms.py",
    "asset_managers": "pages/RWA_Participants_Asset_Managers.py",
    "etps": "pages/US_Crypto_ETPs.py",
    "etf_news": "pages/All_ETF_News.py",
    "crypto": "pages/Crypto_Prices.py",
    "articles": "pages/All_Articles.py",
    "regulatory": "pages/All_Regulatory.py",
    "custodian": "pages/All_Custodian_News.py",
}

STREAMLIT_CHROME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;780&display=swap');

/* Hide Streamlit chrome */
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden !important; height: 0 !important; }
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarNav"], [data-testid="stSidebarNavItems"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

/* App canvas = static site wash + typography */
.stApp {
  background: var(--wash, #f3f7fb);
  font-family: "Outfit", "Segoe UI", system-ui, sans-serif;
}
.block-container {
  padding-top: 0 !important;
  padding-bottom: 2rem !important;
  max-width: calc(var(--max, 68rem) + 17.5rem) !important;
  padding-left: 0.5rem !important;
  padding-right: 0.75rem !important;
}

/* Neutralize Streamlit wrappers inside static home */
.st-parity-root [data-testid="stMarkdownContainer"] { font-family: inherit; }
.st-parity-root [data-testid="stMarkdownContainer"] p:empty { display: none; }
.st-parity-root [data-testid="stVerticalBlock"] { gap: 0 !important; }
.st-parity-root [data-testid="stVerticalBlock"] > div { gap: 0 !important; }
.st-parity-root .stExpander { margin: 0.5rem 0 1rem; max-width: 48rem; }

/* Refresh control ≈ static secondary btn */
.st-parity-root [data-testid="column"]:has(.stRefreshWrap) { margin-bottom: 0.65rem; }
.st-parity-root .stRefreshWrap + div [data-testid="stButton"] button {
  font-family: "Outfit", system-ui, sans-serif;
  font-size: 0.82rem;
  font-weight: 650;
  border-radius: 8px;
  border: 1px solid rgba(42, 95, 130, 0.35);
  background: #fff;
  color: var(--ink, #021d41);
  padding: 0.45rem 0.9rem;
}
.st-parity-root .stRefreshWrap + div [data-testid="stButton"] button:hover {
  border-color: var(--teal, #2a5f82);
  background: rgba(42, 95, 130, 0.06);
}

/* Sticky header inside Streamlit scroll container */
.st-parity-root .site-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  margin: 0 -0.5rem;
  width: calc(100% + 1rem);
}

section.hub-section { scroll-margin-top: 4.5rem; }
</style>
"""

JD_SCROLL_MAP = {
    "top": "page-title",
    "news": "section-news",
    "tmmf": "section-tmmf",
    "stablecoins": "section-stablecoins",
    "onchain": "section-onchain",
    "rwa": "section-onchain",
    "markets": "section-markets",
    "etps": "section-markets",
    "crypto": "section-crypto",
    "market": "section-markets",
    "rwa_global_market": "section-onchain",
    "rwa_explore_asset_type": "section-onchain",
    "rwa_explore_market_participant": "section-onchain",
}


def _read_static_css() -> str:
    chunks: list[str] = []
    for rel in ("styles.css", "css/site-experience.css"):
        path = _STATIC / rel
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def inject_site_styles(*, include_static: bool = True) -> None:
    """Inject GitHub Pages CSS + Streamlit chrome overrides."""
    css = STREAMLIT_CHROME_CSS
    if include_static:
        css += f"<style>{_read_static_css()}</style>"
    st.markdown(css, unsafe_allow_html=True)


def _nav_link(href: str, label: str, *, active: bool = False) -> str:
    cls = ' class="is-active"' if active else ""
    return f'<a href="{escape(href)}"{cls}>{escape(label)}</a>'


def _page_href(key: str) -> str:
    stem = Path(PAGES[key]).stem
    if key == "home":
        return "/?jd_scroll=top"
    return f"/{stem}"


def render_site_nav(*, active: str = "home", is_landing: bool = False) -> None:
    """Primary nav matching static_home/index.html (Streamlit routes)."""
    news_href = "#section-news" if is_landing else "/?jd_scroll=news"
    st.markdown(
        f"""
<header class="site-header" role="banner">
  <div class="site-header__inner">
    <a class="site-brand" href="/?jd_scroll=top">Digital Assets Dashboard</a>
    <nav class="site-nav" aria-label="Primary">
      {_nav_link("/?jd_scroll=top", "Home", active=active == "home")}
      {_nav_link(news_href, "News Hub", active=active == "news")}
      {_nav_link(_page_href("tmmf"), "TMMFs", active=active == "tmmf")}
      {_nav_link(_page_href("stablecoins"), "Stablecoins", active=active == "stablecoins")}
      <div class="site-nav__dropdown">
        <a href="{_page_href("rwa_global")}" class="site-nav__trigger">RWA Market</a>
        <ul class="site-nav__sub">
          <li><a href="{_page_href("rwa_global")}">Market Overview</a></li>
          <li class="site-nav__item site-nav__item--flyout">
            <a href="{_page_href("explore_asset")}" class="site-nav__parent-link">RWA · Assets</a>
            <ul class="site-nav__sub site-nav__sub--nested">
              <li><a href="{_page_href("treasuries")}">U.S. Treasuries</a></li>
              <li><a href="{_page_href("stocks")}">Tokenized Stocks</a></li>
            </ul>
          </li>
          <li class="site-nav__item site-nav__item--flyout">
            <a href="{_page_href("explore_participant")}" class="site-nav__parent-link">RWA · Participants</a>
            <ul class="site-nav__sub site-nav__sub--nested">
              <li><a href="{_page_href("networks")}">Networks</a></li>
              <li><a href="{_page_href("platforms")}">Platforms</a></li>
              <li><a href="{_page_href("asset_managers")}">Asset Managers</a></li>
            </ul>
          </li>
        </ul>
      </div>
      <div class="site-nav__dropdown">
        <span class="site-nav__trigger">U.S. ETPs</span>
        <ul class="site-nav__sub">
          <li><a href="{_page_href("etps")}">U.S. ETP Overview</a></li>
          <li><a href="{_page_href("etf_news")}">ETF/ETP News</a></li>
        </ul>
      </div>
      {_nav_link(_page_href("crypto"), "Crypto Prices", active=active == "crypto")}
    </nav>
  </div>
</header>
""",
        unsafe_allow_html=True,
    )


def render_home_hero() -> None:
    st.markdown(
        """
<section class="hero hero--command" aria-labelledby="page-title">
  <div class="hero-inner hero-inner--single hero-inner--experience">
    <div class="hero-copy hero-copy--lead">
      <p class="home-hero-eyebrow">Market dashboard</p>
      <h1 id="page-title">Digital Assets Dashboard</h1>
      <p class="hero-lead hero-lead--compact">
        <strong>On-chain RWA</strong> from <strong>RWA.xyz</strong>, curated <strong>news</strong>, U.S.-listed
        <strong>crypto ETPs</strong>, and top-line <strong>crypto prices</strong>—one workspace for market direction,
        policy signals, and where tokenization activity is building.
      </p>
""",
        unsafe_allow_html=True,
    )
    render_home_jump_nav()
    st.markdown(
        """
      <p class="hero-dek callout hero-dek--compact">
        For <strong>internal digital asset</strong> materials (documentation, product context, and key contacts),
        see the
        <a href="https://confluence.prod.aws.jpmchase.net/confluence/spaces/viewspace.action?key=DIGITALPRODUCTTEAM"
           target="_blank" rel="noopener noreferrer">Digital Custody Product Team</a>
        space on Confluence (internal).
      </p>
    </div>
  </div>
</section>
""",
        unsafe_allow_html=True,
    )


def render_home_jump_nav() -> None:
    st.markdown(
        """
<nav class="home-jump-nav home-jump-nav--grouped" aria-label="Jump to data sections">
  <div class="home-jump-nav__group">
    <span class="home-jump-nav__group-label">On-chain</span>
    <a href="#section-tmmf" class="home-jump-nav__link home-jump-nav__link--tmmf">
      <span class="home-jump-nav__dot" aria-hidden="true"></span>TMMFs</a>
    <a href="#section-stablecoins" class="home-jump-nav__link home-jump-nav__link--stable">
      <span class="home-jump-nav__dot" aria-hidden="true"></span>Stablecoins</a>
    <a href="#section-onchain" class="home-jump-nav__link home-jump-nav__link--rwa">
      <span class="home-jump-nav__dot" aria-hidden="true"></span>RWA</a>
  </div>
  <div class="home-jump-nav__group">
    <span class="home-jump-nav__group-label">Markets</span>
    <a href="#section-markets" class="home-jump-nav__link home-jump-nav__link--etp">
      <span class="home-jump-nav__dot" aria-hidden="true"></span>ETPs</a>
    <a href="#section-crypto" class="home-jump-nav__link home-jump-nav__link--crypto">
      <span class="home-jump-nav__dot" aria-hidden="true"></span>Crypto</a>
  </div>
</nav>
""",
        unsafe_allow_html=True,
    )


def home_zone_open(
    *,
    section_id: str,
    badge: str,
    title: str,
    subtitle: str,
    zone_class: str,
    related_chips: str = "",
) -> None:
    chips = related_chips or ""
    st.markdown(
        f"""
<section class="hub-section hub-section--panel home-zone {zone_class} home-reveal"
         id="{escape(section_id)}" aria-labelledby="{escape(section_id)}-heading">
  <div class="home-zone__stripe" aria-hidden="true"></div>
  <div class="home-zone__head">
    <span class="home-zone__badge" aria-hidden="true">{escape(badge)}</span>
    <div class="home-zone__titles">
      <h2 class="band-label zone-label" id="{escape(section_id)}-heading">{escape(title)}</h2>
      <p class="section-dek section-dek--wide">{escape(subtitle)}</p>
    </div>
  </div>
  <div class="home-zone__body">
    {chips}
""",
        unsafe_allow_html=True,
    )


def home_zone_close(*, explore_compact: bool = False) -> None:
    explore = ""
    if explore_compact:
        explore = """
    <nav class="home-explore-compact" aria-label="Explore RWA">
      <span class="home-explore-compact__label">Explore</span>
      <a class="home-explore-compact__btn" href="/RWA_Explore_By_Asset_Type">By asset type</a>
      <a class="home-explore-compact__btn" href="/RWA_Explore_By_Market_Participant">By participant</a>
    </nav>
"""
    st.markdown(f"{explore}  </div></section>", unsafe_allow_html=True)


def render_kpi_legend() -> None:
    st.markdown(
        """
<p class="home-kpi-legend-once">
  <strong>How to read KPIs:</strong> On-chain figures use 30-day (30D) % from RWA.xyz.
  U.S. ETP and crypto rows use ~30 calendar days unless noted on the full page.
</p>
""",
        unsafe_allow_html=True,
    )


def _fmt_article_date(published: Any) -> str:
    from datetime import datetime, timezone

    if not published:
        return ""
    if isinstance(published, datetime):
        return published.astimezone(timezone.utc).strftime("%d %b %Y")
    return str(published)


def build_static_news_rail_html(articles: list[dict[str, Any]]) -> str:
    """News Hub rail matching static_home/index.html."""
    items_html: list[str] = []
    for item in articles[:HOME_NEWS_LIMIT]:
        title = escape(str(item.get("title") or "Untitled"))
        link = str(item.get("link") or "").strip()
        source = escape(str(item.get("source") or ""))
        when = escape(_fmt_article_date(item.get("published")))
        meta = ""
        if source or when:
            meta = (
                '<span class="headline-list__meta-row">'
                + (f'<span class="headline-list__source">{source}</span>' if source else "")
                + (f'<span class="headline-list__time">{when}</span>' if when else "")
                + "</span>"
            )
        if link:
            row = (
                f'<li><a class="headline-list__link" href="{escape(link)}" '
                f'target="_blank" rel="noopener noreferrer">{title}</a>{meta}</li>'
            )
        else:
            row = f'<li><span class="headline-list__link headline-list__link--plain">{title}</span>{meta}</li>'
        items_html.append(row)
    if not items_html:
        items_html.append('<li class="headline-list__empty">No headlines loaded yet.</li>')
    list_body = "".join(items_html)
    return f"""
<aside class="home-news-rail home-news-rail--terminal hub-section hub-section--panel hub-section--news-rail home-reveal"
       id="section-news" aria-labelledby="news-heading">
  <h2 class="band-label zone-label" id="news-heading">News Hub</h2>
  <p class="section-dek section-dek--rail">
    Headlines from CoinDesk, CoinTelegraph, Decrypt, The Block, and The Defiant.
  </p>
  <div class="home-news-block">
    <h3 class="home-news-block__heading">Latest Headlines</h3>
    <ul class="headline-list headline-list--rail">{list_body}</ul>
    <div class="home-news-rail__more">
      <a class="btn btn-secondary home-news-rail__cta" href="/All_Articles">All digital asset headlines →</a>
    </div>
  </div>
  <div class="home-news-block home-news-block--feeds">
    <h3 class="home-news-block__heading">Focused News Feeds</h3>
    <nav class="home-feed-links" aria-label="Focused news feeds">
      <a class="btn btn-secondary home-feed-link home-feed-link--regulatory" href="/All_Regulatory">Regulatory News</a>
      <a class="btn btn-secondary home-feed-link home-feed-link--etp" href="/All_ETF_News">ETF / ETP News</a>
      <a class="btn btn-secondary home-feed-link home-feed-link--custody" href="/All_Custodian_News">Custody News</a>
    </nav>
  </div>
</aside>
"""


def render_home_refresh_bar(*, on_refresh_key: str = "parity_refresh") -> bool:
    """Compact refresh control (static site has no sidebar). Returns True if refresh clicked."""
    c1, c2 = st.columns([5, 1])
    with c2:
        return st.button("Refresh data", key=on_refresh_key, use_container_width=True)
    return False


def render_page_shell_open() -> None:
    st.markdown('<div class="page-shell site-experience">', unsafe_allow_html=True)


def render_page_shell_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_home_split_open() -> tuple[Any, Any]:
    """Two-column home layout: markets stack (left) + news rail (right)."""
    render_page_shell_open()
    st.markdown('<div class="home-main-split">', unsafe_allow_html=True)
    return st.columns([1.55, 1], gap="large")


def render_home_split_close() -> None:
    st.markdown("</div></div>", unsafe_allow_html=True)


def related_chips_html(*links: tuple[str, str]) -> str:
    parts = ['<div class="home-related-chips" aria-label="Related pages">']
    parts.append('<span class="home-related-chips__label">Related</span>')
    for href, label in links:
        parts.append(f'<a class="home-chip" href="{escape(href)}">{escape(label)}</a>')
    parts.append("</div>")
    return "".join(parts)
