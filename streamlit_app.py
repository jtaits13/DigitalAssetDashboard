"""
JPM Digital — crypto & digital asset news (RSS aggregation).
Deploy on Streamlit Community Cloud with this file as the main entrypoint.
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st
import streamlit.components.v1 as components

from home_layout import HOME_PAGE_LAYOUT_CSS, section_label_teal
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

HOME_PAGE_EXTRA_CSS = ""

_JD_SCROLL_MAP = {"news": "jd-section-news", "market": "jd-section-market"}


def _jd_consume_scroll_query() -> None:
    """Map ?jd_scroll=news|market from top-nav HTML links into session state; strip param from URL."""
    if "jd_scroll" not in st.query_params:
        return
    raw = st.query_params["jd_scroll"]
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    key = str(raw).strip().lower()
    if key in _JD_SCROLL_MAP:
        st.session_state["jd_scroll_to"] = _JD_SCROLL_MAP[key]
    try:
        del st.query_params["jd_scroll"]
    except KeyError:
        pass


def _jd_inject_scroll_to_section() -> None:
    """Scroll to anchor after home body renders (?jd_scroll= from top nav links)."""
    target = st.session_state.pop("jd_scroll_to", None)
    if not target:
        return
    safe = "".join(c for c in target if c.isalnum() or c in "-_")
    if safe != target:
        return
    components.html(
        f"""
<script>
(function() {{
  const p = window.parent;
  const id = "{safe}";
  function go() {{
    const el = p.document.getElementById(id);
    if (el) {{
      el.scrollIntoView({{ block: "start", behavior: "auto" }});
      return true;
    }}
    return false;
  }}
  let n = 0;
  const t = p.setInterval(function () {{
    if (go() || n++ > 50) p.clearInterval(t);
  }}, 40);
}})();
</script>
""",
        height=0,
        width=0,
    )


def _feed_status_expanders(feed_errors: list[str], regulatory_errors: list[str]) -> None:
    if not feed_errors and not regulatory_errors:
        return
    with st.expander("Feed status", expanded=False):
        if feed_errors:
            st.caption("News RSS")
            for err in feed_errors:
                st.warning(err)
        if regulatory_errors:
            st.caption("Regulatory RSS")
            for err in regulatory_errors:
                st.warning(err)


def _sidebar() -> bool:
    """Returns True if refresh clicked."""
    with st.sidebar:
        st.markdown("### JPM Digital")
        st.caption("Markets, policy, and on-chain market data.")
        st.divider()
        st.markdown("**Pages**")
        if st.button("All articles", use_container_width=True, key="sb_articles"):
            st.switch_page("pages/All_Articles.py")
        if st.button("Regulatory headlines", use_container_width=True, key="sb_reg"):
            st.switch_page("pages/All_Regulatory.py")
        st.divider()
        st.caption("Refresh reloads RSS, prices, ETPs, regulatory feeds, and RWA tables.")
        refresh = st.button("Refresh all data", use_container_width=True, key="sb_refresh")
    return bool(refresh)


def _footer_line() -> None:
    st.caption(
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC · "
        "CoinGecko/CoinCap · RSS · StockAnalysis · RWA.xyz embed"
    )


def main() -> None:
    st.set_page_config(
        page_title="JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.session_state.all_news_page = 1
    st.session_state.all_regulatory_page = 1

    _jd_consume_scroll_query()

    render_home_top_bar("landing", is_landing=True)
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(
        HOME_MAIN_HEADING_CSS + HOME_PAGE_LAYOUT_CSS + HOME_PAGE_EXTRA_CSS,
        unsafe_allow_html=True,
    )
    show_price_ticker()

    refresh = _sidebar()
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

    _feed_status_expanders(feed_errors, regulatory_errors)

    if not articles:
        st.info("No articles loaded. Check your network or RSS URLs in `news_feeds.py`.")
        st.markdown(
            '<div id="jd-section-news" style="scroll-margin-top: 5.5rem;"></div>',
            unsafe_allow_html=True,
        )
        st.markdown(section_label_teal("News & Regulatory"), unsafe_allow_html=True)
        col_news, col_sec = st.columns([1.2, 1], gap="large")
        with col_news:
            st.caption("Headlines will appear here when feeds load.")
        with col_sec:
            show_regulatory_headlines_widget(regulatory_articles)

        st.divider()
        st.markdown(
            '<div id="jd-section-market" style="scroll-margin-top: 5.5rem;"></div>',
            unsafe_allow_html=True,
        )
        st.markdown(section_label_teal("Market Data"), unsafe_allow_html=True)
        col_etp, col_rwa = st.columns([1.2, 1], gap="large")
        with col_etp:
            show_us_crypto_etps_widget(get_etp_user_agent_from_secrets())
        with col_rwa:
            show_rwa_league_widget()

        st.divider()
        _footer_line()
        _jd_inject_scroll_to_section()
        return

    unique = dedupe_articles(articles, max_items=None)
    top = unique[:HOME_HEADLINE_COUNT]

    st.markdown(
        '<div id="jd-section-news" style="scroll-margin-top: 5.5rem;"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(section_label_teal("News & Regulatory"), unsafe_allow_html=True)
    col_news, col_sec = st.columns([1.2, 1], gap="large")
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

    st.divider()
    st.markdown(
        '<div id="jd-section-market" style="scroll-margin-top: 5.5rem;"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(section_label_teal("Market Data"), unsafe_allow_html=True)
    col_etp, col_rwa = st.columns([1.2, 1], gap="large")
    with col_etp:
        show_us_crypto_etps_widget(get_etp_user_agent_from_secrets())
    with col_rwa:
        show_rwa_league_widget()

    st.divider()
    _footer_line()
    _jd_inject_scroll_to_section()


if __name__ == "__main__":
    main()
