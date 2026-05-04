"""RWA.xyz Participants — Networks: distributed value KPIs + Networks league."""

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


def _participants_networks_takeaway_html() -> str:
    return (
        '<div style="border:1px solid #C7D8E8;border-radius:10px;padding:0.75rem 0.95rem;'
        'margin:0 0 0.85rem;background:#ffffff;box-shadow:0 1px 3px rgba(15,23,42,0.06);">'
        '<ul style="margin:0.1rem 0 0 1.05rem;padding:0;color:#1F4C67;font-size:0.9rem;line-height:1.4;">'
        '<li><strong>RWA value remains network-concentrated:</strong> the top chains continue to capture the majority of '
        'distributed issuance and often set near-term market direction.</li>'
        '<li><strong>Institutional expansion is likely staged:</strong> large-scale adoption typically lands on proven '
        'networks first, then broadens as compliance, interoperability, and liquidity deepen.</li>'
        "</ul></div>"
        + monthly_review_note_html()
    )


def main() -> None:
    from rwa_league.widgets import show_rwa_participants_networks_widget
    from news_feeds import (
        app_shared_layout_css,
        article_styles_markdown,
        render_subpage_sidebar,
        render_subpage_top_bar,
    )

    st.set_page_config(
        page_title="Participants — Networks — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Back", key="top_back_rwa_participants_networks"):
        st.switch_page("pages/RWA_Explore_By_Market_Participant.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(
        STREAMLIT_TABLE_UNIFY_CSS
        + ETP_FULLPAGE_AUM_LINE_CSS
        + (
            "<style>.jd-rwa-pn-intro-rule{border:none;border-top:1px solid #dce7f0;margin:0.6rem 0 0.75rem;"
            "height:0;max-width:100%;padding:0}</style>"
        ),
        unsafe_allow_html=True,
    )
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_participants_networks", current="rwa_participants_networks")

    st.markdown(section_label_teal("Participants — Networks", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large" style="margin:0 0 0.55rem 0;">This page mirrors the '
        '<a href="https://app.rwa.xyz/networks">RWA.xyz Networks</a> view, including headline metrics and the '
        "<strong>Networks</strong> table. Top-line <strong>30D</strong> % changes and per-network "
        "<strong>transferability</strong> and share columns match the live page.</p>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="jd-rwa-pn-intro-rule" aria-hidden="true"></div>', unsafe_allow_html=True)

    show_rwa_participants_networks_widget(
        home_preview=False,
        full_page_header=False,
        hide_subsection_title=True,
        full_page_key_observations_html=_participants_networks_takeaway_html(),
    )

    st.divider()
    st.caption(rwa_xyz_mirror_footer_text())


main()
