"""
JPM Digital — crypto & digital asset news (RSS aggregation).
Deploy on Streamlit Community Cloud with this file as the main entrypoint.
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st
import streamlit.components.v1 as components

from home_layout import hub_section_anchor, section_label_teal
from news_feeds import (
    DEFAULT_FEEDS,
    app_shared_layout_css,
    article_styles_markdown,
    build_home_news_lane_body_html,
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
from regulatory_news.widgets import build_home_regulatory_lane_body_html, clear_regulatory_cache
from rwa_league.widgets import clear_rwa_league_cache, show_rwa_league_widget

HOME_HEADLINE_COUNT = 3
HOME_REGULATORY_PREVIEW = 3

HOME_PAGE_EXTRA_CSS = ""

_JD_SCROLL_MAP = {
    "top": "jd-page-top",
    "news": "jd-section-news",
    "markets_funds": "jd-section-markets-funds",
    "onchain": "jd-section-onchain",
    # Legacy query params (old bookmarks / links)
    "market": "jd-section-markets-funds",
    "etps": "jd-section-markets-funds",
    "rwa": "jd-section-onchain",
}


def _jd_consume_scroll_query() -> None:
    """Map ?jd_scroll=top|news|market|… from top-nav links into session state; strip param from URL."""
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
  function findByIdDeep(doc) {{
    if (!doc) return null;
    let el = doc.getElementById(id);
    if (el) return el;
    const frames = doc.querySelectorAll("iframe");
    for (let i = 0; i < frames.length; i++) {{
      try {{
        const child = frames[i].contentDocument;
        if (child) {{
          el = findByIdDeep(child);
          if (el) return el;
        }}
      }} catch (e) {{}}
    }}
    return null;
  }}
  function go() {{
    let el = findByIdDeep(p.document);
    if (!el) {{
      try {{ el = findByIdDeep(window.document); }} catch (e) {{}}
    }}
    if (el) {{
      el.scrollIntoView({{ block: "start", behavior: "auto" }});
      return true;
    }}
    return false;
  }}
  let n = 0;
  const t = p.setInterval(function () {{
    if (go()) {{
      p.clearInterval(t);
      return;
    }}
    n++;
    if (n > 80) {{
      if (id === "jd-page-top") {{
        try {{ p.scrollTo({{ top: 0, left: 0, behavior: "auto" }}); }} catch (e) {{}}
        try {{
          const de = p.document.documentElement;
          const b = p.document.body;
          if (de) de.scrollTop = 0;
          if (b) b.scrollTop = 0;
        }} catch (e) {{}}
      }}
      p.clearInterval(t);
    }}
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
        if st.button("U.S. Digital Asset ETPs", use_container_width=True, key="sb_etp"):
            st.switch_page("pages/US_Crypto_ETPs.py")
        if st.button("RWA league table", use_container_width=True, key="sb_rwa"):
            st.switch_page("pages/RWA_League.py")
        if st.button("RWA Stablecoins", use_container_width=True, key="sb_rwa_sc"):
            st.switch_page("pages/RWA_Stablecoins.py")
        if st.button("RWA US Treasuries", use_container_width=True, key="sb_rwa_tr"):
            st.switch_page("pages/RWA_US_Treasuries.py")
        if st.button("RWA Tokenized Stocks", use_container_width=True, key="sb_rwa_stocks"):
            st.switch_page("pages/RWA_Tokenized_Stocks.py")
        st.divider()
        st.caption(
            "Refresh reloads RSS, prices, ETPs, regulatory feeds, RWA network league, "
            "RWA Stablecoins embed, RWA US Treasuries embed, and RWA Tokenized Stocks embed."
        )
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
        app_shared_layout_css() + HOME_PAGE_EXTRA_CSS,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<h1 class="home-main-heading" id="jd-page-top">Digital Assets Dashboard</h1>',
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
        st.markdown(hub_section_anchor("jd-section-news"), unsafe_allow_html=True)
        st.markdown(section_label_teal("News & Regulatory", placement="first"), unsafe_allow_html=True)
        st.markdown(
            '<p class="jd-hub-dek">Headlines and regulatory wires — open a lane for the full feed.</p>',
            unsafe_allow_html=True,
        )
        _needs_reg_btn_empty = len(regulatory_articles) > HOME_REGULATORY_PREVIEW
        col_news, col_sec = st.columns([1, 1], gap="medium")
        with col_news:
            with st.container(border=True):
                st.markdown(
                    '<div class="jd-home-lane-body jd-home-lane-compact">'
                    '<h2 class="home-lane-heading">Latest Digital Asset News</h2>'
                    '<p class="jd-news-column-footnote">Headlines will appear here when feeds load.</p>'
                    "</div>",
                    unsafe_allow_html=True,
                )
        with col_sec:
            with st.container(border=True):
                st.markdown(
                    build_home_regulatory_lane_body_html(
                        regulatory_articles,
                        max_items=HOME_REGULATORY_PREVIEW,
                    ),
                    unsafe_allow_html=True,
                )
                if _needs_reg_btn_empty:
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
        st.markdown(hub_section_anchor("jd-section-markets-funds"), unsafe_allow_html=True)
        st.markdown(section_label_teal("Markets & Funds", placement="after_divider"), unsafe_allow_html=True)
        st.markdown(
            '<p class="jd-hub-dek">U.S. listed digital asset ETFs and ETPs — preview below; open the full list for search and fund details.</p>',
            unsafe_allow_html=True,
        )
        show_us_crypto_etps_widget(
            get_etp_user_agent_from_secrets(),
            home_preview=True,
        )

        st.divider()
        st.markdown(hub_section_anchor("jd-section-onchain"), unsafe_allow_html=True)
        st.markdown(section_label_teal("On-chain Data", placement="after_divider"), unsafe_allow_html=True)
        st.markdown(
            '<p class="jd-hub-dek">RWA.xyz tokenized markets and network leagues — previews below; open each page for full tables.</p>',
            unsafe_allow_html=True,
        )
        show_rwa_league_widget(home_preview=True)

        st.divider()
        _footer_line()
        _jd_inject_scroll_to_section()
        return

    unique = dedupe_articles(articles, max_items=None)
    top = unique[:HOME_HEADLINE_COUNT]
    needs_news_btn = len(unique) > HOME_HEADLINE_COUNT
    needs_reg_btn = len(regulatory_articles) > HOME_REGULATORY_PREVIEW

    st.markdown(hub_section_anchor("jd-section-news"), unsafe_allow_html=True)
    st.markdown(section_label_teal("News & Regulatory", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek">Crypto RSS headlines and global regulatory wires — use a lane below for the full feed.</p>',
        unsafe_allow_html=True,
    )
    col_news, col_sec = st.columns([1, 1], gap="medium")
    with col_news:
        with st.container(border=True):
            st.markdown(
                build_home_news_lane_body_html(
                    top,
                    show_footnote=len(unique) <= HOME_HEADLINE_COUNT,
                ),
                unsafe_allow_html=True,
            )
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

    with col_sec:
        with st.container(border=True):
            st.markdown(
                build_home_regulatory_lane_body_html(
                    regulatory_articles,
                    max_items=HOME_REGULATORY_PREVIEW,
                ),
                unsafe_allow_html=True,
            )
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
    st.markdown(hub_section_anchor("jd-section-markets-funds"), unsafe_allow_html=True)
    st.markdown(section_label_teal("Markets & Funds", placement="after_divider"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek">U.S. listed digital asset ETFs and ETPs — preview below; open the full list for search and fund details.</p>',
        unsafe_allow_html=True,
    )
    show_us_crypto_etps_widget(
        get_etp_user_agent_from_secrets(),
        home_preview=True,
    )

    st.divider()
    st.markdown(hub_section_anchor("jd-section-onchain"), unsafe_allow_html=True)
    st.markdown(section_label_teal("On-chain Data", placement="after_divider"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek">RWA.xyz tokenized markets and network leagues — previews below; open each page for full tables.</p>',
        unsafe_allow_html=True,
    )
    show_rwa_league_widget(home_preview=True)

    st.divider()
    _footer_line()
    _jd_inject_scroll_to_section()


if __name__ == "__main__":
    main()
