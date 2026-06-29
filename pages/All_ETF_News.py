"""Full ETF/ETP RSS headline list (same layout as All Articles / All Regulatory)."""

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
        page_title="ETF & ETP headlines — Digital Assets Dashboard",
        active="etps",
        style_kind="news_feed",
        show_nav=True,
        nav_style="home",
        back_href=_streamlit_page_href("etps"),
        back_label="← Back to U.S. ETP Overview",
    )
    related = related_chips_html(
        (_streamlit_page_href("etps"), "U.S. ETP overview"),
        ("/?jd_scroll=markets", "Home ETP preview"),
        (_streamlit_page_href("articles"), "All headlines"),
        (_streamlit_page_href("crypto"), "Crypto prices"),
    )

    with st.spinner("Loading ETF/ETP headlines…"):
        payloads = get_news_feed_iframe_payloads("etf_news")
        render_news_feed_body_iframe(
            kind="etf_news",
            payloads=payloads,
            related_chips=related,
        )

    render_subpage_footer(label="ETF/ETP News")


main()
