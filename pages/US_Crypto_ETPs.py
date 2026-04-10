"""Full U.S. crypto ETP list (same data as home widget)."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape

import streamlit as st

from crypto_etps.aum_history import etp_rows_to_fund_pairs, load_aggregate_aum_history_cached
from crypto_etps.client import (
    format_usd_compact,
    sorted_by_assets,
    total_aum_usd,
)
from crypto_etps.dataframe_table import (
    build_etp_dataframe,
    filter_rows_by_fund_name,
)
from crypto_etps.widgets import (
    ETP_DATA_SOURCE_CAPTION,
    etp_table_height,
    get_etp_user_agent_from_secrets,
    load_crypto_etps_cached,
    resolve_etp_user_agent,
    show_etp_dataframe,
)
from home_layout import ETP_FULLPAGE_AUM_LINE_CSS, STREAMLIT_TABLE_UNIFY_CSS
from news_feeds import (
    HOME_MAIN_HEADING_CSS,
    article_styles_markdown,
    render_subpage_top_bar,
)
from price_ticker import show_price_ticker


def main() -> None:
    st.set_page_config(
        page_title="U.S. Crypto ETPs — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Home", key="top_home_etps"):
        st.switch_page("streamlit_app.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(HOME_MAIN_HEADING_CSS, unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()

    st.markdown(
        '<h2 class="home-main-heading">U.S. Crypto ETPs — Full List</h2>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Data from [StockAnalysis.com](https://stockanalysis.com/list/crypto-etfs/) "
        "and each fund’s detail page (issuer, inception, past-year return as 52W %)."
    )

    with st.spinner("Loading U.S. crypto ETPs (list + profile pages)…"):
        data = load_crypto_etps_cached(resolve_etp_user_agent(get_etp_user_agent_from_secrets()))

    if data.error and not data.rows:
        st.warning(escape(data.error))
        return

    rows = data.rows
    total = total_aum_usd(rows)

    if total > 0:
        st.markdown(
            f'<p class="etp-fullpage-aum-line">Total AUM (known assets): {escape(format_usd_compact(total))}</p>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<h3 class="home-main-heading" style="margin-top:1rem;font-size:1rem;">Aggregate AUM trend (12 months)</h3>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Estimated from **Yahoo Finance** weekly closes: each fund’s latest reported AUM from StockAnalysis "
        "is scaled by its price path (constant-shares approximation), then summed. Covers the full list below — "
        "not official fund AUM filings."
    )
    with st.spinner("Loading 12-month price history for aggregate AUM estimate…"):
        pairs = etp_rows_to_fund_pairs(rows)
        chart_df, chart_err = load_aggregate_aum_history_cached(pairs)
    if chart_df is not None and not chart_df.empty:
        plot_df = chart_df.copy()
        plot_df["aum_billions_usd"] = plot_df["total_aum_usd"] / 1e9
        st.line_chart(plot_df, x="date", y="aum_billions_usd", height=320)
        st.caption("Vertical axis: total estimated AUM, **billions USD** (weekly points).")
    elif chart_err:
        st.info(chart_err)

    q = st.text_input(
        "Search fund name",
        "",
        key="etf_search_full",
        placeholder="Filter by fund name…",
    )

    filtered = filter_rows_by_fund_name(rows, q)
    sorted_rows = sorted_by_assets(filtered)
    df = build_etp_dataframe(sorted_rows)

    if q.strip():
        st.caption(
            f"Showing {len(sorted_rows)} of {len(rows)} funds matching “{escape(q.strip())}”."
        )
    else:
        st.caption(f"Showing all {len(sorted_rows)} funds.")

    show_etp_dataframe(df, height=etp_table_height(len(df), max_h=900))
    st.caption(ETP_DATA_SOURCE_CAPTION)
    st.caption(
        f"Last loaded at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "Cached up to one hour; use **Refresh feeds** on the home page to reload."
    )


main()
