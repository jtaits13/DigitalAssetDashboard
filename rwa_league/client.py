"""
Fetch RWA.xyz homepage data from Next.js __NEXT_DATA__: Networks league + Global Market Overview.

Not an official API; structure may change. For production use RWA.xyz's data products.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from typing import Any

import requests

from crypto_etps.client import format_usd_compact

logger = logging.getLogger(__name__)

APP_HOME = "https://app.rwa.xyz/"
APP_STABLECOINS = "https://app.rwa.xyz/stablecoins"
APP_TREASURIES = "https://app.rwa.xyz/treasuries"
APP_STOCKS = "https://app.rwa.xyz/stocks"
USER_AGENT = "JPM-Digital/1.0 (RWA league widget; contact via app maintainer)"


@dataclass(frozen=True)
class RwaNetworkLeagueRow:
    rank: int
    network: str
    network_href: str | None  # path e.g. /networks/ethereum
    rwa_count: int
    total_value_usd: float
    # Fractional change in total value — from embedded field `value_7d_change` (7 calendar days).
    # There is no value_30d_change in the public __NEXT_DATA__ payload.
    value_change_7d_raw: float | None
    market_share_raw: float  # fraction 0–1
    # Optional fractional 7D change in market share (if present in embedded payload).
    market_share_change_7d_raw: float | None
    # Optional fractional 30D change in market share (e.g. ``market_share_pct_30d_change``).
    market_share_change_30d_raw: float | None


@dataclass(frozen=True)
class RwaTreasuryDistributedNetworkRow(RwaNetworkLeagueRow):
    """One row from ``/treasuries`` **Distributed** → **Networks** (not the homepage league)."""


@dataclass(frozen=True)
class RwaTreasuryPlatformRow:
    """One row from ``/treasuries`` **Distributed** → **Platforms** (Tokenized Treasury league by issuer)."""

    rank: int
    platform: str
    platform_href: str | None
    rwa_count: int
    total_value_usd: float
    value_change_7d_raw: float | None
    market_share_raw: float  # fraction 0–1
    market_share_change_30d_raw: float | None


@dataclass(frozen=True)
class RwaStablecoinPlatformRow:
    """One row from the Stablecoins page league table **Platforms** tab."""

    rank: int
    platform: str
    platform_href: str | None
    stablecoin_count: int
    total_value_usd: float
    value_change_7d_raw: float | None
    market_share_raw: float  # fraction 0–1
    market_share_change_30d_raw: float | None  # fractional change in share vs 30d ago


@dataclass(frozen=True)
class RwaTokenizedStockPlatformRow:
    """One row from the Tokenized Stocks page league table **Platforms** tab (Distributed)."""

    rank: int
    platform: str
    platform_href: str | None
    rwa_count: int
    total_value_usd: float
    value_change_7d_raw: float | None
    market_share_raw: float  # fraction 0–1
    market_share_change_30d_raw: float | None  # fractional change in share vs 30d ago


@dataclass(frozen=True)
class RwaGlobalKpi:
    """One card from the homepage “Global Market Overview” (``pageProps.aggregates``)."""

    label: str
    value_display: str
    delta_30d_pct: float | None  # fractional change e.g. 0.075 for +7.5%


def _extract_next_data(html: str) -> dict[str, Any] | None:
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
        html,
        re.DOTALL,
    )
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as e:
        logger.debug("__NEXT_DATA__ JSON: %s", e)
        return None


def _network_rows_from_props(props: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Networks league rows for the **Distributed** tab (not All / Represented)."""
    lt = props.get("pageProps", {}).get("leagueTableTabs", {})
    bucket = lt.get("distributed")
    if not isinstance(bucket, list):
        return None
    for tab in bucket:
        if isinstance(tab, dict) and tab.get("key") == "parent_networks":
            data = tab.get("data") or {}
            rows = data.get("rows")
            if isinstance(rows, list):
                return rows
    return None


def _treasury_network_rows_from_props(props: dict[str, Any]) -> list[dict[str, Any]] | None:
    """US Treasuries page: **Distributed** bucket, **networks** tab (Distributed Value by network)."""
    lt = props.get("pageProps", {}).get("leagueTableTabs", {})
    bucket = lt.get("distributed")
    if not isinstance(bucket, list):
        return None
    for tab in bucket:
        if isinstance(tab, dict) and tab.get("key") == "networks":
            data = tab.get("data") or {}
            rows = data.get("rows")
            if isinstance(rows, list):
                return rows
    return None


