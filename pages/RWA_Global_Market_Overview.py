"""RWA.xyz Global Market Overview: homepage KPIs and Networks table aligned with the live site."""

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
from streamlit_rwa_global_static import (
    get_rwa_global_iframe_payloads,
    render_rwa_global_body_iframe,
)


def main() -> None:
    configure_subpage(
        page_title="RWA Global Market Overview — Digital Assets Dashboard",
        active="rwa_global",
        style_kind="rwa_global",
        show_nav=True,
        nav_style="home",
    )
    related = related_chips_html(
        ("/?jd_scroll=onchain", "Home on-chain preview"),
        (_streamlit_page_href("explore_asset"), "Explore by asset type"),
        (_streamlit_page_href("explore_participant"), "Explore by participant"),
        (_streamlit_page_href("stablecoins"), "Stablecoins"),
        (_streamlit_page_href("tmmf"), "Tokenized MMFs"),
        (_streamlit_page_href("crypto"), "Crypto prices"),
    )

    with st.spinner("Loading RWA global market page…"):
        payloads = get_rwa_global_iframe_payloads()
        render_rwa_global_body_iframe(payloads=payloads, related_chips=related)

    render_subpage_footer(label="RWA Global Market")


main()
