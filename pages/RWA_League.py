"""Full RWA.xyz networks league table (same data as home preview)."""

from __future__ import annotations

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
from rwa_league.widgets import RWA_DATA_SOURCE_CAPTION, show_rwa_league_widget


def main() -> None:
    st.set_page_config(
        page_title="RWA Data — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_league", current="rwa_league")

    st.markdown(section_label_teal("RWA Data", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek">This page summarizes the cross-network RWA market, highlighting distributed value and '
        "share dynamics across blockchain ecosystems. Full <strong>Networks</strong> table with search from the "
        "RWA.xyz homepage embed. <strong>Distributed Value</strong> is a level; the Global Market overview row uses "
        "<strong>30-day (30D)</strong> % changes.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    show_rwa_league_widget(home_preview=False)

    st.divider()
    st.caption(RWA_DATA_SOURCE_CAPTION)
    st.caption(
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "RWA.xyz embed · Cached up to one hour · Use **Refresh all data** on the home page to reload."
    )


main()
