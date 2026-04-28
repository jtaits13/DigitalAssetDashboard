"""RWA.xyz Participants — Networks: distributed value KPIs + Networks league (homepage embed)."""

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
from rwa_league.explore_nav import set_rwa_explore_top_nav_target
from rwa_league.widgets import show_rwa_participants_networks_widget

_MCKINSEY_TOKENIZATION_URL = (
    "https://www.mckinsey.com/industries/financial-services/our-insights/"
    "from-ripples-to-waves-the-transformational-power-of-tokenizing-assets"
)


def main() -> None:
    st.set_page_config(
        page_title="Participants — Networks — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Back", key="top_back_rwa_participants_networks"):
        set_rwa_explore_top_nav_target("home")
        st.switch_page("pages/RWA_Explore_By_Market_Participant.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_participants_networks", current="rwa_participants_networks")

    st.markdown(section_label_teal("Participants — Networks", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">RWA <strong>Participants</strong> · <strong>Networks</strong>: the same '
        "<strong>Networks Overview</strong> headline metrics and on-chain <strong>Networks</strong> table as "
        '<a href="https://app.rwa.xyz/networks">RWA.xyz</a> <strong>Networks</strong> page. '
        "Top-line <strong>30D</strong> % changes and per-network <strong>transferability</strong> / share columns match the live site for the same view.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="border:1px solid #C7D8E8;border-radius:10px;padding:0.75rem 0.95rem;'
        'margin:0.1rem 0 0.55rem;background:#ffffff;box-shadow:0 1px 3px rgba(15,23,42,0.06);">'
        '<p style="margin:0 0 0.28rem 0;font-size:0.9rem;font-weight:700;color:#021D41;">Key Observation</p>'
        '<ul style="margin:0.1rem 0 0 1.05rem;padding:0;color:#1F4C67;font-size:0.9rem;line-height:1.4;">'
        '<li><strong>RWA issuance remains network-concentrated.</strong> The live ranking below makes concentration and '
        'share-shift dynamics explicit via distributed value and market-share changes.</li>'
        '<li><strong>That concentration profile is consistent with “wave” adoption patterns.</strong> '
        '<a href="' + _MCKINSEY_TOKENIZATION_URL + '">McKinsey</a> describes phased institutional rollout, where a few '
        'networks capture scale first before broader multi-chain distribution follows.</li>'
        "</ul></div>",
        unsafe_allow_html=True,
    )
    st.divider()

    show_rwa_participants_networks_widget(home_preview=False, full_page_header=False)

    st.divider()
    st.caption(
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "RWA.xyz embed · Cached up to one hour · Use **Refresh all data** on the home page to reload."
    )


main()
