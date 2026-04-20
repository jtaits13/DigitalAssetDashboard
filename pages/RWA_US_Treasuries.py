"""Full RWA.xyz US Treasuries page: overview KPIs + Distributed · Networks league (Distributed Value)."""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from home_layout import ETP_FULLPAGE_AUM_LINE_CSS, STREAMLIT_TABLE_UNIFY_CSS
from news_feeds import (
    app_shared_layout_css,
    article_styles_markdown,
    render_subpage_top_bar,
)
from price_ticker import show_price_ticker
from rwa_league.widgets import TREASURY_RWA_CAPTION, show_rwa_treasuries_widget


def main() -> None:
    st.set_page_config(
        page_title="US Treasuries — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Home", key="top_home_rwa_treasuries"):
        st.switch_page("streamlit_app.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    st.caption(
        "Tokenized U.S. Treasuries: overview **30-day (30D)** % changes from **RWA.xyz** and league tables where "
        "**Distributed Value** is a level (networks and platforms)."
    )

    show_rwa_treasuries_widget(home_preview=False)

    st.caption(TREASURY_RWA_CAPTION)
    st.caption(
        f"Last loaded at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "Cached up to one hour; use **Refresh all data** on the home page to reload."
    )


main()
