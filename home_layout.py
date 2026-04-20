"""Layout helpers and shared CSS for the Streamlit home page."""

from __future__ import annotations

# Section rhythm: soft labels, ticker spacing, teal accent aligned with primaryColor.
# Streamlit st.dataframe: unify header/body font + color (sortable tables on home).
# KPI tile legends (RWA + ETP): one size/color everywhere.
KPI_WINDOW_NOTE_CSS = """
<style>
.jd-kpi-window-note {
    font-size: 0.72rem;
    font-weight: 400;
    color: #3E6A7A;
    margin: 0 0 0.5rem 0;
    line-height: 1.35;
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
/* Hub hierarchy: hero (h1) → section band (teal) → dek → lane / widget titles */
h1.home-main-heading {
    font-size: clamp(1.45rem, 2.8vw, 1.85rem);
    font-weight: 750;
    letter-spacing: -0.03em;
    line-height: 1.2;
    color: #021D41;
    margin: 0.15rem 0 0.65rem 0;
}
/* Column titles in the News & Regulatory row */
h2.home-lane-heading {
    font-size: 1.02rem;
    font-weight: 650;
    color: #021D41;
    margin: 0 0 0.55rem 0;
    letter-spacing: -0.018em;
    line-height: 1.35;
}
/* Teaser card titles under “Markets & On-chain” (ETP + RWA shells) */
h2.home-widget-heading {
    font-size: 1.1rem;
    font-weight: 700;
    color: #021D41;
    margin: 0 0 0.35rem 0;
    letter-spacing: -0.02em;
    line-height: 1.3;
}
/* CoinDesk-style hub: section band + short dek + teaser content */
.jd-hub-band {
    margin-top: 0.25rem;
    margin-bottom: 0.35rem;
}
.jd-hub-dek {
    font-size: 0.9rem;
    font-weight: 400;
    color: #3E6A7A;
    line-height: 1.5;
    margin: 0.2rem 0 1rem 0;
    max-width: 44rem;
}
.jd-hub-cta-note {
    font-size: 0.78rem;
    color: #3E6A7A;
    margin: 0.45rem 0 0.1rem 0;
    line-height: 1.4;
}
.cd-ticker-shell {
    margin-bottom: 1.1rem !important;
}
.home-band-label {
    font-size: 1.22rem;
    font-weight: 750;
    letter-spacing: -0.022em;
    line-height: 1.25;
    text-transform: none;
    color: #021D41;
    margin: 0.35rem 0 0.35rem 0;
    padding-bottom: 0.45rem;
    border-bottom: 2px solid #C7D8E8;
}
.home-band-label.teal {
    color: #25809C;
    border-bottom-color: #8CB9C9;
}
p.home-band-label.teal.jd-home-band-first {
    margin-top: 0.25rem;
}
p.home-band-label.teal.jd-home-band-after-rule {
    margin-top: 0.35rem;
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
