"""HTML builders shared by FastAPI routes (mirror Streamlit widget output, no placeholders)."""

from __future__ import annotations

import os
from html import escape
from typing import Any

from pandas.io.formats.style import Styler

from crypto_etps.aum_history import (
    aggregate_aum_pct_from_history,
    etp_rows_to_fund_pairs,
    etp_symbol_price_change_cached,
    load_aggregate_aum_history_cached,
)
from crypto_etps.kpi_labels import etp_delta_window_caption, etp_kpi_methodology_footnote_html
from crypto_etps.client import (
    CryptoEtpRow,
    format_usd_compact,
    has_listed_aum_usd,
    total_aum_usd,
)
from crypto_etps.widgets import (
    _ETP_KPI_PANEL_INLINE_STYLE,
    _etf_delta_html,
    _row_by_symbol,
)
from rwa_league.client import RwaGlobalKpi
from rwa_league.widgets import (
    _RWA_KPI_PANEL_INLINE_STYLE,
    _format_pct_change_30d,
    _rwa_kpi_window_note_html,
)


def etp_user_agent() -> str | None:
    s = (os.environ.get("STOCKANALYSIS_USER_AGENT") or "").strip()
    return s or None


def styled_dataframe_to_html(styler: Styler, *, table_id: str | None = None) -> str:
    kwargs: dict[str, Any] = {
        "table_id": table_id,
        "na_rep": "—",
    }
    html = styler.to_html(**kwargs)
    return f'<div class="table-scroll">{html}</div>'


def rwa_overview_kpi_inline_html(
    kpis: list[RwaGlobalKpi],
    *,
    overview_title: str,
) -> str:
    """Same KPI panel as RWA stablecoin / treasuries overview rows in ``rwa_league.widgets``."""
    if not kpis:
        return ""
    cells: list[str] = []
    for k in kpis:
        delta_html = ""
        fd = _format_pct_change_30d(k.delta_30d_pct)
        if fd is not None:
            txt, cls = fd
            delta_html = f"<span class='rwa-kpi-delta {cls}'>{txt}</span>"
        cells.append(
            "<div class='rwa-kpi-cell'>"
            f"<span class='rwa-kpi-label'>{escape(k.label)}</span>"
            f"<span class='rwa-kpi-val'>{escape(k.value_display)}</span>"
            f"{delta_html}"
            "</div>"
        )
    row = "<div class='rwa-kpi-row'>" + "".join(cells) + "</div>"
    legend = _rwa_kpi_window_note_html(overview_title=overview_title)
    return (
        f'<div class="rwa-kpi-wrap" style="{escape(_RWA_KPI_PANEL_INLINE_STYLE, quote=True)}">'
        f"{legend}{row}</div>"
    )


def rwa_global_kpi_block_html(
    kpis: list[RwaGlobalKpi],
    *,
    kpi_legend_name: str = "Global Market",
    tight_bottom: bool = False,
) -> str:
    if not kpis:
        return ""
    cells: list[str] = []
    for k in kpis:
        delta_html = ""
        fd = _format_pct_change_30d(k.delta_30d_pct)
        if fd is not None:
            txt, cls = fd
            delta_html = f"<span class='rwa-kpi-delta {cls}'>{txt}</span>"
        cells.append(
            "<div class='rwa-kpi-cell'>"
            f"<span class='rwa-kpi-label'>{escape(k.label)}</span>"
            f"<span class='rwa-kpi-val'>{escape(k.value_display)}</span>"
            f"{delta_html}"
            "</div>"
        )
    row = "<div class='rwa-kpi-row'>" + "".join(cells) + "</div>"
    mb = "0.35rem" if tight_bottom else "0.9rem"
    panel_style = (
        "background-color:#ffffff;border:1px solid #C7D8E8;border-radius:10px;"
        "box-shadow:0 1px 3px rgba(15,23,42,0.06);padding:0.65rem 0.9rem 0.55rem;"
        f"margin:0.45rem 0 {mb} 0;box-sizing:border-box;"
    )
    return (
        f'<div class="rwa-kpi-wrap" style="{escape(panel_style, quote=True)}">'
        f"{_rwa_kpi_window_note_html(overview_title=kpi_legend_name)}"
        f"{row}"
        "</div>"
    )


def _fund_trailing_pct(symbol: str, row: CryptoEtpRow | None) -> tuple[float | None, str]:
    py, pl = etp_symbol_price_change_cached(symbol)
    if py is not None:
        return py, pl
    if row is not None and row.pct_52w is not None:
        return float(row.pct_52w), "52W"
    return None, ""


