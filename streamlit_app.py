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

HOME_HEADLINE_COUNT = 5


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
        st.rerun()

    col_title, col_tag = st.columns([3, 1])
    with col_title:
        st.title("Digital asset & crypto news")
    with col_tag:
        st.caption("Aggregated headlines · RSS")

    articles, feed_errors = load_all_feeds(DEFAULT_FEEDS)

    if feed_errors:
        with st.expander("Some feeds could not be loaded", expanded=False):
            for err in feed_errors:
                st.warning(err)

    if not articles:
        st.info("No articles loaded. Check your network or RSS URLs in `news_feeds.py`.")
        st.caption(
            f"Last built at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
            "Prices: CoinGecko or CoinCap · Headlines: original publishers."
        )
        return

    unique = dedupe_articles(articles, max_items=None)
    top = unique[:HOME_HEADLINE_COUNT]

    for item in top:
        st.markdown(render_article_card_html(item), unsafe_allow_html=True)

    if len(unique) > HOME_HEADLINE_COUNT:
        if st.button("See more", use_container_width=False, type="primary"):
            st.switch_page("pages/All_Articles.py")
    else:
        st.caption("No additional articles beyond this list.")

    st.divider()
    st.caption(
        f"Last built at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "Prices & 24h % from CoinGecko (fallback: CoinCap) · Headlines link to original publishers."
    )


if __name__ == "__main__":
    main()
