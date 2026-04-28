"""
Fetch RWA.xyz figures from the same public web pages visitors use (homepage, Networks, Platforms, Stablecoins, etc.).

The **Networks** integration reads the dedicated [Networks](https://app.rwa.xyz/networks) page—not only the smaller
homepage league—so KPIs and the table match that experience. **Platforms** follows the on-site **Distributed**
issuer view (distributed vs. represented where the UI exposes it; represented-only rows are omitted when
appropriate). **Asset managers** follows the **Distributed** tab with distributed and represented amounts per manager.

This is not RWA.xyz’s official API; page structure may change. For production workloads, use RWA.xyz data products.
"""

import json
import logging
import re
from dataclasses import asdict, dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)

APP_HOME = "https://app.rwa.xyz/"
APP_NETWORKS = "https://app.rwa.xyz/networks"
APP_PLATFORMS = "https://app.rwa.xyz/platforms"
APP_STABLECOINS = "https://app.rwa.xyz/stablecoins"
APP_TREASURIES = "https://app.rwa.xyz/treasuries"
APP_STOCKS = "https://app.rwa.xyz/stocks"
APP_ASSET_MANAGERS = "https://app.rwa.xyz/asset-managers"
USER_AGENT = "JPM-Digital/1.0 (RWA league widget; contact via app maintainer)"


def format_usd_compact(n: float) -> str:
    """Compact USD formatter used for KPI display values."""
    if n >= 1e12:
        return f"${n / 1e12:.2f}T"
    if n >= 1e9:
        return f"${n / 1e9:.2f}B"
    if n >= 1e6:
        return f"${n / 1e6:.2f}M"
    if n >= 1e3:
        return f"${n / 1e3:.2f}K"
    return f"${n:,.2f}"


@dataclass(frozen=True)
class RwaNetworkLeagueRow:
    rank: int
    network: str
    network_href: str | None  # path e.g. /networks/ethereum
    rwa_count: int
    total_value_usd: float
    # Fractional change in total value — from embedded field `value_7d_change` (7 calendar days).
    # There is no value_30d_change in the public page payload we read.
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
    """One headline metric from the RWA.xyz homepage **Global Market Overview** strip."""

    label: str
    value_display: str
    delta_30d_pct: float | None  # fractional change e.g. 0.075 for +7.5%


@dataclass(frozen=True)
class RwaNetworksTabRow:
    """
    One network row from the public **Networks** page data, aligned with the on-site **Networks** table
    (same view RWA.xyz serves in the browser; not a different scraper or homepage-only league).

    **RWA value (distributed)** = ``transferability.transferable`` (RWA in distributed form, matches overview totals).

    **RWA value (represented)** = ``transferability.non_transferable`` (the site’s *Represented* column).

    **RWA total (excl. stablecoins)** = sum of each non-stablecoin class’s ``bridged_token_value_dollar`` in
    ``asset_class_stats`` (matches RWA *Total Value (Excl. Stablecoins)*).

    **RWA count** = sum of non-stablecoin ``asset_count`` in ``asset_class_stats`` (the site lists ~802 for Ethereum, not
    top-level ``asset_count`` which includes stablecoin assets).
    ``rank`` is 1-based after sorting by **distributed** USD descending.
    """

    rank: int
    network: str
    network_href: str | None
    rwa_count: int
    distributed_usd: float
    represented_usd: float  # non_transferable; site column “RWA Value (Represented)”
    rwa_total_excl_stablecoin_usd: float
    pct_distributed_raw: float  # 0..1, distributed / rwa_total (excl. stables) when that total > 0
    value_change_7d_raw: float | None  # fractional: (t−t_ago)/t_ago; ``t_ago`` = ``transferable_30d`` in the embed
    market_share_raw: float  # fraction 0..1
    market_share_change_30d_raw: float | None  # current share minus share implied by row ``transferable_30d`` / Σ same


@dataclass(frozen=True)
class RwaPlatformsTabRow:
    """
    One **issuer / platform** row from the public **Platforms** page data, aligned with the on-site
    **Distributed** Platforms league.

    When ``tokenization_type_stats`` is present, **distributed** / **represented** USD and RWA counts come from the
    ``distributed`` and ``represented`` buckets there (hybrids such as Figure include both). Issuers with stats but
    no **distributed** value are excluded. If that list is empty, measures fall back to non-stablecoin
    ``asset_class_stats`` bridged/circulating sums and **7D Δ** from top-level ``bridged_token_value_dollar`` (same
    window convention as Networks).
    """

    rank: int
    platform: str
    platform_href: str | None
    rwa_count: int
    distributed_usd: float
    represented_usd: float
    rwa_total_excl_stablecoin_usd: float
    pct_distributed_raw: float
    value_change_7d_raw: float | None
    market_share_raw: float
    market_share_change_30d_raw: float | None


