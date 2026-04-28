"""RWA.xyz Participants — Platforms: issuer overview KPIs + Platforms table (``/platforms`` embed)."""

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
from rwa_league.widgets import show_rwa_participants_platforms_widget

_BCG_ADDX_TOKENIZATION_REPORT_URL = (
    "https://www.addx.co/files/bcg_ADDX_report_Asset_tokenization_trillion_opportunity_by_2030_de2aaa41a4.pdf"
)


def main() -> None:
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
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">RWA <strong>Participants</strong> · <strong>Platforms</strong>: '
        "issuer-level **Platforms Overview** metrics and the **Distributed** Platforms issuer table from "
        '<a href="https://app.rwa.xyz/platforms">RWA.xyz</a> <strong>Platforms</strong> page, aligned with the live '
        "**Distributed** issuers view (including distributed vs. represented splits where the site shows them). "
        "Top-line <strong>30D</strong> % changes and per-issuer columns match the public page.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="border:1px solid #C7D8E8;border-radius:10px;padding:0.75rem 0.95rem;'
        'margin:0.1rem 0 0.55rem;background:#ffffff;box-shadow:0 1px 3px rgba(15,23,42,0.06);">'
        '<p style="margin:0 0 0.28rem 0;font-size:0.9rem;font-weight:700;color:#021D41;">Key Observation</p>'
        '<ul style="margin:0.1rem 0 0 1.05rem;padding:0;color:#1F4C67;font-size:0.9rem;line-height:1.4;">'
        '<li><strong>Platform competition is becoming distribution-led.</strong> The distributed-value leaderboard below '
        'shows where issuer reach and shelf access are translating into sustained market share.</li>'
        '<li><strong>That fits larger tokenization commercialization narratives.</strong> '
        '<a href="' + _BCG_ADDX_TOKENIZATION_REPORT_URL + '">BCG/ADDX</a> frames scale-up as an ecosystem-and-distribution '
        'challenge, not just a protocol feature race.</li>'
        "</ul></div>",
        unsafe_allow_html=True,
    )
    st.divider()

    show_rwa_participants_platforms_widget(home_preview=False, full_page_header=True)

    st.divider()
    st.caption(
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "RWA.xyz embed · Cached up to one hour · Use **Refresh all data** on the home page to reload."
    )


main()
