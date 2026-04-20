"""Full RWA.xyz Tokenized Stocks page: overview KPIs + Distributed · Platforms league."""

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
from rwa_league.widgets import TOKENIZED_STOCKS_RWA_CAPTION, show_rwa_tokenized_stocks_widget


def main() -> None:
    st.set_page_config(
        page_title="Tokenized Stocks — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Home", key="top_home_rwa_tokenized_stocks"):
        st.switch_page("streamlit_app.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_tokenized_stocks", current="rwa_tokenized_stocks")

    st.markdown(section_label_teal("Tokenized Stocks", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek">Tokenized public equities: overview <strong>30-day (30D)</strong> % changes and '
        "<strong>Distributed Value</strong> breakdowns (levels) by platform and network. Full "
        "<strong>Distributed</strong> · <strong>Platforms</strong> league with search — "
        '<a href="https://app.rwa.xyz/stocks">RWA.xyz Tokenized Stocks</a>.</p>',
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
