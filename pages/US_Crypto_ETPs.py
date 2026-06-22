"""Full U.S. crypto ETP list (same data as home widget)."""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

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
from crypto_etps.flows import (
    aggregate_flow_for_symbols,
    aggregate_flow_mom_pct,
    format_flow_usd_compact,
    load_farside_flow_series_cached,
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
    subpage_footnote_markup_html,
    subpage_toolbar_note_html,
)
from news_feeds import (
    ETP_PULSE_PREVIEW_COUNT,
    article_styles_markdown,
    build_etp_market_news_box_html,
    load_all_etf_etp_news_cached,
)
from streamlit_site_parity import (
    close_subpage_layout,
    configure_subpage,
    inner_page_zone_close,
    inner_page_zone_open,
    open_subpage_layout,
    related_chips_html,
    render_subpage_back_link,
    render_subpage_footer,
)

ETP_TOP_SPLIT_AUM_CHART_HEIGHT = 420


def _etp_key_observations_html(
    rows: list,
    *,
    etp_news: list[dict] | None = None,
) -> str:
    from crypto_etps.etp_takeaways import build_etp_key_observations_html

    flow_series, _ = load_farside_flow_series_cached()
    listed_syms = [r.symbol for r in rows if (r.symbol or "").strip()]
    net_flow_1m, _ = aggregate_flow_for_symbols(listed_syms, flow_series, days=30)
    net_flow_1m_pct, _ = aggregate_flow_mom_pct(listed_syms, flow_series, days=30)
    return build_etp_key_observations_html(
        rows,
        net_flow_1m_display=format_flow_usd_compact(net_flow_1m),
        net_flow_1m_pct=net_flow_1m_pct,
        articles=etp_news,
    )


def main() -> None:
    configure_subpage(
        page_title="U.S. Digital Asset ETPs — Digital Assets Dashboard",
        active="etps",
        style_kind="etp",
    )
    render_subpage_back_link(href="/", label="← Back to home")
    open_subpage_layout(style_kind="etp", shell_class="etp-mock-shell")
    inner_page_zone_open(
        section_id="etp-full",
        badge="ETP",
        title="U.S. Digital Asset ETPs",
        subtitle_html=(
            "<strong>U.S. crypto-related exchange-traded products</strong>, with a KPI strip, an estimated aggregate AUM "
            "trend chart, a searchable fund table, and a related ETF/ETP headlines panel. Reference: "
            '<a href="https://stockanalysis.com/list/crypto-etfs/" target="_blank" rel="noopener noreferrer">'
            "StockAnalysis.com</a> (issuer, inception, <strong>1Y %</strong> past-year total return)."
        ),
        zone_classes="zone--etp home-zone home-zone--etp etp-mock-zone",
        related_chips=related_chips_html(
            ("/?jd_scroll=markets", "Home ETP preview"),
            ("/Crypto_Prices", "Crypto prices"),
            ("/All_ETF_News", "All ETF/ETP headlines"),
        ),
        body_class="inner-rich-zone__body etp-mock-zone__body",
    )
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(
        STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS + WIDGET_CSS + KPI_WINDOW_NOTE_CSS,
        unsafe_allow_html=True,
    )

    ua = resolve_etp_user_agent(get_etp_user_agent_from_secrets())
    with st.spinner("Loading funds and headline teaser…"):
        with ThreadPoolExecutor(max_workers=2) as _pool:
            _f_etp_rows = _pool.submit(load_crypto_etps_cached, ua)
            _f_etp_news = _pool.submit(load_all_etf_etp_news_cached)
            data = _f_etp_rows.result()
            etp_all_news, _etp_feed_errors = _f_etp_news.result()

    if data.error and not data.rows:
        st.warning(escape(data.error))
    else:
        rows = data.rows
        etp_pulse = etp_all_news[:ETP_PULSE_PREVIEW_COUNT]
        if _etp_feed_errors:
            with st.expander("Some headline feeds could not be loaded", expanded=False):
                for err in _etp_feed_errors:
                    st.warning(err)

        st.markdown(
            hub_subsection_heading_html("Top-Line Market Snapshot", element_id="jd-etp-summary"),
            unsafe_allow_html=True,
        )
        render_etp_summary_kpi_row(rows, include_styles=False, metrics_above_methodology_note=True)
        st.markdown(hub_subsection_heading_html("Key Observations"), unsafe_allow_html=True)
        st.markdown(_etp_key_observations_html(rows, etp_news=etp_all_news), unsafe_allow_html=True)

        col_aum, col_pulse = st.columns([1, 1], gap="medium", border=True)
        with col_aum:
            st.markdown(
                hub_subsection_heading_html(
                    "Aggregate AUM trend (12 months)",
                    element_id="jd-etp-aggregate-aum",
                ),
                unsafe_allow_html=True,
            )
            st.markdown(
                subpage_footnote_markup_html(
                    "<strong>Yahoo Finance</strong> weekly closes × each fund’s latest StockAnalysis AUM "
                    "(constant-share approximation), summed across the table below. Illustrative only—not filings."
                ),
                unsafe_allow_html=True,
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
                    config={"scrollZoom": True, "displayModeBar": True},
                )
                st.markdown(
                    subpage_footnote_markup_html(
                        "Vertical axis: estimated aggregate AUM (<strong>billions USD</strong>; weekly points). "
                        "Default last <strong>12 months</strong>; use the Plotly toolbar to zoom or pan."
                    ),
                    unsafe_allow_html=True,
                )
            elif chart_err:
                st.info(chart_err)

        with col_pulse:
            st.markdown(build_etp_market_news_box_html(etp_pulse), unsafe_allow_html=True)
            if len(etp_all_news) > ETP_PULSE_PREVIEW_COUNT:
                st.markdown(
                    '<p class="cta-note etp-mock-chart__method">'
                    '<a href="/All_ETF_News">All ETF/ETP headlines →</a></p>',
                    unsafe_allow_html=True,
                )

        q = st.text_input(
            "Search by fund name or ticker",
            "",
            key="etf_search_full",
            placeholder="Filter by name or ticker…",
        )
        filtered = filter_rows_by_fund_name(rows, q)
        sorted_rows = sorted_by_assets(filtered)
        flow_series = load_farside_flow_series_cached()
        df = build_etp_dataframe(sorted_rows, flow_series=flow_series)

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
        st.caption(ETP_DATA_SOURCE_CAPTION)
        st.markdown(
            subpage_footnote_markup_html(
                f"{escape(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))} UTC · "
                "StockAnalysis snapshot · Cached up to ~1 hour · Reload via <strong>Refresh all data</strong> on Home."
            ),
            unsafe_allow_html=True,
        )

    inner_page_zone_close()
    close_subpage_layout(back_href="/", back_label="← Back to home")
    render_subpage_footer(label="U.S. ETPs")


main()
