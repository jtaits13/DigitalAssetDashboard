"""Live KPI fetch for the weekly newsletter.

Committed ``static_home/data`` JSON can lag for weeks because the Pages refresh
workflow deploys without committing. Newsletter builds overlay live TMMF,
stablecoin, RWA, crypto, and ETP strips, and fall back to that JSON only when a
live fetch fails.
"""

from __future__ import annotations

import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_CACHE_DIR = Path(tempfile.gettempdir()) / "jpm-digital-newsletter-kpis"

_LIVE: dict[str, Any] | None = None


def live_kpis_enabled() -> bool:
    raw = str(os.environ.get("NEWSLETTER_LIVE_KPIS") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def fetch_live_newsletter_kpis(*, force: bool = False) -> dict[str, Any]:
    """Return live KPI packs. Cached for the process so chart + HTML share one fetch."""
    global _LIVE
    if _LIVE is not None and not force:
        return _LIVE
    out: dict[str, Any] = {
        "tmmf_kpis": [],
        "stable_kpis": [],
        "rwa_kpis": [],
        "crypto": None,
        "etp": None,
        "etp_aum_series": None,
        "errors": [],
    }
    if not live_kpis_enabled():
        out["errors"].append("Live newsletter KPIs disabled (NEWSLETTER_LIVE_KPIS=0).")
        _LIVE = out
        return out

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=5) as pool:
        fut_tmmf = pool.submit(_fetch_tmmf)
        fut_stable = pool.submit(_fetch_stable)
        fut_rwa = pool.submit(_fetch_rwa)
        fut_crypto = pool.submit(_fetch_crypto)
        fut_etp = pool.submit(_fetch_etp)
        _merge_named(out, "tmmf", fut_tmmf.result())
        _merge_named(out, "stable", fut_stable.result())
        _merge_named(out, "rwa", fut_rwa.result())
        _merge_named(out, "crypto", fut_crypto.result())
        _merge_named(out, "etp", fut_etp.result())
    _LIVE = out
    return out


