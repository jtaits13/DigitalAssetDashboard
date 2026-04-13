"""Pandas DataFrame builders for Streamlit ETF tables.

Numeric columns stay typed for sorting. ``style_etp_dataframe`` uses ``Styler.apply`` for
green/red 52W % text and ``Styler.format`` only on ``52W %`` / ``Assets (B)`` so arrows
and compact **$** assets (``format_usd_compact`` on AUM in USD) appear in-cell. In ``show_etp_dataframe``, those columns use
``NumberColumn(..., format=None)`` so Streamlit does not override Styler formatting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from crypto_etps.client import CryptoEtpRow, format_usd_compact
from crypto_etps.sec_prospectus import edgar_s1_fallback_url


def format_strategy_cell(about: str, index_tracked: str) -> str:
    """One table cell: Index Tracked line (if any) + About narrative from StockAnalysis."""
    parts: list[str] = []
    idx = (index_tracked or "").strip()
    ab = (about or "").strip()
    if idx:
        parts.append(f"Index: {idx}")
    if ab:
        if len(ab) > 320:
            ab = ab[:317] + "…"
        parts.append(ab)
    if not parts:
        return "—"
    return "\n".join(parts)


def _parse_price(s: str) -> float:
    s = (s or "").strip().replace(",", "").replace("$", "")
    if not s:
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def build_etp_dataframe(rows: list[CryptoEtpRow], *, include_strategy: bool = False) -> pd.DataFrame:
    """Numeric / datetime columns for correct sorting in st.dataframe."""
    records: list[dict[str, object]] = []
    for r in rows:
        inc = pd.to_datetime(r.inception, errors="coerce") if (r.inception or "").strip() else pd.NaT
        issuer = (r.issuer or "").strip()
        fund_filing = (r.fund_filing_url or "").strip() or edgar_s1_fallback_url(r.symbol)
        rec: dict[str, object] = {
            "Symbol": r.symbol,
            "Fund Name": r.name,
            "Price": _parse_price(r.price),
            "52W %": r.pct_52w if r.pct_52w is not None else np.nan,
            "Assets (B)": (r.assets_usd / 1e9) if r.assets_usd is not None else np.nan,
            # Empty string so client-side sort is A–Z / Z–A (NaN sorts oddly as text).
            "Issuer": issuer,
            "Inception": inc,
            "Fund Filing": fund_filing,
        }
        if include_strategy:
            rec["Strategy"] = format_strategy_cell(r.etf_about, r.index_tracked)
        records.append(rec)
    return pd.DataFrame(records)


def filter_rows_by_fund_name(rows: list[CryptoEtpRow], query: str) -> list[CryptoEtpRow]:
    q = (query or "").strip().lower()
    if not q:
        return list(rows)
    return [r for r in rows if q in r.name.lower()]


def _fmt_52w_cell(v: object) -> str:
    if pd.isna(v):
        return "—"
    fv = float(v)
    arrow = "\u25b2" if fv >= 0 else "\u25bc"
    return f"{arrow} {fv:+.2f}%"


def _fmt_assets_b_cell(v: object) -> str:
    """Billions in data → USD; same compact $ style as RWA Total Value."""
    if pd.isna(v):
        return "—"
    return format_usd_compact(float(v) * 1e9)


def style_etp_dataframe(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Green/red 52W %; arrows + % and ``x.xxB`` assets via ``format`` (numeric dtypes unchanged)."""

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
        {"52W %": _fmt_52w_cell, "Assets (B)": _fmt_assets_b_cell},
        na_rep="—",
    )
