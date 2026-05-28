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
    rwa_xyz_mirror_footer_text,
    section_label_teal,
)
from price_ticker import show_price_ticker


def _mmf_takeaway_html() -> str:
    from key_observations.feeds import load_takeaway_articles
    from rwa_league.mmf import _aggregate_network_rows, collect_tokenized_mmf_assets
    from rwa_league.mmf_takeaways import build_mmf_key_observations_html

    mmfs, err = collect_tokenized_mmf_assets()
    if err or not mmfs:
        return ""
    net_rows = _aggregate_network_rows(mmfs)
    return build_mmf_key_observations_html(mmfs, net_rows, load_takeaway_articles())


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
