"""Streamlit: U.S. crypto ETPs summary + link to full list page."""

from __future__ import annotations

from html import escape

import streamlit as st

from crypto_etps.client import (
    CryptoEtpRow,
    CryptoEtpsResult,
    fetch_crypto_etps_enriched,
    format_usd_compact,
    sorted_by_assets,
    total_aum_usd,
)
from crypto_etps.aum_history import (
    aggregate_aum_pct_from_history,
    etp_rows_to_fund_pairs,
    etp_symbol_price_change_cached,
    load_aggregate_aum_history_cached,
)
from crypto_etps.custodian import clear_custodian_map_cache
from crypto_etps.sec_prospectus import clear_sec_prospectus_caches
from crypto_etps.dataframe_table import (
    build_etp_dataframe,
    filter_rows_by_fund_name,
    style_etp_dataframe,
)
from home_layout import KPI_WINDOW_NOTE_CSS, STREAMLIT_TABLE_UNIFY_CSS
from news_feeds import load_all_etf_etp_news_cached

WIDGET_CSS = """
<style>
.jd-hub-subsection-head {
    margin: 0.4rem 0 0.55rem 0;
    padding: 0 0 0.45rem 0;
    border-bottom: 1px solid #C7D8E8;
    background: transparent;
    box-shadow: none;
}
.jd-hub-subsection-head h2.home-main-heading,
.jd-hub-subsection-head h2.home-widget-heading {
    margin: 0 !important;
    padding: 0;
}
.etp-aum-line {
    font-size: 0.95rem;
    font-weight: 700;
    color: #021D41;
    margin: 0.5rem 0 0.75rem 0;
}
.etp-kpi-wrap {
    margin: 0.35rem 0 0.85rem 0;
}
.etp-kpi-row {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.65rem 0.5rem;
    padding: 0.5rem 0 0.85rem 0;
    border-bottom: 1px solid #C7D8E8;
}
.etp-kpi-cell {
    flex: 1 1 0;
    min-width: 8.5rem;
    max-width: 100%;
    text-align: center;
}
.etp-kpi-label {
    display: block;
    font-size: 0.88rem;
    font-weight: 600;
    color: #1F4C67;
    margin-bottom: 0.35rem;
    line-height: 1.3;
    letter-spacing: 0.01em;
}
.etp-kpi-val {
    display: block;
    font-size: 1.05rem;
    font-weight: 700;
    color: #25809C;
    line-height: 1.2;
}
.etp-kpi-delta {
    display: block;
    font-size: 0.82rem;
    font-weight: 600;
    margin-top: 0.2rem;
    line-height: 1.2;
}
.etp-kpi-delta.up { color: #28794E; }
.etp-kpi-delta.down { color: #dc2626; }
.etp-kpi-delta.neutral { color: #3E6A7A; }
.etp-kpi-window-tag {
    font-size: 0.72rem;
    font-weight: 600;
    color: #3E6A7A;
}
.etp-custodian-footnote {
    font-size: 0.75rem;
    color: #6c757d;
    margin: 0.35rem 0 0 0;
    line-height: 1.4;
}
</style>
"""


def etp_table_height(num_rows: int, *, max_h: int = 520) -> int:
    header = 38
    row_h = 35
    return min(max_h, header + row_h * max(1, num_rows))


@st.cache_data(ttl=3600, show_spinner=False)
def load_crypto_etps_cached(user_agent: str, *, _row_schema: int = 3) -> CryptoEtpsResult:
    """Bump ``_row_schema`` when ``CryptoEtpRow`` fields change so cached rows are not stale."""
    _ = _row_schema
    return fetch_crypto_etps_enriched(user_agent)


def clear_crypto_etp_cache() -> None:
    load_crypto_etps_cached.clear()
    clear_custodian_map_cache()
    clear_sec_prospectus_caches()
    load_aggregate_aum_history_cached.clear()
    etp_symbol_price_change_cached.clear()
    load_all_etf_etp_news_cached.clear()


def _default_ua() -> str:
    return (
        "JPM-Digital/1.0 (crypto ETP list; set STOCKANALYSIS_USER_AGENT in secrets with contact email)"
    )


def resolve_etp_user_agent(user_agent: str | None) -> str:
    return (user_agent or "").strip() or _default_ua()


ETP_DATA_SOURCE_CAPTION = (
    "Source: [StockAnalysis.com crypto ETF list](https://stockanalysis.com/list/crypto-etfs/) "
    "and ETF detail pages (scraped; not affiliated)."
)

ETP_CUSTODIAN_TABLE_NOTE_HTML = (
    '<p class="etp-custodian-footnote">* <strong>Custodian</strong> column: labels are filled only for '
    "a curated set of leading <strong>spot</strong> Bitcoin and Ethereum funds. "
    "All other rows are left blank.</p>"
)

