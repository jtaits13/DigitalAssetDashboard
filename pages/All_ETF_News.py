"""Full ETF/ETP RSS headline list (same layout as All Articles / All Regulatory)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from datetime import datetime, timezone

import streamlit as st

from news_feeds import (
    ETF_ETP_NEWS_FEED_DAY_CAP,
    article_styles_markdown,
    build_full_page_market_news_feed_html,
    filter_headlines_by_keyword,
    load_all_etf_etp_news_cached,
)
from streamlit_site_parity import (
    close_subpage_layout,
    configure_subpage,
    inner_page_zone_open,
    inner_page_zone_close,
    open_subpage_layout,
    render_subpage_back_link,
    render_subpage_footer,
)

PER_PAGE = 20


def main() -> None:
    configure_subpage(
        page_title="ETF & ETP headlines — Digital Assets Dashboard",
        active="etps",
        style_kind="article_etp",
    )
    render_subpage_back_link(
        href="/US_Crypto_ETPs",
        label="← Back to U.S. ETP Overview",
    )
    open_subpage_layout(style_kind="article_etp")
    inner_page_zone_open(
        section_id="etf-news",
        badge="ETP",
        title="ETF/ETP News",
        subtitle=(
            "ETF and ETP-related headlines from crypto and finance news sources. "
            "Up to five ranked stories per UTC day with search and pagination."
        ),
        zone_classes="zone--etp home-zone home-zone--etp",
    )
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)

    articles, feed_errors = load_all_etf_etp_news_cached()
    if feed_errors:
        with st.expander("Some feeds could not be loaded", expanded=False):
            for err in feed_errors:
                st.warning(err)

    st.text_input(
        "Search headlines",
        key="etf_news_search_input",
        placeholder="Keywords in title, summary, or source — all must match",
    )
    search_q = (st.session_state.get("etf_news_search_input") or "").strip()
    if "_etf_news_search_q_tracked" not in st.session_state:
        st.session_state._etf_news_search_q_tracked = search_q
    elif st.session_state._etf_news_search_q_tracked != search_q:
        st.session_state._etf_news_search_q_tracked = search_q
        st.session_state.etf_news_page = 1

    filtered = filter_headlines_by_keyword(articles, search_q)
    n = len(filtered)

    if n == 0:
        if len(articles) == 0:
            st.info("No ETF/ETP headlines loaded yet. Check your network or use **Refresh all data** on the home page.")
        else:
            st.info("No articles match your search. Try different keywords or clear the search box.")
    else:
        total_pages = max(1, (n + PER_PAGE - 1) // PER_PAGE)
        if "etf_news_page" not in st.session_state:
            st.session_state.etf_news_page = 1
        if st.session_state.etf_news_page > total_pages:
            st.session_state.etf_news_page = total_pages
        if st.session_state.etf_news_page < 1:
            st.session_state.etf_news_page = 1

        page = int(st.session_state.etf_news_page)
        start = (page - 1) * PER_PAGE
        page_items = filtered[start : start + PER_PAGE]

        cap_parts = [f"Showing {start + 1}–{min(start + PER_PAGE, n)} of {n} articles"]
        if search_q:
            cap_parts.append(f"(filtered from {len(articles)} total)")
        st.caption(" · ".join(cap_parts))
        st.markdown(build_full_page_market_news_feed_html(page_items), unsafe_allow_html=True)

        if total_pages <= 18:
            num_cols = st.columns(total_pages)
            for p in range(1, total_pages + 1):
                with num_cols[p - 1]:
                    if st.button(
                        str(p),
                        key=f"etf_pgnum_{p}",
                        use_container_width=True,
                        type="primary" if p == page else "secondary",
                    ):
                        st.session_state.etf_news_page = p
                        st.rerun()
        else:
            new_pg = st.number_input(
                "Go to page",
                min_value=1,
                max_value=total_pages,
                value=page,
                step=1,
                key="etf_news_page_input",
            )
            if new_pg != page:
                st.session_state.etf_news_page = new_pg
                st.rerun()

        c_prev, _c_mid, c_next = st.columns([1, 4, 1])
        with c_prev:
            go_prev = st.button("← Prev", disabled=page <= 1, key="etf_news_prev", use_container_width=True)
        with c_next:
            go_next = st.button("Next →", disabled=page >= total_pages, key="etf_news_next", use_container_width=True)
        if go_prev:
            st.session_state.etf_news_page = page - 1
            st.rerun()
        if go_next:
            st.session_state.etf_news_page = page + 1
            st.rerun()

        st.caption(
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
            f"Page {page} of {total_pages} · ETF/ETP headlines · "
            f"up to {ETF_ETP_NEWS_FEED_DAY_CAP}/UTC day in pipeline"
        )

    inner_page_zone_close()
    close_subpage_layout(
        back_href="/US_Crypto_ETPs",
        back_label="← Back to U.S. ETP Overview",
    )
    render_subpage_footer(label="ETF/ETP News")


main()