@dataclass(frozen=True)
class RwaAssetManagersTabRow:
    """
    One **asset manager** row from the public **Asset managers** page data, aligned with the on-site
    **Distributed** tab. **RWA value (distributed)** / **(represented)** use ``distributed_value`` and
    ``represented_value``; **7D Δ** uses ``(val - val_30d) / val_30d`` on ``distributed_value`` (same 30D baseline
    window as the other Participants tables).
    """

    rank: int
    manager: str
    manager_href: str | None
    rwa_count: int
    distributed_usd: float
    represented_usd: float
    rwa_total_excl_stablecoin_usd: float
    pct_distributed_raw: float
    value_change_7d_raw: float | None
    market_share_raw: float
    market_share_change_30d_raw: float | None


def _dollar_subfield(b: object, key: str) -> float:
    """Read ``key`` (e.g. ``val`` / ``val_30d``) from a RWA money object dict."""
    if not isinstance(b, dict):
        return 0.0
    v = b.get(key)
    return float(v) if isinstance(v, (int, float)) else 0.0


def _extract_next_data(html: str) -> dict[str, Any] | None:
    """Load the JSON payload RWA.xyz embeds in its HTML (Next.js pattern; id must match the live page)."""
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
        logger.debug("RWA.xyz page JSON parse error: %s", e)
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


def _transferable_usd(row: dict[str, Any]) -> float:
    tr = row.get("transferability") or {}
    t = tr.get("transferable")
    return float(t) if isinstance(t, (int, float)) else 0.0


def _transferable_30d_usd(row: dict[str, Any]) -> float:
    tr = row.get("transferability") or {}
    t30 = tr.get("transferable_30d")
    return float(t30) if isinstance(t30, (int, float)) else 0.0


def _is_stablecoin_asset_class(ac: dict[str, Any] | None) -> bool:
    """``asset_class_stats`` item is the RWA *Stablecoins* class (excluded for count / excl. stablecoin value)."""
    if not ac or not isinstance(ac, dict):
        return False
    slug = (ac.get("slug") or "").lower()
    name = (ac.get("name") or "").lower()
    if slug == "stablecoins" or "stablecoin" in slug:
        return True
    if name == "stablecoins" or "stablecoin" in name:
        return True
    return bool(slug == "stable" and "stable" in name)


def _rwa_count_excl_stablecoin(stats: list[dict[str, Any]]) -> int:
    n = 0
    for ac in stats:
        if not isinstance(ac, dict) or _is_stablecoin_asset_class(ac):
            continue
        c = ac.get("asset_count")
        if isinstance(c, (int, float)):
            n += int(c)
    return n


def _bridged_value_sum_excl_stablecoin(stats: list[dict[str, Any]]) -> float:
    t = 0.0
    for ac in stats:
        if not isinstance(ac, dict) or _is_stablecoin_asset_class(ac):
            continue
        o = (ac.get("bridged_token_value_dollar") or {}) if isinstance(ac, dict) else {}
        v = o.get("val")
        if isinstance(v, (int, float)):
            t += float(v)
    return t


def _circulating_value_sum_excl_stablecoin(stats: list[dict[str, Any]]) -> float:
    t = 0.0
    for ac in stats:
        if not isinstance(ac, dict) or _is_stablecoin_asset_class(ac):
            continue
        o = (ac.get("circulating_asset_value_dollar") or {}) if isinstance(ac, dict) else {}
        v = o.get("val")
        if isinstance(v, (int, float)):
            t += float(v)
    return t


def _bridged_value_30d_sum_excl_stablecoin(stats: list[dict[str, Any]]) -> float:
    t = 0.0
    for ac in stats:
        if not isinstance(ac, dict) or _is_stablecoin_asset_class(ac):
            continue
        o = (ac.get("bridged_token_value_dollar") or {}) if isinstance(ac, dict) else {}
        v = o.get("val_30d")
        if isinstance(v, (int, float)):
            t += float(v)
    return t


