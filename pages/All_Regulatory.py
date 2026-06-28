"""Full regulatory headlines list with pagination and day grouping."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import streamlit as st

from streamlit_site_parity import (
    _streamlit_page_href,
    configure_subpage,
    related_chips_html,
    render_subpage_footer,
)
from streamlit_news_feeds_static import (
    get_news_feed_iframe_payloads,
    render_news_feed_body_iframe,
)


def main() -> None:
    configure_subpage(
        page_title="All regulatory headlines — Digital Assets Dashboard",
        active="news",
        style_kind="news_feed",
        show_nav=True,
        nav_style="home",
    )
    related = related_chips_html(
        ("/?jd_scroll=news", "Home News Hub"),
        (_streamlit_page_href("articles"), "All headlines"),
        (_streamlit_page_href("custodian"), "Custody headlines"),
        (_streamlit_page_href("etf_news"), "ETF/ETP headlines"),
    )

    with st.spinner("Loading regulatory headlines…"):
        payloads = get_news_feed_iframe_payloads("regulatory")
        render_news_feed_body_iframe(
            kind="regulatory",
            payloads=payloads,
            related_chips=related,
        )

    render_subpage_footer(label="Regulatory headlines")


main()
