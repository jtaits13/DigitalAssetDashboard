"""Live JSON payload for RWA Global Market Overview (Streamlit iframe + static export)."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape as html_escape
from typing import Any

from home_layout import monthly_review_note_html
from rwa_global_macro_context import RWA_GLOBAL_MARKET_MACRO_CONTEXT_HTML

APP_RWA_NETWORKS_URL = "https://app.rwa.xyz/networks"
GLOBAL_MARKET_RWA_URL = APP_RWA_NETWORKS_URL
GLOBAL_MARKET_RWA_LINK_LABEL = "See RWA Networks on RWA.xyz"
RWA_GMO_CHART_MAX_BARS = 12
RWA_GLOBAL_MARKET_DATA_SOURCE_CAPTION_HTML = (
    'Source: <a href="https://app.rwa.xyz/">RWA.xyz homepage</a>—the same <strong>Global Market Overview</strong> '
    "headline figures and <strong>Networks</strong> league (Distributed / parent networks) shown on the live site, "
    "not RWA.xyz’s separate public API."
)
STATIC_RWA_EXPLORE_ASSET_TYPE_PAGE = "rwa-explore-asset-type.html"
STATIC_RWA_EXPLORE_MARKET_PARTICIPANT_PAGE = "rwa-explore-market-participant.html"


def _rwa_kpi_to_dict(k: object) -> dict[str, object]:
    delta = getattr(k, "delta_30d_pct", None)
    return {
        "label": str(getattr(k, "label", "")),
        "value_display": str(getattr(k, "value_display", "")),
        "delta_30d_pct": float(delta) if delta is not None else None,
    }


def _dataframe_json_records(df: Any) -> tuple[list[dict[str, object]], list[str]]:
    import numpy as np

    if df is None or getattr(df, "empty", True):
        return [], []
    cols = [str(c) for c in df.columns]
    rows_out: list[dict[str, object]] = []
    for rec in df.to_dict(orient="records"):
        row: dict[str, object] = {}
        for key, val in rec.items():
            k = str(key)
            if val is None:
                row[k] = None
                continue
            if isinstance(val, np.integer):
                row[k] = int(val)
            elif isinstance(val, np.floating):
                fv = float(val)
                row[k] = None if np.isnan(fv) or np.isinf(fv) else fv
            elif isinstance(val, float):
                row[k] = None if np.isnan(val) or np.isinf(val) else val
            elif isinstance(val, bool):
                row[k] = val
            elif isinstance(val, int):
                row[k] = val
            else:
                row[k] = val
        rows_out.append(row)
    return rows_out, cols


def _static_rwa_footer_text() -> str:
    return f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · Source: RWA.xyz"


def _rwa_explore_gateways_static_html(at_href: str, mp_href: str) -> str:
    ae = html_escape(at_href, quote=True)
    pe = html_escape(mp_href, quote=True)
    return (
        '<nav class="home-explore-compact" aria-label="Explore RWA">'
        '<span class="home-explore-compact__label">Explore</span>'
        f'<a class="home-explore-compact__btn" href="{ae}">By asset type</a>'
        f'<a class="home-explore-compact__btn" href="{pe}">By participant</a>'
        "</nav>"
    )


def _rwa_table_height(num_rows: int, *, max_h: int = 520) -> int:
    header = 38
    row_h = 35
    return min(max_h, header + row_h * max(1, num_rows))


def build_rwa_global_page_payload(
    *,
    rwa_rows: list[Any] | None = None,
    rwa_kpis: list[Any] | None = None,
    rwa_err: str | None = None,
    for_streamlit: bool = False,
) -> dict[str, Any]:
    """Build RWA Global Market Overview JSON (``rwa_global_market.json`` shape)."""
    import pandas as pd
    from rwa_league.dataframe_table import build_rwa_dataframe

    if rwa_rows is None or rwa_kpis is None:
        if for_streamlit:
            from rwa_streamlit_fetch_cache import cached_rwa_home_data

            fetched_rows, fetched_kpis, fetched_err = cached_rwa_home_data()
        else:
            from rwa_league.client import fetch_rwa_home_data

            fetched_rows, fetched_kpis, fetched_err = fetch_rwa_home_data()
        rwa_rows = fetched_rows if rwa_rows is None else rwa_rows
        rwa_kpis = fetched_kpis if rwa_kpis is None else rwa_kpis
        rwa_err = fetched_err if rwa_err is None else rwa_err

    explore_at = STATIC_RWA_EXPLORE_ASSET_TYPE_PAGE
    explore_mp = STATIC_RWA_EXPLORE_MARKET_PARTICIPANT_PAGE
    home_href = "index.html"
    if for_streamlit:
        from streamlit_site_parity import _streamlit_page_href

        explore_at = _streamlit_page_href("explore_asset")
        explore_mp = _streamlit_page_href("explore_participant")
        home_href = "/?jd_scroll=onchain"

    macro_html = RWA_GLOBAL_MARKET_MACRO_CONTEXT_HTML + monthly_review_note_html()
    kpi_window_note = (
        "All % changes in this row are 30-day (30D) (RWA.xyz). "
        "Headline totals from the RWA.xyz Global Market Overview."
    )

    rwa_full_df = build_rwa_dataframe(list(rwa_rows)) if rwa_rows else pd.DataFrame()
    rwa_full_rows, rwa_full_cols = _dataframe_json_records(rwa_full_df)

    n_sync = min(RWA_GMO_CHART_MAX_BARS, len(rwa_rows)) if rwa_rows else 1
    chart_h = _rwa_table_height(max(1, n_sync), max_h=560)
    chart_note_html = (
        f"The chart lists the top <strong>{RWA_GMO_CHART_MAX_BARS}</strong> networks "
        "by total value (labels include market share). Scroll the table for the full filtered list."
    )

    payload: dict[str, Any] = {
        "page_title": "RWA Global Market Overview — Digital Assets Dashboard",
        "page_subtitle_html": (
            "RWA <strong>Global Market Overview</strong>: <strong>headline metrics</strong> and a "
            '<strong>Networks</strong> table sourced from <a href="https://app.rwa.xyz/">RWA.xyz</a>. '
            "Top-line <strong>30D</strong> % changes and table values reflect RWA.xyz market-overview data."
        ),
        "error": rwa_err,
        "kpis": [_rwa_kpi_to_dict(k) for k in rwa_kpis],
        "kpi_window_note": kpi_window_note,
        "columns": rwa_full_cols,
        "rows": rwa_full_rows,
        "total_networks": len(rwa_rows or []),
        "macro_observations_html": "",
        "explore_gateways_html": "",
        "caption_html": "",
        "chart_max_bars": RWA_GMO_CHART_MAX_BARS,
        "chart_height_px": int(chart_h),
        "chart_note_html": chart_note_html,
        "links": {
            "home": home_href,
            "see_networks_on_rwa_xyz": APP_RWA_NETWORKS_URL,
            "global_market_on_rwa_xyz": GLOBAL_MARKET_RWA_URL,
            "global_market_link_label": GLOBAL_MARKET_RWA_LINK_LABEL,
            "explore_asset_type": explore_at,
            "explore_market_participant": explore_mp,
        },
        "footer_note": _static_rwa_footer_text(),
    }

    if rwa_err and not rwa_rows:
        pass
    elif not rwa_rows:
        payload["empty_message"] = "No network rows returned."
    else:
        payload["macro_observations_html"] = macro_html
        payload["explore_gateways_html"] = _rwa_explore_gateways_static_html(explore_at, explore_mp)
        payload["caption_html"] = RWA_GLOBAL_MARKET_DATA_SOURCE_CAPTION_HTML

    return payload
