"""Layout helpers and shared CSS for the Streamlit home page."""

from __future__ import annotations

from html import escape
from typing import Optional

# Section rhythm: soft labels, ticker spacing, teal accent aligned with primaryColor.
# Streamlit st.dataframe: unify header/body font + color (sortable tables on home).
# KPI tile legends (RWA + ETP): one size/color everywhere.
KPI_WINDOW_NOTE_CSS = """
<style>
.jd-kpi-window-note {
    font-size: 0.64rem;
    font-weight: 400;
    color: #3E6A7A;
    margin: 0 0 0.5rem 0;
    line-height: 1.32;
}
</style>
"""

STREAMLIT_TABLE_UNIFY_CSS = """
<style>
div[data-testid="stDataFrame"] {
  font-size: 0.875rem;
  color: #021D41;
}
div[data-testid="stDataFrame"] [data-testid="stHeaderCell"],
div[data-testid="stDataFrame"] [role="columnheader"] {
  color: #021D41 !important;
  font-weight: 600;
  font-size: 0.875rem;
}
div[data-testid="stDataFrame"] [role="gridcell"] {
  color: #021D41;
  font-size: 0.875rem;
}
</style>
"""

ETP_FULLPAGE_AUM_LINE_CSS = """
<style>
.etp-fullpage-aum-line {
  font-size: 0.95rem;
  font-weight: 700;
  color: #021D41;
  margin: 0.35rem 0 0.85rem 0;
}
</style>
"""

HOME_PAGE_LAYOUT_CSS = """
<style>
/* Hub hierarchy: h1 → major section band (largest body heading) → lane/widget (smaller) → dek (smallest) */
h1.home-main-heading {
    font-size: clamp(1.45rem, 2.8vw, 1.85rem);
    font-weight: 750;
    letter-spacing: -0.03em;
    line-height: 1.2;
    color: #021D41;
    margin: 0.15rem 0 0.65rem 0;
}
h1.home-main-heading#jd-page-top {
    scroll-margin-top: 5.5rem;
}
/* In-page jump targets (nav); zero layout height */
.jd-hub-section-anchor {
    scroll-margin-top: 5.5rem;
    height: 0;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden;
    width: 100%;
    border: none;
}
/* Inside News columns + Markets teasers — always smaller than .home-band-label */
h2.home-lane-heading {
    font-size: 0.97rem;
    font-weight: 600;
    color: #021D41;
    margin: 0 0 0.5rem 0;
    letter-spacing: -0.015em;
    line-height: 1.35;
}
h2.home-widget-heading {
    font-size: 1.02rem;
    font-weight: 650;
    color: #021D41;
    margin: 0 0 0.4rem 0;
    letter-spacing: -0.018em;
    line-height: 1.3;
}
/* CoinDesk-style hub: section band + short dek + teaser content */
.jd-hub-band {
    margin-top: 0.25rem;
    margin-bottom: 0.35rem;
}
.jd-hub-dek {
    font-size: 0.76rem;
    font-weight: 400;
    color: #3E6A7A;
    line-height: 1.5;
    margin: 0 0 1rem 0;
    max-width: min(44rem, 100%);
}
[data-testid="stMarkdownContainer"] p.jd-hub-dek {
    font-size: 0.76rem !important;
}
.jd-hub-cta-note {
    font-size: 0.68rem;
    font-weight: 400;
    color: #3E6A7A;
    margin: 0.4rem 0 0.15rem 0;
    line-height: 1.38;
}
[data-testid="stMarkdownContainer"] p.jd-hub-cta-note {
    font-size: 0.68rem !important;
    line-height: 1.38 !important;
}
/* Multipage: result counts / filters under search (matches hub note color, clearer than raw caption) */
p.jd-subpage-toolbar-note {
    font-size: 0.78rem;
    color: #3E6A7A;
    margin: 0.35rem 0 0.85rem 0;
    line-height: 1.45;
    max-width: min(44rem, 100%);
}
p.jd-subpage-footer-heading {
    font-size: 0.82rem;
    font-weight: 650;
    color: #1F4C67;
    margin: 0.25rem 0 0.45rem 0;
    letter-spacing: -0.01em;
}
.cd-ticker-shell {
    margin-bottom: 1.25rem !important;
}
.home-band-label {
    font-size: 1.28rem;
    font-weight: 800;
    letter-spacing: -0.024em;
    line-height: 1.22;
    text-transform: none;
    color: #021D41;
    margin: 0 0 0.2rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #C7D8E8;
}
.home-band-label.teal {
    color: #25809C;
    border-bottom-color: #8CB9C9;
    /* Slightly larger optical size so teal reads at parity with navy headings */
    font-size: 1.3rem;
}
p.home-band-label.teal.jd-home-band-first {
    margin-top: 0.2rem;
}
p.home-band-label.teal.jd-home-band-after-rule {
    margin-top: 0.3rem;
}
/* Full-bleed dividers between major hub blocks */
[data-testid="stAppViewContainer"] hr {
    margin: 1.25rem 0 !important;
    border: none;
    border-top: 1px solid #dce7f0;
}
/* Smaller default Streamlit captions in main: data-source / legend text (not the sidebar) */
section[data-testid="stMain"] [data-testid="stCaptionContainer"] {
    font-size: 0.75rem;
    line-height: 1.4;
    color: #5f6b7a;
}
section[data-testid="stMain"] [data-testid="stCaptionContainer"] p {
    font-size: inherit !important;
    line-height: inherit;
}
</style>
"""


def section_label_teal(text: str, *, placement: str = "default") -> str:
    """
    HTML for a major hub section title (teal accent, bottom rule).

    ``placement``: ``\"first\"`` — first band below the hero/ticker; ``\"after_divider\"`` —
    band following a full-width ``st.divider()`` (tighter top margin).
    """
    extra = ""
    if placement == "first":
        extra = " jd-home-band-first"
    elif placement == "after_divider":
        extra = " jd-home-band-after-rule"
    return f'<p class="home-band-label teal{extra}">{text}</p>'


def section_label_neutral(text: str) -> str:
    return f'<p class="home-band-label">{text}</p>'


def subpage_toolbar_note_html(text: str) -> str:
    """Muted line for filter/result counts on multipage feeds (pairs with ``.jd-hub-dek`` rhythm)."""
    return f'<p class="jd-subpage-toolbar-note">{escape(text)}</p>'


def subpage_footer_heading_html(text: str) -> str:
    """Small label above pagination controls (aligned with hub subsection color hierarchy)."""
    return f'<p class="jd-subpage-footer-heading">{escape(text)}</p>'


def hub_subsection_heading_html(text: str, *, element_id: Optional[str] = None) -> str:
    """
    HTML for an in-section title matching **RWA Global Market Overview** / **U.S. Digital Asset ETPs** on the hub:
    ``jd-hub-subsection-head`` + ``h2.home-main-heading`` (slim rule, navy text — not the teal major band).
    """
    id_attr = f' id="{escape(element_id, quote=True)}"' if element_id else ""
    return (
        f'<div class="jd-hub-subsection-head"{id_attr}>'
        f'<h2 class="home-main-heading">{escape(text)}</h2></div>'
    )


def hub_section_anchor(element_id: str) -> str:
    """Zero-height scroll target for hub nav / fragment links (IDs must be URL-safe)."""
    safe = "".join(c for c in element_id if c.isalnum() or c in "-_")
    if not safe or safe != element_id.strip():
        raise ValueError("hub_section_anchor: invalid element_id")
    return f'<div id="{safe}" class="jd-hub-section-anchor" aria-hidden="true"></div>'
