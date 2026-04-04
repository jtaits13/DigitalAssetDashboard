"""Full U.S. crypto ETP list (same data as home widget)."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape

import streamlit as st

from crypto_etps.client import (
    format_usd_compact,
    sorted_by_assets,
    total_aum_usd,
)
from crypto_etps.widgets import (
    WIDGET_CSS,
    get_etp_user_agent_from_secrets,
    load_crypto_etps_cached,
    render_etp_table_html,
    resolve_etp_user_agent,
)
from news_feeds import HOME_MAIN_HEADING_CSS, article_styles_markdown, render_home_top_bar
from price_ticker import show_price_ticker


def main() -> None:
    st.set_page_config(
        page_title="U.S. Crypto ETPs — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_home_top_bar("crypto_etps_full")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(HOME_MAIN_HEADING_CSS, unsafe_allow_html=True)
    st.markdown(WIDGET_CSS, unsafe_allow_html=True)
    show_price_ticker()

    st.markdown(
        '<h2 class="home-main-heading">U.S. Crypto ETPs — full list</h2>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Data from [StockAnalysis.com](https://stockanalysis.com/list/crypto-etfs/) "
        "and each fund’s detail page (issuer, inception, past-year return as 52W %). Scraped for display only."
    )

    with st.spinner("Loading U.S. crypto ETPs (list + profile pages)…"):
        data = load_crypto_etps_cached(resolve_etp_user_agent(get_etp_user_agent_from_secrets()))

    if data.error and not data.rows:
        st.warning(escape(data.error))
        return

    rows = sorted_by_assets(data.rows)
    total = total_aum_usd(rows)
    if total > 0:
        st.subheader(f"Total AUM (known assets): {format_usd_compact(total)}")
    st.caption(f"{len(rows)} ETPs · sorted by assets (unknown last)")

    st.markdown(render_etp_table_html(rows), unsafe_allow_html=True)

    st.caption(
        f"Last loaded at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "Cached up to one hour; use **Refresh feeds** on the home page to reload."
    )


main()
