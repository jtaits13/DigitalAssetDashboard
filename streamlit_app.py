"""
JPM Digital — crypto & digital asset news (RSS aggregation).
Deploy on Streamlit Community Cloud with this file as the main entrypoint.
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from news_feeds import (
    DEFAULT_FEEDS,
    article_styles_markdown,
    dedupe_articles,
    load_all_feeds,
    render_article_card_html,
    render_home_top_bar,
)
from price_ticker import fetch_top_crypto_tickers, show_price_ticker
from sec_filings.widgets import (
    clear_fund_filings_cache,
    get_user_agent_from_secrets,
    show_sec_fund_filings_widget,
)

HOME_HEADLINE_COUNT = 5

# Home page only: compact heading + left-aligned “widget” width (CoinDesk-style column).
HOME_PAGE_EXTRA_CSS = """
<style>
h2.home-main-heading {
    font-size: 1.2rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 0.15rem 0;
    letter-spacing: -0.02em;
    line-height: 1.25;
}
</style>
"""


def main() -> None:
    st.set_page_config(
        page_title="JPM Digital — Crypto News",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Returning to home resets All Articles pagination so the next visit starts at page 1.
    st.session_state.all_news_page = 1

    render_home_top_bar("landing")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(HOME_PAGE_EXTRA_CSS, unsafe_allow_html=True)
    show_price_ticker()

    with st.sidebar:
        st.header("Sources")
        st.caption("RSS feeds aggregated on refresh. Add your own in the repo.")
        if st.button("All articles →", use_container_width=True):
            st.switch_page("pages/All_Articles.py")
        refresh = st.button("Refresh feeds", use_container_width=True)

    if refresh:
        import news_feeds

        news_feeds.fetch_feed.clear()
        fetch_top_crypto_tickers.clear()
        clear_fund_filings_cache()
        st.rerun()

    articles, feed_errors = load_all_feeds(DEFAULT_FEEDS)

    if feed_errors:
        with st.expander("Some feeds could not be loaded", expanded=False):
            for err in feed_errors:
                st.warning(err)

    if not articles:
        st.info("No articles loaded. Check your network or RSS URLs in `news_feeds.py`.")
        col_news, col_sec = st.columns([1.15, 1], gap="large")
        with col_news:
            st.caption("Headlines will appear here when feeds load.")
        with col_sec:
            show_sec_fund_filings_widget(get_user_agent_from_secrets())
        st.caption(
            f"Last built at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
            "Prices: CoinGecko or CoinCap · SEC widget: EDGAR full-text search · "
            "Headlines: original publishers."
        )
        return

    unique = dedupe_articles(articles, max_items=None)
    top = unique[:HOME_HEADLINE_COUNT]

    # News (left) and SEC fund filings widget (right).
    col_news, col_sec = st.columns([1.15, 1], gap="large")
    with col_news:
        st.markdown(
            '<h2 class="home-main-heading">Latest Digital Asset News</h2>',
            unsafe_allow_html=True,
        )

        if len(unique) > HOME_HEADLINE_COUNT:
            if st.button(
                "See more news",
                key="see_more_news_top",
                use_container_width=True,
                type="primary",
            ):
                st.switch_page("pages/All_Articles.py")

        for item in top:
            st.markdown(render_article_card_html(item), unsafe_allow_html=True)

        if len(unique) <= HOME_HEADLINE_COUNT:
            st.caption("No additional articles beyond this list.")

    with col_sec:
        show_sec_fund_filings_widget(get_user_agent_from_secrets())

    st.divider()
    st.caption(
        f"Last built at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "Prices & 24h % from CoinGecko (fallback: CoinCap) · "
        "SEC fund filings via EDGAR full-text search (set SEC_EDGAR_USER_AGENT per SEC guidance) · "
        "Headlines link to original publishers."
    )


if __name__ == "__main__":
    main()
