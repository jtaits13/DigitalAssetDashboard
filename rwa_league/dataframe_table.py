"""Pandas DataFrame for sortable RWA league table in Streamlit (no Styler — preserves sort)."""

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
        pct7 = (float(v7) * 100.0) if v7 is not None else np.nan
        recs.append(
            {
                "#": int(r.rank),
                "Network": r.network,
                "Link": url,
                "RWA Count": int(r.rwa_count),
                "Total Value ($M)": float(r.total_value_usd) / 1e6,
                "7D Δ value": pct7,
                "Market Share": float(r.market_share_raw * 100.0),
            }
        )
    return pd.DataFrame(recs)