def _bridged_top_level_30d(row: dict[str, Any]) -> tuple[float, float]:
    """Top-level ``bridged_token_value_dollar`` current and 30d-ago snapshot (issuer total)."""
    o = row.get("bridged_token_value_dollar") or {}
    v = o.get("val")
    v30 = o.get("val_30d")
    vf = float(v) if isinstance(v, (int, float)) else 0.0
    v30f = float(v30) if isinstance(v30, (int, float)) else 0.0
    return vf, v30f


def _tokenization_type_bucket_sums(row: dict[str, Any], type_key: str) -> tuple[float, float, int]:
    """
    For ``tokenization_type_stats`` entries matching ``type_key`` (``distributed`` / ``represented``), sum
    ``bridged_token_value_dollar`` ``val``, ``val_30d``, and ``asset_count``.
    """
    want = (type_key or "").strip().lower()
    val_t = 0.0
    v30_t = 0.0
    rwa = 0
    raw = row.get("tokenization_type_stats")
    if not isinstance(raw, list):
        return 0.0, 0.0, 0
    for item in raw:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").strip().lower() != want:
            continue
        br = item.get("bridged_token_value_dollar") or {}
        v = br.get("val")
        v30 = br.get("val_30d")
        if isinstance(v, (int, float)):
            val_t += float(v)
        if isinstance(v30, (int, float)):
            v30_t += float(v30)
        ac = item.get("asset_count")
        if isinstance(ac, (int, float)):
            rwa += int(ac)
    return val_t, v30_t, rwa


def _rows_from_platforms_list_results(raw: list[dict[str, Any]]) -> list[RwaPlatformsTabRow]:
    """
    Issuer rows for the on-site **Distributed** Platforms league: sorted by **RWA value (distributed)** descending.

    Rows with non-empty ``tokenization_type_stats`` and no positive **distributed** bucket are skipped (represented-only
    issuers). Market share uses Σ distributed; 30D Δ share uses Σ distributed ``val_30d`` per row.
    """
    rows_in = [r for r in raw if isinstance(r, dict)]
    if not rows_in:
        return []

    interim: list[dict[str, Any]] = []
    for row in rows_in:
        name = str(row.get("name") or "").strip() or "—"
        slug = str(row.get("slug") or "").strip()
        href = f"/platforms/{slug}" if slug else None
        tts = row.get("tokenization_type_stats")
        has_tts = isinstance(tts, list) and len(tts) > 0

        if has_tts:
            dist, dist30, rwa = _tokenization_type_bucket_sums(row, "distributed")
            rep, _, _ = _tokenization_type_bucket_sums(row, "represented")
            if dist <= 0:
                continue
            total_excl = dist + rep
            if total_excl <= 0 and dist > 0:
                total_excl = dist
            pct = (dist / total_excl) if total_excl > 0 else 0.0
            v7: float | None
            if dist30 and dist30 > 0:
                v7 = (dist - dist30) / dist30
            else:
                v7 = None
        else:
            ac_stats: list[dict[str, Any]] = [
                a for a in (row.get("asset_class_stats") or []) if isinstance(a, dict)
            ]
            if ac_stats:
                rwa = _rwa_count_excl_stablecoin(ac_stats)
                dist = _bridged_value_sum_excl_stablecoin(ac_stats)
                total_excl = _circulating_value_sum_excl_stablecoin(ac_stats)
                dist30 = _bridged_value_30d_sum_excl_stablecoin(ac_stats)
            else:
                acn = row.get("asset_count")
                rwa = int(acn) if isinstance(acn, (int, float)) else 0
                br = row.get("bridged_token_value_dollar") or {}
                cr = row.get("circulating_asset_value_dollar") or {}
                dist = float(br["val"]) if isinstance(br.get("val"), (int, float)) else 0.0
                total_excl = float(cr["val"]) if isinstance(cr.get("val"), (int, float)) else 0.0
                dist30 = float(br["val_30d"]) if isinstance(br.get("val_30d"), (int, float)) else 0.0

            if total_excl <= 0 and dist > 0:
                total_excl = dist
            rep = max(0.0, total_excl - dist)
            pct = (dist / total_excl) if total_excl > 0 else 0.0

            b_now, b30_top = _bridged_top_level_30d(row)
            if b30_top and b30_top > 0:
                v7 = (b_now - b30_top) / b30_top
            else:
                v7 = None

        interim.append(
            {
                "name": name,
                "href": href,
                "rwa": rwa,
                "dist": dist,
                "rep": rep,
                "total_excl": total_excl,
                "pct": pct,
                "v7": v7,
                "dist30": dist30,
            }
        )

    total_dist = sum(float(x["dist"]) for x in interim) or 0.0
    total_dist30 = sum(float(x["dist30"]) for x in interim) or 0.0

    sorted_interim = sorted(interim, key=lambda x: (-float(x["dist"]), str(x["name"]).lower()))
    out: list[RwaPlatformsTabRow] = []
    for i, x in enumerate(sorted_interim):
        dist_f = float(x["dist"])
        dist30_f = float(x["dist30"])
        ms = (dist_f / total_dist) if total_dist > 0 else 0.0
        ms30: float | None
        if total_dist30 and total_dist30 > 0:
            share30 = dist30_f / total_dist30
            ms30 = (dist_f / total_dist) - share30 if total_dist else None
        else:
            ms30 = None
        out.append(
            RwaPlatformsTabRow(
                rank=i + 1,
                platform=str(x["name"]),
                platform_href=x.get("href") if isinstance(x.get("href"), str) else None,
                rwa_count=int(x["rwa"]),
                distributed_usd=dist_f,
                represented_usd=float(x["rep"]),
                rwa_total_excl_stablecoin_usd=float(x["total_excl"]),
                pct_distributed_raw=float(x["pct"]),
                value_change_7d_raw=x["v7"] if isinstance(x.get("v7"), (int, float)) else None,
                market_share_raw=ms,
                market_share_change_30d_raw=ms30,
            )
        )
    return out


