"""Persist and restore last-good U.S. ETP page payloads when live fetches fail."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_ETP_LIVE_CACHE_NAME = "etp_live_cache.json"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def bundle_from_static_exports(static_dir: Path) -> dict[str, Any] | None:
    """Seed cache from committed ``static_home/data/etp_*.json`` exports."""
    etps = _read_json(static_dir / "etps.json")
    kpis = _read_json(static_dir / "etp_kpis.json")
    if not etps or not kpis:
        return None
    aum = _read_json(static_dir / "aum_series.json") or {"series": []}
    pulse = _read_json(static_dir / "etf_pulse.json") or {"items": []}
    manifest = _read_json(static_dir / "manifest.json") or {}
    return {
        "generated_at": etps.get("generated_at") or kpis.get("generated_at") or "",
        "payloads": {
            "etps.json": etps,
            "etp_kpis.json": kpis,
            "aum_series.json": aum,
            "etf_pulse.json": pulse,
            "manifest.json": {
                "errors": manifest.get("errors") or [],
                "etp_refreshed_at": manifest.get("etp_refreshed_at") or etps.get("generated_at"),
            },
        },
    }


def load_etp_live_cache(
    cache_path: Path,
    *,
    static_dir: Path | None = None,
) -> dict[str, Any] | None:
    cached = _read_json(cache_path)
    if cached and isinstance(cached.get("payloads"), dict):
        etps = cached["payloads"].get("etps.json")
        if isinstance(etps, dict) and etps.get("rows"):
            return cached
    if static_dir is not None:
        return bundle_from_static_exports(static_dir)
    return cached


def save_etp_live_cache(cache_path: Path, snapshot: dict[str, Any]) -> None:
    payloads = snapshot.get("payloads")
    if not isinstance(payloads, dict):
        return
    etps = payloads.get("etps.json")
    if not isinstance(etps, dict) or not etps.get("rows"):
        return
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")


def apply_etp_live_cache_fallback(
    payloads: dict[str, Any],
    *,
    cache: dict[str, Any] | None,
) -> dict[str, Any]:
    if not cache:
        return payloads
    cached_payloads = cache.get("payloads")
    if not isinstance(cached_payloads, dict):
        return payloads

    out = dict(payloads)
    notes: list[str] = []

    live_etps = out.get("etps.json") if isinstance(out.get("etps.json"), dict) else {}
    cached_etps = cached_payloads.get("etps.json") if isinstance(cached_payloads.get("etps.json"), dict) else {}
    if not (live_etps.get("rows") or []) and cached_etps.get("rows"):
        merged = dict(cached_etps)
        if live_etps.get("error"):
            merged["error"] = live_etps["error"]
        merged["stale"] = True
        out["etps.json"] = merged
        notes.append("Fund table restored from the last saved snapshot.")

    live_kpis = out.get("etp_kpis.json") if isinstance(out.get("etp_kpis.json"), dict) else {}
    cached_kpis = cached_payloads.get("etp_kpis.json") if isinstance(cached_payloads.get("etp_kpis.json"), dict) else {}
    if not live_kpis.get("total_aum_display") and cached_kpis.get("total_aum_display"):
        out["etp_kpis.json"] = dict(cached_kpis)
        notes.append("KPI strip restored from the last saved snapshot.")

    live_aum = out.get("aum_series.json") if isinstance(out.get("aum_series.json"), dict) else {}
    cached_aum = cached_payloads.get("aum_series.json") if isinstance(cached_payloads.get("aum_series.json"), dict) else {}
    if not (live_aum.get("series") or []) and cached_aum.get("series"):
        out["aum_series.json"] = dict(cached_aum)
        notes.append("AUM chart restored from the last saved snapshot.")

    live_pulse = out.get("etf_pulse.json") if isinstance(out.get("etf_pulse.json"), dict) else {}
    cached_pulse = cached_payloads.get("etf_pulse.json") if isinstance(cached_payloads.get("etf_pulse.json"), dict) else {}
    if not (live_pulse.get("items") or []) and cached_pulse.get("items"):
        out["etf_pulse.json"] = dict(cached_pulse)

    if notes:
        kpis = dict(out.get("etp_kpis.json") or {})
        kpis["stale"] = True
        prev = str(kpis.get("error") or "").strip()
        note = " ".join(dict.fromkeys(notes))
        kpis["error"] = f"{prev} {note}".strip() if prev else note
        out["etp_kpis.json"] = kpis

    return out
