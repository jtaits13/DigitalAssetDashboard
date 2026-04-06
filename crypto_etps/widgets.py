"""Streamlit: U.S. crypto ETPs summary + link to full list page."""

from __future__ import annotations

from html import escape

import streamlit as st

from crypto_etps.client import (
    CryptoEtpsResult,
    fetch_crypto_etps_enriched,
    format_usd_compact,
    sorted_by_assets,
    total_aum_usd,
)
from crypto_etps.etf_flows import CombinedEtfFlows, fetch_combined_etf_flows, format_flow_millions
from crypto_etps.sec_prospectus import clear_sec_prospectus_caches
from crypto_etps.dataframe_table import (
    build_etp_dataframe,
    filter_rows_by_fund_name,
    style_etp_dataframe,
)

WIDGET_CSS = """
<style>
.etp-widget-shell {
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.75rem 1rem 1rem 1rem;
    margin-bottom: 0.5rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.etp-heading-line {
    font-size: 0.95rem;
    font-weight: 700;
    color: #1E7C99;
    margin: 0 0 0.35rem 0;
}
.etp-widget-shell .etp-heading-line + .etp-heading-line {
    margin-top: 0.65rem;
}
.etp-flow-detail {
    font-size: 0.88rem;
    color: #334155;
    line-height: 1.45;
    margin: 0 0 0.5rem 0;
}
.etp-flow-footnote {
    font-size: 0.72rem;
    color: #64748b;
    line-height: 1.4;
    margin: 0 0 0.75rem 0;
}
</style>
"""


def etp_table_height(num_rows: int, *, max_h: int = 520) -> int:
    header = 38
    row_h = 35
    return min(max_h, header + row_h * max(1, num_rows))


@st.cache_data(ttl=3600, show_spinner=False)
def load_crypto_etps_cached(user_agent: str) -> CryptoEtpsResult:
    return fetch_crypto_etps_enriched(user_agent)


@st.cache_data(ttl=3600, show_spinner=False)
def load_etf_flows_cached(user_agent: str) -> CombinedEtfFlows:
    return fetch_combined_etf_flows(user_agent)


def clear_crypto_etp_cache() -> None:
    load_crypto_etps_cached.clear()
    load_etf_flows_cached.clear()
    clear_sec_prospectus_caches()


def _default_ua() -> str:
    return (
        "JPM-Digital/1.0 (crypto ETP list; set STOCKANALYSIS_USER_AGENT in secrets with contact email)"
    )


def resolve_etp_user_agent(user_agent: str | None) -> str:
    return (user_agent or "").strip() or _default_ua()


def _format_flows_html(flows: CombinedEtfFlows) -> str:
    """HTML for daily net flows block + fund list footnote."""
    if flows.btc is None and flows.eth is None:
        esc = escape(flows.error or "Could not load flow data.")
        return (
            f'<p class="etp-heading-line">Daily inflows</p>'
            f'<p class="etp-flow-detail">Data temporarily unavailable ({esc}).</p>'
        )

    parts: list[str] = [
        '<p class="etp-heading-line">Daily inflows</p>',
        '<p class="etp-flow-detail">',
    ]
    c = flows.combined_usd_millions
    parts.append(f"Combined net (US$m): <strong>{escape(format_flow_millions(c))}</strong>")
    if flows.btc and flows.btc.net_flow_usd_millions is not None:
        parts.append(
            f" · Bitcoin spot: {escape(format_flow_millions(flows.btc.net_flow_usd_millions))} "
            f"({escape(flows.btc.as_of_date)})"
        )
    if flows.eth and flows.eth.net_flow_usd_millions is not None:
        parts.append(
            f" · Ethereum spot: {escape(format_flow_millions(flows.eth.net_flow_usd_millions))} "
            f"({escape(flows.eth.as_of_date)})"
        )
    parts.append(".</p>")

    fn: list[str] = []
    if flows.btc and flows.btc.tickers:
        fn.append(
            "US spot Bitcoin ETFs (tickers): "
            + escape(", ".join(flows.btc.tickers))
        )
    if flows.eth and flows.eth.tickers:
        fn.append(
            "US spot Ethereum ETFs (tickers): "
            + escape(", ".join(flows.eth.tickers))
        )
    foot = (
        '<p class="etp-flow-footnote">'
        + (" · ".join(fn) + " · " if fn else "")
        + 'Net flows from <a href="https://farside.co.uk/btc/" target="_blank" rel="noopener noreferrer">Farside Investors</a> '
        "(US$m; positive = inflow, negative = outflow), retrieved with Jina Reader; not affiliated."
    )
    if flows.error:
        foot += f" Note: {escape(flows.error)}"
    foot += "</p>"
    parts.append(foot)

    return "".join(parts)


