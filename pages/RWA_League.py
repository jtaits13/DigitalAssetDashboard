"""Legacy page path; forwards to :mod:`RWA_Participants_Networks`."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Redirect — RWA",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.switch_page("pages/RWA_Participants_Networks.py")
