"""
Tokenized money market funds (MMF) from RWA.xyz asset lists.

Funds are drawn from the US Treasuries and Non-U.S. Government Debt pages, filtered to
money-market products (name contains "money market", major liquidity-fund tickers, excluding yield vaults).
Networks and platforms are aggregated from per-token ``bridged_token_value_dollar`` on each fund.
"""

from __future__ import annotations

from typing import Any

from rwa_league.client import (
    RwaGlobalKpi,
    RwaTreasuryDistributedNetworkRow,
    RwaTreasuryPlatformRow,
    _dollar_subfield,
    _extract_next_data,
    _fetch_government_bonds_props_payload,
    _fetch_treasuries_props_payload,
    format_usd_compact,
)

# Major tokenized liquidity / MMF tickers on RWA Treasuries that do not include "money market" in the name.
MMF_EXTRA_TICKERS: frozenset[str] = frozenset(
    {
        "USYC",
        "BUIDL",
        "USDY",
        "OUSG",
        "BENJI",
        "IBENJI",
        "WTGXX",
    }
)


def is_tokenized_mmf_asset(asset: dict[str, Any]) -> bool:
    """True when the asset is treated as a tokenized money market fund for this dashboard."""
    if not isinstance(asset, dict):
        return False
    name = (asset.get("name") or "").lower()
    tick = (asset.get("ticker") or "").strip().upper()
    if "yield vault" in name or tick.startswith("XMMF"):
        return False
    if "money market" in name:
        return True
    return tick in MMF_EXTRA_TICKERS


def _asset_slug(asset: dict[str, Any]) -> str:
    return str(asset.get("slug") or asset.get("ticker") or "").strip()


def asset_distributed_value_usd(asset: dict[str, Any]) -> float:
    """Sum ``bridged_token_value_dollar.val`` across deployment rows."""
    total = 0.0
    for tok in asset.get("tokens") or []:
        if not isinstance(tok, dict):
            continue
        b = tok.get("bridged_token_value_dollar")
        if isinstance(b, dict):
            v = b.get("val")
            if isinstance(v, (int, float)):
                total += float(v)
    return total


def _token_val_30d(tok: dict[str, Any]) -> float:
    b = tok.get("bridged_token_value_dollar")
    if isinstance(b, dict):
        v = b.get("val_30d")
        if isinstance(v, (int, float)):
            return float(v)
    return 0.0


def _token_val_7d_ago(tok: dict[str, Any], val_now: float) -> float | None:
    b = tok.get("bridged_token_value_dollar")
    if not isinstance(b, dict):
        return None
    chg = b.get("chg_7d_pct")
    if not isinstance(chg, (int, float)) or val_now <= 0:
        return None
    denom = 1.0 + float(chg) / 100.0
    if denom <= 0:
        return None
    return val_now / denom


def _page_props(props: dict[str, Any]) -> dict[str, Any]:
    pp = props.get("pageProps")
    if isinstance(pp, dict):
        return pp
    return props


def _list_query_assets(props: dict[str, Any]) -> list[dict[str, Any]]:
    lqr = _page_props(props).get("listQueryResponse") or {}
    results = lqr.get("results") if isinstance(lqr, dict) else None
    if not isinstance(results, list):
        return []
    return [r for r in results if isinstance(r, dict)]


def collect_tokenized_mmf_assets() -> tuple[list[dict[str, Any]], str | None]:
    """Merge unique MMF assets from Treasuries and Government Bonds RWA.xyz pages."""
    props_tr, err_tr = _fetch_treasuries_props_payload()
    if err_tr and not props_tr:
        return [], err_tr

    assets: list[dict[str, Any]] = []
    if props_tr:
        assets.extend(_list_query_assets(props_tr))

    props_gb, err_gb = _fetch_government_bonds_props_payload()
    if props_gb:
        assets.extend(_list_query_assets(props_gb))

    if not assets:
        parts = [e for e in (err_tr, err_gb) if e]
        return [], parts[0] if parts else "No asset list returned from RWA.xyz."

    seen: set[str] = set()
    mmfs: list[dict[str, Any]] = []
    for a in assets:
        slug = _asset_slug(a)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        if is_tokenized_mmf_asset(a):
            mmfs.append(a)

    mmfs.sort(key=lambda x: -asset_distributed_value_usd(x))
    if not mmfs:
        return [], "No tokenized money market funds matched the fund filter."
    return mmfs, None


