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
    build_home_news_column_html,
    dedupe_articles,
    load_all_feeds,
    render_home_top_bar,
)
from price_ticker import fetch_top_crypto_tickers, show_price_ticker
from crypto_etps.widgets import (
    clear_crypto_etp_cache,
    get_etp_user_agent_from_secrets,
    show_us_crypto_etps_widget,
)
from regulatory_news.client import load_regulatory_articles
from regulatory_news.widgets import build_home_regulatory_column_html, clear_regulatory_cache
from rwa_league.widgets import clear_rwa_league_cache, show_rwa_league_widget

HOME_HEADLINE_COUNT = 3
HOME_REGULATORY_PREVIEW = 3

HOME_PAGE_EXTRA_CSS = ""

_JD_SCROLL_MAP = {
    "news": "jd-section-news",
    "market": "jd-section-market",
    "etps": "jd-section-etps",
    "rwa": "jd-section-rwa",
}


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
        if st.button("U.S. Crypto ETPs", use_container_width=True, key="sb_etp"):
            st.switch_page("pages/US_Crypto_ETPs.py")
        if st.button("RWA league table", use_container_width=True, key="sb_rwa"):
            st.switch_page("pages/RWA_League.py")
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
        st.markdown(
            '<p class="jd-hub-dek">A quick read of headlines and policy wires — each section links to a full page.</p>',
            unsafe_allow_html=True,
        )
        col_news, col_sec = st.columns([1.2, 1], gap="large")
        with col_news:
            st.markdown(
                '<div class="jd-news-column-shell"><div class="jd-news-column-inner">'
                '<p class="jd-news-column-footnote">Headlines will appear here when feeds load.</p>'
                "</div></div>",
                unsafe_allow_html=True,
            )
        with col_sec:
            st.markdown(
                build_home_regulatory_column_html(
                    regulatory_articles,
                    max_items=HOME_REGULATORY_PREVIEW,
                ),
                unsafe_allow_html=True,
            )
        if len(regulatory_articles) > HOME_REGULATORY_PREVIEW:
            b_news, b_reg = st.columns([1.2, 1], gap="large")
            with b_news:
                st.empty()
            with b_reg:
                if st.button(
                    "Explore all headlines →",
                    key="see_more_regulatory_bottom_empty_feed",
                    use_container_width=True,
                    type="primary",
                ):
                    st.switch_page("pages/All_Regulatory.py")
                st.markdown(
                    '<p class="jd-hub-cta-note">Full regulatory feed on the next page.</p>',
                    unsafe_allow_html=True,
                )

        st.divider()
        st.markdown(
            '<div id="jd-section-market" style="scroll-margin-top: 5.5rem;"></div>',
            unsafe_allow_html=True,
        )
        st.markdown(section_label_teal("Markets & On-chain"), unsafe_allow_html=True)
        st.markdown(
            '<p class="jd-hub-dek">Spot ETPs and tokenized network league data — previews below; open each page for search and full tables.</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div id="jd-section-etps" style="scroll-margin-top: 5.5rem;"></div>',
            unsafe_allow_html=True,
        )
        show_us_crypto_etps_widget(
            get_etp_user_agent_from_secrets(),
            home_preview=True,
        )

        st.divider()
        st.markdown(
            '<div id="jd-section-rwa" style="scroll-margin-top: 5.5rem;"></div>',
            unsafe_allow_html=True,
        )
        show_rwa_league_widget(home_preview=True)

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
    st.markdown(
        '<p class="jd-hub-dek">Headlines from major crypto RSS feeds and global regulatory wires — '
        "open a lane below for the full feed.</p>",
        unsafe_allow_html=True,
    )
    col_news, col_sec = st.columns([1.2, 1], gap="large")
    with col_news:
        st.markdown(
            build_home_news_column_html(
                top,
                show_footnote=len(unique) <= HOME_HEADLINE_COUNT,
            ),
            unsafe_allow_html=True,
        )

    with col_sec:
        st.markdown(
            build_home_regulatory_column_html(
                regulatory_articles,
                max_items=HOME_REGULATORY_PREVIEW,
            ),
            unsafe_allow_html=True,
        )

    needs_news_btn = len(unique) > HOME_HEADLINE_COUNT
    needs_reg_btn = len(regulatory_articles) > HOME_REGULATORY_PREVIEW
    if needs_news_btn or needs_reg_btn:
        b_news, b_reg = st.columns([1.2, 1], gap="large")
        with b_news:
            if needs_news_btn:
                if st.button(
                    "Explore all articles →",
                    key="see_more_news_bottom",
                    use_container_width=True,
                    type="primary",
                ):
                    st.switch_page("pages/All_Articles.py")
                st.markdown(
                    '<p class="jd-hub-cta-note">Full feed with filters and pagination on the next page.</p>',
                    unsafe_allow_html=True,
                )
        with b_reg:
            if needs_reg_btn:
                if st.button(
                    "Explore all headlines →",
                    key="see_more_regulatory_bottom",
                    use_container_width=True,
                    type="primary",
                ):
                    st.switch_page("pages/All_Regulatory.py")
                st.markdown(
                    '<p class="jd-hub-cta-note">Full regulatory feed on the next page.</p>',
                    unsafe_allow_html=True,
                )

    st.divider()
    st.markdown(
        '<div id="jd-section-market" style="scroll-margin-top: 5.5rem;"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(section_label_teal("Markets & On-chain"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek">Spot crypto ETPs and the RWA.xyz network league — '
        "teasers here; use each page for the complete table.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div id="jd-section-etps" style="scroll-margin-top: 5.5rem;"></div>',
        unsafe_allow_html=True,
    )
    show_us_crypto_etps_widget(
        get_etp_user_agent_from_secrets(),
        home_preview=True,
    )

    st.divider()
    st.markdown(
        '<div id="jd-section-rwa" style="scroll-margin-top: 5.5rem;"></div>',
        unsafe_allow_html=True,
    )
    show_rwa_league_widget(home_preview=True)

    st.divider()
    _footer_line()
    _jd_inject_scroll_to_section()


if __name__ == "__main__":
    main()