def apply_live_newsletter_kpis(
    crypto: dict[str, Any],
    etp: dict[str, Any],
    explore: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    live = fetch_live_newsletter_kpis()
    for err in live.get("errors") or []:
        print(f"Warning: {err}", file=sys.stderr)

    crypto_out = dict(crypto)
    live_crypto = live.get("crypto")
    if _crypto_usable(live_crypto):
        crypto_out = live_crypto

    etp_out = dict(etp)
    live_etp = live.get("etp")
    if _etp_usable(live_etp):
        etp_out = live_etp

    explore_out = {
        key: dict(val) if isinstance(val, dict) else val for key, val in explore.items()
    }
    if live.get("tmmf_kpis"):
        sec = dict(explore_out.get("tokenized_mmf") or {})
        sec["kpis"] = list(live["tmmf_kpis"])
        explore_out["tokenized_mmf"] = sec
    if live.get("stable_kpis"):
        sec = dict(explore_out.get("stablecoins") or {})
        sec["kpis"] = list(live["stable_kpis"])
        explore_out["stablecoins"] = sec
    if live.get("rwa_kpis"):
        explore_out["rwa_global"] = {"kpis": list(live["rwa_kpis"])}

    print(_summary_line(live, crypto_out, etp_out), file=sys.stderr)
    return crypto_out, etp_out, explore_out


def tmmf_distributed_kpi() -> dict[str, Any] | None:
    live = fetch_live_newsletter_kpis()
    return _kpi_by_label(live.get("tmmf_kpis") or [], "distributed")


def live_etp_aum_series() -> list[dict[str, Any]] | None:
    live = fetch_live_newsletter_kpis()
    rows = live.get("etp_aum_series")
    return list(rows) if isinstance(rows, list) and rows else None


def _merge_named(out: dict[str, Any], name: str, result: dict[str, Any]) -> None:
    err = result.get("error")
    if err:
        out["errors"].append(f"{name}: {err}")
    if name == "tmmf" and result.get("kpis"):
        out["tmmf_kpis"] = result["kpis"]
    elif name == "stable" and result.get("kpis"):
        out["stable_kpis"] = result["kpis"]
    elif name == "rwa" and result.get("kpis"):
        out["rwa_kpis"] = result["kpis"]
    elif name == "crypto" and result.get("kpis"):
        out["crypto"] = result["kpis"]
    elif name == "etp":
        if result.get("kpis"):
            out["etp"] = result["kpis"]
        if result.get("aum_series"):
            out["etp_aum_series"] = result["aum_series"]


def _kpis_to_dicts(kpis: list[Any]) -> list[dict[str, Any]]:
    from rwa_global_page_payloads import _rwa_kpi_to_dict

    return [_rwa_kpi_to_dict(k) for k in kpis]


def _fetch_tmmf() -> dict[str, Any]:
    from rwa_league.client import fetch_rwa_tokenized_mmf_data

    try:
        _net, _plat, kpis, err = fetch_rwa_tokenized_mmf_data()
        rows = _kpis_to_dicts(kpis)
        if not rows:
            return {"error": err or "TMMF live KPIs were empty."}
        return {"kpis": rows, "error": err}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _fetch_stable() -> dict[str, Any]:
    from rwa_league.client import fetch_rwa_stablecoins_data

    try:
        _net, _plat, kpis, err = fetch_rwa_stablecoins_data()
        rows = _kpis_to_dicts(kpis)
        if not rows:
            return {"error": err or "Stablecoin live KPIs were empty."}
        return {"kpis": rows, "error": err}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _fetch_rwa() -> dict[str, Any]:
    from rwa_league.client import fetch_rwa_home_data

    try:
        _rows, kpis, err = fetch_rwa_home_data()
        rows = _kpis_to_dicts(kpis)
        if not rows:
            return {"error": err or "RWA live KPIs were empty."}
        return {"kpis": rows, "error": err}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _fetch_crypto() -> dict[str, Any]:
    from scripts.export_static_site_data import build_crypto_prices_page_payloads

    try:
        pack = build_crypto_prices_page_payloads(
            skip_about_blurbs=True,
            live_cache_path=_CACHE_DIR / "crypto_live_cache.json",
        )
        kpis = pack.get("kpis") if isinstance(pack, dict) else None
        if not _crypto_usable(kpis):
            err = ""
            if isinstance(kpis, dict):
                err = str(kpis.get("error") or "")
            return {"error": err or "Crypto live KPIs were empty."}
        return {"kpis": kpis}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _fetch_etp() -> dict[str, Any]:
    from scripts.export_static_site_data import build_etp_page_payloads

    try:
        pack = build_etp_page_payloads(
            for_streamlit=True,
            live_cache_path=_CACHE_DIR / "etp_live_cache.json",
        )
        payloads = pack.get("payloads") if isinstance(pack, dict) else {}
        kpis = (payloads or {}).get("etp_kpis.json")
        aum = (payloads or {}).get("aum_series.json") or {}
        series = aum.get("series") if isinstance(aum, dict) else None
        errs = pack.get("errors") if isinstance(pack, dict) else None
        err_txt = "; ".join(str(e) for e in (errs or [])[:3]) if errs else ""
        if not _etp_usable(kpis):
            return {"error": err_txt or "ETP live KPIs were empty."}
        return {
            "kpis": kpis,
            "aum_series": series if isinstance(series, list) else None,
            "error": err_txt or None,
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _kpi_by_label(kpis: list[dict[str, Any]], needle: str) -> dict[str, Any] | None:
    want = needle.lower()
    for kpi in kpis:
        if want in str(kpi.get("label") or "").lower():
            return kpi
    return None


def _crypto_usable(kpis: Any) -> bool:
    if not isinstance(kpis, dict):
        return False
    val = str((kpis.get("primary") or {}).get("value_display") or "").strip()
    return bool(val) and val != "—"


def _etp_usable(kpis: Any) -> bool:
    if not isinstance(kpis, dict):
        return False
    val = str(kpis.get("total_aum_display") or "").strip()
    return bool(val) and val != "—"


def _summary_line(live: dict[str, Any], crypto: dict[str, Any], etp: dict[str, Any]) -> str:
    tmmf = _kpi_by_label(live.get("tmmf_kpis") or [], "distributed") or {}
    stable = _kpi_by_label(live.get("stable_kpis") or [], "market cap") or {}
    rwa = _kpi_by_label(live.get("rwa_kpis") or [], "distributed asset") or {}
    primary = (crypto or {}).get("primary") or {}
    return (
        "Live newsletter KPIs: "
        f"TMMF {tmmf.get('value_display') or '—'} | "
        f"Stable {stable.get('value_display') or '—'} | "
        f"RWA DAV {rwa.get('value_display') or '—'} | "
        f"Crypto {primary.get('value_display') or '—'} | "
        f"ETP AUM {etp.get('total_aum_display') or '—'}"
    )