_SORT = "\u2195"


def _row_by_symbol(rows: list[CryptoEtpRow], symbol: str) -> CryptoEtpRow | None:
    u = symbol.strip().upper()
    for r in rows:
        if r.symbol.strip().upper() == u:
            return r
    return None


def _etf_delta_html(pct: float | None, window_lbl: str) -> str:
    if pct is None or not isinstance(pct, (int, float)):
        return "<span class='etp-kpi-delta neutral'>—</span>"
    p = float(pct)
    cls = "up" if p > 0 else "down" if p < 0 else "neutral"
    sign = "+" if p > 0 else ""
    tag = escape(window_lbl) if window_lbl else ""
    tag_html = f' <span class="etp-kpi-window-tag">({tag})</span>' if tag else ""
    return f"<span class='etp-kpi-delta {cls}'>{escape(f'{sign}{p:.2f}%')}{tag_html}</span>"


def _fund_trailing_pct(symbol: str, row: CryptoEtpRow | None) -> tuple[float | None, str]:
    py, pl = etp_symbol_price_change_cached(symbol)
    if py is not None:
        return py, pl
    if row is not None and row.pct_52w is not None:
        return float(row.pct_52w), "52W"
    return None, ""


def render_etp_summary_kpi_row(
    rows: list[CryptoEtpRow],
    *,
    include_styles: bool = True,
) -> None:
    """
    Home-style KPI strip: total listed AUM (with aggregate 30D % from Yahoo-scaled history),
    IBIT and ETHA AUM with 30D %. Used on the hub preview and the full ETP list page.
    """
    if include_styles:
        st.markdown(WIDGET_CSS + KPI_WINDOW_NOTE_CSS, unsafe_allow_html=True)
    total = total_aum_usd(rows)
    aum_s = format_usd_compact(total) if total > 0 else "—"
    pairs = etp_rows_to_fund_pairs(rows)
    hist_df, _hist_err = load_aggregate_aum_history_cached(pairs)
    agg_pct, _ = aggregate_aum_pct_from_history(hist_df)
    ibit_r = _row_by_symbol(rows, "IBIT")
    etha_r = _row_by_symbol(rows, "ETHA")
    _render_etp_home_kpi_row(
        total_aum_display=aum_s,
        agg_pct=agg_pct,
        ibit_row=ibit_r,
        etha_row=etha_r,
    )


