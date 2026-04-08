"""Pandas DataFrame builders for Streamlit ETF tables (plain dtypes; sort via column_config)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from crypto_etps.client import CryptoEtpRow
from crypto_etps.sec_prospectus import edgar_s1_fallback_url


def _parse_price(s: str) -> float:
    s = (s or "").strip().replace(",", "").replace("$", "")
    if not s:
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def build_etp_dataframe(rows: list[CryptoEtpRow]) -> pd.DataFrame:
    """Numeric / datetime columns for correct sorting in st.dataframe."""
    records: list[dict[str, object]] = []
    for r in rows:
        inc = pd.to_datetime(r.inception, errors="coerce") if (r.inception or "").strip() else pd.NaT
        issuer = (r.issuer or "").strip()
        s1 = (r.s1_filing_url or "").strip() or edgar_s1_fallback_url(r.symbol)
        records.append(
            {
                "Symbol": r.symbol,
                "Fund Name": r.name,
                "Price": _parse_price(r.price),
                "52W %": r.pct_52w if r.pct_52w is not None else np.nan,
                "Assets (B)": (r.assets_usd / 1e9) if r.assets_usd is not None else np.nan,
                # Empty string so client-side sort is A–Z / Z–A (NaN sorts oddly as text).
                "Issuer": issuer,
                "Inception": inc,
                "S-1": s1,
            }
        )
    return pd.DataFrame(records)


def filter_rows_by_fund_name(rows: list[CryptoEtpRow], query: str) -> list[CryptoEtpRow]:
    q = (query or "").strip().lower()
    if not q:
        return list(rows)
    return [r for r in rows if q in r.name.lower()]
