"""Full U.S. crypto ETP list (same data as home widget)."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape

import streamlit as st

from crypto_etps.aum_history import (
    build_aggregate_aum_plotly_figure,
    etp_rows_to_fund_pairs,
    load_aggregate_aum_history_cached,
)
from crypto_etps.client import sorted_by_assets
from crypto_etps.dataframe_table import (
    build_etp_dataframe,
    filter_rows_by_fund_name,
)
from crypto_etps.widgets import (
    ETP_DATA_SOURCE_CAPTION,
    WIDGET_CSS,
    etp_table_height,
    get_etp_user_agent_from_secrets,
    load_crypto_etps_cached,
    render_etp_summary_kpi_row,
    resolve_etp_user_agent,
    show_etp_dataframe,
)
from home_layout import (
    ETP_FULLPAGE_AUM_LINE_CSS,
    KPI_WINDOW_NOTE_CSS,
    STREAMLIT_TABLE_UNIFY_CSS,
    hub_subsection_heading_html,
    section_label_teal,
    subpage_toolbar_note_html,
)
from news_feeds import (
    ETP_PULSE_PREVIEW_COUNT,
    app_shared_layout_css,
    article_styles_markdown,
    build_etp_market_news_box_html,
    load_all_etf_etp_news_cached,
    render_subpage_sidebar,
    render_subpage_top_bar,
)
from price_ticker import show_price_ticker

# Chart sits in a half-width column next to the ETF pulse panel; KPI row is full width above.
ETP_TOP_SPLIT_AUM_CHART_HEIGHT = 420


def main() -> None:
    st.set_page_config(
        page_title="U.S. Digital Asset ETPs — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Home", key="top_home_etps"):
        st.switch_page("streamlit_app.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(
        STREAMLIT_TABLE_UNIFY_CSS
        + ETP_FULLPAGE_AUM_LINE_CSS
        + WIDGET_CSS
        + KPI_WINDOW_NOTE_CSS,
        unsafe_allow_html=True,
    )
    show_price_ticker()
    render_subpage_sidebar(key_prefix="us_crypto_etps", current="etp")

    st.markdown(
        section_label_teal("U.S. Digital Asset ETPs — Full List", placement="first"),
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed">A comprehensive view of U.S. digital asset ETPs, combining market context, aggregate '
        'AUM trend signals, and fund-level reference data in one place. Data from '
        '<a href="https://stockanalysis.com/list/crypto-etfs/">StockAnalysis.com</a> and each fund’s detail page '
        "(issuer, inception, past-year return as <strong>52W %</strong>).</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    with st.spinner("Loading U.S. digital asset ETPs (list + profile pages)…"):
        data = load_crypto_etps_cached(resolve_etp_user_agent(get_etp_user_agent_from_secrets()))

    if data.error and not data.rows:
        st.warning(escape(data.error))
        return

    rows = data.rows

    with st.spinner("Loading crypto ETF / ETP headlines (RSS)…"):
        etp_all_news, _etp_feed_errors = load_all_etf_etp_news_cached()
    etp_pulse = etp_all_news[:ETP_PULSE_PREVIEW_COUNT]
    if _etp_feed_errors:
        with st.expander("Some ETF/ETP RSS feeds could not be loaded", expanded=False):
            for err in _etp_feed_errors:
                st.warning(err)

    st.markdown(
        hub_subsection_heading_html(
            "U.S. Digital Asset ETPs",
            element_id="jd-etp-summary",
        ),
        unsafe_allow_html=True,
    )
    render_etp_summary_kpi_row(rows, include_styles=False)

    # border=True: same as home News & Regulatory row — stretch columns and pin Explore CTA under the hub panel.
    col_aum, col_pulse = st.columns([1, 1], gap="medium", border=True)
    with col_aum:
        st.markdown(
            hub_subsection_heading_html(
                "Aggregate AUM trend (12 months)",
                element_id="jd-etp-aggregate-aum",
            ),
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
            fig = build_aggregate_aum_plotly_figure(
                plot_df,
                height=ETP_TOP_SPLIT_AUM_CHART_HEIGHT,
            )
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={
                    "scrollZoom": True,
                    "displayModeBar": True,
                },
            )
            st.caption(
                "Vertical axis: total estimated AUM, **billions USD** (weekly points). "
                "Default view is the last **12 months** (month labels on the x-axis); scroll or use the "
                "mode bar to zoom and pan the full history."
            )
        elif chart_err:
            st.info(chart_err)

    with col_pulse:
        st.markdown(
            build_etp_market_news_box_html(etp_pulse),
            unsafe_allow_html=True,
        )
        if len(etp_all_news) > ETP_PULSE_PREVIEW_COUNT:
            if st.button(
                "Explore all articles →",
                key="etp_explore_all_etf_news",
                use_container_width=True,
                type="primary",
            ):
                st.switch_page("pages/All_ETF_News.py")
            st.markdown(
                '<p class="jd-hub-cta-note">Full ETF/ETP feed (last <strong>3 months</strong>, UTC) with search and pagination on the next page.</p>',
                unsafe_allow_html=True,
            )

    st.divider()

    q = st.text_input(
        "Search by fund name or ticker",
        "",
        key="etf_search_full",
        placeholder="Filter by name or ticker…",
    )

    filtered = filter_rows_by_fund_name(rows, q)
    sorted_rows = sorted_by_assets(filtered)
    df = build_etp_dataframe(sorted_rows)

    if q.strip():
        st.markdown(
            subpage_toolbar_note_html(
                f"Showing {len(sorted_rows)} of {len(rows)} funds matching “{escape(q.strip())}”."
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            subpage_toolbar_note_html(f"Showing all {len(sorted_rows)} funds."),
            unsafe_allow_html=True,
        )

    empty_msg = None
    if df.empty:
        empty_msg = (
            "No funds match your search. Try a different name, ticker, or clear the search box."
            if q.strip()
            else "No fund data available in the list yet."
        )
    show_etp_dataframe(
        df,
        height=etp_table_height(max(len(df), 1), max_h=900),
        empty_message=empty_msg,
    )
    st.divider()
    st.caption(ETP_DATA_SOURCE_CAPTION)
    st.caption(
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "StockAnalysis · Cached up to one hour · Use **Refresh all data** on the home page to reload."
    )


main()
