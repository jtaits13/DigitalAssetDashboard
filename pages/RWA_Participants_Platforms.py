"""RWA.xyz Participants — Platforms: issuer overview KPIs + Platforms table."""

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


def _participants_platforms_takeaway_html() -> str:
    return (
        '<div style="border:1px solid #C7D8E8;border-radius:10px;padding:0.75rem 0.95rem;'
        'margin:0.1rem 0 0.55rem;background:#ffffff;box-shadow:0 1px 3px rgba(15,23,42,0.06);">'
        '<ul style="margin:0.1rem 0 0 1.05rem;padding:0;color:#1F4C67;font-size:0.9rem;line-height:1.4;">'
        '<li><strong>Platform competition is increasingly distribution-led:</strong> partnership depth and channel reach '
        'are becoming stronger share drivers than technical differentiation alone.</li>'
        '<li><strong>Scale tends to reinforce itself:</strong> once platforms establish issuer and liquidity depth, they '
        'often capture a disproportionate share of incremental distributed value.</li>'
        "</ul></div>"
        + monthly_review_note_html()
    )


def main() -> None:
    from rwa_league.widgets import show_rwa_participants_platforms_widget
    from news_feeds import (
        app_shared_layout_css,
        article_styles_markdown,
        render_subpage_sidebar,
        render_subpage_top_bar,
    )

    st.set_page_config(
        page_title="Participants — Platforms — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Back", key="top_back_rwa_participants_platforms"):
        st.switch_page("pages/RWA_Explore_By_Market_Participant.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_participants_platforms", current="rwa_participants_platforms")

    st.markdown(section_label_teal("Participants — Platforms", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">This page mirrors the '
        '<a href="https://app.rwa.xyz/platforms">RWA.xyz Platforms</a> view, including issuer-level headline metrics '
        "and the <strong>Distributed</strong> issuer table. Top-line <strong>30D</strong> % changes and per-issuer "
        "columns match the live page.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    show_rwa_participants_platforms_widget(
        home_preview=False,
        full_page_header=True,
        full_page_key_observations_html=_participants_platforms_takeaway_html(),
    )

    st.divider()
    st.caption(rwa_xyz_mirror_footer_text())


main()
