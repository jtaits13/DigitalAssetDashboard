"""Fixed site nav as a Streamlit custom component (vanilla JS, no build step)."""

from __future__ import annotations

import os

import streamlit.components.v1 as components

_BUILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
jpm_site_nav = components.declare_component("jpm_site_nav", path=_BUILD)
