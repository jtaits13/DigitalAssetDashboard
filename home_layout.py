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
/* CoinDesk-style hub: section band + short dek + teaser content */
.jd-hub-band {
    margin-top: 0.25rem;
    margin-bottom: 0.35rem;
}
.jd-hub-dek {
    font-size: 0.88rem;
    color: #3E6A7A;
    line-height: 1.45;
    margin: 0.15rem 0 0.85rem 0;
    max-width: 48rem;
}
.jd-hub-cta-note {
    font-size: 0.8rem;
    color: #3E6A7A;
    margin: 0.5rem 0 0.15rem 0;
}
.cd-ticker-shell {
    margin-bottom: 1.35rem !important;
}
.home-band-label {
    font-size: 1.16rem;
    font-weight: 760;
    letter-spacing: -0.015em;
    line-height: 1.3;
    text-transform: none;
    color: #021D41;
    margin: 0.15rem 0 0.75rem 0;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid #C7D8E8;
}
.home-band-label.teal {
    color: #25809C;
    border-bottom-color: #8CB9C9;
}
</style>
"""


def section_label_teal(text: str) -> str:
    """HTML for a section band title (title case, same scale as ``h2.home-main-heading``)."""
    return f'<p class="home-band-label teal">{text}</p>'


def section_label_neutral(text: str) -> str:
    return f'<p class="home-band-label">{text}</p>'
