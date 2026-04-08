"""Pandas DataFrame builders for Streamlit ETF tables.

Sort + display: use ``column_config`` on ``st.dataframe``. For green/red 52W % cells, use
``style_etp_dataframe`` — **color only** (``Styler.apply``), **no** ``Styler.format``.
Streamlit applies number/text formatting from ``column_config`` on top of the underlying
values (docs: column_config overrides Styler formatting), so sorting stays correct.
"""

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
        pct = r.pct_52w
        if pct is None:
            pct_nan = np.nan
            w52_dir = ""
        else:
            fv = float(pct)
            if np.isnan(fv):
                pct_nan = np.nan
                w52_dir = ""
            else:
                pct_nan = fv
                w52_dir = "\u25b2" if fv >= 0 else "\u25bc"  # ▲ / ▼
        records.append(
            {
                "Symbol": r.symbol,
                "Fund Name": r.name,
                "Price": _parse_price(r.price),
                "52W dir": w52_dir,
                "52W %": pct_nan,
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


def style_etp_dataframe(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Green/red on 52W % and on ▲/▼ column — no ``.format()`` (keeps sort + column_config)."""

    def highlight_52w(s: pd.Series) -> list[str]:
        return [
            "color: #059669; font-weight: 600"
            if pd.notna(v) and float(v) >= 0
            else "color: #dc2626; font-weight: 600"
            if pd.notna(v) and float(v) < 0
            else ""
            for v in s
        ]

    def highlight_52w_dir(s: pd.Series) -> list[str]:
        up, down = "\u25b2", "\u25bc"
        return [
            "color: #059669; font-weight: 600"
            if v == up
            else "color: #dc2626; font-weight: 600"
            if v == down
            else ""
            for v in s
        ]

    return df.style.apply(highlight_52w, subset=["52W %"]).apply(highlight_52w_dir, subset=["52W dir"])
