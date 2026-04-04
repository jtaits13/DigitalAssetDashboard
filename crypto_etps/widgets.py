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
.etp-table-wrap {
    overflow-x: auto;
    margin-bottom: 0.5rem;
}
table.etp-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
    line-height: 1.35;
}
table.etp-table thead th {
    font-weight: 700;
    text-align: left;
    padding: 0.45rem 0.5rem;
    border-bottom: 2px solid #cbd5e1;
    color: #0f172a;
    background: #f8fafc;
}
table.etp-table tbody td {
    padding: 0.4rem 0.5rem;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
}
.etp-pct-up {
    color: #059669;
    font-weight: 600;
    white-space: nowrap;
}
.etp-pct-down {
    color: #dc2626;
    font-weight: 600;
    white-space: nowrap;
}
.etp-pct-na {
    color: #94a3b8;
    font-weight: 500;
}
</style>
"""


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


def _format_52w_cell(pct: float | None) -> str:
    """HTML cell for past-year / 52W % (green ▲ / red ▼ like price ticker)."""
    if pct is None:
        return '<span class="etp-pct-na">—</span>'
    arrow = "▲" if pct >= 0 else "▼"
    sign = "+" if pct > 0 else ""
    cls = "etp-pct-up" if pct >= 0 else "etp-pct-down"
    return f'<span class="{cls}">{arrow} {sign}{pct:.2f}%</span>'


def render_etp_table_html(rows: list[CryptoEtpRow], *, max_rows: int | None = None) -> str:
    """Scrollable HTML table with bold header row; 52W uses ticker-style colors."""
    use = rows if max_rows is None else rows[:max_rows]
    thead = (
        "<thead><tr>"
        "<th>Symbol</th>"
        "<th>Fund name</th>"
        "<th>Price</th>"
        "<th>52W %</th>"
        "<th>Assets</th>"
        "<th>Issuer</th>"
        "<th>Inception</th>"
        "</tr></thead>"
    )
    body_parts: list[str] = []
    for r in use:
        body_parts.append(
            "<tr>"
            f"<td>{escape(r.symbol)}</td>"
            f"<td>{escape(r.name)}</td>"
            f"<td>{escape(r.price)}</td>"
            f"<td>{_format_52w_cell(r.pct_52w)}</td>"
            f"<td>{escape(r.assets_display)}</td>"
            f"<td>{escape(r.issuer or '—')}</td>"
            f"<td>{escape(r.inception or '—')}</td>"
            "</tr>"
        )
    return (
        f'<div class="etp-table-wrap"><table class="etp-table">{thead}<tbody>{"".join(body_parts)}</tbody></table></div>'
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

    st.caption("Top 10 by assets · 52W % from past-year total return on each fund’s StockAnalysis profile")
    top10 = sorted_by_assets(rows)[:10]
    st.markdown(render_etp_table_html(top10), unsafe_allow_html=True)

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