def _aggregate_network_rows(mmfs: list[dict[str, Any]]) -> list[RwaTreasuryDistributedNetworkRow]:
    """Per-network distributed value across MMF token deployments."""
    buckets: dict[str, dict[str, Any]] = {}
    fund_ids_per_net: dict[str, set[str]] = {}

    for asset in mmfs:
        fund_id = _asset_slug(asset)
        for tok in asset.get("tokens") or []:
            if not isinstance(tok, dict):
                continue
            net = tok.get("network") or {}
            if not isinstance(net, dict):
                continue
            slug = str(net.get("slug") or net.get("name") or "").strip()
            name = str(net.get("name") or slug or "—").strip()
            if not slug:
                continue
            b = tok.get("bridged_token_value_dollar") or {}
            val = _dollar_subfield(b, "val")
            if val <= 0:
                continue
            val30 = _dollar_subfield(b, "val_30d")
            v7_ago = _token_val_7d_ago(tok, val)

            if slug not in buckets:
                buckets[slug] = {
                    "network": name,
                    "network_href": f"/networks/{slug}",
                    "val": 0.0,
                    "val_30d": 0.0,
                    "val_7d_ago": 0.0,
                    "has_7d": False,
                }
                fund_ids_per_net[slug] = set()
            buckets[slug]["val"] += val
            buckets[slug]["val_30d"] += val30
            if v7_ago is not None:
                buckets[slug]["val_7d_ago"] += v7_ago
                buckets[slug]["has_7d"] = True
            fund_ids_per_net[slug].add(fund_id)

    total = sum(b["val"] for b in buckets.values())
    total_30 = sum(b["val_30d"] for b in buckets.values())

    rows: list[RwaTreasuryDistributedNetworkRow] = []
    for slug, b in sorted(buckets.items(), key=lambda kv: -kv[1]["val"]):
        val = b["val"]
        if val <= 0:
            continue
        v7: float | None = None
        if b["has_7d"] and b["val_7d_ago"] > 0:
            v7 = (val - b["val_7d_ago"]) / b["val_7d_ago"]
        ms = val / total if total > 0 else 0.0
        ms30_now = val / total if total > 0 else 0.0
        ms30_then = b["val_30d"] / total_30 if total_30 > 0 else 0.0
        ms30_delta = ms30_now - ms30_then if total_30 > 0 else None
        rows.append(
            RwaTreasuryDistributedNetworkRow(
                rank=len(rows) + 1,
                network=b["network"],
                network_href=b["network_href"],
                rwa_count=len(fund_ids_per_net.get(slug, set())),
                total_value_usd=val,
                value_change_7d_raw=v7,
                market_share_raw=ms,
                market_share_change_7d_raw=None,
                market_share_change_30d_raw=ms30_delta,
            )
        )
    return rows


def _manager_slug(tok: dict[str, Any]) -> str:
    am = tok.get("asset_manager") or {}
    if isinstance(am, dict):
        return str(am.get("slug") or "").strip()
    return ""


def _manager_name(tok: dict[str, Any], asset: dict[str, Any]) -> str:
    am = tok.get("asset_manager") or {}
    if isinstance(am, dict) and am.get("name"):
        return str(am["name"]).strip()
    return str(asset.get("issuer_name") or "—").strip() or "—"


