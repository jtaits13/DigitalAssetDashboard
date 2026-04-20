"""Full regulatory headlines list with pagination and day grouping."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape

import streamlit as st

from home_layout import section_label_teal
from news_feeds import (
    app_shared_layout_css,
    article_day_key,
    article_styles_markdown,
    filter_headlines_by_keyword,
    format_article_day_label,
    render_subpage_top_bar,
)
from price_ticker import show_price_ticker
from regulatory_news.client import load_regulatory_articles
from regulatory_news.widgets import render_regulatory_card_html

PER_PAGE = 20


def main() -> None:
    st.set_page_config(
        page_title="Regulatory headlines — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Home", key="top_home_regulatory"):
        st.switch_page("streamlit_app.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    show_price_ticker()

    with st.sidebar:
        st.header("Navigation")
        st.caption("Digital-asset regulatory stories from aggregated RSS feeds.")

    st.markdown(
        section_label_teal("Regulatory & Legal Headlines", placement="first"),
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="jd-hub-dek">Digital-asset regulatory and legal stories from aggregated RSS feeds — search and '
        "paginate the full list.</p>",
        unsafe_allow_html=True,
    )

    articles, feed_errors = load_regulatory_articles()
    if feed_errors:
        with st.expander("Some feeds could not be loaded", expanded=False):
            for err in feed_errors:
                st.warning(err)

    st.text_input(
        "Search headlines",
        key="all_regulatory_search_input",
        placeholder="Keywords in title, summary, source, or region — separate with spaces (all must match)",
    )
    search_q = (st.session_state.get("all_regulatory_search_input") or "").strip()
    if "_all_regulatory_search_q_tracked" not in st.session_state:
        st.session_state._all_regulatory_search_q_tracked = search_q
    elif st.session_state._all_regulatory_search_q_tracked != search_q:
        st.session_state._all_regulatory_search_q_tracked = search_q
        st.session_state.all_regulatory_page = 1

    filtered = filter_headlines_by_keyword(articles, search_q)
    n = len(filtered)
    if n == 0:
        if len(articles) == 0:
            st.info("No headlines matched the filters yet. Check your network or try again later.")
        else:
            st.info("No headlines match your search. Try different keywords or clear the search box.")
        return

    total_pages = max(1, (n + PER_PAGE - 1) // PER_PAGE)

    if "all_regulatory_page" not in st.session_state:
        st.session_state.all_regulatory_page = 1
    if st.session_state.all_regulatory_page > total_pages:
        st.session_state.all_regulatory_page = total_pages
    if st.session_state.all_regulatory_page < 1:
        st.session_state.all_regulatory_page = 1

    page = int(st.session_state.all_regulatory_page)
    start = (page - 1) * PER_PAGE
    page_items = filtered[start : start + PER_PAGE]

    cap_parts = [f"Showing {start + 1}–{min(start + PER_PAGE, n)} of {n} headlines"]
    if search_q:
        cap_parts.append(f"(filtered from {len(articles)} total)")
    st.caption(" · ".join(cap_parts))

    prev_day_key = None
    for item in page_items:
        pub = item.get("published")
        dk = article_day_key(pub if isinstance(pub, datetime) else None)
        if dk != prev_day_key:
            if prev_day_key is not None:
                st.markdown('<div class="day-sep"></div>', unsafe_allow_html=True)
            label = format_article_day_label(pub if isinstance(pub, datetime) else None)
            st.markdown(f'<p class="day-label">{escape(label)}</p>', unsafe_allow_html=True)
            prev_day_key = dk

        st.markdown(render_regulatory_card_html(item), unsafe_allow_html=True)

    st.divider()
    st.markdown("**Pages**")
    c_prev, _c_mid, c_next = st.columns([1, 4, 1])
    with c_prev:
        go_prev = st.button("← Prev", disabled=page <= 1, key="reg_prev")
    with c_next:
        go_next = st.button("Next →", disabled=page >= total_pages, key="reg_next")

    if go_prev:
        st.session_state.all_regulatory_page = page - 1
        st.rerun()
    if go_next:
        st.session_state.all_regulatory_page = page + 1
        st.rerun()

    if total_pages <= 18:
        num_cols = st.columns(total_pages)
        for p in range(1, total_pages + 1):
            with num_cols[p - 1]:
                if st.button(
                    str(p),
                    key=f"reg_pgnum_{p}",
                    use_container_width=True,
                    type="primary" if p == page else "secondary",
                ):
                    st.session_state.all_regulatory_page = p
                    st.rerun()
    else:
        new_pg = st.number_input(
            "Go to page",
            min_value=1,
            max_value=total_pages,
            value=page,
            step=1,
            key="reg_page_input",
        )
        if new_pg != page:
            st.session_state.all_regulatory_page = new_pg
            st.rerun()

    st.caption(
        f"Last built at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        f"Page {page} of {total_pages}"
    )


main()
