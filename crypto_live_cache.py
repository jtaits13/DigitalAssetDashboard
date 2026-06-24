"""Persist and restore last-good crypto page payloads when live APIs fail."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CRYPTO_LIVE_CACHE_NAME = "crypto_live_cache.json"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def coinpaprika_total_from_kpis(kpis: dict[str, Any]) -> dict[str, float]:
    """Reconstruct CoinPaprika totals saved inside KPI ``market_structure``."""
    ms = kpis.get("market_structure") if isinstance(kpis.get("market_structure"), dict) else {}
    out: dict[str, float] = {}
    btc_cap = ms.get("btc_market_cap_usd")
    dom = ms.get("btc_dominance_pct")
    try:
        if btc_cap is not None and dom is not None and float(dom) > 0:
            out["total_market_cap_usd"] = float(btc_cap) / (float(dom) / 100.0)
    except (TypeError, ValueError):
        pass
    primary = kpis.get("primary") if isinstance(kpis.get("primary"), dict) else {}
    delta = primary.get("delta") if isinstance(primary.get("delta"), dict) else {}
    try:
        pct = delta.get("pct")
        total_now = out.get("total_market_cap_usd")
        if pct is not None and total_now is not None:
            pct_f = float(pct)
            if pct_f > -99.9:
                total_then = float(total_now) / (1.0 + pct_f / 100.0)
                out["total_market_cap_usd_30d_ago"] = total_then
                out["market_cap_change_pct_1m"] = pct_f
    except (TypeError, ValueError):
        pass
    return out


def bundle_from_static_exports(static_dir: Path) -> dict[str, Any] | None:
    """Seed cache from committed ``static_home/data/crypto_*.json`` exports."""
    kpis = _read_json(static_dir / "crypto_kpis.json")
    prices = _read_json(static_dir / "crypto_prices.json")
    if not kpis or not prices:
        return None
    chart = _read_json(static_dir / "crypto_market_cap_series.json") or {}
    return {
        "generated_at": kpis.get("generated_at") or prices.get("generated_at") or "",
        "kpis": kpis,
        "prices": prices,
        "chart": chart,
        "coinpaprika_total": coinpaprika_total_from_kpis(kpis),
    }


def load_crypto_live_cache(
    cache_path: Path,
    *,
    static_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Load runtime cache, else fall back to last static export bundle."""
    cached = _read_json(cache_path)
    if cached and isinstance(cached.get("prices"), dict) and cached["prices"].get("rows"):
        return cached
    if static_dir is not None:
        return bundle_from_static_exports(static_dir)
    return cached


def save_crypto_live_cache(cache_path: Path, snapshot: dict[str, Any]) -> None:
    """Write last-good crypto snapshot for Streamlit / export fallback."""
    prices = snapshot.get("prices")
    if not isinstance(prices, dict) or not prices.get("rows"):
        return
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")


def _kpi_value_empty(kpi: object) -> bool:
    if not isinstance(kpi, dict):
        return True
    value = str(kpi.get("value_display") or "").strip()
    return not value or value == "—"


def _merge_kpi_field(
    live: dict[str, Any],
    cached: dict[str, Any],
    key: str,
    *,
    notes: list[str],
    label: str,
) -> None:
    if not _kpi_value_empty(live.get(key)):
        return
    cached_val = cached.get(key)
    if _kpi_value_empty(cached_val):
        return
    live[key] = cached_val
    notes.append(label)


def apply_crypto_live_cache_fallback(
    pack: dict[str, Any],
    *,
    cache: dict[str, Any] | None,
    coinpaprika_total: dict[str, float] | None = None,
    rebuild_kpis: Any | None = None,
) -> dict[str, Any]:
    """
    Merge a fresh pack with cached rows / CoinPaprika totals / KPI fields.

    ``rebuild_kpis(rows, coinpaprika_total, prices_error)`` optionally recomputes KPIs
    after row or CoinPaprika restoration.
    """
    if not cache:
        return pack

    notes: list[str] = []
    prices = dict(pack["prices"])
    kpis = dict(pack["kpis"])
    chart = dict(pack["chart"])
    live_rows = list(prices.get("rows") or [])

    cached_prices = cache.get("prices") if isinstance(cache.get("prices"), dict) else {}
    cached_rows = list(cached_prices.get("rows") or [])
    cached_kpis = cache.get("kpis") if isinstance(cache.get("kpis"), dict) else {}
    cached_paprika = (
        cache.get("coinpaprika_total") if isinstance(cache.get("coinpaprika_total"), dict) else {}
    )

    rows_for_kpis = live_rows
    if not live_rows and cached_rows:
        prices = dict(cached_prices)
        prices["stale"] = True
        rows_for_kpis = cached_rows
        if pack["prices"].get("error"):
            prices["error"] = str(pack["prices"]["error"])
        notes.append("Price table restored from the last saved snapshot.")

    paprika = dict(coinpaprika_total or {})
    if not paprika.get("total_market_cap_usd") and cached_paprika.get("total_market_cap_usd"):
        paprika.update({k: v for k, v in cached_paprika.items() if v is not None})
        notes.append("Total market cap restored from the last saved snapshot.")

    if rebuild_kpis is not None and rows_for_kpis and paprika.get("total_market_cap_usd"):
        rebuilt = rebuild_kpis(rows_for_kpis, paprika, str(prices.get("error") or ""))
        if isinstance(rebuilt, dict):
            kpis = rebuilt

    _merge_kpi_field(kpis, cached_kpis, "primary", notes=notes, label="Total market cap restored from cache.")
    _merge_kpi_field(kpis, cached_kpis, "btc_dominance", notes=notes, label="BTC dominance restored from cache.")
    _merge_kpi_field(kpis, cached_kpis, "stablecoin_share", notes=notes, label="Stablecoin share restored from cache.")
    _merge_kpi_field(kpis, cached_kpis, "btc", notes=notes, label="BTC price restored from cache.")
    _merge_kpi_field(kpis, cached_kpis, "eth", notes=notes, label="ETH price restored from cache.")

    if notes:
        kpis["stale"] = True
        stale_note = " ".join(dict.fromkeys(notes))
        prev = str(kpis.get("error") or "").strip()
        kpis["error"] = f"{prev} {stale_note}".strip() if prev else stale_note
        if not live_rows and cached_rows:
            prices["stale"] = True

    return {
        "generated_at": pack["generated_at"],
        "kpis": kpis,
        "prices": prices,
        "chart": chart,
        "ticker": pack.get("ticker"),
        "coinpaprika_total": paprika,
        "_used_cached_rows": not live_rows and bool(cached_rows),
    }
