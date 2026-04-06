"""Streamlit widget: regulatory headlines on digital assets (RSS, global)."""

from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

import streamlit as st

REGULATORY_HEADLINE_COUNT = 5


def clear_regulatory_cache() -> None:
    from regulatory_news.client import load_regulatory_articles

    load_regulatory_articles.clear()


def render_regulatory_card_html(item: dict[str, Any]) -> str:
    pub = item.get("published")
    pub_s = pub.strftime("%b %d, %Y · %H:%M UTC") if isinstance(pub, datetime) else "Date unknown"
    title_esc = escape(item.get("title") or "Untitled")
    link = item.get("link") or "#"
    href = escape(str(link), quote=True)
    summary = (item.get("summary") or "").strip()
    sum_html = ""
    if summary:
        sum_html = f'<div class="news-summary">{escape(summary)}</div>'
    country = escape(str(item.get("country") or "Global"))
    return (
        f'<div class="news-card">'
        f'<div class="news-meta">{escape(str(item.get("source", "")))} · {escape(pub_s)}</div>'
        f'<div class="news-title"><a href="{href}" target="_blank" rel="noopener noreferrer">{title_esc}</a></div>'
        f'<div class="news-country">{country}</div>'
        f"{sum_html}"
        f"</div>"
    )


def show_regulatory_headlines_widget(articles: list[dict[str, Any]]) -> None:
    """Right-column widget matching Latest Digital Asset News layout (heading + See more + cards)."""
    st.markdown(
        '<h2 class="home-main-heading">Regulatory headlines · digital assets</h2>',
        unsafe_allow_html=True,
    )

    if len(articles) > REGULATORY_HEADLINE_COUNT:
        if st.button(
            "See more regulatory headlines",
            key="see_more_regulatory_top",
            use_container_width=True,
            type="primary",
        ):
            st.switch_page("pages/All_Regulatory.py")

    if not articles:
        st.caption("No regulatory headlines matched the filters yet. Try **Refresh feeds** in the sidebar.")
        return

    top = articles[:REGULATORY_HEADLINE_COUNT]
    for item in top:
        st.markdown(render_regulatory_card_html(item), unsafe_allow_html=True)

    if len(articles) <= REGULATORY_HEADLINE_COUNT:
        st.caption("No additional headlines beyond this list.")
