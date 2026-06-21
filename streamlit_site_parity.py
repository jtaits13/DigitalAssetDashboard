"""
Streamlit ↔ GitHub Pages (static_home) parity: shared nav, CSS, and home zone chrome.

Loads the same stylesheets as ``static_home/index.html`` and mirrors layout structure.
"""

from __future__ import annotations

import re
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

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden !important; height: 0 !important; }
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarNav"], [data-testid="stSidebarNavItems"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }

.stApp {
  font-family: "Outfit", "Segoe UI", system-ui, sans-serif;
  color: var(--ink-soft, #1f4c67);
}
.block-container {
  padding-top: 0 !important;
  padding-bottom: 2rem !important;
  max-width: calc(var(--max, 72rem) + 17.5rem) !important;
  width: 100% !important;
  padding-left: 0.5rem !important;
  padding-right: 0.75rem !important;
}

/* Streamlit flex columns collapse custom HTML unless ancestors stretch full width. */
.stApp section.main,
.stApp [data-testid="stMainBlockContainer"] {
  width: 100% !important;
}
.stApp [data-testid="stVerticalBlock"] {
  width: 100% !important;
  align-items: stretch !important;
}
.stApp [data-testid="stElementContainer"] {
  width: 100% !important;
  max-width: none !important;
}
.stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stHtml"],
.stApp [data-testid="stHtml"] > div {
  width: 100% !important;
  max-width: none !important;
}
.stApp [data-testid="column"]:has(.home-news-rail) {
  flex: 0 1 18rem !important;
  max-width: 20rem !important;
  min-width: 13.5rem !important;
}
.stApp [data-testid="column"]:has(.home-markets-stack) {
  flex: 1 1 0 !important;
  min-width: 0 !important;
}
.stApp [data-testid="column"]:has(.home-zone) {
  display: flex !important;
  flex-direction: column !important;
  gap: 1.1rem !important;
}
.stApp .home-markets-stack.page-shell {
  padding: 1.25rem 0 0;
  max-width: none;
}
.stApp .st-streamlit-home-root {
  display: block !important;
  width: 100% !important;
  max-width: none !important;
  min-width: 0;
  box-sizing: border-box;
}
.stApp .site-experience.page-home .home-reveal,
.stApp .st-streamlit-home-root .home-reveal {
  opacity: 1 !important;
  transform: none !important;
}
.stApp iframe[height="0"],
.stApp iframe[width="0"] {
  position: absolute !important;
  width: 0 !important;
  height: 0 !important;
  border: 0 !important;
  overflow: hidden !important;
  visibility: hidden !important;
}

.stApp [data-testid="stMarkdownContainer"] a { color: inherit; text-decoration: inherit; }
.stApp .site-brand {
  color: var(--ink, #021d41) !important;
  text-decoration: none !important;
  font-weight: 780 !important;
}
.stApp .site-nav a,
.stApp .site-nav__trigger,
.stApp .site-nav__parent-link {
  color: var(--ink-soft, #1f4c67) !important;
  text-decoration: none !important;
}
.stApp .site-nav a.is-active {
  color: var(--teal, #2a5f82) !important;
  background: rgba(42, 95, 130, 0.1) !important;
}
.stApp .hero--command a {
  color: #d4eaf2 !important;
  text-decoration: underline !important;
  text-underline-offset: 2px;
}
.stApp .hero--command a:hover { color: #ffffff !important; }
.stApp .home-jump-nav__link {
  color: #f0f7fb !important;
  text-decoration: none !important;
}
.stApp .headline-list__link {
  color: #d4eef8 !important;
  text-decoration: none !important;
}
.stApp .headline-list__link:hover { color: #ffffff !important; }
.stApp .btn, .stApp .home-chip, .stApp .home-explore-compact__btn { text-decoration: none !important; }

.stApp [data-testid="stMarkdownContainer"] { font-family: inherit; color: inherit; }
.stApp [data-testid="stVerticalBlock"] { gap: 0 !important; }
.stApp .stExpander { margin: 0.5rem 0 1rem; max-width: 48rem; }

.stApp .site-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  margin: 0 -0.5rem 0;
  width: calc(100% + 1rem);
}
.stApp .home-refresh-row {
  display: flex;
  justify-content: flex-end;
  margin: 0.5rem 0 0.85rem;
  padding: 0 0.15rem;
}
.stApp a.home-refresh-btn {
  display: inline-block;
  font-size: 0.82rem;
  font-weight: 650;
  padding: 0.45rem 0.9rem;
  border-radius: 8px;
  border: 1px solid rgba(42, 95, 130, 0.35);
  background: #fff;
  color: var(--ink, #021d41) !important;
  text-decoration: none !important;
}
.stApp a.home-refresh-btn:hover {
  border-color: var(--teal, #2a5f82);
  background: rgba(42, 95, 130, 0.06);
}

.stApp .home-loading-panel {
  padding: 2rem 1.5rem;
  text-align: center;
  color: var(--ink-soft, #1f4c67);
}
.stApp .home-loading-title {
  margin: 0 0 0.35rem;
  font-size: 1.05rem;
  font-weight: 650;
}
.stApp .home-loading-hint {
  margin: 0;
  font-size: 0.88rem;
  opacity: 0.75;
}

section.hub-section { scroll-margin-top: 4.5rem; }
</style>
"""

HOME_LOADING_STACK = """
<p class="home-kpi-legend-once" aria-live="polite">Loading market data…</p>
<div class="hub-section hub-section--panel home-loading-panel">
  <p class="home-loading-title">Fetching RWA, ETP, and crypto datasets</p>
  <p class="home-loading-hint">First load can take 1–2 minutes while upstream APIs and caches warm.</p>
</div>
"""

HOME_LOADING_NEWS_RAIL = """
<aside class="home-news-rail home-news-rail--terminal home-reveal is-visible" aria-labelledby="home-news-rail-title">
  <div class="home-news-rail__head">
    <h2 id="home-news-rail-title" class="home-news-rail__title">News Hub</h2>
  </div>
  <p class="home-loading-hint" style="padding:1rem 1.1rem">Loading headlines…</p>
</aside>
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


def _patch_styles_css_for_streamlit(css: str) -> str:
    """Duplicate page-home selectors under ``.stApp`` for Streamlit's DOM."""
    css = css.replace(":root {", ":root, .stApp {", 1)
    css = re.sub(
        r"(?<![\w-])\.page-home\s+",
        ".stApp .st-streamlit-home-root, .stApp .page-home, .page-home ",
        css,
    )
    return css


def _patch_static_css_for_streamlit(css: str) -> str:
    """
    Streamlit splits ``st.markdown`` blocks, so ``.site-experience.page-home`` ancestor
    selectors never match. Duplicate them under ``.stApp`` as well.
    """
    css = css.replace(":root {", ":root, .stApp {", 1)
    css = css.replace(".site-experience {", ".stApp, .site-experience {", 1)
    css = re.sub(
        r"\.site-experience\.page-home\s+",
        ".stApp .site-experience.page-home, .stApp ",
        css,
    )
    css = re.sub(
        r"\.site-experience\s+(?!\.page-home)",
        ".stApp .site-experience, .stApp ",
        css,
    )
    return css


@st.cache_resource(show_spinner=False)
def _cached_static_stylesheet() -> str:
    """Load static CSS once per process; patch ancestor selectors for Streamlit."""
    chunks: list[str] = []
    styles_path = _STATIC / "styles.css"
    if styles_path.is_file():
        chunks.append(_patch_styles_css_for_streamlit(styles_path.read_text(encoding="utf-8")))
    sx_path = _STATIC / "css/site-experience.css"
    if sx_path.is_file():
        chunks.append(_patch_static_css_for_streamlit(sx_path.read_text(encoding="utf-8")))
    return "\n".join(chunks)


def _embedded_home_styles_html() -> str:
    """Return static CSS for injection via ``st.html`` (style-only → event container)."""
    return f"<style>{_cached_static_stylesheet()}</style>"


def inject_site_styles(*, include_static: bool = True) -> None:
    """Inject GitHub Pages CSS + Streamlit chrome overrides."""
    st.markdown(STREAMLIT_CHROME_CSS, unsafe_allow_html=True)
    if include_static:
        # Style-only HTML is routed to Streamlit's event container (no layout slot).
        st.html(_embedded_home_styles_html())


def render_home_markdown(html: str, *, target: Any = None) -> None:
    """Render a compact HTML fragment; must not include ``<style>`` tags."""
    (target or st).markdown(html.strip(), unsafe_allow_html=True)


def build_home_chrome_html(*, include_refresh: bool = True) -> str:
    """Nav + hero (self-contained HTML fragment)."""
    refresh = (
        '<div class="home-refresh-row"><a class="home-refresh-btn" href="?home_refresh=1">Refresh data</a></div>'
        if include_refresh
        else ""
    )
    return "".join(
        [
            '<div class="site-experience page-home st-streamlit-home-root">',
            render_site_nav_html(active="home", is_landing=True).strip(),
            render_home_hero_html().strip(),
            refresh,
            "</div>",
        ]
    )


def build_home_footer_html(*, footer_month: str, footer_iso: str) -> str:
    return (
        f'<footer class="site-footer site-experience">Digital Assets Dashboard · Home · '
        f'<time datetime="{escape(footer_iso)}">{escape(footer_month)}</time>'
        f"</footer>"
    )


def _nav_link(href: str, label: str, *, active: bool = False) -> str:
    cls = ' class="is-active"' if active else ""
    return f'<a href="{escape(href)}"{cls}>{escape(label)}</a>'


def _page_href(key: str) -> str:
    stem = Path(PAGES[key]).stem
    if key == "home":
        return "/?jd_scroll=top"
    return f"/{stem}"


def render_site_nav_html(*, active: str = "home", is_landing: bool = False) -> str:
    news_href = "#section-news" if is_landing else "/?jd_scroll=news"
    return f"""
<header class="site-header site-experience" role="banner">
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
"""


def render_site_nav(*, active: str = "home", is_landing: bool = False) -> None:
    st.markdown(render_site_nav_html(active=active, is_landing=is_landing), unsafe_allow_html=True)


def _home_jump_nav_html() -> str:
    return """
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
"""


def render_home_hero_html() -> str:
    return f"""
<section class="hero hero--command site-experience page-home" aria-labelledby="page-title">
  <div class="hero-inner hero-inner--single hero-inner--experience">
    <div class="hero-copy hero-copy--lead">
      <p class="home-hero-eyebrow">Market dashboard</p>
      <h1 id="page-title">Digital Assets Dashboard</h1>
      <p class="hero-lead hero-lead--compact">
        <strong>On-chain RWA</strong> from <strong>RWA.xyz</strong>, curated <strong>news</strong>, U.S.-listed
        <strong>crypto ETPs</strong>, and top-line <strong>crypto prices</strong>—one workspace for market direction,
        policy signals, and where tokenization activity is building.
      </p>
      {_home_jump_nav_html()}
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
"""


def render_home_hero() -> None:
    st.markdown(render_home_hero_html(), unsafe_allow_html=True)


def render_home_jump_nav() -> None:
    st.markdown(_home_jump_nav_html(), unsafe_allow_html=True)


def build_home_loading_page_html(*, footer_month: str, footer_iso: str) -> str:
    """Deprecated monolithic loader; kept for tests. Prefer column layout in streamlit_app."""
    return build_home_page_html(
        markets_stack=HOME_LOADING_STACK.strip(),
        news_rail=HOME_LOADING_NEWS_RAIL.strip(),
        footer_month=footer_month,
        footer_iso=footer_iso,
        include_refresh=False,
        embed_styles=False,
    )


def build_home_page_html(
    *,
    markets_stack: str,
    news_rail: str,
    footer_month: str,
    footer_iso: str,
    include_refresh: bool = True,
    embed_styles: bool = False,
) -> str:
    """Monolithic home HTML (fallback). Prefer column layout in ``streamlit_app``."""
    refresh = (
        '<div class="home-refresh-row"><a class="home-refresh-btn" href="?home_refresh=1">Refresh data</a></div>'
        if include_refresh
        else ""
    )
    styles = _embedded_home_styles_html() if embed_styles else ""
    return "".join(
        [
            styles,
            '<div class="site-experience page-home st-streamlit-home-root">',
            render_site_nav_html(active="home", is_landing=True).strip(),
            render_home_hero_html().strip(),
            refresh,
            '<div class="page-shell"><div class="home-main-split"><div class="home-markets-stack">',
            markets_stack.strip(),
            "</div>",
            news_rail.strip(),
            "</div></div>",
            build_home_footer_html(footer_month=footer_month, footer_iso=footer_iso),
            "</div>",
        ]
    ).strip()


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
<aside class="home-news-rail home-news-rail--terminal hub-section hub-section--panel hub-section--news-rail home-reveal is-visible"
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
