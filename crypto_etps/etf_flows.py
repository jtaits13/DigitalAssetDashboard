"""
US spot Bitcoin + Ethereum ETF daily net flows from Farside Investors.

Fetches public tables via Jina Reader (`r.jina.ai/...`) because direct requests to
farside.co.uk are often blocked by Cloudflare. Data is in US$ millions; positive =
net inflow, negative = net outflow.

Not affiliated with Farside. See https://farside.co.uk/btc/ and /eth/.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

JINA_BTC = "https://r.jina.ai/https://farside.co.uk/btc/"
JINA_ETH = "https://r.jina.ai/https://farside.co.uk/eth/"

_DATE_ROW_RE = re.compile(
    r"^\|\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s*\|",
)


@dataclass(frozen=True)
class EtfFlowSnapshot:
    """Latest row from one Farside table."""

    asset_class: str  # "Bitcoin" | "Ethereum"
    as_of_date: str  # e.g. "02 Apr 2026"
    net_flow_usd_millions: float | None  # None if row incomplete
    tickers: tuple[str, ...]


@dataclass(frozen=True)
class CombinedEtfFlows:
    btc: EtfFlowSnapshot | None
    eth: EtfFlowSnapshot | None
    combined_usd_millions: float | None
    error: str | None


def _parse_cell_number(raw: str) -> float | None:
    s = raw.strip()
    if not s or s == "-" or s == "—":
        return None
    neg = s.startswith("(") and s.endswith(")")
    inner = s[1:-1].strip() if neg else s
    inner = inner.replace(",", "")
    try:
        v = float(inner)
        return -v if neg else v
    except ValueError:
        return None


def _extract_ticker_row(markdown: str, anchor: tuple[str, str]) -> tuple[str, ...]:
    """Find the pipe row listing ETF tickers (two adjacent symbols anchor the correct line)."""
    a, b = anchor
    for line in markdown.splitlines():
        if f"| {a} |" not in line or f"| {b} |" not in line:
            continue
        if "Fee" in line or "Total" in line.split("|")[1:3]:
            continue
        parts = [p.strip() for p in line.split("|")]
        syms = [p for p in parts if re.fullmatch(r"[A-Z]{2,5}", p)]
        if len(syms) >= 5:
            return tuple(syms)
    return ()


def _parse_flow_table(
    markdown: str,
    asset_class: str,
    ticker_anchor: tuple[str, str],
) -> tuple[EtfFlowSnapshot | None, list[str]]:
    """Extract tickers row and latest complete daily total from Farside markdown."""
    errors: list[str] = []
    tickers = _extract_ticker_row(markdown, ticker_anchor)
    if not tickers:
        errors.append(f"Could not parse ticker row ({asset_class}).")

    rows: list[tuple[str, float | None]] = []
    for line in markdown.splitlines():
        m = _DATE_ROW_RE.match(line.strip())
        if not m:
            continue
        date_str = m.group(1).strip()
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        if parts[-1] == "":
            total_raw = parts[-2]
        else:
            total_raw = parts[-1]
        total = _parse_cell_number(total_raw)
        rows.append((date_str, total))

    if not rows:
        errors.append(f"No dated rows found ({asset_class}).")
        return None, errors

    # Prefer last row with a numeric Total; skip incomplete (-) totals.
    chosen_date, chosen_total = None, None
    for date_str, total in reversed(rows):
        if total is not None:
            chosen_date, chosen_total = date_str, total
            break

    if chosen_date is None:
        errors.append(f"No complete Total column ({asset_class}).")
        return None, errors

    return (
        EtfFlowSnapshot(
            asset_class=asset_class,
            as_of_date=chosen_date,
            net_flow_usd_millions=chosen_total,
            tickers=tickers,
        ),
        errors,
    )


def fetch_combined_etf_flows(user_agent: str) -> CombinedEtfFlows:
    """Load BTC + ETH Farside tables and combine latest daily net flows (US$m)."""
    ua = user_agent.strip() or "JPM-Digital/1.0 (ETF flows; contact in app secrets)"
    headers = {"User-Agent": ua, "Accept": "text/plain,application/json;q=0.9,*/*;q=0.8"}
    err_parts: list[str] = []
    btc_snap: EtfFlowSnapshot | None = None
    eth_snap: EtfFlowSnapshot | None = None

    try:
        r = requests.get(JINA_BTC, headers=headers, timeout=45)
        r.raise_for_status()
        btc_snap, e1 = _parse_flow_table(r.text, "Bitcoin", ("IBIT", "FBTC"))
        err_parts.extend(e1)
    except (requests.RequestException, ValueError, OSError) as e:
        logger.debug("BTC ETF flow fetch: %s", e)
        err_parts.append(f"Bitcoin flows: {e!s}")

    try:
        r = requests.get(JINA_ETH, headers=headers, timeout=45)
        r.raise_for_status()
        eth_snap, e2 = _parse_flow_table(r.text, "Ethereum", ("ETHA", "ETHB"))
        err_parts.extend(e2)
    except (requests.RequestException, ValueError, OSError) as e:
        logger.debug("ETH ETF flow fetch: %s", e)
        err_parts.append(f"Ethereum flows: {e!s}")

    combined: float | None = None
    if btc_snap and eth_snap and btc_snap.net_flow_usd_millions is not None and eth_snap.net_flow_usd_millions is not None:
        combined = btc_snap.net_flow_usd_millions + eth_snap.net_flow_usd_millions
    elif btc_snap and btc_snap.net_flow_usd_millions is not None:
        combined = btc_snap.net_flow_usd_millions
    elif eth_snap and eth_snap.net_flow_usd_millions is not None:
        combined = eth_snap.net_flow_usd_millions

    msg = " · ".join(err_parts) if err_parts else None
    return CombinedEtfFlows(btc=btc_snap, eth=eth_snap, combined_usd_millions=combined, error=msg)


def format_flow_millions(v: float | None) -> str:
    if v is None:
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:,.1f}"
