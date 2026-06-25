"""Tokenized money market funds: KPIs + network/platform aggregates from RWA.xyz fund lists."""

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
from streamlit_tmmf_static import (
    get_tmmf_deep_payload,
    render_tmmf_body_iframe,
)


def main() -> None:
    configure_subpage(
        page_title="Tokenized Money Market Funds — Digital Assets Dashboard",
        active="tmmf",
        style_kind="tmmf",
    )
    related = related_chips_html(
        ("/?jd_scroll=tmmf", "Home TMMF preview"),
        (_streamlit_page_href("stablecoins"), "Stablecoins"),
        (_streamlit_page_href("etps"), "U.S. ETPs"),
        (_streamlit_page_href("rwa_global"), "RWA market overview"),
    )

    payload = get_tmmf_deep_payload()
    render_tmmf_body_iframe(payload=payload, related_chips=related)

    render_subpage_footer(label="Tokenized Money Market Funds")


main()
