"""RWA.xyz Global Market Overview: homepage KPI + Networks table (homepage embed)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from datetime import datetime, timezone

import streamlit as st

from home_layout import ETP_FULLPAGE_AUM_LINE_CSS, STREAMLIT_TABLE_UNIFY_CSS, section_label_teal
from news_feeds import (
    app_shared_layout_css,
    article_styles_markdown,
    render_subpage_sidebar,
    render_subpage_top_bar,
)
from price_ticker import show_price_ticker
from rwa_league.widgets import show_rwa_participants_networks_widget

# Macro context for readers (third-party research; not investment advice). Single perimeter for sizing: McKinsey tokenized financial assets.
_MCKINSEY_TOKENIZATION_URL = (
    "https://www.mckinsey.com/industries/financial-services/our-insights/"
    "from-ripples-to-waves-the-transformational-power-of-tokenizing-assets"
)

RWA_GLOBAL_MARKET_MACRO_CONTEXT_HTML = f"""
<style>
.rwa-gmo-takeaways {{
  border: 1px solid #C7D8E8;
  border-radius: 10px;
  padding: 0.9rem 1.05rem 1rem;
  margin: 0.15rem 0 0.5rem;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(15,23,42,0.06);
}}
.rwa-gmo-takeaways h3 {{
  margin: 0 0 0.55rem 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #021D41;
  letter-spacing: 0.01em;
}}
.rwa-gmo-takeaways ul {{
  margin: 0.35rem 0 0.25rem 1.1rem;
  padding: 0;
  color: #1F4C67;
  font-size: 0.92rem;
  line-height: 1.45;
}}
.rwa-gmo-takeaways li {{
  margin-bottom: 0.45rem;
}}
.rwa-gmo-takeaways ul ul {{
  margin: 0.2rem 0 0.1rem 0.85rem;
  padding: 0;
  list-style-type: disc;
}}
.rwa-gmo-takeaways ul ul li {{
  margin-bottom: 0.3rem;
}}
.rwa-gmo-takeaways .rwa-gmo-takeaway-note {{
  margin: 0.55rem 0 0 0;
  font-size: 0.78rem;
  color: #3E6A7A;
  line-height: 1.4;
}}
</style>
<div class="rwa-gmo-takeaways">
  <h3>RWA Market - Key Observations</h3>
  <ul>
    <li><strong>Institutional momentum.</strong> Large asset managers, banks, and market utilities are scaling tokenized
    cash funds, bonds, and repo-style workflows—often on permissioned networks first—while public-ledger RWA issuance
    keeps expanding in parallel.</li>
    <li><strong>2030 tokenized financial assets (single perimeter).</strong> The bullets below use <strong>one</strong>
    definitional scope—<strong>tokenized financial assets</strong> (conventional instruments on digital rails)—from the same
    <a href="{_MCKINSEY_TOKENIZATION_URL}">McKinsey &amp; Company</a> <strong>June&nbsp;2024</strong> paper. That study
    <strong>excludes</strong> major crypto and stablecoins to limit double counting. Other well-known forecasts (e.g.
    illiquid-asset tokenization, stablecoin TAMs, single asset-class slices) sit on <strong>different perimeters</strong> and are
    omitted here so the numbers stay comparable.
      <ul>
        <li><strong>Scenario band.</strong> Central case <strong>~$2&nbsp;trillion</strong> global market cap of tokenized
        financial assets by <strong>2030</strong>; the same publication’s scenarios span about <strong>$1–4&nbsp;trillion</strong>.</li>
        <li><strong>Composition (“waves”).</strong> In that analysis, adoption is ordered across instrument types (including
        cash-like balances, funds, and fixed income); the report’s exhibits break down how those pieces contribute to the
        totals above.</li>
      </ul>
      <p class="rwa-gmo-takeaway-note" style="margin-top:0.35rem;margin-bottom:0;">Directional scenarios only—not investment
      advice. Do not sum line items from the exhibits as if they were independent “extra” markets outside the study’s model.</p>
    </li>
  </ul>
  <p class="rwa-gmo-takeaway-note">Snapshot for context only (not investment advice). The chart and table below reflect
  RWA.xyz embedded homepage data, not the McKinsey scenarios above.</p>
</div>
"""


def main() -> None:
    st.set_page_config(
        page_title="RWA Global Market Overview — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Home", key="top_home_rwa_global_market_overview"):
        st.switch_page("streamlit_app.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_global_market_overview", current="rwa_participants_networks")

    st.markdown(section_label_teal("RWA Global Market Overview", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">RWA <strong>Global Market Overview</strong>: the same '
        "<strong>headline metrics</strong> and <strong>Networks</strong> table as the "
        '<a href="https://app.rwa.xyz/">RWA.xyz</a> Market Overview tab (embedded in <code>__NEXT_DATA__</code>). '
        "Top-line <strong>30D</strong> % changes and table values are pulled from that homepage dataset.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    show_rwa_participants_networks_widget(
        home_preview=False,
        full_page_header=True,
        global_market_observations_html=RWA_GLOBAL_MARKET_MACRO_CONTEXT_HTML,
    )

    st.caption(
        f"As of {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC. "
        "RWA.xyz data in the section above is cached up to one hour; use **Refresh all data** on the home page to reload."
    )


main()
