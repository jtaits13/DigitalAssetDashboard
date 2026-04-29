"""Full ETF/ETP RSS headline list (same layout as All Articles / All Regulatory)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from datetime import datetime, timezone
from html import escape

import streamlit as st

from home_layout import (
    section_label_teal,
    subpage_footer_heading_html,
    subpage_footnote_html,
    subpage_toolbar_note_html,
)
from news_feeds import (
    ETP_NEWS_FEEDS,
    app_shared_layout_css,
    article_styles_markdown,
    build_full_page_market_news_feed_html,
    cap_market_news_per_day,
    filter_headlines_by_keyword,
    load_all_etf_etp_news_cached,
    render_subpage_sidebar,
    render_subpage_top_bar,
)
try:
    from price_ticker import show_price_ticker
except Exception:
    def show_price_ticker() -> None:
        return

PER_PAGE = 20
MAX_HEADLINES_PER_DAY = 7
_ETF_ONLY_RE = re.compile(r"\b(etf|etfs|exchange[-\s]traded\s+funds?)\b", re.I)


def _is_etf_only_item(item: dict) -> bool:
    blob = " ".join(
        str(x or "")
        for x in (
            item.get("title"),
            item.get("summary"),
            item.get("source"),
        )
    )
    return _ETF_ONLY_RE.search(blob) is not None


def main() -> None:
    st.set_page_config(
        page_title="ETF & ETP Market News — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Back", key="top_back_etf_news"):
        st.switch_page("pages/US_Crypto_ETPs.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="all_etf_news", current="etf_news")

    st.markdown(
        section_label_teal("ETF & ETP Market News", placement="first"),
        unsafe_allow_html=True,
    )
    _feed_name_list = ", ".join(n for n, _ in ETP_NEWS_FEEDS)
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">Headlines from major crypto RSS sources plus ETF/issuer feeds, '
        "filtered for <strong>ETF/ETP-focused</strong> stories. "
        "Use search and pagination to browse results. The list covers the <strong>last three calendar months</strong> (UTC). "
        "RSS feeds typically publish only recent posts, and <strong>Google News</strong> adds coverage but is still not a complete archive. "
        f"Sources: {escape(_feed_name_list)}.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    articles, feed_errors = load_all_etf_etp_news_cached()
    if feed_errors:
        with st.expander("Some feeds could not be loaded", expanded=False):
            for err in feed_errors:
                st.warning(err)

    st.text_input(
        "Search headlines",
        key="etf_news_search_input",
        placeholder="Keywords in title, summary, or source — separate with spaces (all must match)",
    )
    search_q = (st.session_state.get("etf_news_search_input") or "").strip()
    if "_etf_news_search_q_tracked" not in st.session_state:
        st.session_state._etf_news_search_q_tracked = search_q
    elif st.session_state._etf_news_search_q_tracked != search_q:
        st.session_state._etf_news_search_q_tracked = search_q
        st.session_state.etf_news_page = 1

    etf_only_articles = [a for a in articles if _is_etf_only_item(a)]
    etf_only_articles = cap_market_news_per_day(etf_only_articles, max_per_day=MAX_HEADLINES_PER_DAY)

    filtered = filter_headlines_by_keyword(etf_only_articles, search_q)
    n = len(filtered)
    if n == 0:
        if len(etf_only_articles) == 0:
            st.info("No matching ETF/ETP headlines yet. Check your network or use **Refresh all data** on the home page.")
        else:
            st.info("No articles match your search. Try different keywords or clear the search box.")
        return

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
        cap_parts.append(f"(filtered from {len(etf_only_articles)} total)")
    st.markdown(subpage_toolbar_note_html(" · ".join(cap_parts)), unsafe_allow_html=True)

    st.markdown(build_full_page_market_news_feed_html(page_items), unsafe_allow_html=True)

    st.divider()
    st.markdown(subpage_footer_heading_html("Pages"), unsafe_allow_html=True)

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

    c_prev, c_mid, c_next = st.columns([1, 4, 1])
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

    st.divider()
    st.markdown(
        subpage_footnote_html(
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
            f"Page {page} of {total_pages} · ETF/ETP RSS (filtered)"
        ),
        unsafe_allow_html=True,
    )


main()
