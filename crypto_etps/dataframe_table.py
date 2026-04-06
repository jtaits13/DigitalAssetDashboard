"""Pandas DataFrame + Styler for sortable, searchable Streamlit ETF tables."""

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


def _fmt_52w(v: object) -> str:
    if pd.isna(v):
        return "—"
    fv = float(v)
    arrow = "▲" if fv >= 0 else "▼"
    return f"{arrow} {fv:+.2f}%"


def _fmt_price(v: object) -> str:
    if pd.isna(v):
        return "—"
    return f"${float(v):.2f}"


def _fmt_assets_b(v: object) -> str:
    if pd.isna(v):
        return "—"
    return f"{float(v):.2f}B"


def _fmt_inception(v: object) -> str:
    if pd.isna(v):
        return "—"
    if hasattr(v, "strftime"):
        return v.strftime("%b %d, %Y")
    return str(v)


def _fmt_issuer(v: object) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    s = str(v).strip()
    return s if s else "—"


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
                "Issuer": issuer if issuer else np.nan,
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
    """Green/red 52W column; formatted display; underlying data stays sortable."""

    def highlight_52w(s: pd.Series) -> list[str]:
        return [
            "color: #059669; font-weight: 600"
            if pd.notna(v) and float(v) >= 0
            else "color: #dc2626; font-weight: 600"
            if pd.notna(v) and float(v) < 0
            else ""
            for v in s
        ]

    return df.style.apply(highlight_52w, subset=["52W %"]).format(
        {
            "Price": _fmt_price,
            "52W %": _fmt_52w,
            "Assets (B)": _fmt_assets_b,
            "Inception": _fmt_inception,
            "Issuer": _fmt_issuer,
        },
        na_rep="—",
    )
