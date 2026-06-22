"""Global Custodian custody headlines (full feed)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from datetime import datetime, timezone

import streamlit as st

from custodian_news.client import CUSTODIAN_HEADLINES_PER_UTC_DAY, load_custodian_articles
from news_feeds import (
    article_styles_markdown,
    build_full_page_market_news_feed_html,
    filter_headlines_by_keyword,
)
from streamlit_site_parity import (
    close_subpage_layout,
    configure_subpage,
    inner_page_zone_close,
    inner_page_zone_open,
    open_subpage_layout,
    render_subpage_back_link,
    render_subpage_footer,
)

PER_PAGE = 20


def main() -> None:
    configure_subpage(
        page_title="All custody headlines — Digital Assets Dashboard",
        active="news",
        style_kind="article",
    )
    render_subpage_back_link(
        href="/?jd_scroll=news",
        label="← Back to home (News Hub)",
    )
    open_subpage_layout(style_kind="article")
    inner_page_zone_open(
        section_id="all-custodian",
        badge="NEWS",
        title="All custody headlines",
        subtitle_html=(
            "Crypto and digital-asset stories from "
            '<a href="https://www.globalcustodian.com/" target="_blank" rel="noopener noreferrer">'
            "Global Custodian</a> (digital-asset category RSS plus site search). "
            f"Up to {CUSTODIAN_HEADLINES_PER_UTC_DAY} ranked headlines per UTC day on the home rail; "
            f"this page lists the full archive ({PER_PAGE} per page)."
        ),
        zone_classes="zone--news",
    )
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)

    articles, feed_errors = load_custodian_articles(per_day_cap=0)
    if feed_errors:
        with st.expander("Some feeds could not be loaded", expanded=False):
            for err in feed_errors:
                st.warning(err)

    st.text_input(
        "Search headlines",
        key="all_custodian_search_input",
        placeholder="Keywords in title, summary, source, or category — all must match",
    )
    search_q = (st.session_state.get("all_custodian_search_input") or "").strip()
    if "_all_custodian_search_q_tracked" not in st.session_state:
        st.session_state._all_custodian_search_q_tracked = search_q
    elif st.session_state._all_custodian_search_q_tracked != search_q:
        st.session_state._all_custodian_search_q_tracked = search_q
        st.session_state.all_custodian_page = 1

    filtered = filter_headlines_by_keyword(articles, search_q)
    n = len(filtered)

    if n == 0:
        st.info("No custody headlines loaded yet." if not articles else "No headlines match your search.")
    else:
        total_pages = max(1, (n + PER_PAGE - 1) // PER_PAGE)
        if "all_custodian_page" not in st.session_state:
            st.session_state.all_custodian_page = 1
        if st.session_state.all_custodian_page > total_pages:
            st.session_state.all_custodian_page = total_pages
        if st.session_state.all_custodian_page < 1:
            st.session_state.all_custodian_page = 1

        page = int(st.session_state.all_custodian_page)
        start = (page - 1) * PER_PAGE
        page_items = filtered[start : start + PER_PAGE]

        st.caption(
            f"Showing {start + 1}–{min(start + PER_PAGE, n)} of {n} headlines · page {page} of {total_pages}"
        )
        st.markdown(build_full_page_market_news_feed_html(page_items), unsafe_allow_html=True)

        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if page > 1 and st.button("← Previous", key="custodian_prev", use_container_width=True):
                st.session_state.all_custodian_page = page - 1
                st.rerun()
        with c3:
            if page < total_pages and st.button("Next →", key="custodian_next", use_container_width=True):
                st.session_state.all_custodian_page = page + 1
                st.rerun()

        st.caption(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC · Global Custodian RSS")

    inner_page_zone_close()
    close_subpage_layout(
        back_href="/?jd_scroll=news",
        back_label="← Back to home (News Hub)",
    )
    render_subpage_footer(label="Custody headlines")


main()
