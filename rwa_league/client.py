"""
Fetch RWA.xyz data from public Next.js ``__NEXT_DATA__`` embeds (homepage, /networks, /stablecoins, etc.).

The **Networks** dashboard uses ``/networks`` (not only the smaller homepage **parent_networks** league) so that
overviews and the network table line up with the on-site [Networks](https://app.rwa.xyz/networks) experience.

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
APP_NETWORKS = "https://app.rwa.xyz/networks"
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
class RwaTokenizedStockNetworkRow(RwaNetworkLeagueRow):
    """One row from the Tokenized Stocks page league table **Networks** tab (Distributed)."""


@dataclass(frozen=True)
class RwaGlobalKpi:
    """One card from the homepage “Global Market Overview” (``pageProps.aggregates``)."""

    label: str
    value_display: str
    delta_30d_pct: float | None  # fractional change e.g. 0.075 for +7.5%


@dataclass(frozen=True)
class RwaNetworksTabRow:
    """
    One network row from ``/networks`` (``listQueryResponse.results``).

    **Distributed** RWA value is ``transferability.transferable`` in the public embed — it lines up with the homepage
    ``parent_networks`` league and with the “Distributed Asset Value” top-line (sum of transferables, ~same as
    the Networks overview KPIs). **Represented** is ``transferable + non_transferable`` for that same block.
    """

    rank: int
    network: str
    network_href: str | None
    rwa_count: int
    distributed_usd: float
    represented_usd: float
    pct_distributed_raw: float  # 0..1 (``transferability.pct_transferable``)
    value_change_7d_raw: float | None  # fractional: (t−t_ago)/t_ago; ``t_ago`` = ``transferable_30d`` in the embed
    market_share_raw: float  # fraction 0..1
    market_share_change_30d_raw: float | None  # current share minus share implied by row ``transferable_30d`` / Σ same


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


def _stocks_network_rows_from_props(props: dict[str, Any]) -> list[dict[str, Any]] | None:
    """
    Tokenized Stocks page: ``leagueTableTabs.distributed`` contains tab objects.
    We need the **networks** tab rows.
    """
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


def _rows_from_networks_list_results(raw: list[dict[str, Any]]) -> list[RwaNetworksTabRow]:
    """
    Build rows in **API list order** (``listQueryResponse.results`` — the Networks page default in ``__NEXT_DATA__``
    is often name A→Z, see ``listQueryResponse.sort``).
    """
    if not raw:
        return []
    ts: list[float] = []
    t30s: list[float] = []
    for row in raw:
        if not isinstance(row, dict):
            ts.append(0.0)
            t30s.append(0.0)
            continue
        tr = row.get("transferability") or {}
        t = tr.get("transferable")
        t30 = tr.get("transferable_30d")
        ts.append(float(t) if isinstance(t, (int, float)) else 0.0)
        t30s.append(float(t30) if isinstance(t30, (int, float)) else 0.0)
    total_t = sum(ts) or 0.0
    total_t30 = sum(t30s) or 0.0

    out: list[RwaNetworksTabRow] = []
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip() or "—"
        slug = str(row.get("slug") or "").strip()
        href = f"/networks/{slug}" if slug else None

        tr = row.get("transferability") or {}
        t = tr.get("transferable")
        t30 = tr.get("transferable_30d")
        nt = tr.get("non_transferable")
        pctf = tr.get("pct_transferable")
        t_f = float(t) if isinstance(t, (int, float)) else 0.0
        t30_f = float(t30) if isinstance(t30, (int, float)) else 0.0
        nt_f = float(nt) if isinstance(nt, (int, float)) else 0.0
        pct = float(pctf) if isinstance(pctf, (int, float)) else (t_f / (t_f + nt_f) if (t_f + nt_f) > 0 else 0.0)

        ac = row.get("asset_count")
        rwa = int(ac) if isinstance(ac, (int, float)) else 0

        v7: float | None
        if t30_f and t30_f > 0 and isinstance(t, (int, float)):
            v7 = (t_f - t30_f) / t30_f
        else:
            v7 = None

        ms = (t_f / total_t) if total_t > 0 else 0.0
        ms30: float | None
        if total_t30 and total_t30 > 0:
            share30 = t30_f / total_t30
            ms30 = (t_f / total_t) - share30 if total_t else None
        else:
            ms30 = None

        out.append(
            RwaNetworksTabRow(
                rank=i + 1,
                network=name,
                network_href=href,
                rwa_count=rwa,
                distributed_usd=t_f,
                represented_usd=t_f + nt_f,
                pct_distributed_raw=pct,
                value_change_7d_raw=v7,
                market_share_raw=ms,
                market_share_change_30d_raw=ms30,
            )
        )
    return out


def _fetch_networks_props_payload() -> tuple[dict[str, Any] | None, str | None]:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    try:
        r = requests.get(APP_NETWORKS, headers=headers, timeout=60)
        r.raise_for_status()
    except (requests.RequestException, OSError) as e:
        logger.debug("RWA /networks fetch: %s", e)
        return None, str(e)
    payload = _extract_next_data(r.text)
    if not payload:
        return None, "Could not parse __NEXT_DATA__ from app.rwa.xyz/networks (layout may have changed)."
    if payload.get("page") != "/networks":
        return None, (
            f"Expected Next.js page route /networks in __NEXT_DATA__, got {payload.get('page')!r}. "
            "Refusing to parse a different route."
        )
    props = payload.get("props")
    if not isinstance(props, dict):
        return None, "Invalid __NEXT_DATA__ structure."
    return props, None


def fetch_rwa_networks_page_data() -> tuple[list[RwaNetworksTabRow], list[RwaGlobalKpi], str | None]:
    """
    RWA **Networks** page: ``pageProps.aggregates`` (same top-line as the /networks overview) + **networks table** rows
    from ``listQueryResponse.results`` (transferability / asset counts; not the raw homepage ``leagueTableTabs`` object).
    """
    props, err = _fetch_networks_props_payload()
    if err:
        return [], [], err
    assert props is not None

    lqr = props.get("pageProps", {}).get("listQueryResponse")
    if not isinstance(lqr, dict):
        return [], [], "listQueryResponse missing from app.rwa.xyz/networks page data."
    results = lqr.get("results")
    if not isinstance(results, list) or not results:
        return [], _parse_aggregates(props), "No networks in listQueryResponse on /networks."

    rows = _rows_from_networks_list_results([r for r in results if isinstance(r, dict)])
    kpis = _parse_aggregates(props)
    if not rows:
        return [], kpis, "Could not parse listQueryResponse results into network rows."
    return rows, kpis, None


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


def fetch_rwa_network_league() -> tuple[list[RwaNetworksTabRow], str | None]:
    """Return the **Networks** page table (``/networks``), same as :func:`fetch_rwa_networks_page_data` rows."""
    rows, _, err = fetch_rwa_networks_page_data()
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
    list[RwaTokenizedStockNetworkRow],
    list[RwaTokenizedStockPlatformRow],
    list[RwaGlobalKpi],
    str | None,
]:
    """
    Tokenized Stocks dashboard: overview aggregates + **Distributed** · **Networks** and **Platforms** league tabs.

    Row value is platform distributed value in USD; aggregate percentChange fields are typically 30d.
    """
    props, err = _fetch_stocks_props_payload()
    if err:
        return [], [], [], err
    assert props is not None

    raw_net = _stocks_network_rows_from_props(props)
    raw_plat = _stocks_platform_rows_from_props(props)
    kpis = _parse_aggregates(props)
    if not raw_net and not raw_plat:
        return [], [], kpis, "Tokenized Stocks Distributed · Networks / Platforms league data not found in page data."

    net_out: list[RwaTokenizedStockNetworkRow] = []
    if raw_net:
        league = _rows_from_raw(raw_net)
        net_out = [RwaTokenizedStockNetworkRow(**asdict(r)) for r in league]

    plat_out = _stocks_platform_rows_from_raw(raw_plat or [])
    return net_out, plat_out, kpis, None
