"""Full RWA.xyz Stablecoins page: overview KPIs + Platforms league (same embed as home preview)."""

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
from rwa_league.widgets import STABLECOIN_RWA_CAPTION, show_rwa_stablecoins_widget


def main() -> None:
    st.set_page_config(
        page_title="Stablecoins — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Back", key="top_back_rwa_stablecoins"):
        st.switch_page("pages/RWA_Explore_By_Asset_Type.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_stablecoins", current="rwa_stablecoins")

    st.markdown(section_label_teal("Stablecoins", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed">Tokenized stablecoins: overview <strong>30-day (30D)</strong> % changes and '
        "<strong>Platforms</strong> <strong>market caps</strong> (levels) by issuance platform. Full "
        "<strong>Platforms</strong> league with search from the "
        '<a href="https://app.rwa.xyz/stablecoins">RWA.xyz Stablecoins</a> embed; each row’s <strong>market cap</strong> '
        "is a level.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    show_rwa_stablecoins_widget(home_preview=False, full_page_header=True)

    st.divider()
    st.caption(STABLECOIN_RWA_CAPTION)
    st.caption(
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "RWA.xyz embed · Cached up to one hour · Use **Refresh all data** on the home page to reload."
    )


main()
