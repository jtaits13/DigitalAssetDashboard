"""
Estimated aggregate U.S. crypto ETP AUM over time.

Uses **yfinance** spot prices vs the latest close to scale each fund’s **current reported AUM**
backward (constant-shares approximation). This is not official AUM history; it tracks how the
aggregate **market value** of the same list would have moved with prices over ~12 months.
"""

from __future__ import annotations

import logging
import re
import time
import pandas as pd
import streamlit as st

from crypto_etps.client import CryptoEtpRow

logger = logging.getLogger(__name__)

_REQUEST_PAUSE_SEC = 0.22


def _clean_symbol(sym: str) -> str:
    s = re.sub(r"\s+", "", sym or "").strip().upper()
    return s


def etp_rows_to_fund_pairs(rows: list[CryptoEtpRow]) -> tuple[tuple[str, float], ...]:
    """Stable cache key + input for AUM history (symbol, latest reported AUM USD)."""
    agg: dict[str, float] = {}
    for r in rows:
        if r.assets_usd is None or r.assets_usd <= 0:
            continue
        sym = _clean_symbol(r.symbol)
        if not sym:
            continue
        agg[sym] = agg.get(sym, 0.0) + float(r.assets_usd)
    return tuple(sorted(agg.items(), key=lambda x: x[0]))


def build_aggregate_aum_history_12m(
    funds: list[tuple[str, float]],
) -> tuple[pd.DataFrame | None, str | None]:
    """
    Return a DataFrame with columns ``date`` and ``total_aum_usd`` (weekly points), or
    ``(None, error_message)``.

    ``funds`` is ``(symbol, current_reported_aum_usd)`` per fund from the list scrape.
    """
    try:
        import yfinance as yf
    except ImportError:
        return None, "Add `yfinance` to requirements to show the AUM chart."

    if not funds:
        return None, "No funds with reported assets under management."

    total_series: pd.Series | None = None

    for sym, assets in funds:
        sym = _clean_symbol(sym)
        if not sym or assets <= 0:
            continue
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="1y", interval="1wk", auto_adjust=True)
            time.sleep(_REQUEST_PAUSE_SEC)
        except Exception as e:
            logger.debug("yfinance %s: %s", sym, e)
            continue

        if hist is None or hist.empty or "Close" not in hist.columns:
            continue

        close = hist["Close"].dropna()
        if len(close) < 2:
            continue

        ref = float(close.iloc[-1])
        if ref <= 0:
            continue

        contrib = assets * (close / ref)
        contrib.name = sym
        if total_series is None:
            total_series = contrib
        else:
            total_series = total_series.add(contrib, fill_value=0)

    if total_series is None or total_series.empty:
        return (
            None,
            "Could not load price history from Yahoo Finance for these symbols. Try again later.",
        )

    total_series = total_series.sort_index()
    # Naive dates for Streamlit / display (strip timezone from Yahoo index)
    dates = pd.to_datetime(
        pd.DatetimeIndex(total_series.index).strftime("%Y-%m-%d"),
        utc=False,
    )
    out = pd.DataFrame({"date": dates, "total_aum_usd": total_series.values.astype(float)})
    return out, None


@st.cache_data(ttl=3600, show_spinner=False)
def load_aggregate_aum_history_cached(
    funds_key: tuple[tuple[str, float], ...],
) -> tuple[pd.DataFrame | None, str | None]:
    """Cache Yahoo price pulls (keyed by symbol + scraped AUM snapshot)."""
    return build_aggregate_aum_history_12m(list(funds_key))
