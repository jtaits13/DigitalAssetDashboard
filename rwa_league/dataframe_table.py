"""Pandas DataFrame + Styler for sortable RWA league table in Streamlit."""

from __future__ import annotations

import numpy as np
import pandas as pd

from crypto_etps.client import format_usd_compact
from rwa_league.client import RwaNetworkLeagueRow

_APP_BASE = "https://app.rwa.xyz"


def build_rwa_dataframe(rows: list[RwaNetworkLeagueRow]) -> pd.DataFrame:
    """Numeric columns for correct sorting; Network URL + network_name for LinkColumn."""
    recs: list[dict[str, object]] = []
    for r in rows:
        href = (r.network_href or "").strip()
        url = (_APP_BASE + href) if href.startswith("/") else f"{_APP_BASE}/"
        v7 = r.value_change_7d_raw
        recs.append(
            {
                "#": int(r.rank),
                "Network": url,
                "network_name": r.network,
                "RWA Count": int(r.rwa_count),
                "Total Value": float(r.total_value_usd),
                "7D Δ value": float(v7) if v7 is not None else np.nan,
                "Market Share": float(r.market_share_raw * 100.0),
            }
        )
    return pd.DataFrame(recs)


def _fmt_total_value(v: object) -> str:
    if pd.isna(v):
        return "—"
    return format_usd_compact(float(v))


def _fmt_7d(v: object) -> str:
    if pd.isna(v):
        return "—"
    f = float(v)
    arrow = "▲" if f >= 0 else "▼"
    return f"{arrow} {abs(f * 100.0):.2f}%"


def _fmt_ms(v: object) -> str:
    if pd.isna(v):
        return "—"
    return f"{float(v):.2f}%"


def _fmt_rwa_count(v: object) -> str:
    if pd.isna(v):
        return "—"
    return f"{int(round(float(v))):,}"


def style_rwa_dataframe(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Green/red 7D column; compact currency; sortable underlying values."""

    def highlight_7d(s: pd.Series) -> list[str]:
        return [
            "color: #059669; font-weight: 600"
            if pd.notna(v) and float(v) >= 0
            else "color: #dc2626; font-weight: 600"
            if pd.notna(v) and float(v) < 0
            else ""
            for v in s
        ]

    return df.style.apply(highlight_7d, subset=["7D Δ value"]).format(
        {
            "Total Value": _fmt_total_value,
            "7D Δ value": _fmt_7d,
            "Market Share": _fmt_ms,
            "RWA Count": _fmt_rwa_count,
        },
        na_rep="—",
    )
