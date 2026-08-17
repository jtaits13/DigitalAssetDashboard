"""Live KPI fetch for the weekly newsletter.

Committed ``static_home/data`` JSON can lag for weeks because the Pages refresh
workflow deploys without committing. Each newsletter build:

1. Fetches live TMMF, stablecoin, RWA, crypto, and ETP strips.
2. Saves a weekly snapshot so the next run can detect a failed refresh.
3. Falls back to that snapshot (not month-old JSON) if a live source fails,
   and reports an error so the issue is not sent silently.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA = ROOT / "static_home" / "data"
SNAPSHOT_PATH = DATA / "newsletter_kpi_snapshot.json"
_CACHE_DIR = Path(tempfile.gettempdir()) / "jpm-digital-newsletter-kpis"

REQUIRED_SECTIONS: tuple[tuple[str, str], ...] = (
    ("tmmf", "TMMF"),
    ("stable", "Stablecoins"),
    ("rwa", "RWA"),
    ("crypto", "Crypto"),
    ("etp", "U.S. crypto ETPs"),
)
ETP_SERIES_MAX_LAG_DAYS = 16
HISTORY_WEEKS = 12

_LIVE: dict[str, Any] | None = None
_LOGGED_APPLY = False


def live_kpis_enabled() -> bool:
    raw = str(os.environ.get("NEWSLETTER_LIVE_KPIS") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def fetch_live_newsletter_kpis(*, force: bool = False) -> dict[str, Any]:
    """Return live KPI packs. Cached for the process so chart + HTML share one fetch."""
    global _LIVE
    if _LIVE is not None and not force:
        return _LIVE
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    out: dict[str, Any] = {
        "tmmf_kpis": [],
        "stable_kpis": [],
        "rwa_kpis": [],
        "crypto": None,
        "etp": None,
        "etp_aum_series": None,
        "errors": [],
        "fetched_at": fetched_at,
        "fetched_sources": {},
        "sources": {},
        "week_end": None,
        "fingerprints": {},
        "issues": [],
    }
    if not live_kpis_enabled():
        out["errors"].append("Live newsletter KPIs disabled (NEWSLETTER_LIVE_KPIS=0).")
        out["fetched_sources"] = {key: "disabled" for key, _ in REQUIRED_SECTIONS}
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
    out["sources"] = dict(out["fetched_sources"])
    _LIVE = out
    return out


def apply_live_newsletter_kpis(
    crypto: dict[str, Any],
    etp: dict[str, Any],
    explore: dict[str, dict[str, Any]],
    *,
    week_end: date | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    global _LOGGED_APPLY
    live = fetch_live_newsletter_kpis()
    live["week_end"] = week_end.isoformat() if week_end else live.get("week_end")
    snap = _read_snapshot()
    latest = (snap.get("latest") or {}) if snap else {}

    crypto_out = dict(crypto)
    live_crypto = live.get("crypto")
    if _crypto_usable(live_crypto):
        crypto_out = live_crypto
        live["sources"]["crypto"] = "live"
    else:
        snap_crypto = latest.get("crypto")
        if _crypto_usable(snap_crypto):
            crypto_out = snap_crypto
            live["sources"]["crypto"] = _snapshot_source(snap, week_end, "crypto")
        else:
            live["sources"]["crypto"] = live.get("fetched_sources", {}).get("crypto") or "failed"

    etp_out = dict(etp)
    live_etp = live.get("etp")
    if _etp_usable(live_etp):
        etp_out = live_etp
        live["sources"]["etp"] = "live"
    else:
        snap_etp = latest.get("etp")
        if _etp_usable(snap_etp):
            etp_out = snap_etp
            live["sources"]["etp"] = _snapshot_source(snap, week_end, "etp")
        else:
            live["sources"]["etp"] = live.get("fetched_sources", {}).get("etp") or "failed"

    explore_out = {
        key: dict(val) if isinstance(val, dict) else val for key, val in explore.items()
    }
    _overlay_explore_section(
        live,
        explore_out,
        latest,
        week_end,
        snap,
        live_key="tmmf_kpis",
        section_id="tokenized_mmf",
        source_key="tmmf",
    )
    _overlay_explore_section(
        live,
        explore_out,
        latest,
        week_end,
        snap,
        live_key="stable_kpis",
        section_id="stablecoins",
        source_key="stable",
    )
    if live.get("rwa_kpis"):
        explore_out["rwa_global"] = {"kpis": list(live["rwa_kpis"])}
        live["sources"]["rwa"] = "live"
    elif latest.get("rwa_kpis"):
        explore_out["rwa_global"] = {"kpis": list(latest["rwa_kpis"])}
        live["sources"]["rwa"] = _snapshot_source(snap, week_end, "rwa")
    else:
        live["sources"]["rwa"] = live.get("fetched_sources", {}).get("rwa") or "failed"

    live["fingerprints"] = _fingerprints(explore_out, crypto_out, etp_out)
    live["issues"] = _refresh_issues(live, snap, week_end)
    _write_snapshot(live, snap, week_end, crypto_out, etp_out, explore_out)

    if not _LOGGED_APPLY:
        _LOGGED_APPLY = True
        for err in live.get("errors") or []:
            print(f"Warning: {err}", file=sys.stderr)
        print(_summary_line(live, crypto_out, etp_out), file=sys.stderr)
        _print_issues(live.get("issues") or [])
    return crypto_out, etp_out, explore_out


def tmmf_distributed_kpi(*, live_only: bool = False) -> dict[str, Any] | None:
    live = fetch_live_newsletter_kpis()
    if live.get("fetched_sources", {}).get("tmmf") == "live":
        return _kpi_by_label(live.get("tmmf_kpis") or [], "distributed")
    if live_only:
        return None
    return _kpi_by_label(live.get("tmmf_kpis") or [], "distributed")


def live_etp_aum_series() -> list[dict[str, Any]] | None:
    live = fetch_live_newsletter_kpis()
    rows = live.get("etp_aum_series")
    if isinstance(rows, list) and rows:
        return list(rows)
    snap = _read_snapshot()
    latest = (snap.get("latest") or {}) if snap else {}
    snap_rows = latest.get("etp_aum_series")
    return list(snap_rows) if isinstance(snap_rows, list) and snap_rows else None


def kpi_refresh_issues(week_end: date | None = None) -> list[str]:
    live = _LIVE
    if live is None:
        return ["Newsletter KPIs were not refreshed (live fetch never ran)."]
    issues = list(live.get("issues") or [])
    if week_end is not None:
        extra = _etp_series_lag_issue(week_end)
        if extra and extra not in issues:
            issues.append(extra)
            live["issues"] = issues
    return issues


def kpi_stale_banner_html(issues: list[str], *, outlook: bool = False) -> str:
    if not issues:
        return ""
    items = "".join(f"<li>{escape(item)}</li>" for item in issues)
    title = "KPI refresh failed — do not send this issue"
    body = (
        "One or more printed figures did not update for this week. "
        "Rebuild after the live sources recover, or pass --allow-stale only for a local draft."
    )
    if outlook:
        return (
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="margin:0 0 16px;border-collapse:collapse;border:1px solid #b42318;'
            'background:#fff5f5;">'
            f'<tr><td style="padding:12px 14px;font-family:Segoe UI,Arial,sans-serif;">'
            f'<p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#b42318;">{title}</p>'
            f'<p style="margin:0 0 8px;font-size:12px;line-height:1.5;color:#7f1d1d;">{escape(body)}</p>'
            f'<ul style="margin:0;padding:0 0 0 18px;color:#7f1d1d;font-size:12px;line-height:1.5;">{items}</ul>'
            "</td></tr></table>"
        )
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="margin:0 0 1.1rem;border-collapse:collapse;border:1px solid #b42318;'
        'background:#fff5f5;border-radius:8px;">'
        '<tr><td style="padding:0.85rem 1rem;">'
        f'<p style="margin:0 0 0.35rem;font-size:13px;font-weight:700;color:#b42318;">{title}</p>'
        f'<p style="margin:0 0 0.45rem;font-size:12px;line-height:1.5;color:#7f1d1d;">{escape(body)}</p>'
        f'<ul style="margin:0;padding:0 0 0 1.15rem;color:#7f1d1d;font-size:12px;line-height:1.55;">{items}</ul>'
        "</td></tr></table>"
    )


def _print_issues(issues: list[str]) -> None:
    if not issues:
        print("Newsletter KPI refresh: all required sections updated this week.", file=sys.stderr)
        return
    print("ERROR: newsletter KPIs did not refresh this week:", file=sys.stderr)
    for item in issues:
        print(f"  - {item}", file=sys.stderr)


def _overlay_explore_section(
    live: dict[str, Any],
    explore_out: dict[str, dict[str, Any]],
    latest: dict[str, Any],
    week_end: date | None,
    snap: dict[str, Any] | None,
    *,
    live_key: str,
    section_id: str,
    source_key: str,
) -> None:
    if live.get(live_key):
        sec = dict(explore_out.get(section_id) or {})
        sec["kpis"] = list(live[live_key])
        explore_out[section_id] = sec
        live["sources"][source_key] = "live"
        return
    snap_kpis = latest.get(live_key) or []
    if snap_kpis:
        sec = dict(explore_out.get(section_id) or {})
        sec["kpis"] = list(snap_kpis)
        explore_out[section_id] = sec
        live["sources"][source_key] = _snapshot_source(snap, week_end, source_key)
        return
    live["sources"][source_key] = live.get("fetched_sources", {}).get(source_key) or "failed"


def _snapshot_source(
    snap: dict[str, Any] | None,
    week_end: date | None,
    section_key: str,
) -> str:
    if not snap or week_end is None:
        return "stale_snapshot"
    latest_src = str(((snap.get("latest") or {}).get("sources") or {}).get(section_key) or "")
    if str(snap.get("week_end") or "") == week_end.isoformat() and latest_src == "live":
        return "snapshot"
    return "stale_snapshot"


def _refresh_issues(
    live: dict[str, Any],
    snap: dict[str, Any] | None,
    week_end: date | None,
) -> list[str]:
    issues: list[str] = []
    prev_week = str((snap or {}).get("week_end") or "")
    prev_fp = ((snap or {}).get("latest") or {}).get("fingerprints") or {}
    week_txt = week_end.isoformat() if week_end else "this week"
    sources = live.get("sources") or {}
    fingerprints = live.get("fingerprints") or {}
    for key, label in REQUIRED_SECTIONS:
        src = str(sources.get(key) or "failed")
        if src == "live" or src == "snapshot":
            continue
        fp = str(fingerprints.get(key) or "")
        value = fp.split("|", 1)[0] if fp else "—"
        if src == "stale_snapshot":
            extra = f" still {value}" if value and value != "—" else ""
            from_week = f" from week ending {prev_week}" if prev_week else ""
            issues.append(f"{label}: did not refresh for week ending {week_txt}; using last good snapshot{from_week}{extra}.")
            continue
        if src == "disabled":
            issues.append(f"{label}: live fetch disabled (NEWSLETTER_LIVE_KPIS=0).")
            continue
        same = bool(prev_week and prev_week != week_txt and fp and fp == str(prev_fp.get(key) or ""))
        stuck = f" still {value} from week ending {prev_week}" if same else ""
        issues.append(f"{label}: live fetch failed this week{stuck}.")
    lag = _etp_series_lag_issue(week_end, live.get("etp_aum_series")) if week_end else None
    if lag:
        issues.append(lag)
    return issues


def _etp_series_lag_issue(week_end: date, rows: object = None) -> str | None:
    series = rows
    if not isinstance(series, list) or not series:
        live_rows = None
        if _LIVE is not None:
            live_rows = _LIVE.get("etp_aum_series")
        series = live_rows if isinstance(live_rows, list) and live_rows else None
    if not series:
        payload = _read_json(DATA / "aum_series.json") or {}
        series = payload.get("series") if isinstance(payload, dict) else None
    last: date | None = None
    for row in series or []:
        if not isinstance(row, dict):
            continue
        try:
            day = datetime.fromisoformat(str(row.get("date") or "")).date()
        except ValueError:
            continue
        if last is None or day > last:
            last = day
    if last is None:
        return None
    if (week_end - last).days > ETP_SERIES_MAX_LAG_DAYS:
        return (
            f"U.S. crypto ETPs: AUM series last point is {last.isoformat()}, "
            f"more than {ETP_SERIES_MAX_LAG_DAYS} days before week ending {week_end.isoformat()}."
        )
    return None


def _fingerprints(
    explore: dict[str, dict[str, Any]],
    crypto: dict[str, Any],
    etp: dict[str, Any],
) -> dict[str, str]:
    tmmf = _kpi_by_label((explore.get("tokenized_mmf") or {}).get("kpis") or [], "distributed") or {}
    stable = _kpi_by_label((explore.get("stablecoins") or {}).get("kpis") or [], "market cap") or {}
    rwa = _kpi_by_label((explore.get("rwa_global") or {}).get("kpis") or [], "distributed asset") or {}
    primary = (crypto or {}).get("primary") or {}
    return {
        "tmmf": _fp_value_delta(tmmf.get("value_display"), tmmf.get("delta_30d_pct")),
        "stable": _fp_value_delta(stable.get("value_display"), stable.get("delta_30d_pct")),
        "rwa": _fp_value_delta(rwa.get("value_display"), rwa.get("delta_30d_pct")),
        "crypto": _fp_value_delta(primary.get("value_display"), (primary.get("delta") or {}).get("pct")),
        "etp": _fp_value_delta(etp.get("total_aum_display"), etp.get("aggregate_pct")),
    }


def _fp_value_delta(value: object, delta: object) -> str:
    return f"{str(value or '').strip()}|{delta}"


def _compact_crypto(crypto: dict[str, Any]) -> dict[str, Any]:
    keep = ("generated_at", "source", "primary", "btc_dominance", "stablecoin_share", "btc", "eth")
    return {key: crypto[key] for key in keep if key in crypto}


def _compact_etp(etp: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "generated_at",
        "total_aum_display",
        "aggregate_pct",
        "aggregate_window",
        "net_flow_1m_usd",
        "net_flow_1m_display",
        "net_flow_1m_pct",
        "net_flow_pct_window",
        "ibit",
        "etha",
    )
    return {key: etp[key] for key in keep if key in etp}


def _write_snapshot(
    live: dict[str, Any],
    prev: dict[str, Any] | None,
    week_end: date | None,
    crypto: dict[str, Any],
    etp: dict[str, Any],
    explore: dict[str, dict[str, Any]],
) -> None:
    if week_end is None:
        return
    prev = prev or {}
    prev_latest = dict(prev.get("latest") or {})
    sources = live.get("sources") or {}
    latest = {
        "tmmf_kpis": list(
            live.get("tmmf_kpis")
            or (explore.get("tokenized_mmf") or {}).get("kpis")
            or prev_latest.get("tmmf_kpis")
            or []
        ),
        "stable_kpis": list(
            live.get("stable_kpis")
            or (explore.get("stablecoins") or {}).get("kpis")
            or prev_latest.get("stable_kpis")
            or []
        ),
        "rwa_kpis": list(
            live.get("rwa_kpis")
            or (explore.get("rwa_global") or {}).get("kpis")
            or prev_latest.get("rwa_kpis")
            or []
        ),
        "crypto": _compact_crypto(crypto) if _crypto_usable(crypto) else prev_latest.get("crypto"),
        "etp": _compact_etp(etp) if _etp_usable(etp) else prev_latest.get("etp"),
        "etp_aum_series": live.get("etp_aum_series") or prev_latest.get("etp_aum_series"),
        "sources": dict(sources),
        "fingerprints": dict(live.get("fingerprints") or {}),
        "fetched_at": live.get("fetched_at"),
    }
    history = [row for row in (prev.get("history") or []) if isinstance(row, dict)]
    week_key = week_end.isoformat()
    history = [row for row in history if str(row.get("week_end") or "") != week_key]
    history.append(
        {
            "week_end": week_key,
            "fetched_at": live.get("fetched_at"),
            "sources": dict(sources),
            "fingerprints": dict(live.get("fingerprints") or {}),
            "issues": list(live.get("issues") or []),
        }
    )
    history = history[-HISTORY_WEEKS:]
    payload = {
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "week_end": week_key,
        "latest": latest,
        "history": history,
    }
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_snapshot() -> dict[str, Any] | None:
    return _read_json(SNAPSHOT_PATH)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _merge_named(out: dict[str, Any], name: str, result: dict[str, Any]) -> None:
    err = result.get("error")
    if err:
        out["errors"].append(f"{name}: {err}")
    ok = False
    if name == "tmmf" and result.get("kpis"):
        out["tmmf_kpis"] = result["kpis"]
        ok = True
    elif name == "stable" and result.get("kpis"):
        out["stable_kpis"] = result["kpis"]
        ok = True
    elif name == "rwa" and result.get("kpis"):
        out["rwa_kpis"] = result["kpis"]
        ok = True
    elif name == "crypto" and result.get("kpis"):
        out["crypto"] = result["kpis"]
        ok = True
    elif name == "etp":
        if result.get("kpis"):
            out["etp"] = result["kpis"]
            ok = True
        if result.get("aum_series"):
            out["etp_aum_series"] = result["aum_series"]
    out["fetched_sources"][name] = "live" if ok else "failed"


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
    sources = live.get("sources") or {}
    src = " ".join(f"{key}={sources.get(key) or '?'}" for key, _ in REQUIRED_SECTIONS)
    return (
        "Live newsletter KPIs: "
        f"TMMF {tmmf.get('value_display') or '—'} | "
        f"Stable {stable.get('value_display') or '—'} | "
        f"RWA DAV {rwa.get('value_display') or '—'} | "
        f"Crypto {primary.get('value_display') or '—'} | "
        f"ETP AUM {etp.get('total_aum_display') or '—'} "
        f"({src})"
    )
