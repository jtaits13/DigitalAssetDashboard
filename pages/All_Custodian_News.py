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
from home_layout import (
    section_label_teal,
    subpage_footer_heading_html,
    subpage_footnote_html,
    subpage_toolbar_note_html,
)
from news_feeds import (
    app_shared_layout_css,
    article_styles_markdown,
    build_full_page_market_news_feed_html,
    filter_headlines_by_keyword,
    render_subpage_top_bar,
)

PER_PAGE = 20


def main() -> None:
    st.set_page_config(
        page_title="All custody headlines — Digital Assets Dashboard",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    render_subpage_top_bar(active="news")
    if st.button("← Back to home (News Hub)", key="top_home_custodian"):
        st.switch_page("streamlit_app.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)

    st.markdown(
        section_label_teal("All custody headlines", placement="first"),
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">'
        "Crypto and digital-asset stories from "
        '<a href="https://www.globalcustodian.com/" target="_blank" rel="noopener noreferrer">Global Custodian</a> '
        "(digital-asset category RSS plus site search). "
        f"Up to <strong>{CUSTODIAN_HEADLINES_PER_UTC_DAY}</strong> ranked headlines per UTC day on the home rail; "
        f"this page lists the full archive (<strong>{PER_PAGE}</strong> per page).</p>",
        unsafe_allow_html=True,
    )
    st.divider()

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
        return

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

    st.markdown(
        subpage_toolbar_note_html(
            f"Showing {start + 1}–{min(start + PER_PAGE, n)} of {n} headlines · page {page} of {total_pages}"
        ),
        unsafe_allow_html=True,
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

    st.markdown(subpage_footer_heading_html("End of page"), unsafe_allow_html=True)
    st.markdown(subpage_footnote_html(), unsafe_allow_html=True)
    st.caption(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC · Global Custodian RSS")


if __name__ == "__main__":
    main()
