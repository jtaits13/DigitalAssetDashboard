"""Pandas DataFrame for the RWA league table in Streamlit.

Use ``style_rwa_dataframe`` for green/red **7D Δ value** only (``apply``, no ``format``);
number formatting comes from ``column_config`` so sorting stays numeric.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from rwa_league.client import RwaNetworkLeagueRow

_APP_BASE = "https://app.rwa.xyz"


def build_rwa_dataframe(rows: list[RwaNetworkLeagueRow]) -> pd.DataFrame:
    """
    Typed columns for st.dataframe sorting. Total Value in USD millions; 7D in percentage points.
    """
    recs: list[dict[str, object]] = []
    for r in rows:
        href = (r.network_href or "").strip()
        url = (_APP_BASE + href) if href.startswith("/") else f"{_APP_BASE}/"
        v7 = r.value_change_7d_raw
        if v7 is None:
            pct7 = np.nan
            d7_dir = ""
        else:
            f7 = float(v7)
            if np.isnan(f7):
                pct7 = np.nan
                d7_dir = ""
            else:
                pct7 = f7 * 100.0
                d7_dir = "\u25b2" if f7 >= 0 else "\u25bc"
        recs.append(
            {
                "#": int(r.rank),
                "Network": r.network,
                "Link": url,
                "RWA Count": int(r.rwa_count),
                "Total Value ($M)": float(r.total_value_usd) / 1e6,
                "7D dir": d7_dir,
                "7D Δ value": pct7,
                "Market Share": float(r.market_share_raw * 100.0),
            }
        )
    return pd.DataFrame(recs)


def style_rwa_dataframe(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Green/red on 7D Δ value and on ▲/▼ column — no ``.format()`` here."""

    def highlight_7d(s: pd.Series) -> list[str]:
        return [
            "color: #059669; font-weight: 600"
            if pd.notna(v) and float(v) >= 0
            else "color: #dc2626; font-weight: 600"
            if pd.notna(v) and float(v) < 0
            else ""
            for v in s
        ]

    def highlight_7d_dir(s: pd.Series) -> list[str]:
        up, down = "\u25b2", "\u25bc"
        return [
            "color: #059669; font-weight: 600"
            if v == up
            else "color: #dc2626; font-weight: 600"
            if v == down
            else ""
            for v in s
        ]

    return df.style.apply(highlight_7d, subset=["7D Δ value"]).apply(highlight_7d_dir, subset=["7D dir"])