def _rows_from_asset_managers_list_results(raw: list[dict[str, Any]]) -> list[RwaAssetManagersTabRow]:
    """
    **Asset managers** **Distributed** tab: per-row ``distributed_value`` / ``represented_value`` (USD).
    Rows with no positive distributed value are excluded. Sorted by distributed descending; market share and 30D share
    deltas use the distributed ``val_30d`` series.
    """
    rows_in = [r for r in raw if isinstance(r, dict)]
    if not rows_in:
        return []

    interim: list[dict[str, Any]] = []
    for row in rows_in:
        name = str(row.get("name") or "").strip() or "—"
        slug = str(row.get("slug") or "").strip()
        href = f"/asset-managers/{slug}" if slug else None
        dv = row.get("distributed_value") or {}
        rv = row.get("represented_value") or {}
        dist = _dollar_subfield(dv, "val")
        if dist <= 0:
            continue
        dist30 = _dollar_subfield(dv, "val_30d")
        rep = _dollar_subfield(rv, "val")
        total_excl = dist + rep
        if total_excl <= 0 and dist > 0:
            total_excl = dist
        pct = (dist / total_excl) if total_excl > 0 else 0.0
        v7: float | None
        if dist30 and dist30 > 0:
            v7 = (dist - dist30) / dist30
        else:
            v7 = None
        rwa_c = row.get("rwa_asset_count")
        if isinstance(rwa_c, (int, float)):
            rwa = int(rwa_c)
        else:
            acn = row.get("asset_count")
            rwa = int(acn) if isinstance(acn, (int, float)) else 0
        interim.append(
            {
                "name": name,
                "href": href,
                "rwa": rwa,
                "dist": dist,
                "rep": rep,
                "total_excl": total_excl,
                "pct": pct,
                "v7": v7,
                "dist30": dist30,
            }
        )

    total_dist = sum(float(x["dist"]) for x in interim) or 0.0
    total_dist30 = sum(float(x["dist30"]) for x in interim) or 0.0
    sorted_interim = sorted(interim, key=lambda x: (-float(x["dist"]), str(x["name"]).lower()))
    out: list[RwaAssetManagersTabRow] = []
    for i, x in enumerate(sorted_interim):
        dist_f = float(x["dist"])
        dist30_f = float(x["dist30"])
        ms = (dist_f / total_dist) if total_dist > 0 else 0.0
        ms30: float | None
        if total_dist30 and total_dist30 > 0:
            share30 = dist30_f / total_dist30
            ms30 = (dist_f / total_dist) - share30 if total_dist else None
        else:
            ms30 = None
        out.append(
            RwaAssetManagersTabRow(
                rank=i + 1,
                manager=str(x["name"]),
                manager_href=x.get("href") if isinstance(x.get("href"), str) else None,
                rwa_count=int(x["rwa"]),
                distributed_usd=dist_f,
                represented_usd=float(x["rep"]),
                rwa_total_excl_stablecoin_usd=float(x["total_excl"]),
                pct_distributed_raw=float(x["pct"]),
                value_change_7d_raw=x["v7"] if isinstance(x.get("v7"), (int, float)) else None,
                market_share_raw=ms,
                market_share_change_30d_raw=ms30,
            )
        )
    return out


