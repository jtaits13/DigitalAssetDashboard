"""Home page widget: RWA.xyz Networks league table (embedded page data)."""

from __future__ import annotations

from html import escape

import streamlit as st

from crypto_etps.client import format_usd_compact
from rwa_league.client import RwaNetworkLeagueRow, fetch_rwa_network_league

WIDGET_CSS = """
<style>
.rwa-league-shell {
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.75rem 1rem 1rem 1rem;
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.rwa-league-shell h2.home-main-heading {
    margin-bottom: 0.35rem;
}
.rwa-league-scroll {
    max-height: 28rem;
    overflow: auto;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #ffffff;
}
.rwa-league-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
    line-height: 1.35;
}
.rwa-league-table thead th {
    position: sticky;
    top: 0;
    background: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
    padding: 0.5rem 0.45rem;
    text-align: left;
    font-weight: 700;
    color: #475569;
    white-space: nowrap;
}
.rwa-league-table td {
    padding: 0.45rem 0.45rem;
    border-bottom: 1px solid #f1f5f9;
    vertical-align: middle;
}
.rwa-league-table tbody tr:hover td {
    background: #f8fafc;
}
.rwa-league-table td.rwa-num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}
.rwa-league-table td.rwa-rank {
    text-align: center;
    width: 2.25rem;
    color: #64748b;
    font-weight: 600;
}
.rwa-pct-up { color: #059669; font-weight: 600; }
.rwa-pct-down { color: #dc2626; font-weight: 600; }
.rwa-net-link a {
    color: #0f172a;
    font-weight: 600;
    text-decoration: none;
}
.rwa-net-link a:hover { text-decoration: underline; color: #1E7C99; }
</style>
"""


def _fmt_value_delta(change_fraction: float | None) -> str:
    """▲/▼ change in total value — from embedded `value_7d_change` (7 days)."""
    if change_fraction is None:
        return '<span style="color:#94a3b8;">—</span>'
    pct = change_fraction * 100.0
    arrow = "▲" if change_fraction >= 0 else "▼"
    cls = "rwa-pct-up" if change_fraction >= 0 else "rwa-pct-down"
    body = f"{arrow} {abs(pct):.2f}%"
    return f'<span class="{cls}">{escape(body)}</span>'


def _rows_to_html(rows: list[RwaNetworkLeagueRow]) -> str:
    base = "https://app.rwa.xyz"
    thead = (
        "<thead><tr>"
        "<th>#</th><th>Network</th><th>RWA Count</th>"
        "<th>Total Value</th><th>7D Δ value</th><th>Market Share</th>"
        "</tr></thead>"
    )
    body_parts: list[str] = ["<tbody>"]
    for row in rows:
        tv = format_usd_compact(row.total_value_usd)
        ms = row.market_share_raw * 100.0
        ms_s = f"{ms:.2f}%"
        name_cell: str
        if row.network_href:
            url = base + row.network_href
            name_cell = (
                f'<td class="rwa-net-link"><a href="{escape(url, quote=True)}" '
                f'target="_blank" rel="noopener noreferrer">{escape(row.network)}</a></td>'
            )
        else:
            name_cell = f'<td>{escape(row.network)}</td>'
        body_parts.append(
            "<tr>"
            f'<td class="rwa-rank">{row.rank}</td>'
            f"{name_cell}"
            f'<td class="rwa-num">{row.rwa_count:,}</td>'
            f'<td class="rwa-num">{escape(tv)}</td>'
            f'<td class="rwa-num">{_fmt_value_delta(row.value_change_7d_raw)}</td>'
            f'<td class="rwa-num">{escape(ms_s)}</td>'
            "</tr>"
        )
    body_parts.append("</tbody>")
    return f'<table class="rwa-league-table">{thead}{"".join(body_parts)}</table>'


@st.cache_data(ttl=3600, show_spinner=False)
def load_rwa_league_cached() -> tuple[list[RwaNetworkLeagueRow], str | None]:
    return fetch_rwa_network_league()


def clear_rwa_league_cache() -> None:
    load_rwa_league_cached.clear()


def show_rwa_league_widget() -> None:
    st.markdown(WIDGET_CSS, unsafe_allow_html=True)
    rows, err = load_rwa_league_cached()

    if err and not rows:
        st.markdown(
            '<div class="rwa-league-shell">'
            '<h2 class="home-main-heading">RWA League Table · Networks (All)</h2></div>',
            unsafe_allow_html=True,
        )
        st.warning(escape(err))
        return

    if not rows:
        st.info("No network rows returned.")
        return

    intro = (
        '<div class="rwa-league-shell">'
        '<h2 class="home-main-heading">RWA League Table · Networks (All)</h2>'
        '<p style="font-size:0.78rem;color:#64748b;margin:0 0 0.65rem 0;">'
        "From "
        '<a href="https://app.rwa.xyz/" target="_blank" rel="noopener noreferrer">RWA.xyz</a> '
        "embedded data (not the API). "
        "The <strong>7D Δ value</strong> column is <strong>change in total value over 7 days</strong>.</p>"
        '<div class="rwa-league-scroll">'
        + _rows_to_html(rows)
        + "</div></div>"
    )
    st.markdown(intro, unsafe_allow_html=True)

    if err:
        st.caption(escape(f"Note: {err}"))
    st.caption(
        "Source: RWA.xyz app homepage (`app.rwa.xyz`) · "
        "“All” asset view, Networks grouping · "
        "Data may change without notice."
    )
