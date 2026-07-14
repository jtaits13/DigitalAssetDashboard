"""News hub — ETF/ETP lane entry."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import streamlit as st

from streamlit_site_parity import configure_subpage, render_subpage_footer
from streamlit_news_feeds_static import get_news_hub_iframe_payloads, render_news_hub_body_iframe


def main() -> None:
    configure_subpage(
        page_title="ETF/ETP news — Digital Assets Dashboard",
        active="etps",
        style_kind="news_feed",
        show_nav=True,
        nav_style="home",
    )

    with st.spinner("Loading news hub…"):
        payloads = get_news_hub_iframe_payloads()
        render_news_hub_body_iframe(
            payloads=payloads,
            initial_lane="etf",
            back_href="/US_Crypto_ETPs",
            back_label="← Back to U.S. ETP Overview",
        )

    render_subpage_footer(label="News Hub")


main()