def _treasury_platform_rows_from_props(props: dict[str, Any]) -> list[dict[str, Any]] | None:
    """US Treasuries page: **Distributed** bucket, **platforms** tab (Tokenized Treasury league by platform)."""
    lt = props.get("pageProps", {}).get("leagueTableTabs", {})
    bucket = lt.get("distributed")
    if not isinstance(bucket, list):
        return None
    for tab in bucket:
        if isinstance(tab, dict) and tab.get("key") == "platforms":
            data = tab.get("data") or {}
            rows = data.get("rows")
            if isinstance(rows, list):
                return rows
    return None


def _treasury_platform_rows_from_raw(raw_rows: list[dict[str, Any]]) -> list[RwaTreasuryPlatformRow]:
    out: list[RwaTreasuryPlatformRow] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        group = row.get("group") or {}
        name = str(group.get("name") or "").strip() or "—"
        link = group.get("linkTo") or {}
        href = link.get("href") if isinstance(link, dict) else None
        if isinstance(href, str) and href.strip():
            platform_href = href.strip()
        else:
            platform_href = None

        ri = row.get("rowIndex")
        rank = int(ri) + 1 if isinstance(ri, int) else len(out) + 1

        ac = row.get("asset_count")
        n_assets = int(ac) if isinstance(ac, (int, float)) else 0

        val = row.get("value")
        total = float(val) if isinstance(val, (int, float)) else 0.0

        ms = row.get("market_share_pct")
        msf = float(ms) if isinstance(ms, (int, float)) else 0.0

        ms30 = row.get("market_share_pct_30d_change")
        ms30f = float(ms30) if isinstance(ms30, (int, float)) else None

        v7 = row.get("value_7d_change")
        v7f = float(v7) if isinstance(v7, (int, float)) else None

        out.append(
            RwaTreasuryPlatformRow(
                rank=rank,
                platform=name,
                platform_href=platform_href,
                rwa_count=n_assets,
                total_value_usd=total,
                value_change_7d_raw=v7f,
                market_share_raw=msf,
                market_share_change_30d_raw=ms30f,
            )
        )
    return out


def _format_aggregate_value(raw: dict[str, Any]) -> str:
    typ = str(raw.get("type") or "")
    val = raw.get("value")
    if typ in ("dollar_compact",):
        if isinstance(val, (int, float)):
            return format_usd_compact(float(val))
        return "—"
    if typ in ("count", "count_compact"):
        if isinstance(val, (int, float)):
            return f"{int(round(float(val))):,}"
        return "—"
    if isinstance(val, (int, float)):
        return f"{val:,.4g}" if isinstance(val, float) and val != int(val) else f"{int(val):,}"
    return str(val) if val is not None else "—"


def _aggregates_look_like_us_treasuries_page(kpis: list[RwaGlobalKpi]) -> bool:
    """Homepage overview starts with **Distributed Asset Value**; US Treasuries starts with **Distributed Value**."""
    if not kpis:
        return False
    return kpis[0].label.strip() == "Distributed Value"


def _parse_aggregates(props: dict[str, Any]) -> list[RwaGlobalKpi]:
    ag = props.get("pageProps", {}).get("aggregates")
    if not isinstance(ag, list):
        return []
    out: list[RwaGlobalKpi] = []
    for item in ag:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip() or "—"
        disp = _format_aggregate_value(item)
        pc = item.get("percentChange")
        delta: float | None = None
        if isinstance(pc, dict):
            v = pc.get("value")
            if isinstance(v, (int, float)):
                delta = float(v)
        out.append(RwaGlobalKpi(label=label, value_display=disp, delta_30d_pct=delta))
    return out


