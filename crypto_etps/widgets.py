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
.etp-aum-line {
    font-size: 0.95rem;
    font-weight: 700;
    color: #0f172a;
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


def clear_crypto_etp_cache() -> None:
    load_crypto_etps_cached.clear()


def _default_ua() -> str:
    return (
        "JPM-Digital/1.0 (crypto ETP list; set STOCKANALYSIS_USER_AGENT in secrets with contact email)"
    )


def resolve_etp_user_agent(user_agent: str | None) -> str:
    return (user_agent or "").strip() or _default_ua()


def show_etp_dataframe(df, *, height: int) -> None:
    """Sortable columns (Streamlit dataframe); 52W colors + display via Pandas Styler."""
    st.dataframe(
        style_etp_dataframe(df),
        use_container_width=True,
        height=height,
        hide_index=True,
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol", width="small"),
            "Fund name": st.column_config.TextColumn("Fund name", width="large"),
            "Issuer": st.column_config.TextColumn("Issuer", width="medium"),
        },
    )


def show_us_crypto_etps_widget(user_agent: str | None) -> None:
    st.markdown(WIDGET_CSS, unsafe_allow_html=True)

    ua = resolve_etp_user_agent(user_agent)
    with st.spinner("Loading U.S. crypto ETPs (list + profile pages)…"):
        data = load_crypto_etps_cached(ua)

    if data.error and not data.rows:
        st.markdown(
            '<div class="etp-widget-shell">'
            '<h2 class="home-main-heading">U.S. Crypto ETPs</h2>'
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
        f'<p class="etp-aum-line">Total AUM (listed, known assets): {escape(aum_s)}</p>'
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
