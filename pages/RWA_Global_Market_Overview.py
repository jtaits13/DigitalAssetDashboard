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
from rwa_league.widgets import (
    RWA_GLOBAL_MARKET_DATA_SOURCE_CAPTION,
    show_rwa_participants_networks_widget,
)

# Macro context for readers (third-party research; not investment advice). Links verified via public pages.
_MCKINSEY_TOKENIZATION_URL = (
    "https://www.mckinsey.com/industries/financial-services/our-insights/"
    "from-ripples-to-waves-the-transformational-power-of-tokenizing-assets"
)
_BCG_TOKENIZED_FUNDS_PDF_URL = (
    "https://web-assets.bcg.com/81/71/6ff0849641a58706581b5a77113f/"
    "tokenized-funds-the-third-revolution-in-asset-management-decoded.pdf"
)

RWA_GLOBAL_MARKET_MACRO_CONTEXT_HTML = f"""
<style>
.rwa-gmo-takeaways {{
  border: 1px solid #C7D8E8;
  border-radius: 10px;
  padding: 0.85rem 1rem 0.95rem;
  margin: 0.35rem 0 0.85rem;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(15,23,42,0.06);
}}
.rwa-gmo-takeaways h3 {{
  margin: 0 0 0.5rem 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #021D41;
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
    <li><strong>Growth from a small share of global markets.</strong> On-chain aggregates such as the RWA.xyz snapshot
    below can grow quickly in percentage terms as pilots multiply, yet still represent a thin slice of total global
    financial assets—so month-to-month moves in headline figures are expected.</li>
    <li><strong>2030 market size (estimates only; definitions differ).</strong>
      <ul>
        <li><a href="{_MCKINSEY_TOKENIZATION_URL}">McKinsey</a> (June&nbsp;2024): <strong>~$2&nbsp;trillion</strong> tokenized
        financial-asset market cap by <strong>2030</strong> (central case); about <strong>$1–4&nbsp;trillion</strong> across their
        published scenarios; excludes major crypto and stablecoins to avoid double counting.</li>
        <li><a href="{_BCG_TOKENIZED_FUNDS_PDF_URL}">BCG</a> (tokenized funds): secondary coverage often cites
        <strong>~$16&nbsp;trillion</strong> for a broader “tokenized economy” / illiquid-asset framing—<strong>not</strong> the same
        scope as McKinsey’s line item.</li>
        <li>Use these as <strong>directional scenarios</strong>, not a single consensus forecast.</li>
      </ul>
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

    st.divider()
    st.caption(RWA_GLOBAL_MARKET_DATA_SOURCE_CAPTION)
    st.caption(
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "RWA.xyz embed · Cached up to one hour · Use **Refresh all data** on the home page to reload."
    )


main()
