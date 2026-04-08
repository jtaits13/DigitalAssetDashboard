"""Streamlit widget: SEC fund filings (crypto / digital assets / blockchain)."""

from __future__ import annotations

from html import escape

import streamlit as st

from sec_filings.client import FORM_TYPES_LABEL, FundFilingsResult, fetch_crypto_fund_filings

WIDGET_CSS = """
<style>
.sec-widget-shell {
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.75rem 1rem 1rem 1rem;
    margin-bottom: 0.5rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.sec-filing-list {
    max-height: 28rem;
    overflow-y: auto;
    font-size: 0.82rem;
    line-height: 1.35;
}
.sec-filing-item {
    border-bottom: 1px solid #e2e8f0;
    padding: 0.5rem 0;
}
.sec-filing-item:last-child { border-bottom: none; }
.sec-filing-meta {
    font-size: 0.72rem;
    color: #64748b;
    margin-top: 0.2rem;
}
a.sec-filing-link {
    color: #0f172a;
    font-weight: 600;
    text-decoration: none;
}
a.sec-filing-link:hover { text-decoration: underline; color: #0d9488; }
</style>
"""


def _default_user_agent() -> str:
    return "JPM-Digital/1.0 (SEC EDGAR widget; set SEC_EDGAR_USER_AGENT in secrets with your contact email per sec.gov)"


@st.cache_data(ttl=3600, show_spinner=False)
def load_fund_filings_cached(user_agent: str) -> FundFilingsResult:
    return fetch_crypto_fund_filings(user_agent)


def clear_fund_filings_cache() -> None:
    load_fund_filings_cached.clear()


def show_sec_fund_filings_widget(user_agent: str | None) -> None:
    st.markdown(WIDGET_CSS, unsafe_allow_html=True)
    ua = (user_agent or "").strip() or _default_user_agent()

    data = load_fund_filings_cached(ua)

    if data.error and not data.filings:
        st.markdown(
            '<div class="sec-widget-shell">'
            '<h2 class="home-main-heading">SEC fund filings · digital assets</h2>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.warning(escape(data.error))
        return

    st.markdown(
        '<div class="sec-widget-shell">'
        '<h2 class="home-main-heading">SEC fund filings · digital assets</h2>'
        "<p style=\"font-size:0.78rem;color:#64748b;margin:0 0 0.5rem 0;\">"
        f"Form types: {escape(FORM_TYPES_LABEL)}. Sourced via EDGAR.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    parts: list[str] = ['<div class="sec-filing-list">']
    for f in data.filings:
        safe_title = escape(f.title)
        safe_form = escape(f.form)
        safe_date = escape(f.file_date or "—")
        safe_url = escape(f.detail_url, quote=True)
        parts.append(
            f'<div class="sec-filing-item">'
            f'<a class="sec-filing-link" href="{safe_url}" target="_blank" rel="noopener noreferrer">'
            f"{safe_title}</a>"
            f'<div class="sec-filing-meta">{safe_form} · Filed {safe_date}</div>'
            f"</div>"
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)

    st.caption(
        "Links open SEC.gov filing viewers. "
        "[EDGAR search](https://www.sec.gov/edgar/search/) · "
        "Automated access must use a valid User-Agent with contact info ([SEC guidance](https://www.sec.gov/os/accessing-edgar-data))."
    )


def get_user_agent_from_secrets() -> str | None:
    try:
        ua = st.secrets.get("SEC_EDGAR_USER_AGENT", "")
    except Exception:
        return None
    if ua is None:
        return None
    s = str(ua).strip()
    return s or None
