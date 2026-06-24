"""Digital Assets Dashboard — Streamlit home matching static_home/index.html."""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import streamlit as st
import streamlit.components.v1 as components

from crypto_etps.widgets import (
    clear_crypto_etp_cache,
    get_etp_user_agent_from_secrets,
    resolve_etp_user_agent,
)
from crypto_prices.widgets import clear_crypto_snapshot_cache
from news_feeds import DEFAULT_FEEDS, load_all_feeds, prepare_home_hub_market_news_lane
from price_ticker import fetch_top_crypto_tickers
from regulatory_news.client import load_regulatory_articles
from regulatory_news.widgets import clear_regulatory_cache
from rwa_league.widgets import clear_rwa_league_cache
from streamlit_home_static import (
    load_home_zone_data,
    render_home_body_iframe,
)
from streamlit_site_parity import (
    HOME_BODY_IFRAME_SIZE_JS,
    HOME_IFRAME_HEIGHT_SYNC_JS,
    HOME_PAGE_SCROLL_JS,
    JD_SCROLL_MAP,
    build_home_footer_html,
    build_static_news_rail_html,
    consume_jd_page_query,
    inject_site_styles,
    inject_streamlit_nav_router,
    render_home_chrome,
    render_home_hero_content_gap,
    render_home_markdown,
)


def _jd_consume_scroll_query() -> None:
    if "jd_scroll" not in st.query_params:
        return
    raw = st.query_params["jd_scroll"]
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    key = str(raw).strip().lower()
    if key in JD_SCROLL_MAP:
        st.session_state["jd_scroll_to"] = JD_SCROLL_MAP[key]
    try:
        del st.query_params["jd_scroll"]
    except KeyError:
        pass


def _consume_home_refresh_query() -> None:
    if "home_refresh" not in st.query_params:
        return
    try:
        del st.query_params["home_refresh"]
    except KeyError:
        pass
    _clear_all_caches()
    st.rerun()


def _jd_inject_scroll_to_section() -> None:
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
  var win = window.parent;
  var id = "{safe}";
  function go() {{
    if (typeof win.jpmPollScrollToHomeSection === "function") {{
      win.jpmPollScrollToHomeSection(id, 120);
      return true;
    }}
    return false;
  }}
  if (!go()) {{
    var n = 0;
    var t = win.setInterval(function () {{
      if (go() || ++n > 40) win.clearInterval(t);
    }}, 50);
  }}
}})();
</script>
""",
        height=0,
        width=0,
    )


def _clear_all_caches() -> None:
    import news_feeds

    news_feeds.fetch_feed.clear()
    fetch_top_crypto_tickers.clear()
    clear_regulatory_cache()
    clear_crypto_etp_cache()
    clear_rwa_league_cache()
    clear_crypto_snapshot_cache()
    from streamlit_crypto_prices_static import _cached_crypto_prices_iframe_payloads

    _cached_crypto_prices_iframe_payloads.clear()
    from streamlit_etps_static import _cached_etp_iframe_payloads

    _cached_etp_iframe_payloads.clear()
    from streamlit_news_feeds_static import _cached_news_feed_iframe_payloads

    _cached_news_feed_iframe_payloads.clear()


def main() -> None:
    st.set_page_config(
        page_title="Digital Assets Dashboard",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    _consume_home_refresh_query()
    _jd_consume_scroll_query()
    consume_jd_page_query()
    inject_site_styles(include_static=True)
    inject_streamlit_nav_router()

    from streamlit_site_parity import inject_streamlit_table_fullscreen_host

    inject_streamlit_table_fullscreen_host()

    now = datetime.now(timezone.utc)
    footer_month = now.strftime("%b %Y")
    footer_iso = now.strftime("%Y-%m")

    render_home_chrome(include_refresh=False)
    components.html(HOME_PAGE_SCROLL_JS, height=0, width=0)

    etp_ua = resolve_etp_user_agent(get_etp_user_agent_from_secrets())

    with st.spinner("Loading market data…"):
        with ThreadPoolExecutor(max_workers=4) as pool:
            f_news = pool.submit(load_all_feeds, DEFAULT_FEEDS)
            f_reg = pool.submit(load_regulatory_articles)
            f_data = pool.submit(load_home_zone_data, etp_ua)
            articles, feed_errors = f_news.result()
            _, reg_errors = f_reg.result()
            zone_data = f_data.result()

    errors = [e for e in (feed_errors + reg_errors) if e]
    if errors:
        with st.expander("Feed status", expanded=False):
            for err in errors:
                st.warning(err)

    home_news, _ = prepare_home_hub_market_news_lane(articles)
    news_rail = build_static_news_rail_html(home_news)

    render_home_hero_content_gap()

    render_home_body_iframe(
        news_rail=news_rail,
        mmf_kpis=zone_data["mmf_kpis"],
        mmf_funds=zone_data["mmf_funds"],
        stable_kpis=zone_data["stable_kpis"],
        stable_df=zone_data["stable_df"],
        rwa_kpis=zone_data["rwa_kpis"],
        rwa_df=zone_data["rwa_df"],
        etp_rows=zone_data["etp_rows"],
        crypto_rows=zone_data["crypto_rows"],
        crypto_paprika=zone_data["crypto_paprika"],
    )

    render_home_markdown(build_home_footer_html(footer_month=footer_month, footer_iso=footer_iso))

    components.html(HOME_IFRAME_HEIGHT_SYNC_JS, height=0, width=0)
    components.html(HOME_BODY_IFRAME_SIZE_JS, height=0, width=0)
    _jd_inject_scroll_to_section()


if __name__ == "__main__":
    main()
