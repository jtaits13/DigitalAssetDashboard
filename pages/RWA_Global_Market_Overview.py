"""RWA.xyz Global Market Overview: homepage KPIs and Networks table aligned with the live site."""

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

# Macro context for readers (third-party research; not investment advice). Links verified via public pages.
_MCKINSEY_TOKENIZATION_URL = (
    "https://www.mckinsey.com/industries/financial-services/our-insights/"
    "from-ripples-to-waves-the-transformational-power-of-tokenizing-assets"
)
_BCG_ADDX_TOKENIZATION_REPORT_URL = (
    "https://www.addx.co/files/bcg_ADDX_report_Asset_tokenization_trillion_opportunity_by_2030_de2aaa41a4.pdf"
)
_CITI_GPS_STABLECOINS_2030_URL = (
    "https://www.citigroup.com/rcs/citigpa/storage/public/GPS_Report_Stablecoins_2030.pdf"
)
_WEF_ASSET_TOKENIZATION_2025_URL = (
    "https://reports.weforum.org/docs/WEF_Asset_Tokenization_in_Financial_Markets_2025.pdf"
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
    <li><strong>2030 market size (estimates only; not apples-to-apples).</strong>
      <ul>
        <li><a href="{_MCKINSEY_TOKENIZATION_URL}">McKinsey &amp; Company</a> (June&nbsp;2024): <strong>~$2&nbsp;trillion</strong>
        tokenized financial-asset market cap by <strong>2030</strong> (central case); about <strong>$1–4&nbsp;trillion</strong> across
        published scenarios; excludes major crypto and stablecoins to avoid double counting.</li>
        <li><a href="{_BCG_ADDX_TOKENIZATION_REPORT_URL}">Boston Consulting Group</a> (with ADDX): widely cited
        <strong>~$16&nbsp;trillion</strong> framing for <strong>illiquid-asset</strong> tokenization potential by <strong>2030</strong>
        (see joint report PDF; scope is broader than McKinsey’s tokenized-financial-assets slice).</li>
        <li><a href="{_CITI_GPS_STABLECOINS_2030_URL}">Citigroup</a> (GPS, <em>Stablecoins 2030</em>, 2025 refresh): bank
        scenario work summarized in the press points to roughly <strong>~$1.9&nbsp;trillion (base) to ~$4&nbsp;trillion (bull)</strong>
        for <strong>stablecoin-related</strong> market size by <strong>2030</strong>—definitions are payment-rail / bank-token
        oriented, not “all RWAs.”</li>
        <li><a href="{_WEF_ASSET_TOKENIZATION_2025_URL}">World Economic Forum</a> (2025, <em>Asset Tokenization in Financial
        Markets</em>): cites industry projections that global private equity / venture capital <strong>could reach ~$7&nbsp;trillion
        by 2030</strong>, with discussion that <strong>~10%</strong> might be tokenized—one asset-class lens inside a wider survey
        of markets and policy.</li>
      </ul>
      <p class="rwa-gmo-takeaway-note" style="margin-top:0.35rem;margin-bottom:0;">Treat each line as a <strong>directional
      scenario</strong> from a different perimeter—do not sum or average across firms.</p>
    </li>
  </ul>
  <p class="rwa-gmo-takeaway-note">Snapshot for context only (not investment advice). The chart and table below reflect
  RWA.xyz embedded homepage data, not the third-party forecasts above.</p>
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
        '<a href="https://app.rwa.xyz/">RWA.xyz</a> <strong>Market Overview</strong> tab on the live site. '
        "Top-line <strong>30D</strong> % changes and table values are read from that page so they stay in sync with what visitors see.</p>",
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
