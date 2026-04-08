"""Teal header styling via HTML + pandas Styler (avoids Glide/canvas ``st.dataframe`` theming)."""

from __future__ import annotations

import uuid

import pandas as pd
import streamlit.components.v1 as components

# Prepended to Styler ``set_table_styles`` so thead matches site teal (#1E7C99).
TEAL_HEAD_TABLE_STYLES: list[dict[str, object]] = [
    {
        "selector": "thead th",
        "props": [
            ("background-color", "#1E7C99"),
            ("color", "#ffffff"),
            ("font-weight", "700"),
            ("font-size", "0.875rem"),
            ("padding", "0.55rem 0.75rem"),
            ("text-align", "left"),
            ("border", "1px solid #1a6d86"),
        ],
    },
    {
        "selector": "tbody td",
        "props": [
            ("font-size", "0.875rem"),
            ("padding", "0.45rem 0.75rem"),
            ("color", "#0f172a"),
            ("border-bottom", "1px solid #e2e8f0"),
        ],
    },
    {
        "selector": "",
        "props": [
            ("border-collapse", "collapse"),
            ("width", "100%"),
        ],
    },
]


def write_teal_styled_dataframe(styler: pd.io.formats.style.Styler, *, height: int) -> None:
    """
    Render a styled DataFrame in an iframe so ``<style>`` from pandas is preserved.
    Header row uses white text on teal (#1E7C99).
    """
    uid = uuid.uuid4().hex[:12]
    inner = (
        styler.set_table_styles(TEAL_HEAD_TABLE_STYLES, overwrite=False)
        .hide(axis="index")
        .to_html(table_uuid=f"jdteal_{uid}")
    )
    doc = (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"/>"
        "<style>html,body{margin:0;padding:0;}"
        "body{font-family:'Source Sans Pro',sans-serif;}</style></head>"
        "<body>"
        f'<div style="max-height:{height}px;overflow:auto;width:100%;box-sizing:border-box;">'
        f"{inner}</div></body></html>"
    )
    components.html(doc, height=height + 8, scrolling=True, width=None)
