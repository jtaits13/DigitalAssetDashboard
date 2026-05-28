"""RWA.xyz Participants — Asset Managers: overview KPIs + Distributed tab table."""

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


def _participants_asset_managers_takeaway_html() -> str:
    from key_observations.page_ko import build_legacy_page_ko

    return build_legacy_page_ko("participants_asset_managers")


def main() -> None:
    from rwa_league.widgets import show_rwa_participants_asset_managers_widget
    from news_feeds import (
        app_shared_layout_css,
        article_styles_markdown,
        render_subpage_sidebar,
        render_subpage_top_bar,
    )

    st.set_page_config(
        page_title="Participants — Asset Managers — Digital Assets Dashboard",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Back", key="top_back_rwa_participants_asset_managers"):
        st.switch_page("pages/RWA_Explore_By_Market_Participant.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_participants_asset_managers", current="rwa_participants_asset_managers")

    st.markdown(section_label_teal("Participants — Asset Managers", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">This page mirrors the '
        '<a href="https://app.rwa.xyz/asset-managers">RWA.xyz Asset Managers</a> view, including manager-level '
        "headline metrics and the <strong>Distributed</strong> table. Top-line <strong>30D</strong> % changes and "
        "per-manager columns match the live page.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    show_rwa_participants_asset_managers_widget(
        home_preview=False,
        full_page_header=True,
        full_page_key_observations_html=_participants_asset_managers_takeaway_html(),
    )

    st.divider()
    st.caption(rwa_xyz_mirror_footer_text())


main()
