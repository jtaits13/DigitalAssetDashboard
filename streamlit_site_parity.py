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
import streamlit.components.v1 as components

from news_feeds import format_relative_time

_REPO = Path(__file__).resolve().parent
_STATIC = _REPO / "static_home"

HOME_NEWS_LIMIT = 4
HOME_PREVIEW_ROWS = 5
# Seam between chrome iframe and body iframe (0 = internal note sits flush below hero).
HOME_HERO_TO_CONTENT_GAP = "0px"
HOME_CHROME_IFRAME_INITIAL_HEIGHT = 300
# Subpixel slack so the hero band is not clipped by the chrome iframe edge.
HOME_CHROME_HEIGHT_SLACK_PX = 2

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
  background: var(--wash, #f3f7fb);
}
.block-container {
  padding-top: 0 !important;
  padding-bottom: 2rem !important;
  max-width: calc(var(--max, 72rem) + 17.5rem) !important;
  width: 100% !important;
  padding-left: 0.5rem !important;
  padding-right: 0.75rem !important;
}
/* Home: full-bleed nav + hero and body split (match GitHub Pages edge-to-edge bands). */
.stApp:has(.home-chrome-iframe-marker) .block-container {
  padding-left: 0 !important;
  padding-right: 0 !important;
  max-width: none !important;
  width: 100% !important;
}
.stApp [data-testid="stElementContainer"]:has(.home-chrome-iframe-marker),
.stApp [data-testid="stElementContainer"]:has(.home-body-iframe-marker),
.stApp [data-testid="stElementContainer"]:has(.home-hero-content-gap) {
  width: 100vw !important;
  max-width: 100vw !important;
  margin-left: calc(50% - 50vw) !important;
  margin-right: calc(50% - 50vw) !important;
  padding: 0 !important;
}
.stApp .home-hero-content-gap {
  display: block;
  width: 100%;
  height: HOME_HERO_TO_CONTENT_GAP_PLACEHOLDER;
  min-height: HOME_HERO_TO_CONTENT_GAP_PLACEHOLDER;
  max-height: HOME_HERO_TO_CONTENT_GAP_PLACEHOLDER;
  margin: 0;
  padding: 0;
  background: var(--wash, #f3f7fb);
  border: 0;
  overflow: hidden;
  flex-shrink: 0;
}
.stApp [data-testid="stElementContainer"]:has(.home-hero-content-gap) {
  margin: 0 !important;
  padding: 0 !important;
  height: HOME_HERO_TO_CONTENT_GAP_PLACEHOLDER !important;
  min-height: HOME_HERO_TO_CONTENT_GAP_PLACEHOLDER !important;
  max-height: HOME_HERO_TO_CONTENT_GAP_PLACEHOLDER !important;
  line-height: 0;
  overflow: hidden;
  flex-shrink: 0;
}
.stApp [data-testid="stElementContainer"]:has(.home-hero-content-gap) [data-testid="stHtml"],
.stApp [data-testid="stElementContainer"]:has(.home-hero-content-gap) [data-testid="stHtml"] > div,
.stApp [data-testid="stElementContainer"]:has(.home-hero-content-gap) [data-testid="stMarkdownContainer"],
.stApp [data-testid="stElementContainer"]:has(.home-hero-content-gap) [data-testid="stMarkdownContainer"] > div {
  margin: 0 !important;
  padding: 0 !important;
  line-height: 0;
  height: HOME_HERO_TO_CONTENT_GAP_PLACEHOLDER !important;
  min-height: HOME_HERO_TO_CONTENT_GAP_PLACEHOLDER !important;
  max-height: HOME_HERO_TO_CONTENT_GAP_PLACEHOLDER !important;
}
.stApp:has(.home-body-iframe-marker) [data-testid="stElementContainer"]:has([data-testid="stSpinner"]) {
  margin: 0 !important;
  padding: 0 !important;
  min-height: 0 !important;
}
.stApp:has(.home-body-iframe-marker) [data-testid="stMarkdownContainer"]:has(.site-footer) {
  max-width: calc(var(--max, 72rem) + 17.5rem);
  margin-left: auto;
  margin-right: auto;
  padding-left: 0.5rem;
  padding-right: 0.75rem;
  width: 100%;
  box-sizing: border-box;
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
  flex: 0 0 18rem !important;
  width: 18rem !important;
  max-width: 20rem !important;
  min-width: 13.5rem !important;
}
.stApp [data-testid="column"]:has(.home-markets-iframe),
.stApp [data-testid="column"]:has(.home-kpi-legend-once),
.stApp [data-testid="column"]:has(.home-zone) {
  flex: 1 1 0 !important;
  min-width: 0 !important;
  width: auto !important;
  padding-top: 1.25rem;
}
.stApp [data-testid="stHorizontalBlock"]:has(.home-news-rail) {
  display: flex !important;
  flex-direction: row !important;
  align-items: stretch !important;
  gap: 1.35rem !important;
  overflow: visible !important;
  width: 100% !important;
  height: auto !important;
  max-height: none !important;
}
.stApp [data-testid="stHorizontalBlock"]:has(.home-news-rail) > [data-testid="column"] {
  align-self: stretch !important;
  overflow: visible !important;
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
}
.stApp [data-testid="column"]:has(.home-news-rail) [data-testid="stVerticalBlock"] {
  min-height: 100% !important;
  height: auto !important;
  overflow: visible !important;
  width: 100% !important;
}
.stApp [data-testid="stHorizontalBlock"]:has(.home-news-rail) [data-testid="stElementContainer"] {
  overflow: visible !important;
  height: auto !important;
  max-height: none !important;
}
.stApp [data-testid="column"]:has(.home-markets-iframe) {
  overflow: visible !important;
  flex: 1 1 0 !important;
}
.stApp [data-testid="stHorizontalBlock"]:has(.home-news-rail) iframe {
  display: block !important;
  width: 100% !important;
  max-height: none !important;
  overflow: hidden !important;
}
.stApp .home-news-rail {
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}
.stApp .home-news-rail-placeholder {
  width: 100% !important;
  visibility: hidden !important;
  pointer-events: none !important;
}
/* Streamlit splits markdown blocks — zones are not inside .home-markets-stack in the DOM. */
.stApp .home-zone.hub-section--panel {
  display: block !important;
  width: 100% !important;
  margin: 0 0 1.35rem !important;
  border: 1px solid rgba(199, 216, 232, 0.9);
  border-radius: 14px;
  padding: 0;
  overflow: hidden;
  background: #ffffff;
  box-shadow:
    0 1px 2px rgba(2, 29, 65, 0.04),
    0 8px 26px rgba(2, 29, 65, 0.06);
}
.stApp .home-kpi-legend-once {
  margin: 0 0 0.85rem;
  padding: 0.65rem 0.85rem;
  font-size: 0.78rem;
  line-height: 1.45;
  color: var(--ink-soft, #1f4c67);
  background: rgba(42, 95, 130, 0.06);
  border: 1px solid rgba(42, 95, 130, 0.14);
  border-radius: 10px;
}
.stApp .home-kpi-legend-once strong {
  color: var(--ink, #021d41);
  font-weight: 650;
}
.stApp [data-testid="stElementContainer"]:has(.home-chrome-iframe-marker),
.stApp [data-testid="column"]:has(.home-markets-iframe) [data-testid="stElementContainer"] {
  height: auto !important;
  min-height: 0 !important;
  overflow: visible !important;
  flex-shrink: 0 !important;
}
.stApp [data-testid="stElementContainer"]:has(.home-chrome-iframe-marker) iframe {
  display: block;
  width: 100% !important;
  border: 0;
  overflow: hidden;
  margin: 0 !important;
  padding: 0 !important;
  vertical-align: top;
}
.stApp .block-container,
.stApp [data-testid="stMainBlockContainer"],
.stApp [data-testid="stElementContainer"]:has(.st-streamlit-home-root),
.stApp [data-testid="stMarkdownContainer"]:has(.st-streamlit-home-root) {
  overflow: visible !important;
  max-height: none !important;
}
.stApp .home-news-rail:not(.home-news-rail--st-fixed) {
  position: relative !important;
  top: auto !important;
}
.stApp .home-news-rail.home-news-rail--st-fixed {
  position: fixed !important;
  top: 0.75rem !important;
  max-height: calc(100vh - 1.5rem) !important;
  overflow-y: auto !important;
  z-index: 999 !important;
}
.stApp .st-streamlit-home-root .hero.hero--command {
  margin-bottom: 0;
}
.stApp [data-testid="stElementContainer"]:has(.home-chrome-iframe-marker) {
  margin-bottom: 0 !important;
  position: sticky !important;
  top: 0 !important;
  z-index: 20 !important;
}
.stApp [data-testid="stElementContainer"]:has(.home-body-iframe-marker) {
  margin-top: 0 !important;
  margin-bottom: 0 !important;
  padding-top: 0 !important;
}
.stApp:has(.home-body-iframe-marker) [data-testid="stElementContainer"]:has([data-testid="stSpinner"]) {
  margin: 0 !important;
  padding: 0 !important;
  min-height: 0 !important;
  height: auto !important;
}
.stApp [data-testid="stElementContainer"]:has(.home-body-iframe-marker) iframe {
  display: block !important;
  width: 100% !important;
  border: 0;
  overflow: hidden !important;
}
.stApp:has(.home-body-iframe-marker) .block-container {
  padding-bottom: 0.5rem !important;
}
.stApp:has(.home-body-iframe-marker) [data-testid="stVerticalBlock"] {
  gap: 0 !important;
}
.stApp:has(.home-body-iframe-marker) [data-testid="stMainBlockContainer"] {
  min-height: 0 !important;
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
  position: relative;
  top: auto;
  z-index: 10;
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

.stApp .hub-section { scroll-margin-top: 4.5rem; }
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
    # Zones render as sibling markdown blocks, not nested under .home-markets-stack.
    css = css.replace(
        ".home-markets-stack .hub-section--panel",
        ".home-markets-stack .hub-section--panel, .home-zone.hub-section--panel",
    )
    return css


def _patch_inner_page_css_for_streamlit(css: str) -> str:
    """Mirror inner-page ``body`` / ``.site-experience.page-inner--rich`` rules onto the subpage wrapper."""
    if ":root, .stApp {" not in css:
        css = css.replace(":root {", ":root, .stApp {", 1)
    css = re.sub(
        r"\.site-experience\.page-inner--rich",
        ".stApp .streamlit-subpage-root.site-experience.page-inner--rich, .site-experience.page-inner--rich",
        css,
    )
    css = re.sub(
        r"body\.(page-[a-z][a-z0-9-]*)",
        r".stApp .streamlit-subpage-root.\1, body.\1",
        css,
    )
    return css


_SUBPAGE_INNER_CSS = (
    "css/inner-page-experience.css",
    "css/inner-page-zone-parity.css",
)
_SUBPAGE_MOCK_CSS: dict[str, tuple[str, ...]] = {
    "etp": ("mockups/etp-inner-page-mock.css",),
    "crypto": ("mockups/etp-inner-page-mock.css", "mockups/crypto-inner-page-mock.css"),
}
SUBPAGE_ROOT_CLASS: dict[str, str] = {
    "article": "page-full-feed page-article-feed page-inner--rich",
    "article_etp": "page-full-feed page-article-feed page-etp page-inner--rich",
    "etp": "page-etp page-inner--rich mock-etp-inner",
    "crypto": "page-crypto page-inner--rich mock-crypto-inner",
}

SUBPAGE_STREAMLIT_CSS = """
.stApp .streamlit-subpage-root {
  display: block;
  width: 100%;
}
.stApp:has(.streamlit-subpage-root) .block-container {
  padding-top: 0 !important;
}
.stApp .streamlit-subpage-root .page-shell {
  max-width: calc(var(--max, 72rem) + 17.5rem);
  margin-left: auto;
  margin-right: auto;
  width: 100%;
  box-sizing: border-box;
}
.stApp .streamlit-subpage-root .inner-rich-zone {
  opacity: 1 !important;
  transform: none !important;
}
.stApp:has(.streamlit-subpage-root) [data-testid="stElementContainer"],
.stApp:has(.streamlit-subpage-root) [data-testid="stVerticalBlock"],
.stApp:has(.streamlit-subpage-root) [data-testid="stMarkdownContainer"] {
  opacity: 1 !important;
  visibility: visible !important;
  max-height: none !important;
}
"""


@st.cache_resource(show_spinner=False)
def _cached_subpage_stylesheet(kind: str) -> str:
    chunks: list[str] = []
    for rel in _SUBPAGE_INNER_CSS:
        path = _STATIC / rel
        if path.is_file():
            chunks.append(_patch_inner_page_css_for_streamlit(path.read_text(encoding="utf-8")))
    for rel in _SUBPAGE_MOCK_CSS.get(kind, ()):
        path = _STATIC / rel
        if path.is_file():
            chunks.append(_patch_inner_page_css_for_streamlit(path.read_text(encoding="utf-8")))
    return "\n".join(chunks)


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


STREAMLIT_HOME_INTERNAL_NOTE_CSS = """
body.page-home.site-experience .home-internal-note {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.4rem 0.55rem;
  margin: 0 0 0.65rem;
  padding: 0.38rem 0.65rem 0.38rem 0.5rem;
  font-size: 0.76rem;
  line-height: 1.42;
  color: #3a6070;
  background: linear-gradient(90deg, rgba(37, 128, 156, 0.07) 0%, rgba(37, 128, 156, 0.02) 100%);
  border: 1px solid rgba(37, 128, 156, 0.16);
  border-left: 3px solid #25809c;
  border-radius: 0 8px 8px 0;
}
body.page-home.site-experience .home-internal-note__badge {
  flex-shrink: 0;
  padding: 0.1rem 0.4rem;
  font-size: 0.6rem;
  font-weight: 750;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #25809c;
  background: rgba(37, 128, 156, 0.1);
  border-radius: 4px;
}
body.page-home.site-experience .home-internal-note strong {
  color: #2a5563;
  font-weight: 650;
}
body.page-home.site-experience .home-internal-note a {
  color: #1a6b7e;
  font-weight: 650;
  text-decoration: underline;
  text-decoration-color: rgba(26, 107, 126, 0.35);
  text-underline-offset: 0.14em;
}
body.page-home.site-experience .home-internal-note a:hover {
  color: #134d5c;
  text-decoration-color: rgba(19, 77, 92, 0.55);
}
"""


@st.cache_resource(show_spinner=False)
def _cached_iframe_body_stylesheet() -> str:
    """CSS for combined news + markets iframe (news sets height; markets scroll)."""
    chunks: list[str] = [
        "@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;780&display=swap');",
    ]
    styles_path = _STATIC / "styles.css"
    if styles_path.is_file():
        chunks.append(styles_path.read_text(encoding="utf-8"))
    sx_path = _STATIC / "css/site-experience.css"
    if sx_path.is_file():
        chunks.append(sx_path.read_text(encoding="utf-8"))
    chunks.append(
        f"""
html, body.page-home.site-experience {{
  margin: 0;
  padding: 0;
  background: var(--wash, #f3f7fb);
  overflow: visible;
}}
.home-reveal {{ opacity: 1 !important; transform: none !important; }}
body.page-home.site-experience .jd-kpi-window-note {{ display: none; }}
body.page-home.site-experience .page-shell {{
  max-width: calc(var(--max, 72rem) + 17.5rem);
  margin-left: auto;
  margin-right: auto;
  width: 100%;
  padding-top: 0;
  padding-right: 0.75rem;
  padding-bottom: 0.75rem;
  padding-left: 0.5rem;
  overflow: visible;
  box-sizing: border-box;
}}
body.page-home.site-experience .home-kpi-legend-once {{
  margin-top: 0;
}}
body.page-home.site-experience .home-main-split {{
  align-items: start;
  overflow: visible;
}}
body.page-home.site-experience .home-news-rail {{
  position: relative;
  top: auto;
  max-height: none;
  align-self: start;
  margin-top: 0;
}}
body.page-home.site-experience .home-news-rail--terminal {{
  overflow: hidden;
}}
body.page-home.site-experience .home-markets-stack {{
  display: block !important;
  overflow-x: hidden !important;
  overflow-y: auto !important;
  min-height: 0;
  scrollbar-width: thin;
  scrollbar-color: rgba(42, 95, 130, 0.35) transparent;
  -webkit-overflow-scrolling: touch;
}}
body.page-home.site-experience .home-markets-stack .home-kpi-legend-once,
body.page-home.site-experience .home-markets-stack .home-zone,
body.page-home.site-experience .home-markets-stack .hub-section--panel {{
  flex: none !important;
  flex-shrink: 0 !important;
  height: auto !important;
  min-height: auto !important;
  max-height: none !important;
}}
body.page-home.site-experience .home-markets-stack .hub-section--panel {{
  overflow: hidden;
  margin-bottom: 1.35rem;
}}
body.page-home.site-experience .home-markets-stack .hub-section--panel:last-child {{
  margin-bottom: 0;
}}
body.page-home.site-experience .home-markets-stack .home-zone__body,
body.page-home.site-experience .home-markets-stack .table-wrap {{
  overflow: visible !important;
}}
body.page-home.site-experience .home-markets-stack::-webkit-scrollbar {{
  width: 8px;
}}
body.page-home.site-experience .home-markets-stack::-webkit-scrollbar-thumb {{
  background: rgba(42, 95, 130, 0.28);
  border-radius: 999px;
}}
{STREAMLIT_HOME_INTERNAL_NOTE_CSS}
"""
    )
    return "\n".join(chunks)


@st.cache_resource(show_spinner=False)
def _cached_iframe_home_stylesheet() -> str:
    """Unpatched static CSS for chrome / legacy markets-only iframe."""
    chunks: list[str] = [
        "@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;780&display=swap');",
    ]
    styles_path = _STATIC / "styles.css"
    if styles_path.is_file():
        chunks.append(styles_path.read_text(encoding="utf-8"))
    sx_path = _STATIC / "css/site-experience.css"
    if sx_path.is_file():
        chunks.append(sx_path.read_text(encoding="utf-8"))
    chunks.append(
        """
html, body.page-home.site-experience {
  margin: 0;
  padding: 0;
  background: transparent;
  width: 100%;
  min-width: 0;
  overflow: hidden;
  height: auto;
}
.home-reveal { opacity: 1 !important; transform: none !important; }
body.page-home.site-experience .jd-kpi-window-note { display: none; }
body.page-home.site-experience .home-news-rail { position: relative; top: auto; max-height: none; }
body.page-home.site-experience .site-header { position: relative; top: auto; width: 100%; }
body.page-home.site-experience .hero.hero--command {
  width: 100%;
  margin-bottom: 0;
  padding-bottom: 0.25rem !important;
}
body.page-home.site-experience .home-jump-nav {
  margin-bottom: 0;
}
"""
    )
    return "\n".join(chunks)


def iframe_internal_link_script() -> str:
    """
    Streamlit ``components.html`` iframes are sandboxed without ``allow-top-navigation``,
    so ``target="_top"`` is ignored. Intercept internal links and ask the host to navigate.
    """
    return """
<script>
(function () {
  function normalizeHref(href) {
    href = String(href || "").trim();
    if (!href) return "";
    if (href.charAt(0) === "/") return href;
    if (href.charAt(0) === "?") return "/" + href;
    return href;
  }
  function isRoutable(href) {
    if (!href) return false;
    href = href.trim();
    if (href.charAt(0) === "#") return false;
    if (/^https?:\\/\\//i.test(href)) return false;
    if (href.charAt(0) === "/" || href.charAt(0) === "?") return true;
    return false;
  }
  function bindInternalLinks() {
    document.querySelectorAll("a[href]").forEach(function (a) {
      if (a.dataset.jpmNavBound) return;
      var href = a.getAttribute("href") || "";
      if (!isRoutable(href)) return;
      if (a.classList.contains("home-jump-nav__link")) return;
      a.dataset.jpmNavBound = "1";
      a.addEventListener("click", function (ev) {
        ev.preventDefault();
        try {
          window.parent.postMessage(
            { type: "jpm-navigate", href: normalizeHref(href) },
            "*"
          );
        } catch (e) {}
      });
    });
  }
  bindInternalLinks();
  window.addEventListener("load", bindInternalLinks);
})();
</script>"""


def iframe_jump_nav_script() -> str:
    """Hero jump pills: post section id to parent (zones live in the body iframe)."""
    return """
<script>
(function () {
  function bindJumpNav() {
    document.querySelectorAll(".home-jump-nav__link").forEach(function (link) {
      if (link.dataset.jpmJumpBound) return;
      link.dataset.jpmJumpBound = "1";
      link.addEventListener("click", function (ev) {
        var href = link.getAttribute("href") || "";
        var sectionId = "";
        if (href.charAt(0) === "#") {
          sectionId = href.slice(1);
        } else {
          var m = href.match(/[?&]jd_scroll=([^&]+)/);
          if (m) sectionId = m[1];
        }
        if (!sectionId) return;
        if (sectionId.indexOf("section-") !== 0) {
          var map = {
            tmmf: "section-tmmf",
            stablecoins: "section-stablecoins",
            onchain: "section-onchain",
            rwa: "section-onchain",
            markets: "section-markets",
            etps: "section-markets",
            crypto: "section-crypto"
          };
          sectionId = map[sectionId] || sectionId;
        }
        ev.preventDefault();
        document.querySelectorAll(".home-jump-nav__link").forEach(function (item) {
          item.classList.remove("is-active");
          item.removeAttribute("aria-current");
        });
        link.classList.add("is-active");
        link.setAttribute("aria-current", "true");
        try {
          window.parent.postMessage({ type: "jpm-home-scroll", sectionId: sectionId }, "*");
        } catch (e) {}
      });
    });
  }
  bindJumpNav();
  window.addEventListener("load", bindJumpNav);
})();
</script>"""


STREAMLIT_SITE_NAV_ROUTER_JS = """
<script>
(function () {
  var win = window.parent && window.parent.document ? window.parent : window;
  var doc = win.document;
  if (win.__jpmNavRouterBound) return;
  win.__jpmNavRouterBound = true;

  function isHomePath() {
    var p = win.location.pathname || "/";
    return p === "/" || p.endsWith("/");
  }

  function navigate(href) {
    href = String(href || "").trim();
    if (!href) return;
    var scrollKey = null;
    try {
      var u = new URL(href, win.location.origin);
      scrollKey = u.searchParams.get("jd_scroll");
      if (scrollKey && isHomePath() && typeof win.jpmPollScrollToHomeSection === "function") {
        var map = {
          top: "page-title",
          news: "section-news",
          tmmf: "section-tmmf",
          stablecoins: "section-stablecoins",
          onchain: "section-onchain",
          rwa: "section-onchain",
          markets: "section-markets",
          etps: "section-markets",
          crypto: "section-crypto"
        };
        var sectionId = map[scrollKey] || scrollKey;
        if (sectionId.indexOf("section-") !== 0 && scrollKey === "top") {
          sectionId = "page-title";
        }
        win.jpmPollScrollToHomeSection(sectionId, 120);
        return;
      }
      win.top.location.href = u.pathname + u.search + u.hash;
    } catch (e) {
      win.top.location.href = href;
    }
  }

  function shouldHandleLink(a) {
    if (!a) return false;
    if (a.target === "_blank") return false;
    var href = (a.getAttribute("href") || "").trim();
    if (!href || href.charAt(0) === "#") return false;
    if (/^https?:\\/\\//i.test(href)) return false;
    return href.charAt(0) === "/" || href.charAt(0) === "?";
  }

  win.addEventListener("message", function (ev) {
    if (!ev.data || ev.data.type !== "jpm-navigate") return;
    navigate(ev.data.href);
  });

  doc.addEventListener(
    "click",
    function (ev) {
      var a = ev.target.closest(
        ".site-experience a, .page-back-below-header a, .back-link a, .home-chip, .btn-primary, .btn-secondary"
      );
      if (!shouldHandleLink(a)) return;
      ev.preventDefault();
      navigate(a.getAttribute("href"));
    },
    true
  );
})();
</script>
"""


HOME_PAGE_SCROLL_JS = """
<script>
(function () {
  var win = window.parent && window.parent.document ? window.parent : window;
  var doc = win.document;
  var JD_SCROLL_MAP = {
    top: "page-title",
    news: "section-news",
    tmmf: "section-tmmf",
    stablecoins: "section-stablecoins",
    onchain: "section-onchain",
    rwa: "section-onchain",
    markets: "section-markets",
    etps: "section-markets",
    crypto: "section-crypto",
    market: "section-markets",
    rwa_global_market: "section-onchain",
    rwa_explore_asset_type: "section-onchain",
    rwa_explore_market_participant: "section-onchain"
  };

  function isHomePath() {
    var p = win.location.pathname || "/";
    return p === "/" || p.endsWith("/");
  }

  function navigateFromMessage(href) {
    href = String(href || "").trim();
    if (!href) return;
    var scrollKey = null;
    try {
      var u = new URL(href, win.location.origin);
      scrollKey = u.searchParams.get("jd_scroll");
      if (u.searchParams.has("home_refresh")) {
        win.top.location.href = u.pathname + u.search;
        return;
      }
    } catch (e) {}

    if (scrollKey && isHomePath()) {
      var sectionId = JD_SCROLL_MAP[scrollKey] || scrollKey;
      if (sectionId.indexOf("section-") !== 0 && scrollKey === "top") {
        sectionId = "page-title";
      }
      if (sectionId !== "page-title") setActiveSection(sectionId);
      if (!scrollToSection(sectionId)) pollScroll(sectionId, 120);
      return;
    }

    try {
      var target = new URL(href, win.location.origin);
      win.top.location.href = target.pathname + target.search + target.hash;
    } catch (e) {
      win.top.location.href = href;
    }
  }

  function findBodyFrame() {
    var match = null;
    doc.querySelectorAll("iframe").forEach(function (frame) {
      try {
        var inner = frame.contentDocument;
        if (inner && inner.querySelector(".home-main-split")) match = frame;
      } catch (e) {}
    });
    return match;
  }

  function findChromeFrame() {
    var match = null;
    doc.querySelectorAll("iframe").forEach(function (frame) {
      try {
        var inner = frame.contentDocument;
        if (inner && inner.querySelector(".hero--command") && !inner.querySelector(".home-main-split")) {
          match = frame;
        }
      } catch (e) {}
    });
    return match;
  }

  function setActiveSection(sectionId) {
    if (!sectionId) return;
    var chromeFrame = findChromeFrame();
    if (!chromeFrame) return;
    var chromeDoc;
    try {
      chromeDoc = chromeFrame.contentDocument;
    } catch (e) {
      return;
    }
    if (!chromeDoc) return;
    chromeDoc.querySelectorAll(".home-jump-nav__link").forEach(function (link) {
      var href = link.getAttribute("href") || "";
      var on = href === "#" + sectionId;
      link.classList.toggle("is-active", on);
      if (on) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    });
  }

  function initSectionSpy() {
    var bodyFrame = findBodyFrame();
    if (!bodyFrame) return false;
    var inner;
    try {
      inner = bodyFrame.contentDocument;
    } catch (e) {
      return false;
    }
    if (!inner) return false;
    var markets = inner.querySelector(".home-markets-stack");
    if (!markets) return false;
    if (markets.dataset.jpmSpyBound === "1") return true;

    var sectionIds = [
      "section-tmmf",
      "section-stablecoins",
      "section-onchain",
      "section-markets",
      "section-crypto"
    ];
    var sections = [];
    sectionIds.forEach(function (id) {
      var el = inner.getElementById(id);
      if (el) sections.push(el);
    });
    if (!sections.length) return false;

    markets.dataset.jpmSpyBound = "1";

    if ("IntersectionObserver" in win) {
      var navObserver = new IntersectionObserver(
        function (entries) {
          var visible = entries
            .filter(function (e) {
              return e.isIntersecting;
            })
            .sort(function (a, b) {
              return b.intersectionRatio - a.intersectionRatio;
            });
          if (visible.length) setActiveSection(visible[0].target.id);
        },
        { root: markets, rootMargin: "-20% 0px -55% 0px", threshold: [0, 0.15, 0.4] }
      );
      sections.forEach(function (section) {
        navObserver.observe(section);
      });
    } else {
      markets.addEventListener("scroll", function () {
        var best = null;
        var bestScore = -1;
        var rootTop = markets.getBoundingClientRect().top;
        var rootBottom = markets.getBoundingClientRect().bottom;
        sections.forEach(function (section) {
          var rect = section.getBoundingClientRect();
          var visible = Math.min(rect.bottom, rootBottom) - Math.max(rect.top, rootTop);
          if (visible > bestScore) {
            bestScore = visible;
            best = section;
          }
        });
        if (best) setActiveSection(best.id);
      });
    }

    setActiveSection(sections[0].id);
    return true;
  }

  function scrollToSection(sectionId) {
    if (!sectionId) return false;
    if (sectionId === "page-title") {
      try {
        win.scrollTo({ top: 0, behavior: "auto" });
      } catch (e) {}
      return true;
    }
    var bodyFrame = findBodyFrame();
    if (!bodyFrame) return false;
    var inner;
    try {
      inner = bodyFrame.contentDocument;
    } catch (e) {
      return false;
    }
    if (!inner) return false;
    var target = inner.getElementById(sectionId);
    if (!target) return false;

    var markets = inner.querySelector(".home-markets-stack");
    if (markets && markets.contains(target)) {
      var top =
        target.getBoundingClientRect().top -
        markets.getBoundingClientRect().top +
        markets.scrollTop;
      var smooth = !win.matchMedia("(prefers-reduced-motion: reduce)").matches;
      try {
        markets.scrollTo({ top: Math.max(0, top - 6), behavior: smooth ? "smooth" : "auto" });
      } catch (e) {
        markets.scrollTop = Math.max(0, top - 6);
      }
    }
    setActiveSection(sectionId);
    return true;
  }

  function pollScroll(sectionId, attempts) {
    var left = attempts || 120;
    var timer = win.setInterval(function () {
      if (scrollToSection(sectionId)) {
        win.clearInterval(timer);
        return;
      }
      if (--left <= 0) win.clearInterval(timer);
    }, 50);
  }

  win.addEventListener("message", function (ev) {
    if (!ev.data) return;
    if (ev.data.type === "jpm-navigate") {
      navigateFromMessage(ev.data.href);
      return;
    }
    if (ev.data.type !== "jpm-home-scroll") return;
    var id = String(ev.data.sectionId || "").trim();
    if (!id) return;
    setActiveSection(id);
    if (!scrollToSection(id)) pollScroll(id, 120);
  });

  win.jpmScrollToHomeSection = scrollToSection;
  win.jpmPollScrollToHomeSection = pollScroll;
  win.jpmSetActiveHomeSection = setActiveSection;

  (function pollSpy() {
    var tries = 0;
    var timer = win.setInterval(function () {
      if (initSectionSpy() || ++tries > 120) win.clearInterval(timer);
    }, 50);
  })();
})();
</script>
"""


def iframe_chrome_height_script() -> str:
    """Resize chrome iframe to the full hero band (callout + blue padding), with a small slack buffer."""
    slack = HOME_CHROME_HEIGHT_SLACK_PX
    return f"""
<script>
(function () {{
  var slack = {slack};
  function measureChromeHeight() {{
    var hero = document.querySelector(".hero--command");
    if (!hero) return 0;
    var docTop = document.documentElement.getBoundingClientRect().top;
    return Math.ceil(hero.getBoundingClientRect().bottom - docTop + slack);
  }}
  function sendHeight() {{
    var h = measureChromeHeight();
    if (h <= 80) return;
    window.parent.postMessage({{ type: "streamlit:setFrameHeight", height: h }}, "*");
    try {{
      window.parent.postMessage({{ type: "jpm-chrome-height", height: h }}, "*");
    }} catch (e) {{}}
  }}
  sendHeight();
  window.addEventListener("load", sendHeight);
  if (document.fonts && document.fonts.ready) {{
    document.fonts.ready.then(sendHeight);
  }}
  if (typeof ResizeObserver !== "undefined") {{
    var hero = document.querySelector(".hero--command");
    if (hero) new ResizeObserver(sendHeight).observe(hero);
  }}
  [50, 150, 400, 800, 1500, 3000, 5000].forEach(function (ms) {{
    setTimeout(sendHeight, ms);
  }});
}})();
</script>"""


def iframe_auto_height_script(*, root_selector: str = "body", extra_pad: int = 32) -> str:
    """Resize a Streamlit ``components.html`` iframe to its document height."""
    return f"""
<script>
(function () {{
  function measureHeight() {{
    var hero = document.querySelector(".hero--command");
    if (hero) {{
      var top = document.body.getBoundingClientRect().top;
      return Math.ceil(hero.getBoundingClientRect().bottom - top + {extra_pad});
    }}
    var root = document.querySelector({root_selector!r}) || document.body;
    return Math.ceil(Math.max(
      root.scrollHeight,
      root.offsetHeight,
      document.body.scrollHeight,
      document.documentElement.scrollHeight,
      document.body.offsetHeight,
      document.documentElement.offsetHeight
    )) + {extra_pad};
  }}
  function sendHeight() {{
    var h = measureHeight();
    window.parent.postMessage({{ type: "streamlit:setFrameHeight", height: h }}, "*");
  }}
  sendHeight();
  window.addEventListener("load", sendHeight);
  if (document.fonts && document.fonts.ready) {{
    document.fonts.ready.then(sendHeight);
  }}
  if (typeof ResizeObserver !== "undefined") {{
    var ro = new ResizeObserver(sendHeight);
    ro.observe(document.body);
    ro.observe(document.documentElement);
    var root = document.querySelector({root_selector!r});
    if (root) ro.observe(root);
  }}
  [50, 150, 400, 800, 1500, 3000, 5000].forEach(function (ms) {{
    setTimeout(sendHeight, ms);
  }});
}})();
</script>"""


HOME_IFRAME_HEIGHT_SYNC_JS = f"""
<script>
(function () {{
  var doc = window.parent && window.parent.document ? window.parent.document : document;
  var slack = {HOME_CHROME_HEIGHT_SLACK_PX};

  function measureChromeHeight(inner) {{
    var hero = inner.querySelector(".hero--command");
    if (!hero) return 0;
    var docTop = inner.documentElement.getBoundingClientRect().top;
    return Math.ceil(hero.getBoundingClientRect().bottom - docTop + slack);
  }}

  function applyChromeHeight(frame, h) {{
    if (!frame || h <= 80) return;
    frame.style.height = h + "px";
    frame.style.minHeight = "0";
    frame.style.maxHeight = h + "px";
    frame.style.marginBottom = "0";
    frame.style.paddingBottom = "0";
    frame.setAttribute("height", String(h));
  }}

  function syncHeights() {{
    doc.querySelectorAll("iframe").forEach(function (frame) {{
      try {{
        var inner = frame.contentDocument;
        if (!inner || !inner.body) return;
        if (inner.querySelector(".home-main-split")) return;
        var isMarkets = inner.querySelector(".home-markets-stack");
        var isChrome = inner.querySelector(".hero--command");
        if (!isMarkets && !isChrome) return;
        if (isChrome) {{
          applyChromeHeight(frame, measureChromeHeight(inner));
          return;
        }}
        var h = Math.max(
          inner.body.scrollHeight,
          inner.documentElement.scrollHeight,
          inner.body.offsetHeight
        ) + 32;
        if (h > 80) {{
          frame.style.height = h + "px";
        }}
      }} catch (e) {{}}
    }});
  }}

  window.addEventListener("message", function (ev) {{
    if (!ev.data || ev.data.type !== "jpm-chrome-height") return;
    var h = Number(ev.data.height);
    if (!isFinite(h) || h <= 80) return;
    doc.querySelectorAll("iframe").forEach(function (frame) {{
      try {{
        var inner = frame.contentDocument;
        if (inner && inner.querySelector(".hero--command") && !inner.querySelector(".home-main-split")) {{
          applyChromeHeight(frame, h);
        }}
      }} catch (e) {{}}
    }});
  }});

  syncHeights();
  window.addEventListener("load", syncHeights);
  [100, 400, 1000, 2500, 5000].forEach(function (ms) {{
    setTimeout(syncHeights, ms);
  }});
  setInterval(syncHeights, 1200);
}})();
</script>
"""

HOME_BODY_IFRAME_SIZE_JS = """
<script>
(function () {
  var win = window.parent;
  var doc = win.document;

  function findBodyFrame() {
    var match = null;
    doc.querySelectorAll("iframe").forEach(function (frame) {
      try {
        var inner = frame.contentDocument;
        if (inner && inner.querySelector(".home-main-split")) match = frame;
      } catch (e) {}
    });
    return match;
  }

  function measureBodyFrameHeight(inner) {
    if (!inner) return 0;
    if (typeof inner.syncHomeSplitHeights === "function") {
      inner.syncHomeSplitHeights();
    }
    var shell = inner.querySelector(".page-shell");
    var rail = inner.querySelector(".home-news-rail");
    if (!shell || !rail || rail.offsetHeight < 200) return 0;
    var shellTop = shell.getBoundingClientRect().top;
    var railRect = rail.getBoundingClientRect();
    var st = inner.defaultView.getComputedStyle(shell);
    var pb = parseFloat(st.paddingBottom) || 0;
    return Math.ceil(railRect.bottom - shellTop + pb + 2);
  }

  function applyBodyFrameHeight(bodyFrame, h) {
    if (!bodyFrame || h <= 80) return;
    bodyFrame.style.height = h + "px";
    bodyFrame.style.minHeight = "0";
  }

  function sizeBodyFrame() {
    var bodyFrame = findBodyFrame();
    if (!bodyFrame) return;
    try {
      var inner = bodyFrame.contentDocument;
      if (!inner) return;
      applyBodyFrameHeight(bodyFrame, measureBodyFrameHeight(inner));
    } catch (e) {}
  }

  win.addEventListener("message", function (ev) {
    if (!ev.data || ev.data.type !== "jpm-home-body-height") return;
    var h = Number(ev.data.height);
    if (!isFinite(h) || h <= 80) return;
    applyBodyFrameHeight(findBodyFrame(), h);
  });

  sizeBodyFrame();
  win.addEventListener("resize", sizeBodyFrame);
  win.addEventListener("load", sizeBodyFrame);
  [150, 500, 1200, 2500, 4000, 6000].forEach(function (ms) { setTimeout(sizeBodyFrame, ms); });
  setInterval(sizeBodyFrame, 2000);
})();
</script>
"""

HOME_NEWS_STICKY_JS = """
<script>
/* Deprecated: news rail sticky is handled inside the combined home-body iframe. */
</script>
"""


def _embedded_home_styles_html() -> str:
    """Return static CSS for injection via ``st.html`` (style-only → event container)."""
    return f"<style>{_cached_static_stylesheet()}</style>"


def inject_subpage_styles(*, kind: str = "article") -> None:
    """GitHub Pages base + inner-page CSS for Streamlit subpages."""
    inject_site_styles(include_static=True)
    inner_css = _cached_subpage_stylesheet(kind)
    st.markdown(
        f"<style>{inner_css}\n{SUBPAGE_STREAMLIT_CSS}</style>",
        unsafe_allow_html=True,
    )


def inject_streamlit_nav_router() -> None:
    """Host-side router for iframe ``jpm-navigate`` messages (sandbox blocks target=_top)."""
    components.html(STREAMLIT_SITE_NAV_ROUTER_JS, height=0, width=0)


def configure_subpage(*, page_title: str, active: str, style_kind: str = "article") -> None:
    """Shared subpage setup: collapsed sidebar, nav, and static/inner CSS."""
    st.set_page_config(
        page_title=page_title,
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_subpage_styles(kind=style_kind)
    inject_streamlit_nav_router()
    render_site_nav(active=active, is_landing=False)


def render_subpage_back_link(*, href: str, label: str) -> None:
    st.markdown(
        f'<div class="page-back-below-header"><p class="back-link back-link--below-header">'
        f'<a href="{escape(href)}">{escape(label)}</a></p></div>',
        unsafe_allow_html=True,
    )


def open_subpage_layout(*, style_kind: str, shell_class: str = "") -> None:
    root_class = SUBPAGE_ROOT_CLASS.get(style_kind, SUBPAGE_ROOT_CLASS["article"])
    shell_cls = f"page-shell {shell_class}".strip()
    st.markdown(
        f'<div class="streamlit-subpage-root site-experience {root_class}">'
        f'<main class="{shell_cls}">',
        unsafe_allow_html=True,
    )


def close_subpage_layout(*, back_href: str = "", back_label: str = "") -> None:
    back = ""
    if back_href and back_label:
        back = (
            f'<p class="back-link"><a href="{escape(back_href)}">{escape(back_label)}</a></p>'
        )
    st.markdown(f"{back}</main></div>", unsafe_allow_html=True)


def inner_page_zone_open(
    *,
    section_id: str,
    badge: str,
    title: str,
    subtitle: str = "",
    subtitle_html: str = "",
    zone_classes: str = "",
    related_chips: str = "",
    body_class: str = "inner-rich-zone__body",
) -> None:
    dek = subtitle_html if subtitle_html else escape(subtitle)
    zone_extra = f" {zone_classes}" if zone_classes else ""
    chips = related_chips or ""
    st.markdown(
        f"""
<article class="hub-section hub-section--panel inner-rich-zone home-reveal is-visible{zone_extra}"
         id="{escape(section_id)}">
  <div class="home-zone__stripe" aria-hidden="true"></div>
  <header class="home-zone__head">
    <span class="home-zone__badge" aria-hidden="true">{escape(badge)}</span>
    <div class="home-zone__titles">
      <h1 class="page-intro__title" id="{escape(section_id)}-heading">{escape(title)}</h1>
      <p class="page-intro__dek">{dek}</p>
    </div>
  </header>
  <div class="home-zone__body {body_class}">
    {chips}
""",
        unsafe_allow_html=True,
    )


def inner_page_zone_close() -> None:
    st.markdown("  </div></article>", unsafe_allow_html=True)


def render_subpage_footer(*, label: str) -> None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    month = now.strftime("%b %Y")
    iso = now.strftime("%Y-%m")
    st.markdown(
        f'<footer class="site-footer site-experience">Digital Assets Dashboard · {escape(label)} · '
        f'<time datetime="{escape(iso)}">{escape(month)}</time></footer>',
        unsafe_allow_html=True,
    )


def inject_site_styles(*, include_static: bool = True) -> None:
    """Inject GitHub Pages CSS + Streamlit chrome overrides."""
    gap_css = HOME_HERO_TO_CONTENT_GAP.replace("'", "\\'")
    chrome_css = STREAMLIT_CHROME_CSS.replace(
        "HOME_HERO_TO_CONTENT_GAP_PLACEHOLDER", gap_css
    )
    st.markdown(chrome_css, unsafe_allow_html=True)
    if include_static:
        css = _cached_static_stylesheet()
        # Main document: markdown style block for news/footer chrome.
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        # Event container: backup injection for Cloud when markdown style blocks are dropped.
        st.html(f"<style>{css}</style>")


def render_home_markdown(html: str, *, target: Any = None) -> None:
    """Render a compact HTML fragment; must not include ``<style>`` tags."""
    (target or st).markdown(html.strip(), unsafe_allow_html=True)


def build_home_chrome_html(*, include_refresh: bool = True) -> str:
    """Nav + hero (self-contained HTML fragment). Prefer ``render_home_chrome`` on Streamlit."""
    refresh = (
        '<div class="home-refresh-row"><a class="home-refresh-btn" href="?home_refresh=1">Refresh data</a></div>'
        if include_refresh
        else ""
    )
    return "".join(
        [
            '<div class="site-experience page-home st-streamlit-home-root">',
            render_site_nav_html(active="home", is_landing=True, for_streamlit=True).strip(),
            render_home_hero_html(for_streamlit=True).strip(),
            refresh,
            "</div>",
        ]
    )


def build_home_chrome_iframe_html(*, include_refresh: bool = False) -> str:
    """Self-contained nav + hero for ``components.html`` (matches GitHub Pages styling on Cloud)."""
    refresh = (
        '<div class="home-refresh-row"><a class="home-refresh-btn" href="?home_refresh=1" target="_top">Refresh data</a></div>'
        if include_refresh
        else ""
    )
    css = _cached_iframe_home_stylesheet()
    body = "".join(
        [
            render_site_nav_html(active="home", is_landing=True, for_streamlit=True).strip(),
            render_home_hero_html(for_streamlit=True).strip(),
            refresh,
        ]
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
</head>
<body class="page-home site-experience">
{body}
{iframe_chrome_height_script()}
{iframe_jump_nav_script()}
{iframe_internal_link_script()}
</body>
</html>"""


def render_home_chrome(*, include_refresh: bool = False) -> None:
    """Render nav + hero as an auto-height iframe with embedded static CSS."""
    st.markdown(
        '<span class="home-chrome-iframe-marker" hidden aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    components.html(
        build_home_chrome_iframe_html(include_refresh=include_refresh),
        height=HOME_CHROME_IFRAME_INITIAL_HEIGHT,
        scrolling=False,
    )


def render_home_hero_content_gap() -> None:
    """Visible wash band between hero iframe and body iframe (Streamlit-only seam)."""
    st.html('<div class="home-hero-content-gap" aria-hidden="true"></div>')


def build_home_footer_html(*, footer_month: str, footer_iso: str) -> str:
    return (
        f'<footer class="site-footer site-experience">Digital Assets Dashboard · Home · '
        f'<time datetime="{escape(footer_iso)}">{escape(footer_month)}</time>'
        f"</footer>"
    )


def _nav_link(href: str, label: str, *, active: bool = False, target: str = "") -> str:
    cls = ' class="is-active"' if active else ""
    tgt = f' target="{escape(target)}"' if target else ""
    return f'<a href="{escape(href)}"{cls}{tgt}>{escape(label)}</a>'


def _page_href(key: str) -> str:
    if key == "home":
        return "/?jd_scroll=top"
    script_path = Path(PAGES[key])
    if not script_path.is_absolute():
        script_path = (_REPO / script_path).resolve()
    try:
        from streamlit.source_util import page_icon_and_name

        _, url_path = page_icon_and_name(script_path)
        if url_path:
            return f"/{url_path}"
    except Exception:
        pass
    return f"/{script_path.stem}"


def render_site_nav_html(*, active: str = "home", is_landing: bool = False, for_streamlit: bool = False) -> str:
    top = "_top" if for_streamlit else ""
    news_href = (
        "/?jd_scroll=news"
        if for_streamlit or not is_landing
        else "#section-news"
    )
    t = f' target="{top}"' if top else ""

    def a(href: str, label: str, *, active_link: bool = False, extra_cls: str = "") -> str:
        cls = "is-active" if active_link else ""
        if extra_cls:
            cls = f"{extra_cls} {cls}".strip()
        class_attr = f' class="{cls}"' if cls else ""
        return f'<a href="{escape(href)}"{class_attr}{t}>{escape(label)}</a>'

    return f"""
<header class="site-header site-experience" role="banner">
  <div class="site-header__inner">
    {a("/?jd_scroll=top", "Digital Assets Dashboard", extra_cls="site-brand")}
    <nav class="site-nav" aria-label="Primary">
      {_nav_link("/?jd_scroll=top", "Home", active=active == "home", target=top)}
      {_nav_link(news_href, "News Hub", active=active == "news", target=top)}
      {_nav_link(_page_href("tmmf"), "TMMFs", active=active == "tmmf", target=top)}
      {_nav_link(_page_href("stablecoins"), "Stablecoins", active=active == "stablecoins", target=top)}
      <div class="site-nav__dropdown">
        {a(_page_href("rwa_global"), "RWA Market", extra_cls="site-nav__trigger")}
        <ul class="site-nav__sub">
          <li>{a(_page_href("rwa_global"), "Market Overview")}</li>
          <li class="site-nav__item site-nav__item--flyout">
            {a(_page_href("explore_asset"), "RWA · Assets", extra_cls="site-nav__parent-link")}
            <ul class="site-nav__sub site-nav__sub--nested">
              <li>{a(_page_href("treasuries"), "U.S. Treasuries")}</li>
              <li>{a(_page_href("stocks"), "Tokenized Stocks")}</li>
            </ul>
          </li>
          <li class="site-nav__item site-nav__item--flyout">
            {a(_page_href("explore_participant"), "RWA · Participants", extra_cls="site-nav__parent-link")}
            <ul class="site-nav__sub site-nav__sub--nested">
              <li>{a(_page_href("networks"), "Networks")}</li>
              <li>{a(_page_href("platforms"), "Platforms")}</li>
              <li>{a(_page_href("asset_managers"), "Asset Managers")}</li>
            </ul>
          </li>
        </ul>
      </div>
      <div class="site-nav__dropdown">
        <span class="site-nav__trigger">U.S. ETPs</span>
        <ul class="site-nav__sub">
          <li>{a(_page_href("etps"), "U.S. ETP Overview")}</li>
          <li>{a(_page_href("etf_news"), "ETF/ETP News")}</li>
        </ul>
      </div>
      {_nav_link(_page_href("crypto"), "Crypto Prices", active=active == "crypto", target=top)}
    </nav>
  </div>
</header>
"""


def render_site_nav(*, active: str = "home", is_landing: bool = False) -> None:
    st.markdown(render_site_nav_html(active=active, is_landing=is_landing), unsafe_allow_html=True)


def _home_jump_nav_html(*, for_streamlit: bool = False) -> str:
    links = (
        ("tmmf", "section-tmmf", "home-jump-nav__link--tmmf", "TMMFs"),
        ("stablecoins", "section-stablecoins", "home-jump-nav__link--stable", "Stablecoins"),
        ("onchain", "section-onchain", "home-jump-nav__link--rwa", "RWA"),
        ("markets", "section-markets", "home-jump-nav__link--etp", "ETPs"),
        ("crypto", "section-crypto", "home-jump-nav__link--crypto", "Crypto"),
    )

    def href(_key: str, anchor: str) -> str:
        return f"#{anchor}"

    onchain = "".join(
        f'<a href="{href(key, anchor)}" class="home-jump-nav__link {cls}">'
        f'<span class="home-jump-nav__dot" aria-hidden="true"></span>{label}</a>'
        for key, anchor, cls, label in links[:3]
    )
    markets = "".join(
        f'<a href="{href(key, anchor)}" class="home-jump-nav__link {cls}">'
        f'<span class="home-jump-nav__dot" aria-hidden="true"></span>{label}</a>'
        for key, anchor, cls, label in links[3:]
    )
    return f"""
<nav class="home-jump-nav home-jump-nav--grouped" aria-label="Jump to data sections">
  <div class="home-jump-nav__group">
    <span class="home-jump-nav__group-label">On-chain</span>
    {onchain}
  </div>
  <div class="home-jump-nav__group">
    <span class="home-jump-nav__group-label">Markets</span>
    {markets}
  </div>
</nav>
"""

HOME_CONFLUENCE_TEAM_URL = (
    "https://confluence.prod.aws.jpmchase.net/confluence/spaces/viewspace.action?key=DIGITALPRODUCTTEAM"
)


def home_internal_note_html() -> str:
    """Slim internal note at the top of the white content band (not in the hero)."""
    url = escape(HOME_CONFLUENCE_TEAM_URL)
    return f"""
<p class="home-internal-note" role="note">
  <span class="home-internal-note__badge" aria-hidden="true">Internal</span>
  <span class="home-internal-note__text">
    For <strong>internal digital asset</strong> materials (documentation, product context, and key contacts),
    see the
    <a href="{url}" target="_blank" rel="noopener noreferrer">Digital Custody Product Team</a>
    space on Confluence.
  </span>
</p>"""


def render_home_hero_html(*, for_streamlit: bool = False) -> str:
    return f"""
<div class="hero hero--command site-experience page-home" role="region" aria-labelledby="page-title">
  <div class="hero-inner hero-inner--single hero-inner--experience">
    <div class="hero-copy hero-copy--lead">
      <p class="home-hero-eyebrow">Market dashboard</p>
      <h1 id="page-title">Digital Assets Dashboard</h1>
      <p class="hero-lead hero-lead--compact">
        <strong>On-chain RWA</strong> from <strong>RWA.xyz</strong>, curated <strong>news</strong>, U.S.-listed
        <strong>crypto ETPs</strong>, and top-line <strong>crypto prices</strong>—one workspace for market direction,
        policy signals, and where tokenization activity is building.
      </p>
      {_home_jump_nav_html(for_streamlit=for_streamlit)}
    </div>
  </div>
</div>
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
            '<div class="page-shell">',
            home_internal_note_html().strip(),
            '<div class="home-main-split"><div class="home-markets-stack">',
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


def _fmt_article_relative_time(published: Any) -> str:
    from datetime import datetime

    if isinstance(published, datetime):
        return format_relative_time(published)
    return str(published) if published else ""


def build_static_news_rail_html(articles: list[dict[str, Any]]) -> str:
    """News Hub rail matching static_home/index.html."""
    items_html: list[str] = []
    for item in articles[:HOME_NEWS_LIMIT]:
        title = escape(str(item.get("title") or "Untitled"))
        link = str(item.get("link") or "").strip()
        source = escape(str(item.get("source") or ""))
        when = escape(_fmt_article_relative_time(item.get("published")))
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
