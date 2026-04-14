"""Pandas DataFrame for the RWA league table in Streamlit.

``style_rwa_dataframe`` applies green/red and ``Styler.format`` for **7D Δ value** (arrow + %)
and **Total Value** (compact USD). Use ``NumberColumn(..., format=None)`` for those columns
so Styler display is not overridden.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from crypto_etps.client import format_usd_compact
from rwa_league.client import (
    RwaNetworkLeagueRow,
    RwaStablecoinPlatformRow,
    RwaTreasuryDistributedNetworkRow,
)

_APP_BASE = "https://app.rwa.xyz"


def build_rwa_dataframe(rows: list[RwaNetworkLeagueRow]) -> pd.DataFrame:
    """
    Total Value in USD (float); 7D in percentage points (fraction × 100) for sorting.
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
        ms30 = r.market_share_change_30d_raw
        if ms30 is None:
            pct_ms30 = np.nan
        else:
            fm = float(ms30)
            pct_ms30 = np.nan if np.isnan(fm) else fm * 100.0
        recs.append(
            {
                "#": int(r.rank),
                "Network": r.network,
                "Link": url,
                "RWA Count": int(r.rwa_count),
                "Total Value": float(r.total_value_usd),
                "7D Δ value": pct7,
                "Market Share": float(r.market_share_raw * 100.0),
                "30D Δ share": pct_ms30,
            }
        )
    return pd.DataFrame(recs)


def build_us_treasury_network_dataframe(rows: list[RwaTreasuryDistributedNetworkRow]) -> pd.DataFrame:
    """Same as ``build_rwa_dataframe`` but the value column is labeled **Distributed Value** (US Treasuries embed)."""

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
        ms30 = r.market_share_change_30d_raw
        if ms30 is None:
            pct_ms30 = np.nan
        else:
            fm = float(ms30)
            pct_ms30 = np.nan if np.isnan(fm) else fm * 100.0
        recs.append(
            {
                "#": int(r.rank),
                "Network": r.network,
                "Link": url,
                "RWA Count": int(r.rwa_count),
                "Distributed Value": float(r.total_value_usd),
                "7D Δ value": pct7,
                "Market Share": float(r.market_share_raw * 100.0),
                "30D Δ share": pct_ms30,
            }
        )
    return pd.DataFrame(recs)


def build_stablecoin_platform_dataframe(rows: list[RwaStablecoinPlatformRow]) -> pd.DataFrame:
    """Platform market cap in USD; 7D / 30D deltas as percentage points (fraction × 100)."""
    recs: list[dict[str, object]] = []
    for r in rows:
        href = (r.platform_href or "").strip()
        url = f"{_APP_BASE}{href}" if href.startswith("/") else f"{_APP_BASE}/"
        v7 = r.value_change_7d_raw
        if v7 is None:
            pct7 = np.nan
        else:
            f7 = float(v7)
            pct7 = np.nan if np.isnan(f7) else f7 * 100.0
        ms30 = r.market_share_change_30d_raw
        if ms30 is None:
            pct_ms30 = np.nan
        else:
            fm = float(ms30)
            pct_ms30 = np.nan if np.isnan(fm) else fm * 100.0
        recs.append(
            {
                "#": int(r.rank),
                "Platform": r.platform,
                "Link": url,
                "Stablecoins": int(r.stablecoin_count),
                "Total Value": float(r.total_value_usd),
                "7D Δ value": pct7,
                "Market Share": float(r.market_share_raw * 100.0),
                "30D Δ share": pct_ms30,
            }
        )
    return pd.DataFrame(recs)


def filter_stablecoin_platform_rows(
    rows: list[RwaStablecoinPlatformRow], query: str
) -> list[RwaStablecoinPlatformRow]:
    q = (query or "").strip().lower()
    if not q:
        return list(rows)
    return [r for r in rows if q in (r.platform or "").lower()]


def filter_rows_by_network(rows: list[RwaNetworkLeagueRow], query: str) -> list[RwaNetworkLeagueRow]:
    q = (query or "").strip().lower()
    if not q:
        return list(rows)
    return [r for r in rows if q in (r.network or "").lower()]


def filter_treasury_network_rows(
    rows: list[RwaTreasuryDistributedNetworkRow], query: str
) -> list[RwaTreasuryDistributedNetworkRow]:
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
    if pd.isna(v):
        return "—"
    return f"{float(v):.2f}%"


def style_stablecoin_platform_dataframe(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Green/red for 7D value and 30D share columns."""

    def highlight_delta(s: pd.Series) -> list[str]:
        return [
            "color: #059669; font-weight: 600"
            if pd.notna(v) and float(v) >= 0
            else "color: #dc2626; font-weight: 600"
            if pd.notna(v) and float(v) < 0
            else ""
            for v in s
        ]

    styler = df.style.apply(highlight_delta, subset=["7D Δ value"]).apply(
        highlight_delta, subset=["30D Δ share"]
    )
    return styler.format(
        {
            "7D Δ value": _fmt_7d_cell,
            "30D Δ share": _fmt_7d_cell,
            "Total Value": _fmt_total_value_cell,
            "Market Share": _fmt_market_share_cell,
        },
        na_rep="—",
    )


def style_us_treasury_network_dataframe(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Same styling as ``style_rwa_dataframe`` for the **Distributed Value** column name."""

    def highlight_delta(s: pd.Series) -> list[str]:
        return [
            "color: #059669; font-weight: 600"
            if pd.notna(v) and float(v) >= 0
            else "color: #dc2626; font-weight: 600"
            if pd.notna(v) and float(v) < 0
            else ""
            for v in s
        ]

    return df.style.apply(highlight_delta, subset=["7D Δ value"]).apply(
        highlight_delta, subset=["30D Δ share"]
    ).format(
        {
            "7D Δ value": _fmt_7d_cell,
            "30D Δ share": _fmt_7d_cell,
            "Distributed Value": _fmt_total_value_cell,
            "Market Share": _fmt_market_share_cell,
        },
        na_rep="—",
    )


def style_rwa_dataframe(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Green/red for 7D value and 30D share; arrow + % and compact USD via ``format``."""

    def highlight_delta(s: pd.Series) -> list[str]:
        return [
            "color: #059669; font-weight: 600"
            if pd.notna(v) and float(v) >= 0
            else "color: #dc2626; font-weight: 600"
            if pd.notna(v) and float(v) < 0
            else ""
            for v in s
        ]

    return df.style.apply(highlight_delta, subset=["7D Δ value"]).apply(
        highlight_delta, subset=["30D Δ share"]
    ).format(
        {
            "7D Δ value": _fmt_7d_cell,
            "30D Δ share": _fmt_7d_cell,
            "Total Value": _fmt_total_value_cell,
            "Market Share": _fmt_market_share_cell,
        },
        na_rep="—",
    )