def _render_etp_home_kpi_row(
    *,
    total_aum_display: str,
    agg_pct: float | None,
    ibit_row: CryptoEtpRow | None,
    etha_row: CryptoEtpRow | None,
) -> None:
    ibit_aum = (
        format_usd_compact(ibit_row.assets_usd)
        if ibit_row and ibit_row.assets_usd is not None and ibit_row.assets_usd > 0
        else "—"
    )
    etha_aum = (
        format_usd_compact(etha_row.assets_usd)
        if etha_row and etha_row.assets_usd is not None and etha_row.assets_usd > 0
        else "—"
    )
    ip, _ = _fund_trailing_pct("IBIT", ibit_row)
    ep, _ = _fund_trailing_pct("ETHA", etha_row)

    cells = [
        (
            "Total AUM (listed)",
            escape(total_aum_display),
            _etf_delta_html(agg_pct, ""),
        ),
        (
            "IBIT · AUM",
            escape(ibit_aum),
            _etf_delta_html(ip, ""),
        ),
        (
            "ETHA · AUM",
            escape(etha_aum),
            _etf_delta_html(ep, ""),
        ),
    ]
    parts = []
    for label, val_html, delta_html in cells:
        parts.append(
            "<div class='etp-kpi-cell'>"
            f"<span class='etp-kpi-label'>{escape(label)}</span>"
            f"<span class='etp-kpi-val'>{val_html}</span>"
            f"{delta_html}"
            "</div>"
        )
    st.markdown(
        '<div class="etp-kpi-wrap">'
        "<p class=\"jd-kpi-window-note\">"
        "All % changes in this row are <strong>30-day (30D)</strong> (<strong>Yahoo Finance</strong>). "
        "Headline totals are listed AUM from <strong>StockAnalysis</strong> "
        "(crypto ETF list and detail pages; scraped; not affiliated)."
        "</p>"
        "<div class='etp-kpi-row'>"
        f"{''.join(parts)}"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def show_etp_dataframe(
    df,
    *,
    height: int,
    empty_message: str | None = None,
) -> None:
    """Render styled dataframe, or an info note when there are no rows."""
    if df.empty:
        st.info(
            empty_message
            or "No funds to display."
        )
        return
    order = [
        "Symbol",
        "Fund Name",
        "Price",
        "52W %",
        "Assets (B)",
        "Issuer",
        "Custodian",
        "Inception",
        "Fund Filing",
    ]
    order = [c for c in order if c in df.columns]

    cfg = {
        "Symbol": st.column_config.TextColumn(
            f"Symbol {_SORT}",
            width="small",
        ),
        "Fund Name": st.column_config.TextColumn(
            f"Fund Name {_SORT}",
            width="large",
        ),
        "Price": st.column_config.NumberColumn(
            f"Price {_SORT}",
            format="$%.2f",
            width="small",
        ),
        "52W %": st.column_config.NumberColumn(
            f"52W % {_SORT}",
            format=None,
            width="small",
            help="Past-year return from fund narrative (proxy for 52-week %)",
        ),
        "Assets (B)": st.column_config.NumberColumn(
            f"Assets (B) {_SORT}",
            format=None,
            width="small",
        ),
        "Issuer": st.column_config.TextColumn(
            f"Issuer {_SORT}",
            width="medium",
        ),
        "Custodian": st.column_config.TextColumn(
            f"* Custodian {_SORT}",
            width="large",
            help="Filled only for selected **spot** Bitcoin and Ethereum funds in the curated map; "
            "otherwise blank. Bitcoin / digital-asset custody (and futures collateral where applicable).",
        ),
        "Inception": st.column_config.DatetimeColumn(
            f"Inception {_SORT}",
            format="YYYY-MM-DD",
            width="small",
        ),
        "Fund Filing": st.column_config.LinkColumn(
            f"Fund Filing {_SORT}",
            display_text="↗",
            validate=r"^https://",
            width="small",
            help="SEC EDGAR filing index or S-1 / search fallback",
        ),
    }
    column_config = {k: v for k, v in cfg.items() if k in df.columns}

    st.dataframe(
        style_etp_dataframe(df),
        use_container_width=True,
        height=height,
        hide_index=True,
        column_order=order,
        column_config=column_config,
    )
    st.markdown(ETP_CUSTODIAN_TABLE_NOTE_HTML, unsafe_allow_html=True)


def show_us_crypto_etps_widget(
    user_agent: str | None,
    *,
    home_preview: bool = False,
    preview_row_limit: int = 5,
) -> None:
    """
    U.S. crypto ETP table. On the home page, pass ``home_preview=True`` for a short slice
    without search (CoinDesk-style teaser); full sort/filter lives on ``US_Crypto_ETPs``.
    """
    st.markdown(WIDGET_CSS + KPI_WINDOW_NOTE_CSS + STREAMLIT_TABLE_UNIFY_CSS, unsafe_allow_html=True)

    ua = resolve_etp_user_agent(user_agent)
    with st.spinner("Loading U.S. digital asset ETPs (list + profile pages)…"):
        data = load_crypto_etps_cached(ua)

    h2_cls = "home-widget-heading" if home_preview else "home-main-heading"
    if data.error and not data.rows:
        st.markdown(
            f'<div class="jd-hub-subsection-head">'
            f'<h2 class="{h2_cls}">U.S. Digital Asset ETPs</h2></div>',
            unsafe_allow_html=True,
        )
        st.warning(escape(data.error))
        return

    rows = data.rows
    total = total_aum_usd(rows)
    aum_s = format_usd_compact(total) if total > 0 else "—"
    st.markdown(
        f'<div class="jd-hub-subsection-head">'
        f'<h2 class="{h2_cls}">U.S. Digital Asset ETPs</h2></div>',
        unsafe_allow_html=True,
    )

    if home_preview:
        render_etp_summary_kpi_row(rows, include_styles=False)
    else:
        st.markdown(
            f'<p class="etp-aum-line">Total AUM (listed, known assets): {escape(aum_s)}</p>',
            unsafe_allow_html=True,
        )

    q = ""
    if not home_preview:
        q = st.text_input(
            "Search by fund name or ticker",
            "",
            key="etf_search_home",
            placeholder="Filter by name or ticker…",
        )

    ranked = sorted_by_assets(rows)
    filtered = filter_rows_by_fund_name(ranked, q)
    cap = preview_row_limit if home_preview else 10
    display_rows = filtered[:cap]
    df = build_etp_dataframe(display_rows)
    empty_msg = None
    if df.empty and q.strip():
        empty_msg = "No funds match your search. Try a different name, ticker, or clear the search box."
    show_etp_dataframe(
        df,
        height=etp_table_height(max(len(df), 1)),
        empty_message=empty_msg,
    )
    if not home_preview:
        st.caption(ETP_DATA_SOURCE_CAPTION)

    if st.button("See full ETF list", key="see_full_etf_list", use_container_width=True, type="primary"):
        st.switch_page("pages/US_Crypto_ETPs.py")


def get_etp_user_agent_from_secrets() -> str | None:
    try:
        ua = st.secrets.get("STOCKANALYSIS_USER_AGENT", "")
    except Exception:
        return None
    if ua is None:
        return None
    s = str(ua).strip()
    return s or None