def _rows_from_networks_list_results(raw: list[dict[str, Any]]) -> list[RwaNetworksTabRow]:
    """
    Build rows sorted by **RWA value (distributed)** descending (``transferability.transferable``), then
    **#** is 1-based rank. Market share uses Σ transferable across all networks (unchanged by sort).
    """
    rows_in = [r for r in raw if isinstance(r, dict)]
    if not rows_in:
        return []

    total_t = sum(_transferable_usd(r) for r in rows_in) or 0.0
    total_t30 = sum(_transferable_30d_usd(r) for r in rows_in) or 0.0

    sorted_rows = sorted(
        rows_in,
        key=lambda r: (-_transferable_usd(r), str(r.get("name") or "").lower()),
    )

    out: list[RwaNetworksTabRow] = []
    for i, row in enumerate(sorted_rows):
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

        ac_stats: list[dict[str, Any]] = [
            a for a in (row.get("asset_class_stats") or []) if isinstance(a, dict)
        ]
        if ac_stats:
            rwa = _rwa_count_excl_stablecoin(ac_stats)
        else:
            acn = row.get("asset_count")
            rwa = int(acn) if isinstance(acn, (int, float)) else 0

        excl_sum = _bridged_value_sum_excl_stablecoin(ac_stats) if ac_stats else 0.0
        if excl_sum <= 0 and t_f + nt_f > 0:
            excl_sum = t_f + nt_f
        if excl_sum > 0:
            pct = t_f / excl_sum
        else:
            pct = float(pctf) if isinstance(pctf, (int, float)) else 0.0

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
                represented_usd=nt_f,
                rwa_total_excl_stablecoin_usd=excl_sum,
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
        return None, "Could not read data from the RWA.xyz Networks page (the site layout may have changed)."
    if payload.get("page") != "/networks":
        return None, (
            f"The RWA.xyz Networks page returned an unexpected layout (expected Networks, got {payload.get('page')!r})."
        )
    props = payload.get("props")
    if not isinstance(props, dict):
        return None, "The RWA.xyz Networks page data was not in the expected format."
    return props, None


def fetch_rwa_networks_page_data() -> tuple[list[RwaNetworksTabRow], list[RwaGlobalKpi], str | None]:
    """
    RWA **Networks** page: overview KPIs plus the main Networks table, using the same transferability and
    per-asset-class breakdown as the live site (not a separate homepage-only league).
    """
    props, err = _fetch_networks_props_payload()
    if err:
        return [], [], err
    assert props is not None

    lqr = props.get("pageProps", {}).get("listQueryResponse")
    if not isinstance(lqr, dict):
        return [], [], "The RWA.xyz Networks page did not include the expected network list."
    results = lqr.get("results")
    if not isinstance(results, list) or not results:
        return [], _parse_aggregates(props), "The RWA.xyz Networks page returned an empty network list."

    rows = _rows_from_networks_list_results([r for r in results if isinstance(r, dict)])
    kpis = _parse_aggregates(props)
    if not rows:
        return [], kpis, "Could not interpret network rows from the RWA.xyz Networks page."
    return rows, kpis, None


def _fetch_platforms_props_payload() -> tuple[dict[str, Any] | None, str | None]:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    try:
        r = requests.get(APP_PLATFORMS, headers=headers, timeout=60)
        r.raise_for_status()
    except (requests.RequestException, OSError) as e:
        logger.debug("RWA /platforms fetch: %s", e)
        return None, str(e)
    payload = _extract_next_data(r.text)
    if not payload:
        return None, "Could not read data from the RWA.xyz Platforms page (the site layout may have changed)."
    if payload.get("page") != "/platforms":
        return None, (
            f"The RWA.xyz Platforms page returned an unexpected layout (expected Platforms, got {payload.get('page')!r})."
        )
    props = payload.get("props")
    if not isinstance(props, dict):
        return None, "The RWA.xyz Platforms page data was not in the expected format."
    return props, None