def show_etp_dataframe(df, *, height: int) -> None:
    """Sortable columns (Streamlit dataframe); 52W colors + display via Pandas Styler."""
    st.dataframe(
        style_etp_dataframe(df),
        use_container_width=True,
        height=height,
        hide_index=True,
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol", width="small"),
            "Fund Name": st.column_config.TextColumn("Fund Name", width="large"),
            "Issuer": st.column_config.TextColumn("Issuer", width="medium"),
            "S-1": st.column_config.LinkColumn(
                "S-1",
                help="Newest S-1 filing document when available; otherwise EDGAR S-1 list or search.",
                display_text="Open",
                validate=r"^https://",
            ),
        },
    )


def show_us_crypto_etps_widget(user_agent: str | None) -> None:
    st.markdown(WIDGET_CSS, unsafe_allow_html=True)

    ua = resolve_etp_user_agent(user_agent)
    with st.spinner("Loading U.S. crypto ETPs (list + profile pages) and ETF flows…"):
        data = load_crypto_etps_cached(ua)
        flows = load_etf_flows_cached(ua)

    if data.error and not data.rows:
        st.markdown(
            '<div class="etp-widget-shell">'
            '<h2 class="home-main-heading">U.S. Crypto ETPs</h2>'
            '<p class="etp-heading-line">Total AUM (listed, known assets): —</p>'
            f"{_format_flows_html(flows)}"
            "</div>",
            unsafe_allow_html=True,
        )
        st.warning(escape(data.error))
        return

    rows = data.rows
    total = total_aum_usd(rows)
    aum_s = format_usd_compact(total) if total > 0 else "—"
    st.markdown(
        '<div class="etp-widget-shell">'
        '<h2 class="home-main-heading">U.S. Crypto ETPs</h2>'
        f'<p class="etp-heading-line">Total AUM (listed, known assets): {escape(aum_s)}</p>'
        f"{_format_flows_html(flows)}"
        "</div>",
        unsafe_allow_html=True,
    )

    st.caption(
        "Top 10 by assets (or matches when searching) · 52W % from past-year total return on each fund’s StockAnalysis profile · "
        "Click column headers to sort."
    )
    q = st.text_input(
        "Search fund name",
        "",
        key="etf_search_home",
        placeholder="Filter by fund name…",
    )

    ranked = sorted_by_assets(rows)
    filtered = filter_rows_by_fund_name(ranked, q)
    display_rows = filtered[:10]
    df = build_etp_dataframe(display_rows)
    show_etp_dataframe(df, height=etp_table_height(len(df)))

    if st.button("See full ETF list", key="see_full_etf_list", use_container_width=True, type="primary"):
        st.switch_page("pages/US_Crypto_ETPs.py")

    st.caption(
        "Source: [StockAnalysis.com crypto ETF list](https://stockanalysis.com/list/crypto-etfs/) "
        "and ETF detail pages (scraped; not affiliated)."
    )


def get_etp_user_agent_from_secrets() -> str | None:
    try:
        ua = st.secrets.get("STOCKANALYSIS_USER_AGENT", "")
    except Exception:
        return None
    if ua is None:
        return None
    s = str(ua).strip()
    return s or None
