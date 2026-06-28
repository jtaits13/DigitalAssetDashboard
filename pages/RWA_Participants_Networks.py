"""Participants — Networks: distributed value KPIs + Networks league (GitHub Pages parity iframe)."""

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
from streamlit_rwa_asset_deep_static import get_rwa_asset_deep_payload, render_rwa_asset_deep_body_iframe


def main() -> None:
    configure_subpage(
        page_title="Participants — Networks — Digital Assets Dashboard",
        active="networks",
        style_kind="networks",
        show_nav=True,
        nav_style="home",
    )
    related = related_chips_html(
        (_streamlit_page_href("explore_participant"), "Explore by participant"),
        (_streamlit_page_href("rwa_global"), "RWA market overview"),
        (_streamlit_page_href("explore_asset"), "Explore by asset type"),
        (_streamlit_page_href("platforms"), "Platforms"),
        (_streamlit_page_href("asset_managers"), "Asset Managers"),
    )

    with st.spinner("Loading Participants — Networks…"):
        payload = get_rwa_asset_deep_payload("networks")
        render_rwa_asset_deep_body_iframe(
            kind="networks",
            payload=payload,
            related_chips=related,
            back_href=_streamlit_page_href("explore_participant"),
        )

    render_subpage_footer(label="Participants — Networks")


main()
