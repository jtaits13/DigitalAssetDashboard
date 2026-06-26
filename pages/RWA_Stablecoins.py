"""Tokenized stablecoins: KPIs + network/platform aggregates from RWA.xyz."""

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
from streamlit_stablecoins_static import (
    get_stablecoins_deep_payload,
    render_stablecoins_body_iframe,
)


def main() -> None:
    configure_subpage(
        page_title="Stablecoins — Digital Assets Dashboard",
        active="stablecoins",
        style_kind="stablecoins",
    )
    related = related_chips_html(
        ("/?jd_scroll=stablecoins", "Home stablecoins preview"),
        (_streamlit_page_href("tmmf"), "Tokenized MMFs"),
        (_streamlit_page_href("crypto"), "Crypto prices"),
        (_streamlit_page_href("rwa_global"), "RWA market overview"),
    )

    with st.spinner("Loading stablecoins page…"):
        payload = get_stablecoins_deep_payload()
        render_stablecoins_body_iframe(payload=payload, related_chips=related)

    render_subpage_footer(label="Stablecoins")


main()
