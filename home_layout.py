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

# Glide Data Grid (st.dataframe) reads --gdg-* variables; headers are canvas-drawn (DOM CSS alone is not enough).
# Pair with ``inject_dataframe_teal_header_fix()`` after each styled dataframe mounts.
STREAMLIT_DATAFRAME_TEAL_HEADER_CSS = """
<style>
div[data-testid="stDataFrame"],
div[data-testid="stDataFrame"] .gdg-wmyidgi {
  --gdg-bg-header: #1E7C99;
  --gdg-bg-header-has-focus: #196f87;
  --gdg-text-group-header: #ffffff;
  --gdg-border-color: rgba(255, 255, 255, 0.22);
}
</style>
"""

_DATAFRAME_TEAL_HEADER_FIX_HTML = """
<script>
(function () {
  var doc = window.parent.document;
  var TEAL = "#1E7C99";
  var TEAL_FOCUS = "#196f87";
  var FG = "#ffffff";
  var BORDER = "rgba(255, 255, 255, 0.22)";
  function paint() {
    doc.querySelectorAll('div[data-testid="stDataFrame"] .gdg-wmyidgi').forEach(function (el) {
      el.style.setProperty("--gdg-bg-header", TEAL, "important");
      el.style.setProperty("--gdg-bg-header-has-focus", TEAL_FOCUS, "important");
      el.style.setProperty("--gdg-text-group-header", FG, "important");
      el.style.setProperty("--gdg-border-color", BORDER, "important");
    });
    try {
      window.parent.dispatchEvent(new Event("resize"));
    } catch (e) {}
  }
  paint();
  var n = 0;
  var t = window.parent.setInterval(function () {
    paint();
    if (++n > 25) window.parent.clearInterval(t);
  }, 120);
})();
</script>
"""


def inject_dataframe_teal_header_fix() -> None:
    """Apply teal header colors to Glide-based ``st.dataframe`` (run once after the table is rendered)."""
    import streamlit.components.v1 as components

    components.html(_DATAFRAME_TEAL_HEADER_FIX_HTML, height=0, width=0)

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