def etp_summary_kpi_row_html(
    rows: list[CryptoEtpRow],
    *,
    metrics_above_methodology_note: bool = False,
) -> str:
    """Same KPI strip as :func:`crypto_etps.widgets.render_etp_summary_kpi_row` but as HTML."""
    total = total_aum_usd(rows)
    aum_s = format_usd_compact(total) if total > 0 else "—"
    pairs = etp_rows_to_fund_pairs(rows)
    hist_df, _hist_err = load_aggregate_aum_history_cached(pairs)
    agg_pct, agg_win = aggregate_aum_pct_from_history(hist_df)
    ibit_r = _row_by_symbol(rows, "IBIT")
    etha_r = _row_by_symbol(rows, "ETHA")
    ibit_aum = (
        format_usd_compact(ibit_r.assets_usd)
        if ibit_r and has_listed_aum_usd(ibit_r.assets_usd)
        else "—"
    )
    etha_aum = (
        format_usd_compact(etha_r.assets_usd)
        if etha_r and has_listed_aum_usd(etha_r.assets_usd)
        else "—"
    )
    ip, ip_win = _fund_trailing_pct("IBIT", ibit_r)
    ep, ep_win = _fund_trailing_pct("ETHA", etha_r)

    cells: list[tuple[str, str, str]] = [
        ("Total AUM (listed)", escape(aum_s), _etf_delta_html(agg_pct, etp_delta_window_caption(agg_win))),
        ("IBIT · AUM", escape(ibit_aum), _etf_delta_html(ip, etp_delta_window_caption(ip_win))),
        ("ETHA · AUM", escape(etha_aum), _etf_delta_html(ep, etp_delta_window_caption(ep_win))),
    ]
    parts: list[str] = []
    for label, val_html, delta_html in cells:
        parts.append(
            "<div class='etp-kpi-cell'>"
            f"<span class='etp-kpi-label'>{escape(label)}</span>"
            f"<span class='etp-kpi-val'>{val_html}</span>"
            f"{delta_html}"
            "</div>"
        )
    note_block = etp_kpi_methodology_footnote_html()
    row_block = f"<div class='etp-kpi-row'>{''.join(parts)}</div>"
    wrap_class = (
        "etp-kpi-wrap etp-kpi-wrap--metrics-first"
        if metrics_above_methodology_note
        else "etp-kpi-wrap"
    )
    inner = row_block + note_block
    return (
        f'<div class="{wrap_class}" style="{_ETP_KPI_PANEL_INLINE_STYLE}">'
        f"{inner}"
        "</div>"
    )


def plotly_figure_to_div(fig: Any, *, plotly_config: dict[str, Any] | None = None) -> str:
    import plotly.io as pio

    cfg: dict[str, Any] = {"displayModeBar": True, "scrollZoom": True}
    if plotly_config:
        cfg.update(plotly_config)
    return pio.to_html(
        fig,
        full_html=False,
        include_plotlyjs="cdn",
        config=cfg,
    )


def rwa_explore_gateways_html(key_prefix: str = "web") -> str:
    """Two-column Explore cards (same links as Streamlit home On-chain section)."""
    at_url = "/rwa/explore/asset-type"
    mp_url = "/rwa/explore/participant"
    return f"""
<section class="rwa-explore-row">
  <div class="rwa-explore-card">
    <p class="eyebrow">On-chain</p>
    <h3 id="{key_prefix}-asset">Explore by Asset Type</h3>
    <ul class="rwa-explore-list">
      <li>Stablecoins</li>
      <li>US Treasuries</li>
      <li>Tokenized Stocks</li>
    </ul>
    <p class="rwa-explore-tail">Use <strong>Explore</strong> to open the hub and go deeper on the next pages.</p>
    <a class="btn primary" href="{at_url}">Explore</a>
  </div>
  <div class="rwa-explore-card">
    <p class="eyebrow">On-chain</p>
    <h3 id="{key_prefix}-mp">Explore by Market Participant</h3>
    <ul class="rwa-explore-list">
      <li>Networks</li>
      <li>Platforms</li>
      <li>Asset Managers</li>
    </ul>
    <p class="rwa-explore-tail">Use <strong>Explore</strong> to open the hub and go deeper on the next pages.</p>
    <a class="btn primary" href="{mp_url}">Explore</a>
  </div>
</section>
"""
