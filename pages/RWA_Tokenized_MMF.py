"""Tokenized money market funds: KPIs + network/platform aggregates from RWA.xyz fund lists."""

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
    monthly_review_note_class_html,
    rwa_xyz_mirror_footer_text,
    section_label_teal,
)
from price_ticker import show_price_ticker


def _mmf_takeaway_html() -> str:
    return (
        '<div style="border:1px solid #C7D8E8;border-radius:10px;padding:0.75rem 0.95rem;'
        'margin:0.1rem 0 0.55rem;background:#ffffff;box-shadow:0 1px 3px rgba(15,23,42,0.06);">'
        '<ul style="margin:0.1rem 0 0 1.05rem;padding:0;color:#1F4C67;font-size:0.9rem;line-height:1.4;">'
        "<li><strong>Liquidity funds anchor institutional RWA adoption:</strong> tokenized MMFs concentrate "
        "in short-duration government and repo-like products used for cash management and collateral.</li>"
        "<li><strong>Multi-chain distribution is selective:</strong> largest funds deploy on a handful of "
        "networks where issuer integrations and transferability matter—not every chain carries meaningful AUM.</li>"
        "<li><strong>Issuer concentration reflects fund franchises:</strong> a small set of asset managers "
        "accounts for most distributed value; tail funds are often regional or single-chain programs.</li>"
        "</ul>"
        '<p class="takeaways__note">Context only—not investment advice. Observations contextualize the '
        "headline KPI row above (RWA.xyz US Treasuries and Non-U.S. Government Debt fund aggregates).</p>"
        "</div>"
        + monthly_review_note_class_html()
    )


def main() -> None:
    from rwa_league.widgets import show_rwa_mmf_widget
    from news_feeds import (
        app_shared_layout_css,
        article_styles_markdown,
        render_subpage_sidebar,
        render_subpage_top_bar,
    )

    st.set_page_config(
        page_title="Tokenized Money Market Funds — Digital Assets Dashboard",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Back", key="top_back_rwa_mmf"):
        st.switch_page("pages/RWA_Explore_By_Asset_Type.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_tokenized_mmf", current="rwa_tokenized_mmf")

    st.markdown(
        section_label_teal("Tokenized Money Market Funds", placement="first"),
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">Aggregated view of tokenized money market '
        "funds from <strong>RWA.xyz</strong> US Treasuries and Non-U.S. Government Debt listings. "
        "<strong>Networks</strong> and <strong>Platforms</strong> tables sum each fund's on-chain token "
        "deployments; headline <strong>30-day (30D)</strong> % applies to total distributed value.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    show_rwa_mmf_widget(
        home_preview=False,
        full_page_header=True,
        full_page_key_observations_html=_mmf_takeaway_html(),
    )

    st.divider()
    st.caption(rwa_xyz_mirror_footer_text())


if __name__ == "__main__":
    main()
