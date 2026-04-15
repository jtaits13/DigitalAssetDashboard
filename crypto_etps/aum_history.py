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
from typing import Any

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


def aggregate_aum_pct_from_history(
    df: pd.DataFrame | None,
) -> tuple[float | None, str]:
    """
    Percent change in **estimated** aggregate AUM (constant-shares price scaling).

    Prefers **~1 month** (last weekly point on or before 30 days ago vs latest).
    Falls back to **~1 year** if insufficient weekly history for a month window.
    Returns ``(pct, "1M"|"1Y")`` or ``(None, "")`` if not computable.
    """
    if df is None or df.empty or "date" not in df.columns or "total_aum_usd" not in df.columns:
        return None, ""
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d.sort_values("date").dropna(subset=["total_aum_usd"])
    if len(d) < 2:
        return None, ""
    end_date = d["date"].iloc[-1]
    end_val = float(d["total_aum_usd"].iloc[-1])
    if end_val <= 0:
        return None, ""

    def _pct_for_cut(cut: pd.Timestamp) -> float | None:
        prior = d[d["date"] <= cut]
        if prior.empty:
            return None
        old_val = float(prior["total_aum_usd"].iloc[-1])
        if old_val <= 0:
            return None
        return (end_val - old_val) / old_val * 100.0

    cut_1m = end_date - pd.Timedelta(days=30)
    p1m = _pct_for_cut(cut_1m)
    if p1m is not None:
        return p1m, "1M"

    cut_1y = end_date - pd.DateOffset(years=1)
    p1y = _pct_for_cut(cut_1y)
    if p1y is not None:
        return p1y, "1Y"

    old_val = float(d["total_aum_usd"].iloc[0])
    first_date = d["date"].iloc[0]
    if old_val > 0 and (end_date - first_date).days >= 60:
        return (end_val - old_val) / old_val * 100.0, "1Y*"

    return None, ""


@st.cache_data(ttl=3600, show_spinner=False)
def etp_symbol_price_change_cached(symbol: str, _rev: int = 1) -> tuple[float | None, str]:
    """
    Trailing return on **adjusted** ETF price (proxy for AUM when shares outstanding are stable).

    Prefers **~1 month** (close vs close on or before 30 calendar days ago).
    Falls back to **~1 year** (same vs ~365 days ago) on daily history.
    Returns ``(pct, "1M"|"1Y")`` or ``(None, "")``.
    """
    _ = _rev
    sym = re.sub(r"\s+", "", symbol or "").strip().upper()
    if not sym:
        return None, ""
    try:
        import yfinance as yf
    except ImportError:
        return None, ""

    try:
        t = yf.Ticker(sym)
        hist = t.history(period="14mo", interval="1d", auto_adjust=True)
        time.sleep(_REQUEST_PAUSE_SEC)
    except Exception as e:
        logger.debug("yfinance single %s: %s", sym, e)
        return None, ""

    if hist is None or hist.empty or "Close" not in hist.columns:
        return None, ""
    close = hist["Close"].dropna()
    if len(close) < 5:
        return None, ""

    end = float(close.iloc[-1])
    end_ts = close.index[-1]
    if end <= 0:
        return None, ""

    def _pct_days_back(days: int) -> float | None:
        cut = end_ts - pd.Timedelta(days=days)
        past = close[close.index <= cut]
        if past.empty:
            return None
        old = float(past.iloc[-1])
        if old <= 0:
            return None
        return (end - old) / old * 100.0

    p1m = _pct_days_back(30)
    if p1m is not None:
        return p1m, "1M"

    p1y = _pct_days_back(365)
    if p1y is not None:
        return p1y, "1Y"

    return None, ""


def build_aggregate_aum_plotly_figure(
    plot_df: pd.DataFrame,
    *,
    height: int = 640,
    line_color: str = "#25809C",
) -> Any:
    """
    Line chart of aggregate AUM (billions USD) vs time.

    Default x-axis view is the **last 12 months** with month ticks (e.g. January 2025).
    The trace still contains the full loaded history so users can zoom/pan/scroll to other ranges.
    """
    import plotly.graph_objects as go

    df = plot_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    end = df["date"].max()
    start_12m = end - pd.DateOffset(months=12)

    fig = go.Figure(
        data=[
            go.Scatter(
                x=df["date"],
                y=df["aum_billions_usd"],
                mode="lines",
                line=dict(color=line_color, width=2),
                hovertemplate="%{x|%Y-%m-%d}<br>%{y:.2f} B USD<extra></extra>",
                name="",
                showlegend=False,
            )
        ]
    )
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=8, b=48),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(
            title=dict(text="Billions USD"),
            gridcolor="rgba(148,163,184,0.35)",
            zeroline=False,
        ),
        xaxis=dict(
            title=dict(text=""),
            range=[start_12m, end],
            tickformat="%B %Y",
            dtick="M1",
            gridcolor="rgba(148,163,184,0.25)",
            # Initial window is 12 months; full series remains in the trace for zoom/scroll.
        ),
        hovermode="x unified",
    )
    return fig
