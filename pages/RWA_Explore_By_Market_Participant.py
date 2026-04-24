"""RWA.xyz hub index: Networks, Platforms, and Asset Managers (same previews as the home hub)."""

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
from rwa_league.widgets import show_rwa_explore_by_market_participant_widget


def main() -> None:
    st.set_page_config(
        page_title="Explore by Market Participant — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Home", key="top_home_rwa_explore_market_participant"):
        st.switch_page("streamlit_app.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_explore_market_participant", current="rwa_explore_market_participant")

    st.markdown(section_label_teal("Explore by Market Participant", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<div class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-explore-blurb">'
        "<p>Data from <strong>RWA.xyz</strong>. Below are three ways the market is shown:</p>"
        "<ul>"
        "<li>Networks</li>"
        "<li>Platforms</li>"
        "<li>Asset managers</li>"
        "</ul>"
        '<p class="jd-hub-explore-blurb--tail">'
        "Each section is a quick preview. Use the links inside when you want the full RWA view."
        "</p></div>",
        unsafe_allow_html=True,
    )
    st.divider()

    show_rwa_explore_by_market_participant_widget(preview_rows=8)

    st.divider()
    st.caption(
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "RWA.xyz embeds · Cached up to one hour · Use **Refresh all data** on the home page to reload."
    )


main()
