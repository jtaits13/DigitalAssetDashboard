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
    HOME_PREVIEW_FILTER_JS,
    load_home_zone_data,
    render_home_markets_stack,
)
from streamlit_site_parity import (
    JD_SCROLL_MAP,
    build_home_chrome_html,
    build_home_footer_html,
    build_static_news_rail_html,
    inject_site_styles,
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
  const p = window.parent;
  const id = "{safe}";
  function findByIdDeep(doc) {{
    if (!doc) return null;
    let el = doc.getElementById(id);
    if (el) return el;
    for (const frame of doc.querySelectorAll("iframe")) {{
      try {{
        const hit = findByIdDeep(frame.contentDocument);
        if (hit) return hit;
      }} catch (e) {{}}
    }}
    return null;
  }}
  let n = 0;
  const t = p.setInterval(function () {{
    const el = findByIdDeep(p.document);
    if (el) {{
      el.scrollIntoView({{ block: "start", behavior: "auto" }});
      p.clearInterval(t);
      return;
    }}
    if (++n > 80) {{
      if (id === "page-title") try {{ p.scrollTo(0, 0); }} catch (e) {{}}
      p.clearInterval(t);
    }}
  }}, 40);
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


def main() -> None:
    st.set_page_config(
        page_title="Digital Assets Dashboard",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    _consume_home_refresh_query()
    _jd_consume_scroll_query()
    inject_site_styles(include_static=True)

    now = datetime.now(timezone.utc)
    footer_month = now.strftime("%b %Y")
    footer_iso = now.strftime("%Y-%m")

    render_home_markdown(build_home_chrome_html(include_refresh=False))

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

    news_col, markets_col = st.columns([1, 2.85], gap="large")
    with news_col:
        st.markdown(news_rail.strip(), unsafe_allow_html=True)
    with markets_col:
        render_home_markets_stack(
            markets_col,
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

    components.html(HOME_PREVIEW_FILTER_JS, height=0, width=0)
    _jd_inject_scroll_to_section()


if __name__ == "__main__":
    main()
