"""Full regulatory headlines list with pagination and day grouping."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from datetime import datetime, timezone

import streamlit as st

from news_feeds import (
    article_styles_markdown,
    build_full_page_regulatory_feed_html,
    filter_headlines_by_keyword,
)
from regulatory_news.client import REGULATORY_HEADLINES_PER_UTC_DAY, load_regulatory_articles
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
        page_title="All regulatory headlines — Digital Assets Dashboard",
        active="news",
        style_kind="article",
    )
    render_subpage_back_link(
        href="/?jd_scroll=news",
        label="← Back to home (News Hub)",
    )
    open_subpage_layout(style_kind="article")
    inner_page_zone_open(
        section_id="all-regulatory",
        badge="NEWS",
        title="All regulatory headlines",
        subtitle=(
            "Digital-asset regulatory and policy headlines from regulator, central-bank, and news feeds. "
            f"Up to five ranked stories per UTC day; {PER_PAGE} per page with search."
        ),
        zone_classes="zone--news",
    )
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)

    articles, feed_errors = load_regulatory_articles()
    if feed_errors:
        with st.expander("Some feeds could not be loaded", expanded=False):
            for err in feed_errors:
                st.warning(err)

    st.text_input(
        "Search headlines",
        key="all_regulatory_search_input",
        placeholder="Keywords in title, summary, source, or region — all must match",
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
    else:
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
        st.markdown(build_full_page_regulatory_feed_html(page_items), unsafe_allow_html=True)

        c_prev, _c_mid, c_next = st.columns([1, 4, 1])
        with c_prev:
            go_prev = st.button("← Prev", disabled=page <= 1, key="reg_prev", use_container_width=True)
        with c_next:
            go_next = st.button("Next →", disabled=page >= total_pages, key="reg_next", use_container_width=True)
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
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
            f"Page {page} of {total_pages} · All regulatory headlines · "
            f"up to {REGULATORY_HEADLINES_PER_UTC_DAY}/UTC day on hub"
        )

    inner_page_zone_close()
    close_subpage_layout(
        back_href="/?jd_scroll=news",
        back_label="← Back to home (News Hub)",
    )
    render_subpage_footer(label="Regulatory headlines")


main()
