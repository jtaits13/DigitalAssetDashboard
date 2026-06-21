"""
Digital Assets Dashboard — Streamlit home matching static_home/index.html.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from concurrent.futures import ThreadPoolExecutor

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
    build_home_markets_stack_html,
    load_home_zone_data,
)
from streamlit_site_parity import (
    JD_SCROLL_MAP,
    build_static_news_rail_html,
    inject_site_styles,
    render_home_hero,
    render_site_nav,
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

    _jd_consume_scroll_query()
    inject_site_styles()

    # Page shell matches static: body.page-home.site-experience > header + main
    st.markdown('<div class="page-home site-experience st-parity-root">', unsafe_allow_html=True)
    render_site_nav(active="home", is_landing=True)

    st.markdown('<main id="top">', unsafe_allow_html=True)
    render_home_hero()

    etp_ua = resolve_etp_user_agent(get_etp_user_agent_from_secrets())

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
    markets_stack = build_home_markets_stack_html(
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

    refresh_col, _ = st.columns([1, 5])
    with refresh_col:
        st.markdown('<div class="stRefreshWrap"></div>', unsafe_allow_html=True)
        if st.button("Refresh data", key="home_refresh", type="secondary"):
            _clear_all_caches()
            st.rerun()

    # Single HTML block: CSS grid puts news rail LEFT, markets stack RIGHT (matches static)
    st.markdown(
        f"""
<div class="page-shell">
  <div class="home-main-split">
    <div class="home-markets-stack">
      {markets_stack}
    </div>
    {news_rail}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    components.html(HOME_PREVIEW_FILTER_JS, height=0, width=0)

    month_label = datetime.now(timezone.utc).strftime("%b %Y")
    st.markdown(
        f'</main><footer class="site-footer">Digital Assets Dashboard · Home · '
        f'<time datetime="{datetime.now(timezone.utc).strftime("%Y-%m")}">{month_label}</time></footer>'
        "</div>",
        unsafe_allow_html=True,
    )

    _jd_inject_scroll_to_section()


if __name__ == "__main__":
    main()