def _aggregate_platform_rows(mmfs: list[dict[str, Any]]) -> list[RwaTreasuryPlatformRow]:
    """Per asset-manager (issuer) distributed value across MMF deployments."""
    buckets: dict[str, dict[str, Any]] = {}
    fund_ids_per_plat: dict[str, set[str]] = {}

    for asset in mmfs:
        fund_id = _asset_slug(asset)
        plat_key = ""
        plat_name = ""
        plat_href: str | None = None
        for tok in asset.get("tokens") or []:
            if not isinstance(tok, dict):
                continue
            slug = _manager_slug(tok)
            if slug:
                plat_key = slug
                plat_name = _manager_name(tok, asset)
                plat_href = f"/asset-managers/{slug}"
                break
        if not plat_key:
            plat_name = str(asset.get("issuer_name") or fund_id or "—").strip()
            plat_key = plat_name.lower().replace(" ", "-")[:48] or "unknown"

        if plat_key not in buckets:
            buckets[plat_key] = {
                "platform": plat_name,
                "platform_href": plat_href,
                "val": 0.0,
                "val_30d": 0.0,
                "val_7d_ago": 0.0,
                "has_7d": False,
            }
            fund_ids_per_plat[plat_key] = set()

        for tok in asset.get("tokens") or []:
            if not isinstance(tok, dict):
                continue
            b = tok.get("bridged_token_value_dollar") or {}
            val = _dollar_subfield(b, "val")
            if val <= 0:
                continue
            val30 = _dollar_subfield(b, "val_30d")
            v7_ago = _token_val_7d_ago(tok, val)
            buckets[plat_key]["val"] += val
            buckets[plat_key]["val_30d"] += val30
            if v7_ago is not None:
                buckets[plat_key]["val_7d_ago"] += v7_ago
                buckets[plat_key]["has_7d"] = True
        fund_ids_per_plat[plat_key].add(fund_id)

    total = sum(b["val"] for b in buckets.values())
    total_30 = sum(b["val_30d"] for b in buckets.values())

    rows: list[RwaTreasuryPlatformRow] = []
    for key, b in sorted(buckets.items(), key=lambda kv: -kv[1]["val"]):
        val = b["val"]
        if val <= 0:
            continue
        v7: float | None = None
        if b["has_7d"] and b["val_7d_ago"] > 0:
            v7 = (val - b["val_7d_ago"]) / b["val_7d_ago"]
        ms = val / total if total > 0 else 0.0
        ms30_now = val / total if total > 0 else 0.0
        ms30_then = b["val_30d"] / total_30 if total_30 > 0 else 0.0
        ms30_delta = ms30_now - ms30_then if total_30 > 0 else None
        rows.append(
            RwaTreasuryPlatformRow(
                rank=len(rows) + 1,
                platform=b["platform"],
                platform_href=b.get("platform_href"),
                rwa_count=len(fund_ids_per_plat.get(key, set())),
                total_value_usd=val,
                value_change_7d_raw=v7,
                market_share_raw=ms,
                market_share_change_30d_raw=ms30_delta,
            )
        )
    return rows


def _blended_apy_7d(mmfs: list[dict[str, Any]]) -> float | None:
    num = 0.0
    den = 0.0
    for asset in mmfs:
        for tok in asset.get("tokens") or []:
            if not isinstance(tok, dict):
                continue
            apy = tok.get("apy_7_day")
            b = tok.get("bridged_token_value_dollar") or {}
            val = _dollar_subfield(b, "val")
            if isinstance(apy, (int, float)) and val > 0:
                num += float(apy) * val
                den += val
    if den <= 0:
        return None
    return num / den


def _total_value_30d_ago(mmfs: list[dict[str, Any]]) -> float:
    total = 0.0
    for asset in mmfs:
        for tok in asset.get("tokens") or []:
            if isinstance(tok, dict):
                total += _token_val_30d(tok)
    return total


def build_mmf_kpis(mmfs: list[dict[str, Any]]) -> list[RwaGlobalKpi]:
    total = sum(asset_distributed_value_usd(a) for a in mmfs)
    total_30 = _total_value_30d_ago(mmfs)
    delta_30: float | None = None
    if total_30 > 0:
        delta_30 = (total - total_30) / total_30

    networks = {slug for a in mmfs for tok in (a.get("tokens") or []) if isinstance(tok, dict) for slug in [str((tok.get("network") or {}).get("slug") or "")] if slug}
    apy = _blended_apy_7d(mmfs)
    apy_disp = f"{apy:.2f}%" if apy is not None else "—"

    return [
        RwaGlobalKpi("Distributed value", format_usd_compact(total), delta_30),
        RwaGlobalKpi("Tokenized funds", str(len(mmfs)), None),
        RwaGlobalKpi("Active networks", str(len(networks)), None),
        RwaGlobalKpi("7D blended APY", apy_disp, None),
    ]


def fetch_rwa_tokenized_mmf_data() -> tuple[
    list[RwaTreasuryDistributedNetworkRow],
    list[RwaTreasuryPlatformRow],
    list[RwaGlobalKpi],
    str | None,
]:
    """
    Tokenized MMF dashboard: KPIs plus network and platform tables aggregated from fund token rows.
    """
    mmfs, err = collect_tokenized_mmf_assets()
    if err:
        return [], [], [], err
    kpis = build_mmf_kpis(mmfs)
    net_rows = _aggregate_network_rows(mmfs)
    plat_rows = _aggregate_platform_rows(mmfs)
    if not net_rows and not plat_rows:
        return [], [], kpis, "Could not build network or platform aggregates for tokenized MMFs."
    return net_rows, plat_rows, kpis, None
