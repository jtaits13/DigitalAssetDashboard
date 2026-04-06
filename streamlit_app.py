"""
JPM Digital — crypto & digital asset news (RSS aggregation).
Deploy on Streamlit Community Cloud with this file as the main entrypoint.
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from news_feeds import (
    DEFAULT_FEEDS,
    HOME_MAIN_HEADING_CSS,
    article_styles_markdown,
    dedupe_articles,
    load_all_feeds,
    render_article_card_html,
    render_home_top_bar,
)
from price_ticker import fetch_top_crypto_tickers, show_price_ticker
from crypto_etps.widgets import (
    clear_crypto_etp_cache,
    get_etp_user_agent_from_secrets,
    show_us_crypto_etps_widget,
)
from regulatory_news.client import load_regulatory_articles
from regulatory_news.widgets import clear_regulatory_cache, show_regulatory_headlines_widget
from rwa_league.widgets import clear_rwa_league_cache, show_rwa_league_widget

HOME_HEADLINE_COUNT = 5

# Home page: shared heading style is HOME_MAIN_HEADING_CSS (news_feeds.py).
HOME_PAGE_EXTRA_CSS = ""


def main() -> None:
    st.set_page_config(
        page_title="JPM Digital — Crypto News",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Returning to home resets All Articles / All Regulatory pagination.
    st.session_state.all_news_page = 1
    st.session_state.all_regulatory_page = 1

    render_home_top_bar("landing")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(HOME_MAIN_HEADING_CSS + HOME_PAGE_EXTRA_CSS, unsafe_allow_html=True)
    show_price_ticker()

    with st.sidebar:
        st.header("Sources")
        st.caption("RSS feeds aggregated on refresh. Add your own in the repo.")
        if st.button("All articles →", use_container_width=True):
            st.switch_page("pages/All_Articles.py")
        if st.button("All regulatory headlines →", use_container_width=True):
            st.switch_page("pages/All_Regulatory.py")
        refresh = st.button("Refresh feeds", use_container_width=True)

    if refresh:
        import news_feeds

        news_feeds.fetch_feed.clear()
        fetch_top_crypto_tickers.clear()
        clear_regulatory_cache()
        clear_crypto_etp_cache()
        clear_rwa_league_cache()
        st.rerun()

    articles, feed_errors = load_all_feeds(DEFAULT_FEEDS)
    regulatory_articles, regulatory_errors = load_regulatory_articles()

    if feed_errors:
        with st.expander("Some feeds could not be loaded", expanded=False):
            for err in feed_errors:
                st.warning(err)

    if regulatory_errors:
        with st.expander("Some regulatory feeds could not be loaded", expanded=False):
            for err in regulatory_errors:
                st.warning(err)

    if not articles:
        st.info("No articles loaded. Check your network or RSS URLs in `news_feeds.py`.")
        col_news, col_sec = st.columns([1.15, 1], gap="large")
        with col_news:
            st.caption("Headlines will appear here when feeds load.")
        with col_sec:
            show_regulatory_headlines_widget(regulatory_articles)
        show_us_crypto_etps_widget(get_etp_user_agent_from_secrets())
        show_rwa_league_widget()
        st.caption(
            f"Last built at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
            "Prices: CoinGecko or CoinCap · Regulatory headlines: official & secondary RSS · "
            "Crypto ETPs: StockAnalysis.com list · "
            "Headlines: original publishers."
        )
        return

    unique = dedupe_articles(articles, max_items=None)
    top = unique[:HOME_HEADLINE_COUNT]

    # News (left) and regulatory headlines (right).
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
        show_regulatory_headlines_widget(regulatory_articles)

    show_us_crypto_etps_widget(get_etp_user_agent_from_secrets())
    show_rwa_league_widget()

    st.divider()
    st.caption(
        f"Last built at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "Prices & 24h % from CoinGecko (fallback: CoinCap) · "
        "Regulatory headlines: SEC, FCA, ECB, Federal Reserve, CoinDesk, Decrypt (filtered) · "
        "Crypto ETP list via StockAnalysis.com (optional STOCKANALYSIS_USER_AGENT) · "
        "Headlines link to original publishers."
    )


if __name__ == "__main__":
    main()
