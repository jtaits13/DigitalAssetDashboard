"""Full article list with pagination and day grouping."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape

import streamlit as st

from news_feeds import (
    DEFAULT_FEEDS,
    app_shared_layout_css,
    article_day_key,
    article_styles_markdown,
    dedupe_articles,
    filter_headlines_by_keyword,
    format_article_day_label,
    load_all_feeds,
    render_article_card_html,
    render_subpage_top_bar,
)
from price_ticker import show_price_ticker

PER_PAGE = 20


def main() -> None:
    st.set_page_config(
        page_title="All articles — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Home", key="top_home_articles"):
        st.switch_page("streamlit_app.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    show_price_ticker()

    with st.sidebar:
        st.header("Navigation")
        st.caption("All stories from aggregated RSS feeds.")

    st.markdown(
        '<h1 class="home-main-heading">All News Articles</h1>',
        unsafe_allow_html=True,
    )

    articles, feed_errors = load_all_feeds(DEFAULT_FEEDS)
    if feed_errors:
        with st.expander("Some feeds could not be loaded", expanded=False):
            for err in feed_errors:
                st.warning(err)

    st.text_input(
        "Search headlines",
        key="all_news_search_input",
        placeholder="Keywords in title, summary, or source — separate with spaces (all must match)",
    )
    search_q = (st.session_state.get("all_news_search_input") or "").strip()
    if "_all_news_search_q_tracked" not in st.session_state:
        st.session_state._all_news_search_q_tracked = search_q
    elif st.session_state._all_news_search_q_tracked != search_q:
        st.session_state._all_news_search_q_tracked = search_q
        st.session_state.all_news_page = 1

    unique = dedupe_articles(articles, max_items=None)
    filtered = filter_headlines_by_keyword(unique, search_q)
    n = len(filtered)
    if n == 0:
        if len(unique) == 0:
            st.info("No articles loaded yet.")
        else:
            st.info("No articles match your search. Try different keywords or clear the search box.")
        return

    total_pages = max(1, (n + PER_PAGE - 1) // PER_PAGE)

    if "all_news_page" not in st.session_state:
        st.session_state.all_news_page = 1
    if st.session_state.all_news_page > total_pages:
        st.session_state.all_news_page = total_pages
    if st.session_state.all_news_page < 1:
        st.session_state.all_news_page = 1

    page = int(st.session_state.all_news_page)
    start = (page - 1) * PER_PAGE
    page_items = filtered[start : start + PER_PAGE]

    cap_parts = [f"Showing {start + 1}–{min(start + PER_PAGE, n)} of {n} articles"]
    if search_q:
        cap_parts.append(f"(filtered from {len(unique)} total)")
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

        st.markdown(render_article_card_html(item), unsafe_allow_html=True)

    st.divider()
    st.markdown("**Pages**")
    c_prev, c_mid, c_next = st.columns([1, 4, 1])
    with c_prev:
        go_prev = st.button("← Prev", disabled=page <= 1, key="all_prev")
    with c_next:
        go_next = st.button("Next →", disabled=page >= total_pages, key="all_next")

    if go_prev:
        st.session_state.all_news_page = page - 1
        st.rerun()
    if go_next:
        st.session_state.all_news_page = page + 1
        st.rerun()

    if total_pages <= 18:
        num_cols = st.columns(total_pages)
        for p in range(1, total_pages + 1):
            with num_cols[p - 1]:
                if st.button(
                    str(p),
                    key=f"pgnum_{p}",
                    use_container_width=True,
                    type="primary" if p == page else "secondary",
                ):
                    st.session_state.all_news_page = p
                    st.rerun()
    else:
        new_pg = st.number_input(
            "Go to page",
            min_value=1,
            max_value=total_pages,
            value=page,
            step=1,
            key="all_page_input",
        )
        if new_pg != page:
            st.session_state.all_news_page = new_pg
            st.rerun()

    st.caption(
        f"Last built at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        f"Page {page} of {total_pages}"
    )


main()
