"""Full article list with pagination and day grouping."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from datetime import datetime, timezone

import streamlit as st

from home_layout import (
    section_label_teal,
    subpage_footer_heading_html,
    subpage_footnote_html,
    subpage_toolbar_note_html,
)
from news_feeds import (
    ALL_ARTICLES_FEEDS,
    ALL_ARTICLES_FEED_DAY_CAP,
    ALL_ARTICLES_PER_PAGE,
    app_shared_layout_css,
    article_styles_markdown,
    build_full_page_market_news_feed_html,
    cap_market_news_per_day,
    dedupe_articles,
    filter_headlines_by_keyword,
    load_all_feeds,
    render_subpage_sidebar,
    render_subpage_top_bar,
)
try:
    from price_ticker import show_price_ticker
except Exception:
    def show_price_ticker() -> None:
        return

PER_PAGE = ALL_ARTICLES_PER_PAGE


def main() -> None:
    st.set_page_config(
        page_title="All digital asset headlines — Digital Assets Dashboard",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Back to home (News & Regulatory)", key="top_home_articles"):
        st.switch_page("streamlit_app.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="all_articles", current="articles")

    st.markdown(
        section_label_teal("All digital asset headlines", placement="first"),
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">'
        "Same <strong>All articles</strong> feed bundle as the static export (core crypto RSS plus supplemental Google News searches). "
        f"After deduplication, the session keeps <strong>up to {ALL_ARTICLES_FEED_DAY_CAP}</strong> ranked headlines "
        "<strong>per UTC calendar day</strong>, "
        "matching regulatory headline density. How far back the list goes depends on the feeds—there is no fixed monthly cutoff "
        f"or export ceiling. <strong>{PER_PAGE}</strong> headlines per page. "
        "Each search token must appear in the title, summary, or source (all tokens required).</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    articles, feed_errors = load_all_feeds(ALL_ARTICLES_FEEDS)
    if feed_errors:
        with st.expander("Some feeds could not be loaded", expanded=False):
            for err in feed_errors:
                st.warning(err)

    st.text_input(
        "Search headlines",
        key="all_news_search_input",
        placeholder="Keywords in title, summary, or source — all must match",
    )
    search_q = (st.session_state.get("all_news_search_input") or "").strip()
    if "_all_news_search_q_tracked" not in st.session_state:
        st.session_state._all_news_search_q_tracked = search_q
    elif st.session_state._all_news_search_q_tracked != search_q:
        st.session_state._all_news_search_q_tracked = search_q
        st.session_state.all_news_page = 1

    unique = dedupe_articles(articles, max_items=None)
    unique = cap_market_news_per_day(unique, max_per_day=ALL_ARTICLES_FEED_DAY_CAP)
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

    cap_parts = [
        f"Showing {start + 1}–{min(start + PER_PAGE, n)} of {n} articles",
    ]
    if search_q:
        cap_parts.append(f"(filtered from {len(unique)} total)")
    st.markdown(subpage_toolbar_note_html(" · ".join(cap_parts)), unsafe_allow_html=True)

    st.markdown(build_full_page_market_news_feed_html(page_items), unsafe_allow_html=True)

    st.divider()
    st.markdown(subpage_footer_heading_html("Pages"), unsafe_allow_html=True)

    c_prev, _c_mid, c_next = st.columns([1, 4, 1])
    with c_prev:
        go_prev = st.button("← Prev", disabled=page <= 1, key="all_prev", use_container_width=True)
    with c_next:
        go_next = st.button("Next →", disabled=page >= total_pages, key="all_next", use_container_width=True)

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

    st.divider()
    st.markdown(
        subpage_footnote_html(
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
            f"Page {page} of {total_pages} · All digital asset headlines"
        ),
        unsafe_allow_html=True,
    )


main()
