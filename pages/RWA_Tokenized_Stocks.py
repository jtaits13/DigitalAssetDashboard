"""Full RWA.xyz Tokenized Stocks page: overview KPIs + Distributed · Platforms league."""

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
from rwa_league.widgets import TOKENIZED_STOCKS_RWA_CAPTION, show_rwa_tokenized_stocks_widget

_WEF_ASSET_TOKENIZATION_2025_URL = (
    "https://reports.weforum.org/docs/WEF_Asset_Tokenization_in_Financial_Markets_2025.pdf"
)


def main() -> None:
    st.set_page_config(
        page_title="Tokenized Stocks — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Back", key="top_back_rwa_tokenized_stocks"):
        st.switch_page("pages/RWA_Explore_By_Asset_Type.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_tokenized_stocks", current="rwa_tokenized_stocks")

    st.markdown(section_label_teal("Tokenized Stocks", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">Tokenized public equities: overview <strong>30-day (30D)</strong> % changes and '
        "<strong>Distributed Value</strong> breakdowns (levels) by platform and network. Full "
        "<strong>Distributed</strong> · <strong>Platforms</strong> league with search — "
        '<a href="https://app.rwa.xyz/stocks">RWA.xyz Tokenized Stocks</a>.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="border:1px solid #C7D8E8;border-radius:10px;padding:0.75rem 0.95rem;'
        'margin:0.1rem 0 0.55rem;background:#ffffff;box-shadow:0 1px 3px rgba(15,23,42,0.06);">'
        '<p style="margin:0 0 0.28rem 0;font-size:0.9rem;font-weight:700;color:#021D41;">Key Observation</p>'
        '<ul style="margin:0.1rem 0 0 1.05rem;padding:0;color:#1F4C67;font-size:0.9rem;line-height:1.4;">'
        '<li><strong>Tokenized stocks are still an early adoption lane.</strong> The platform and network rankings below '
        'show where limited liquidity is concentrating, which matters more than raw listing count.</li>'
        '<li><strong>Longer-term equity tokenization potential is large but scenario-based.</strong> '
        '<a href="' + _WEF_ASSET_TOKENIZATION_2025_URL + '">WEF (2025)</a> cites industry projections for private-market '
        'tokenization by 2030; this page is useful for tracking how much of that thesis is translating into live '
        'distributed value today.</li>'
        "</ul></div>",
        unsafe_allow_html=True,
    )
    st.divider()

    show_rwa_tokenized_stocks_widget(home_preview=False, full_page_header=True)

    st.divider()
    st.caption(TOKENIZED_STOCKS_RWA_CAPTION)
    st.caption(
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "RWA.xyz embed · Cached up to one hour · Use **Refresh all data** on the home page to reload."
    )


main()
