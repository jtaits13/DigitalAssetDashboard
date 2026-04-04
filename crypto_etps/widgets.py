"""Streamlit: U.S. crypto ETPs summary + link to full list page."""

from __future__ import annotations

from html import escape

import streamlit as st

from crypto_etps.client import (
    CryptoEtpsResult,
    fetch_crypto_etps_list,
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
.etp-widget-title {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #0f766e;
    font-weight: 700;
    margin: 0 0 0.35rem 0;
}
.etp-aum-line {
    font-size: 0.95rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 0.75rem 0;
}
</style>
"""


@st.cache_data(ttl=3600, show_spinner=False)
def load_crypto_etps_cached(user_agent: str) -> CryptoEtpsResult:
    return fetch_crypto_etps_list(user_agent)


def clear_crypto_etp_cache() -> None:
    load_crypto_etps_cached.clear()


def _default_ua() -> str:
    return (
        "JPM-Digital/1.0 (crypto ETP list; set STOCKANALYSIS_USER_AGENT in secrets with contact email)"
    )


def resolve_etp_user_agent(user_agent: str | None) -> str:
    return (user_agent or "").strip() or _default_ua()


def show_us_crypto_etps_widget(user_agent: str | None) -> None:
    st.markdown(WIDGET_CSS, unsafe_allow_html=True)
    data = load_crypto_etps_cached(resolve_etp_user_agent(user_agent))

    if data.error and not data.rows:
        st.markdown(
            '<div class="etp-widget-shell">'
            '<p class="etp-widget-title">U.S. Crypto ETPs</p>'
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
        '<p class="etp-widget-title">U.S. Crypto ETPs</p>'
        f'<p class="etp-aum-line">Total AUM (listed, known assets): {escape(aum_s)}</p>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.caption("Top 10 by assets")
    top10 = sorted_by_assets(rows)[:10]
    st.dataframe(
        [
            {
                "Symbol": r.symbol,
                "Fund name": r.name,
                "Price": r.price,
                "% Chg": r.pct_change,
                "Assets": r.assets_display,
            }
            for r in top10
        ],
        use_container_width=True,
        hide_index=True,
        height=min(420, 56 + 36 * len(top10)),
    )

    if st.button("See full ETF list", key="see_full_etf_list", use_container_width=True, type="primary"):
        st.switch_page("pages/US_Crypto_ETPs.py")

    st.caption(
        "Source: [StockAnalysis.com crypto ETF list](https://stockanalysis.com/list/crypto-etfs/) "
        "(scraped; not affiliated). Figures reflect the page at fetch time."
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
