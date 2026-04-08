"""Layout helpers and shared CSS for the Streamlit home page."""

from __future__ import annotations

# Section rhythm: soft labels, ticker spacing, teal accent aligned with primaryColor.
# Streamlit st.dataframe: unify header/body font + color (sortable tables on home).
STREAMLIT_TABLE_UNIFY_CSS = """
<style>
div[data-testid="stDataFrame"] {
  font-size: 0.875rem;
  color: #0f172a;
}
div[data-testid="stDataFrame"] [data-testid="stHeaderCell"],
div[data-testid="stDataFrame"] [role="columnheader"] {
  color: #0f172a !important;
  font-weight: 600;
  font-size: 0.875rem;
}
div[data-testid="stDataFrame"] [role="gridcell"] {
  color: #0f172a;
  font-size: 0.875rem;
}
</style>
"""

ETP_FULLPAGE_AUM_LINE_CSS = """
<style>
.etp-fullpage-aum-line {
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0.35rem 0 0.85rem 0;
}
</style>
"""

HOME_PAGE_LAYOUT_CSS = """
<style>
.cd-ticker-shell {
    margin-bottom: 1.35rem !important;
}
.home-band-label {
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    line-height: 1.3;
    text-transform: none;
    color: #64748b;
    margin: 0 0 0.85rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #e2e8f0;
}
.home-band-label.teal {
    color: #1E7C99;
    border-bottom-color: #cbd5e1;
}
</style>
"""


def section_label_teal(text: str) -> str:
    """HTML for a section band title (title case, same scale as ``h2.home-main-heading``)."""
    return f'<p class="home-band-label teal">{text}</p>'


def section_label_neutral(text: str) -> str:
    return f'<p class="home-band-label">{text}</p>'
