"""
Daily net flows for U.S. spot Bitcoin and Ethereum ETFs (Farside Investors).

Values are reported in **millions USD** on Farside and converted to USD here. Coverage is
limited to funds on Farside's BTC/ETH flow tables (not futures, leveraged, or other ETP types).
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FARSIDE_CACHE_PATH = _REPO_ROOT / "static_home" / "data" / "farside_flow_cache.json"

_FARSIDE_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
_FARSIDE_BTC_ALL = "https://farside.co.uk/bitcoin-etf-flow-all-data/"
_FARSIDE_ETH_ALL = "https://farside.co.uk/ethereum-etf-flow-all-data/"
_FARSIDE_REFERER = "https://farside.co.uk/btc/"

_FLOW_MILLIONS_RE = re.compile(r"[^0-9.\-()]")


@dataclass(frozen=True)
class FarsideFlowSeries:
    """Daily net flow per symbol (USD, not millions)."""

    by_symbol: dict[str, list[tuple[datetime, float]]]
    latest_date: datetime | None


def _parse_flow_cell(raw: str) -> float | None:
    s = (raw or "").strip()
    if not s or s in ("-", "—", "–"):
        return None
    neg = "(" in s and ")" in s
    s = _FLOW_MILLIONS_RE.sub("", s)
    if not s or s in (".", "-"):
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    if neg and v > 0:
        v = -v
    return v * 1e6  # Farside reports $m


def _parse_date_cell(raw: str) -> datetime | None:
    s = (raw or "").strip()
    if not s:
        return None
    try:
        return date_parser.parse(s, dayfirst=True).replace(tzinfo=None)
    except (ValueError, TypeError, OverflowError):
        return None


def _farside_request_headers(*, referer: str = _FARSIDE_REFERER) -> dict[str, str]:
    return {
        "User-Agent": _FARSIDE_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": referer,
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }


def _fetch_farside_html(url: str, *, timeout: int = 60, retries: int = 3) -> str | None:
    """Fetch Farside HTML; may return None when blocked (common on CI/datacenter IPs)."""
    last_err: Exception | None = None
    for attempt in range(max(1, retries)):
        if attempt:
            time.sleep(1.5 * attempt)
        try:
            r = requests.get(
                url,
                headers=_farside_request_headers(),
                timeout=timeout,
            )
            if r.status_code == 403:
                logger.warning("Farside fetch %s: HTTP 403 (often blocked off residential IP)", url)
                last_err = requests.HTTPError(f"403 for {url}")
                continue
            r.raise_for_status()
            text = r.text or ""
            if len(text) < 5000 or "IBIT" not in text and "bitcoin-etf-flow" in url:
                logger.warning("Farside fetch %s: short or unexpected body (%s bytes)", url, len(text))
                continue
            if "ETHA" not in text and "ethereum-etf-flow" in url:
                logger.warning("Farside fetch %s: ETH table markers missing", url)
                continue
            return text
        except requests.RequestException as e:
            logger.warning("Farside fetch %s (attempt %s): %s", url, attempt + 1, e)
            last_err = e
    if last_err:
        logger.debug("Farside fetch failed for %s: %s", url, last_err)
    return None


def _parse_btc_table(soup: BeautifulSoup) -> FarsideFlowSeries:
    """BTC table: header row lists tickers; data rows have Date + symbols + Total."""
    by_symbol: dict[str, list[tuple[datetime, float]]] = {}
    latest: datetime | None = None

    for table in soup.find_all("table"):
        good = [tr for tr in table.find_all("tr") if len(tr.find_all(["th", "td"])) >= 5]
        if len(good) < 10:
            continue
        hdr = [c.get_text(strip=True) for c in good[0].find_all(["th", "td"])]
        if not hdr or hdr[0] != "Date" or "Total" not in hdr:
            continue
        symbols = [s.upper() for s in hdr[1:] if s and s.upper() != "TOTAL"]
        if "IBIT" not in symbols:
            continue
        for tr in good[1:]:
            cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
            if len(cells) != len(hdr) or cells[0] in ("Total", "Fee"):
                continue
            dt = _parse_date_cell(cells[0])
            if dt is None:
                continue
            if latest is None or dt > latest:
                latest = dt
            for sym, raw in zip(symbols, cells[1 : 1 + len(symbols)]):
                flow = _parse_flow_cell(raw)
                if flow is None:
                    continue
                by_symbol.setdefault(sym, []).append((dt, flow))
        break

    for sym in by_symbol:
        by_symbol[sym].sort(key=lambda x: x[0])
    return FarsideFlowSeries(by_symbol=by_symbol, latest_date=latest)


def _parse_eth_table(soup: BeautifulSoup) -> FarsideFlowSeries:
    """ETH table: row 1 lists tickers; data rows start after Fee/Seed rows."""
    by_symbol: dict[str, list[tuple[datetime, float]]] = {}
    latest: datetime | None = None

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        symbol_row = None
        for tr in rows:
            cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
            if len(cells) >= 10 and "ETHA" in [c.upper() for c in cells]:
                symbol_row = cells
                break
        if not symbol_row:
            continue
        symbols = [s.upper() for s in symbol_row[1:] if s and s.upper() != "TOTAL"]
        ncol = len(symbol_row)
        for tr in rows:
            cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
            if len(cells) != ncol:
                continue
            if cells[0] in ("", "Fee", "Seed") or cells[1] == "ETHA":
                continue
            dt = _parse_date_cell(cells[0])
            if dt is None:
                continue
            if latest is None or dt > latest:
                latest = dt
            for sym, raw in zip(symbols, cells[1 : 1 + len(symbols)]):
                flow = _parse_flow_cell(raw)
                if flow is None:
                    continue
                by_symbol.setdefault(sym, []).append((dt, flow))
        break

    for sym in by_symbol:
        by_symbol[sym].sort(key=lambda x: x[0])
    return FarsideFlowSeries(by_symbol=by_symbol, latest_date=latest)


def _series_to_cache_dict(series: FarsideFlowSeries) -> dict:
    by_symbol: dict[str, list[dict[str, object]]] = {}
    for sym, points in series.by_symbol.items():
        by_symbol[sym] = [
            {"date": d.strftime("%Y-%m-%d"), "flow_usd": float(v)} for d, v in points
        ]
    latest = series.latest_date.strftime("%Y-%m-%d") if series.latest_date else None
    return {
        "fetched_at": datetime.now().replace(tzinfo=None).isoformat(),
        "latest_date": latest,
        "by_symbol": by_symbol,
    }


def _series_from_cache_dict(data: dict) -> FarsideFlowSeries | None:
    raw = data.get("by_symbol")
    if not isinstance(raw, dict) or not raw:
        return None
    merged: dict[str, list[tuple[datetime, float]]] = {}
    latest: datetime | None = None
    for sym, points in raw.items():
        if not isinstance(points, list):
            continue
        rows: list[tuple[datetime, float]] = []
        for pt in points:
            if not isinstance(pt, dict):
                continue
            dt = _parse_date_cell(str(pt.get("date") or ""))
            try:
                flow = float(pt.get("flow_usd"))
            except (TypeError, ValueError):
                continue
            if dt is None:
                continue
            rows.append((dt, flow))
            if latest is None or dt > latest:
                latest = dt
        if rows:
            merged[str(sym).upper()] = sorted(rows, key=lambda x: x[0])
    if not merged:
        return None
    ld = data.get("latest_date")
    if isinstance(ld, str) and ld.strip():
        parsed = _parse_date_cell(ld)
        if parsed is not None:
            latest = parsed
    return FarsideFlowSeries(by_symbol=merged, latest_date=latest)


def save_farside_flow_cache(
    series: FarsideFlowSeries,
    path: Path | None = None,
) -> None:
    """Persist parsed flows for CI fallback when farside.co.uk blocks datacenter IPs."""
    if not series.by_symbol:
        return
    dest = path or DEFAULT_FARSIDE_CACHE_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(_series_to_cache_dict(series), indent=2), encoding="utf-8")


def load_farside_flow_cache(path: Path | None = None) -> FarsideFlowSeries | None:
    dest = path or DEFAULT_FARSIDE_CACHE_PATH
    if not dest.is_file():
        return None
    try:
        data = json.loads(dest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        logger.warning("Farside cache read %s: %s", dest, e)
        return None
    if not isinstance(data, dict):
        return None
    return _series_from_cache_dict(data)


def _load_farside_flow_series_live(*, timeout: int = 60) -> FarsideFlowSeries:
    """Merge BTC + ETH Farside daily flow series (USD) from live HTML."""
    merged: dict[str, list[tuple[datetime, float]]] = {}
    latest: datetime | None = None

    for url, parser in (
        (_FARSIDE_BTC_ALL, _parse_btc_table),
        (_FARSIDE_ETH_ALL, _parse_eth_table),
    ):
        html = _fetch_farside_html(url, timeout=timeout)
        if not html:
            continue
        part = parser(BeautifulSoup(html, "html.parser"))
        if part.latest_date and (latest is None or part.latest_date > latest):
            latest = part.latest_date
        for sym, points in part.by_symbol.items():
            merged.setdefault(sym, []).extend(points)
        time.sleep(0.4)

    for sym in merged:
        merged[sym].sort(key=lambda x: x[0])
    return FarsideFlowSeries(by_symbol=merged, latest_date=latest)


def load_farside_flow_series(
    *,
    timeout: int = 60,
    cache_path: Path | None = None,
) -> FarsideFlowSeries:
    """
    Daily net flows (USD). Tries live Farside HTML, then ``farside_flow_cache.json``.

    GitHub Actions often receives HTTP 403 from farside.co.uk; the committed cache
  keeps export/deploy working until a residential/local export refreshes it.
    """
    live = _load_farside_flow_series_live(timeout=timeout)
    if live.by_symbol:
        try:
            save_farside_flow_cache(live, cache_path)
        except OSError as e:
            logger.warning("Could not write Farside flow cache: %s", e)
        return live

    cached = load_farside_flow_cache(cache_path)
    if cached and cached.by_symbol:
        logger.info(
            "Using Farside flow cache (%s symbols); live fetch returned no data",
            len(cached.by_symbol),
        )
        return cached
    return live


def load_farside_flow_series_with_source(
    *,
    timeout: int = 60,
    cache_path: Path | None = None,
) -> tuple[FarsideFlowSeries, Literal["live", "cache", "none"]]:
    """Like :func:`load_farside_flow_series` but reports data source for export warnings."""
    live = _load_farside_flow_series_live(timeout=timeout)
    if live.by_symbol:
        try:
            save_farside_flow_cache(live, cache_path)
        except OSError as e:
            logger.warning("Could not write Farside flow cache: %s", e)
        return live, "live"

    cached = load_farside_flow_cache(cache_path)
    if cached and cached.by_symbol:
        return cached, "cache"
    return live, "none"


def sum_flow_window(
    points: list[tuple[datetime, float]],
    *,
    days: int,
    latest: datetime | None = None,
) -> float | None:
    """Sum daily flows over the last ``days`` calendar days through ``latest``."""
    if not points:
        return None
    end = latest or points[-1][0]
    cut = end - timedelta(days=days)
    total = sum(v for d, v in points if d > cut)
    if not any(d > cut for d, _ in points):
        return None
    return total


def flow_window_label(
    points: list[tuple[datetime, float]],
    *,
    days: int,
    latest: datetime | None = None,
) -> Literal["1M", "1Y", "1Y*", ""]:
    """Return lookback tag when enough history exists for the requested window."""
    if not points:
        return ""
    end = latest or points[-1][0]
    start = points[0][0]
    span = (end - start).days
    if days <= 31:
        return "1M" if span >= 20 else ""
    if span >= 330:
        return "1Y"
    if span >= 60:
        return "1Y*"
    return ""


def fund_flow_usd(
    symbol: str,
    series: FarsideFlowSeries,
    *,
    days: int,
) -> tuple[float | None, str]:
    """Net flow for one ticker over ``days`` (30 → 1M, 365 → 1Y)."""
    sym = re.sub(r"\s+", "", symbol or "").strip().upper()
    points = series.by_symbol.get(sym)
    if not points:
        return None, ""
    total = sum_flow_window(points, days=days, latest=series.latest_date)
    lbl = flow_window_label(points, days=days, latest=series.latest_date)
    return total, lbl


def aggregate_flow_for_symbols(
    symbols: list[str],
    series: FarsideFlowSeries,
    *,
    days: int,
) -> tuple[float | None, str]:
    """Sum net flows for listed tickers that appear on Farside."""
    total = 0.0
    any_flow = False
    label = ""
    for sym in symbols:
        v, lbl = fund_flow_usd(sym, series, days=days)
        if v is None:
            continue
        total += v
        any_flow = True
        if lbl:
            label = lbl
    if not any_flow:
        return None, ""
    return total, label


def format_flow_usd_compact(n: float | None) -> str:
    """Signed compact USD for KPI / table (e.g. +$1.23B, −$45M)."""
    if n is None:
        return "—"
    try:
        x = float(n)
    except (TypeError, ValueError):
        return "—"
    if not (x == x):  # NaN
        return "—"
    sign = "+" if x > 0 else "−" if x < 0 else ""
    ax = abs(x)
    if ax >= 1e12:
        body = f"${ax / 1e12:.2f}T"
    elif ax >= 1e9:
        body = f"${ax / 1e9:.2f}B"
    elif ax >= 1e6:
        body = f"${ax / 1e6:.0f}M"
    elif ax >= 1e3:
        body = f"${ax / 1e3:.0f}K"
    else:
        body = f"${ax:,.0f}"
    return f"{sign}{body}" if sign else body


def load_farside_flow_series_cached():
    """Streamlit cache wrapper (optional; no-op when Streamlit is absent)."""
    try:
        import streamlit as st

        @st.cache_data(ttl=3600, show_spinner=False)
        def _inner() -> FarsideFlowSeries:
            return load_farside_flow_series()

        return _inner()
    except Exception:
        return load_farside_flow_series()
