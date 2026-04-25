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
        '<p class="jd-hub-dek jd-hub-dek-fullbleed">RWA <strong>Global Market Overview</strong>: the same '
        "<strong>headline metrics</strong> and <strong>Networks</strong> table as the "
        '<a href="https://app.rwa.xyz/">RWA.xyz</a> Market Overview tab (embedded in <code>__NEXT_DATA__</code>). '
        "Top-line <strong>30D</strong> % changes and table values are pulled from that homepage dataset.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    show_rwa_participants_networks_widget(home_preview=False, full_page_header=True)

    st.divider()
    st.caption(RWA_GLOBAL_MARKET_DATA_SOURCE_CAPTION)
    st.caption(
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "RWA.xyz embed · Cached up to one hour · Use **Refresh all data** on the home page to reload."
    )


main()
