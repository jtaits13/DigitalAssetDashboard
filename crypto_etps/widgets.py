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
from crypto_etps.sec_prospectus import clear_sec_prospectus_caches
from crypto_etps.dataframe_table import (
    build_etp_dataframe,
    filter_rows_by_fund_name,
    style_etp_dataframe,
)
from home_layout import (
    STREAMLIT_DATAFRAME_TEAL_HEADER_CSS,
    STREAMLIT_TABLE_UNIFY_CSS,
    inject_dataframe_teal_header_fix,
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
    margin: 0.5rem 0 0.75rem 0;
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
    clear_sec_prospectus_caches()


def _default_ua() -> str:
    return (
        "JPM-Digital/1.0 (crypto ETP list; set STOCKANALYSIS_USER_AGENT in secrets with contact email)"
    )


def resolve_etp_user_agent(user_agent: str | None) -> str:
    return (user_agent or "").strip() or _default_ua()


_SORT = "\u2195"  # ↕ sort hint in column headers

ETP_DATA_SOURCE_CAPTION = (
    "Source: [StockAnalysis.com crypto ETF list](https://stockanalysis.com/list/crypto-etfs/) "
    "and ETF detail pages (scraped; not affiliated)."
)


def show_etp_dataframe(df, *, height: int) -> None:
    """Styler formats 52W % (arrow + %) and Assets (B) (compact USD); ``format=None`` avoids overriding."""
    st.dataframe(
        style_etp_dataframe(df),
        use_container_width=True,
        height=height,
        hide_index=True,
        column_config={
            "Symbol": st.column_config.TextColumn(
                f"Symbol {_SORT}",
                width="small",
                help="Ascending: A→Z · Descending: Z→A",
            ),
            "Fund Name": st.column_config.TextColumn(
                f"Fund Name {_SORT}",
                width="large",
                help="Ascending: A→Z · Descending: Z→A",
            ),
            "Price": st.column_config.NumberColumn(
                f"Price {_SORT}",
                format="$%.2f",
                help="Ascending: lowest first · Descending: highest first",
            ),
            "52W %": st.column_config.NumberColumn(
                f"52W % {_SORT}",
                format=None,
                width=100,
                help="Past-year total return — Ascending: lowest first",
            ),
            "Assets (B)": st.column_config.NumberColumn(
                f"Assets (B) {_SORT}",
                format=None,
                width=140,
                help="AUM (compact USD) — Ascending: smallest first",
            ),
            "Issuer": st.column_config.TextColumn(
                f"Issuer {_SORT}",
                width="medium",
                help="Ascending: A→Z · Descending: Z→A",
            ),
            "Inception": st.column_config.DatetimeColumn(
                f"Inception {_SORT}",
                format="MMM DD, YYYY",
                help="Ascending: oldest first · Descending: newest first",
            ),
            "S-1": st.column_config.LinkColumn(
                f"S-1 {_SORT}",
                help="Newest S-1 filing document when available; otherwise EDGAR S-1 list or search. "
                "Sort order follows the filing URL.",
                display_text="Open",
                validate=r"^https://",
            ),
        },
    )


def show_us_crypto_etps_widget(user_agent: str | None) -> None:
    st.markdown(
        WIDGET_CSS + STREAMLIT_TABLE_UNIFY_CSS + STREAMLIT_DATAFRAME_TEAL_HEADER_CSS,
        unsafe_allow_html=True,
    )

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
        "</div>",
        unsafe_allow_html=True,
    )

    q = st.text_input(
        "Search fund name",
        "",
        key="etf_search_home",
        placeholder="Filter by fund name…",
    )

    st.markdown(
        f'<p class="etp-aum-line">Total AUM (listed, known assets): {escape(aum_s)}</p>',
        unsafe_allow_html=True,
    )

    ranked = sorted_by_assets(rows)
    filtered = filter_rows_by_fund_name(ranked, q)
    display_rows = filtered[:10]
    df = build_etp_dataframe(display_rows)
    show_etp_dataframe(df, height=etp_table_height(len(df)))
    inject_dataframe_teal_header_fix()
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
