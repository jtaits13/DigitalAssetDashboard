"""Pandas DataFrame for the RWA league table in Streamlit.

``style_rwa_dataframe`` applies green/red and ``Styler.format`` for **7D Δ value** (arrow + %)
and **Total Value** (compact USD). Use ``NumberColumn(..., format=None)`` for those columns
so Styler display is not overridden.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from crypto_etps.client import format_usd_compact
from rwa_league.client import RwaNetworkLeagueRow

_APP_BASE = "https://app.rwa.xyz"


def build_rwa_dataframe(rows: list[RwaNetworkLeagueRow]) -> pd.DataFrame:
    """
    Total Value in USD (float); 7D in percentage points (fraction × 100) for sorting.
    Market Share stores (current_share_pct, market_share_7d_change_raw|None).
    """
    recs: list[dict[str, object]] = []
    for r in rows:
        href = (r.network_href or "").strip()
        url = f"{_APP_BASE}{href}" if href.startswith("/") else f"{_APP_BASE}/"
        v7 = r.value_change_7d_raw
        if v7 is None:
            pct7 = np.nan
        else:
            f7 = float(v7)
            pct7 = np.nan if np.isnan(f7) else f7 * 100.0
        ms_change_7d = getattr(r, "market_share_change_7d_raw", None)
        recs.append(
            {
                "#": int(r.rank),
                "Network": r.network,
                "Link": url,
                "RWA Count": int(r.rwa_count),
                "Total Value": float(r.total_value_usd),
                "7D Δ value": pct7,
                "Market Share": (float(r.market_share_raw * 100.0), ms_change_7d),
            }
        )
    return pd.DataFrame(recs)


def filter_rows_by_network(rows: list[RwaNetworkLeagueRow], query: str) -> list[RwaNetworkLeagueRow]:
    q = (query or "").strip().lower()
    if not q:
        return list(rows)
    return [r for r in rows if q in (r.network or "").lower()]


def _fmt_7d_cell(v: object) -> str:
    if pd.isna(v):
        return "—"
    p = float(v)
    arrow = "\u25b2" if p >= 0 else "\u25bc"
    return f"{arrow} {abs(p):.2f}%"


def _fmt_total_value_cell(v: object) -> str:
    if pd.isna(v):
        return "—"
    return format_usd_compact(float(v))


def _fmt_market_share_cell(v: object) -> str:
    if isinstance(v, tuple) and len(v) == 2:
        pct, delta = v
    else:
        pct, delta = v, None
    if pd.isna(pct):
        return "—"
    pf = float(pct)
    if delta is None or pd.isna(delta):
        return f"{pf:.2f}%"
    df = float(delta)
    if df > 0:
        return f"\u25b2 {pf:.2f}%"
    if df < 0:
        return f"\u25bc {pf:.2f}%"
    return f"{pf:.2f}%"


def style_rwa_dataframe(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Green/red 7D; arrow + % and compact USD via ``format`` (numeric dtypes unchanged)."""

    def highlight_7d(s: pd.Series) -> list[str]:
        return [
            "color: #059669; font-weight: 600"
            if pd.notna(v) and float(v) >= 0
            else "color: #dc2626; font-weight: 600"
            if pd.notna(v) and float(v) < 0
            else ""
            for v in s
        ]

    def highlight_market_share(s: pd.Series) -> list[str]:
        out: list[str] = []
        for v in s:
            if isinstance(v, tuple) and len(v) == 2 and v[1] is not None and not pd.isna(v[1]):
                delta = float(v[1])
                if delta > 0:
                    out.append("color: #059669; font-weight: 600")
                elif delta < 0:
                    out.append("color: #dc2626; font-weight: 600")
                else:
                    out.append("")
            else:
                out.append("")
        return out

    return df.style.apply(highlight_7d, subset=["7D Δ value"]).apply(
        highlight_market_share, subset=["Market Share"]
    ).format(
        {
            "7D Δ value": _fmt_7d_cell,
            "Total Value": _fmt_total_value_cell,
            "Market Share": _fmt_market_share_cell,
        },
        na_rep="—",
    )