def _stablecoin_platform_rows_from_props(props: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Platforms tab rows on ``/stablecoins`` (``leagueTableTabs`` is a list of tab objects)."""
    lt = props.get("pageProps", {}).get("leagueTableTabs")
    if not isinstance(lt, list):
        return None
    for item in lt:
        if isinstance(item, dict) and item.get("key") == "platforms":
            data = item.get("data") or {}
            rows = data.get("rows")
            if isinstance(rows, list):
                return rows
    return None


def _stablecoin_platform_rows_from_raw(raw_rows: list[dict[str, Any]]) -> list[RwaStablecoinPlatformRow]:
    out: list[RwaStablecoinPlatformRow] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        group = row.get("group") or {}
        name = str(group.get("name") or "").strip() or "—"
        link = group.get("linkTo") or {}
        href = link.get("href") if isinstance(link, dict) else None
        if isinstance(href, str) and href.strip():
            platform_href = href.strip()
        else:
            platform_href = None

        ri = row.get("rowIndex")
        rank = int(ri) + 1 if isinstance(ri, int) else len(out) + 1

        ac = row.get("asset_count")
        n_coins = int(ac) if isinstance(ac, (int, float)) else 0

        val = row.get("value")
        total = float(val) if isinstance(val, (int, float)) else 0.0

        ms = row.get("market_share_pct")
        msf = float(ms) if isinstance(ms, (int, float)) else 0.0

        ms30 = row.get("market_share_pct_30d_change")
        ms30f = float(ms30) if isinstance(ms30, (int, float)) else None

        v7 = row.get("value_7d_change")
        v7f = float(v7) if isinstance(v7, (int, float)) else None

        out.append(
            RwaStablecoinPlatformRow(
                rank=rank,
                platform=name,
                platform_href=platform_href,
                stablecoin_count=n_coins,
                total_value_usd=total,
                value_change_7d_raw=v7f,
                market_share_raw=msf,
                market_share_change_30d_raw=ms30f,
            )
        )
    return out


def _stocks_platform_rows_from_props(props: dict[str, Any]) -> list[dict[str, Any]] | None:
    """
    Tokenized Stocks page: ``leagueTableTabs.distributed`` contains tab objects.
    We need the **platforms** tab rows.
    """
    lt = props.get("pageProps", {}).get("leagueTableTabs", {})
    bucket = lt.get("distributed")
    if not isinstance(bucket, list):
        return None
    for tab in bucket:
        if isinstance(tab, dict) and tab.get("key") == "platforms":
            data = tab.get("data") or {}
            rows = data.get("rows")
            if isinstance(rows, list):
                return rows
    return None


def _stocks_platform_rows_from_raw(raw_rows: list[dict[str, Any]]) -> list[RwaTokenizedStockPlatformRow]:
    out: list[RwaTokenizedStockPlatformRow] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        group = row.get("group") or {}
        name = str(group.get("name") or "").strip() or "—"
        link = group.get("linkTo") or {}
        href = link.get("href") if isinstance(link, dict) else None
        if isinstance(href, str) and href.strip():
            platform_href = href.strip()
        else:
            platform_href = None

        ri = row.get("rowIndex")
        rank = int(ri) + 1 if isinstance(ri, int) else len(out) + 1

        ac = row.get("asset_count")
        n_assets = int(ac) if isinstance(ac, (int, float)) else 0

        val = row.get("value")
        total = float(val) if isinstance(val, (int, float)) else 0.0

        ms = row.get("market_share_pct")
        msf = float(ms) if isinstance(ms, (int, float)) else 0.0

        ms30 = row.get("market_share_pct_30d_change")
        ms30f = float(ms30) if isinstance(ms30, (int, float)) else None

        v7 = row.get("value_7d_change")
        v7f = float(v7) if isinstance(v7, (int, float)) else None

        out.append(
            RwaTokenizedStockPlatformRow(
                rank=rank,
                platform=name,
                platform_href=platform_href,
                rwa_count=n_assets,
                total_value_usd=total,
                value_change_7d_raw=v7f,
                market_share_raw=msf,
                market_share_change_30d_raw=ms30f,
            )
        )
    return out


def _rows_from_raw(raw_rows: list[dict[str, Any]]) -> list[RwaNetworkLeagueRow]:
    out: list[RwaNetworkLeagueRow] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        group = row.get("group") or {}
        name = str(group.get("name") or "").strip() or "—"
        link = group.get("linkTo") or {}
        href = link.get("href") if isinstance(link, dict) else None
        if isinstance(href, str) and href.strip():
            network_href = href.strip()
        else:
            network_href = None

        ri = row.get("rowIndex")
        rank = int(ri) + 1 if isinstance(ri, int) else len(out) + 1

        ac = row.get("asset_count")
        rwa_count = int(ac) if isinstance(ac, (int, float)) else 0

        val = row.get("value")
        total = float(val) if isinstance(val, (int, float)) else 0.0

        ms = row.get("market_share_pct")
        msf = float(ms) if isinstance(ms, (int, float)) else 0.0

        ms7 = None
        for k in (
            "market_share_7d_change",
            "market_share_pct_7d_change",
            "market_share_change_7d",
            "market_share_change",
        ):
            raw = row.get(k)
            if isinstance(raw, (int, float)):
                ms7 = float(raw)
                break

        v7 = row.get("value_7d_change")
        v7f = float(v7) if isinstance(v7, (int, float)) else None

        ms30f: float | None = None
        for k in (
            "market_share_pct_30d_change",
            "market_share_30d_change",
            "market_share_change_30d",
        ):
            raw30 = row.get(k)
            if isinstance(raw30, (int, float)):
                ms30f = float(raw30)
                break

        out.append(
            RwaNetworkLeagueRow(
                rank=rank,
                network=name,
                network_href=network_href,
                rwa_count=rwa_count,
                total_value_usd=total,
                value_change_7d_raw=v7f,
                market_share_raw=msf,
                market_share_change_7d_raw=ms7,
                market_share_change_30d_raw=ms30f,
            )
        )
    return out


def _fetch_props_payload() -> tuple[dict[str, Any] | None, str | None]:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    try:
        r = requests.get(APP_HOME, headers=headers, timeout=60)
        r.raise_for_status()
    except (requests.RequestException, OSError) as e:
        logger.debug("RWA fetch: %s", e)
        return None, str(e)

    payload = _extract_next_data(r.text)
    if not payload:
        return None, "Could not parse __NEXT_DATA__ from app.rwa.xyz (layout may have changed)."
    props = payload.get("props")
    if not isinstance(props, dict):
        return None, "Invalid __NEXT_DATA__ structure."
    return props, None


def fetch_rwa_home_data() -> tuple[list[RwaNetworkLeagueRow], list[RwaGlobalKpi], str | None]:
    """
    Homepage Networks league (**Distributed** tab) plus Global Market Overview aggregates.

    Percentage change in total value comes from **`value_7d_change`** on each league row.
    Overview metrics use **30d** ``percentChange`` when present.
    """
    props, err = _fetch_props_payload()
    if err:
        return [], [], err
    assert props is not None

    raw_rows = _network_rows_from_props(props)
    if not raw_rows:
        kpis = _parse_aggregates(props)
        return [], kpis, "Networks league table not found in page data."

    kpis = _parse_aggregates(props)
    return _rows_from_raw(raw_rows), kpis, None


def fetch_rwa_network_league() -> tuple[list[RwaNetworkLeagueRow], str | None]:
    """Return Networks league table for the **Distributed** view only."""
    rows, _, err = fetch_rwa_home_data()
    return rows, err


def _fetch_stablecoins_props_payload() -> tuple[dict[str, Any] | None, str | None]:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    try:
        r = requests.get(APP_STABLECOINS, headers=headers, timeout=60)
        r.raise_for_status()
    except (requests.RequestException, OSError) as e:
        logger.debug("RWA stablecoins fetch: %s", e)
        return None, str(e)

    payload = _extract_next_data(r.text)
    if not payload:
        return None, "Could not parse __NEXT_DATA__ from app.rwa.xyz/stablecoins (layout may have changed)."
    props = payload.get("props")
    if not isinstance(props, dict):
        return None, "Invalid __NEXT_DATA__ structure."
    return props, None


def _fetch_treasuries_props_payload() -> tuple[dict[str, Any] | None, str | None]:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    try:
        r = requests.get(APP_TREASURIES, headers=headers, timeout=60)
        r.raise_for_status()
    except (requests.RequestException, OSError) as e:
        logger.debug("RWA treasuries fetch: %s", e)
        return None, str(e)

    payload = _extract_next_data(r.text)
    if not payload:
        return None, "Could not parse __NEXT_DATA__ from app.rwa.xyz/treasuries (layout may have changed)."
    if payload.get("page") != "/treasuries":
        return None, (
            f"Expected Next.js page route /treasuries in __NEXT_DATA__, got {payload.get('page')!r}. "
            "Refusing to parse a different route so league rows are not mixed with the global homepage table."
        )
    props = payload.get("props")
    if not isinstance(props, dict):
        return None, "Invalid __NEXT_DATA__ structure."
    return props, None


def _fetch_stocks_props_payload() -> tuple[dict[str, Any] | None, str | None]:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    try:
        r = requests.get(APP_STOCKS, headers=headers, timeout=60)
        r.raise_for_status()
    except (requests.RequestException, OSError) as e:
        logger.debug("RWA tokenized stocks fetch: %s", e)
        return None, str(e)

    payload = _extract_next_data(r.text)
    if not payload:
        return None, "Could not parse __NEXT_DATA__ from app.rwa.xyz/stocks (layout may have changed)."
    if payload.get("page") != "/stocks":
        return None, (
            f"Expected Next.js page route /stocks in __NEXT_DATA__, got {payload.get('page')!r}. "
            "Refusing to parse a different route so league rows are not mixed with another page payload."
        )
    props = payload.get("props")
    if not isinstance(props, dict):
        return None, "Invalid __NEXT_DATA__ structure."
    return props, None


def fetch_rwa_treasuries_data() -> tuple[
    list[RwaTreasuryDistributedNetworkRow],
    list[RwaTreasuryPlatformRow],
    list[RwaGlobalKpi],
    str | None,
]:
    """
    US Treasuries dashboard: overview aggregates + **Distributed** tab **networks** and **platforms** leagues.

    Network row ``value`` is **Distributed Value** (USD) per chain; platform row ``value`` is total value
    for that issuer on the Tokenized Treasury league table.
    """
    props, err = _fetch_treasuries_props_payload()
    if err:
        return [], [], [], err
    assert props is not None

    kpis = _parse_aggregates(props)
    if kpis and not _aggregates_look_like_us_treasuries_page(kpis):
        return [], [], kpis, (
            "Overview metrics do not match the US Treasuries page (expected first KPI label “Distributed Value”). "
            "Aborting so the table is not populated from the global homepage embed."
        )

    raw_net = _treasury_network_rows_from_props(props)
    raw_plat = _treasury_platform_rows_from_props(props)
    if not raw_net and not raw_plat:
        return [], [], kpis, "US Treasuries Distributed · Networks / Platforms league data not found in page data."

    net_out: list[RwaTreasuryDistributedNetworkRow] = []
    if raw_net:
        league = _rows_from_raw(raw_net)
        net_out = [RwaTreasuryDistributedNetworkRow(**asdict(r)) for r in league]

    plat_out: list[RwaTreasuryPlatformRow] = _treasury_platform_rows_from_raw(raw_plat or [])

    return net_out, plat_out, kpis, None


def fetch_rwa_stablecoins_data() -> tuple[list[RwaStablecoinPlatformRow], list[RwaGlobalKpi], str | None]:
    """
    Stablecoins dashboard: overview aggregates + **Platforms** league tab (not Networks).

    Row value is platform stablecoin **market cap** (same as RWA.xyz table). ``percentChange``
    on aggregates uses the interval in the payload (typically **30d**).
    """
    props, err = _fetch_stablecoins_props_payload()
    if err:
        return [], [], err
    assert props is not None

    raw_rows = _stablecoin_platform_rows_from_props(props)
    kpis = _parse_aggregates(props)
    if not raw_rows:
        return [], kpis, "Stablecoins Platforms league table not found in page data."
    return _stablecoin_platform_rows_from_raw(raw_rows), kpis, None


def fetch_rwa_tokenized_stocks_data() -> tuple[
    list[RwaTokenizedStockPlatformRow], list[RwaGlobalKpi], str | None
]:
    """
    Tokenized Stocks dashboard: overview aggregates + **Distributed** · **Platforms** league tab.

    Row value is platform distributed value in USD; aggregate percentChange fields are typically 30d.
    """
    props, err = _fetch_stocks_props_payload()
    if err:
        return [], [], err
    assert props is not None

    raw_rows = _stocks_platform_rows_from_props(props)
    kpis = _parse_aggregates(props)
    if not raw_rows:
        return [], kpis, "Tokenized Stocks Distributed · Platforms league table not found in page data."
    return _stocks_platform_rows_from_raw(raw_rows), kpis, None
