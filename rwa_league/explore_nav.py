"""Session hint for RWA Explore index pages: top-left **Home** vs **Back** to Global Market Overview."""

from __future__ import annotations

from typing import Final, Literal

import streamlit as st

RWA_EXPLORE_TOP_NAV_SESSION_KEY: Final[str] = "_rwa_explore_top_nav"
RwaExploreTopNavTarget = Literal["home", "global_market"]


def set_rwa_explore_top_nav_target(target: RwaExploreTopNavTarget) -> None:
    """Set before ``st.switch_page`` to an Explore index so that page can render the correct top control."""
    st.session_state[RWA_EXPLORE_TOP_NAV_SESSION_KEY] = target


def render_rwa_explore_top_nav_button(*, key: str) -> None:
    """Top-left control on Explore-by index pages: **Back** to Global Market Overview or **Home** to landing."""
    target = st.session_state.get(RWA_EXPLORE_TOP_NAV_SESSION_KEY, "home")
    if target == "global_market":
        if st.button("← Back", key=key):
            st.switch_page("pages/RWA_Global_Market_Overview.py")
    else:
        if st.button("← Home", key=key):
            st.switch_page("streamlit_app.py")
