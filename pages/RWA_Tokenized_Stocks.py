"""Full RWA.xyz Tokenized Stocks page: overview KPIs + Distributed · Networks then Platforms leagues."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import streamlit as st

from home_layout import (
    ETP_FULLPAGE_AUM_LINE_CSS,
    STREAMLIT_TABLE_UNIFY_CSS,
    rwa_xyz_mirror_footer_text,
    section_label_teal,
)
from price_ticker import show_price_ticker


def _tokenized_stocks_takeaway_html() -> str:
    from key_observations.page_ko import build_legacy_page_ko

    return build_legacy_page_ko("tokenized_stocks")


def main() -> None:
    from rwa_league.widgets import show_rwa_tokenized_stocks_widget
    from news_feeds import (
        app_shared_layout_css,
        article_styles_markdown,
        render_subpage_sidebar,
        render_subpage_top_bar,
    )

    st.set_page_config(
        page_title="Tokenized Stocks — Digital Assets Dashboard",
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
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">This page mirrors the '
        '<a href="https://app.rwa.xyz/stocks">RWA.xyz Tokenized Stocks</a> view, including headline '
        "<strong>30-day (30D)</strong> % changes and searchable <strong>Distributed Networks</strong> "
        "and <strong>Platforms</strong> tables (Networks first). <strong>Distributed Value</strong> columns are "
        "current levels.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    show_rwa_tokenized_stocks_widget(
        home_preview=False,
        full_page_header=True,
        full_page_key_observations_html=_tokenized_stocks_takeaway_html(),
    )

    st.divider()
    st.caption(rwa_xyz_mirror_footer_text())


main()