def fetch_rwa_platforms_page_data() -> tuple[list[RwaPlatformsTabRow], list[RwaGlobalKpi], str | None]:
    """
    RWA **Platforms** page: overview KPIs plus issuer rows from the same public
    [Platforms](https://app.rwa.xyz/platforms) view as in the browser. The table follows the on-site **Distributed**
    league (distributed vs. represented splits when the page provides them).
    """
    props, err = _fetch_platforms_props_payload()
    if err:
        return [], [], err
    assert props is not None

    lqr = props.get("pageProps", {}).get("listQueryResponse")
    if not isinstance(lqr, dict):
        return [], [], "The RWA.xyz Platforms page did not include the expected issuer list."
    results = lqr.get("results")
    if not isinstance(results, list) or not results:
        return [], _parse_aggregates(props), "The RWA.xyz Platforms page returned an empty issuer list."

    rows = _rows_from_platforms_list_results([r for r in results if isinstance(r, dict)])
    kpis = _parse_aggregates(props)
    if not rows:
        return [], kpis, "Could not interpret issuer rows from the RWA.xyz Platforms page."
    return rows, kpis, None


def _fetch_asset_managers_props_payload() -> tuple[dict[str, Any] | None, str | None]:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    try:
        r = requests.get(APP_ASSET_MANAGERS, headers=headers, timeout=60)
        r.raise_for_status()
    except (requests.RequestException, OSError) as e:
        logger.debug("RWA /asset-managers fetch: %s", e)
        return None, str(e)
    payload = _extract_next_data(r.text)
    if not payload:
        return None, "Could not read data from the RWA.xyz Asset Managers page (the site layout may have changed)."
    if payload.get("page") != "/asset-managers":
        return None, (
            f"The RWA.xyz Asset Managers page returned an unexpected layout "
            f"(expected Asset Managers, got {payload.get('page')!r})."
        )
    props = payload.get("props")
    if not isinstance(props, dict):
        return None, "The RWA.xyz Asset Managers page data was not in the expected format."
    return props, None


def fetch_rwa_asset_managers_page_data() -> tuple[list[RwaAssetManagersTabRow], list[RwaGlobalKpi], str | None]:
    """
    RWA **Asset managers** page: overview KPIs plus manager rows from the same public
    [Asset managers](https://app.rwa.xyz/asset-managers) view. The table follows the on-site **Distributed** tab
    (managers with meaningful distributed value).
    """
    props, err = _fetch_asset_managers_props_payload()
    if err:
        return [], [], err
    assert props is not None

    lqr = props.get("pageProps", {}).get("listQueryResponse")
    if not isinstance(lqr, dict):
        return [], [], "The RWA.xyz Asset Managers page did not include the expected manager list."
    results = lqr.get("results")
    if not isinstance(results, list) or not results:
        return [], _parse_aggregates(props), "The RWA.xyz Asset Managers page returned an empty manager list."

    rows = _rows_from_asset_managers_list_results([r for r in results if isinstance(r, dict)])
    kpis = _parse_aggregates(props)
    if not rows:
        return [], kpis, "Could not interpret manager rows from the RWA.xyz Asset Managers page."
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
        return None, "Could not read data from the RWA.xyz homepage (the site layout may have changed)."
    props = payload.get("props")
    if not isinstance(props, dict):
        return None, "The RWA.xyz homepage data was not in the expected format."
    return props, None


def fetch_rwa_home_data() -> tuple[list[RwaNetworkLeagueRow], list[RwaGlobalKpi], str | None]:
    """
    Homepage Networks league (**Distributed** tab) plus Global Market Overview aggregates.

    Percentage change in total value comes from the **7-day** change field on each league row.
    Overview metrics use **30-day** percentage change when the homepage provides it.
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
    """Return the **Networks** page table, same as :func:`fetch_rwa_networks_page_data` rows."""
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
        return None, "Could not read data from the RWA.xyz Stablecoins page (the site layout may have changed)."
    props = payload.get("props")
    if not isinstance(props, dict):
        return None, "The RWA.xyz Stablecoins page data was not in the expected format."
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
        return None, "Could not read data from the RWA.xyz US Treasuries page (the site layout may have changed)."
    if payload.get("page") != "/treasuries":
        return None, (
            f"The RWA.xyz Treasuries page returned an unexpected layout (expected Treasuries, got {payload.get('page')!r})."
        )
    props = payload.get("props")
    if not isinstance(props, dict):
        return None, "The RWA.xyz Treasuries page data was not in the expected format."
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
        return None, "Could not read data from the RWA.xyz Tokenized Stocks page (the site layout may have changed)."
    if payload.get("page") != "/stocks":
        return None, (
            f"The RWA.xyz Tokenized Stocks page returned an unexpected layout (expected Stocks, got {payload.get('page')!r})."
        )
    props = payload.get("props")
    if not isinstance(props, dict):
        return None, "The RWA.xyz Tokenized Stocks page data was not in the expected format."
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
