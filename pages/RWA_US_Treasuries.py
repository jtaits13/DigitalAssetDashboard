"""Full RWA.xyz US Treasuries page: overview KPIs + Distributed · Networks league (Distributed Value)."""

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
    monthly_review_note_html,
    rwa_xyz_mirror_footer_text,
    section_label_teal,
)
from price_ticker import show_price_ticker


def _treasuries_takeaway_html() -> str:
    return (
        '<div style="border:1px solid #C7D8E8;border-radius:10px;padding:0.75rem 0.95rem;'
        'margin:0.1rem 0 0.55rem;background:#ffffff;box-shadow:0 1px 3px rgba(15,23,42,0.06);">'
        '<ul style="margin:0.1rem 0 0 1.05rem;padding:0;color:#1F4C67;font-size:0.9rem;line-height:1.4;">'
        '<li><strong>Tokenized U.S. Treasuries remain the institutional bridge into RWAs:</strong> adoption is strongest '
        'where products plug into cash management, collateral, and liquidity workflows.</li>'
        '<li><strong>Distribution still drives outcomes:</strong> network/platform leadership generally follows issuer '
        'reach, treasury utility, and integration quality more than feature novelty.</li>'
        "</ul></div>"
        + monthly_review_note_html()
    )


def main() -> None:
    from rwa_league.widgets import show_rwa_treasuries_widget
    from news_feeds import (
        app_shared_layout_css,
        article_styles_markdown,
        render_subpage_sidebar,
        render_subpage_top_bar,
    )

    st.set_page_config(
        page_title="US Treasuries — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Back", key="top_back_rwa_treasuries"):
        st.switch_page("pages/RWA_Explore_By_Asset_Type.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_us_treasuries", current="rwa_treasuries")

    st.markdown(section_label_teal("US Treasuries", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">This page mirrors the '
        '<a href="https://app.rwa.xyz/treasuries">RWA.xyz US Treasuries</a> view, including headline '
        "<strong>30-day (30D)</strong> % changes and searchable <strong>Distributed</strong> tables for "
        "<strong>Networks</strong> and <strong>Platforms</strong>. <strong>Distributed Value</strong> columns are "
        "shown as current levels.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    show_rwa_treasuries_widget(
        home_preview=False,
        full_page_header=True,
        full_page_key_observations_html=_treasuries_takeaway_html(),
    )

    st.divider()
    st.caption(rwa_xyz_mirror_footer_text())


main()
