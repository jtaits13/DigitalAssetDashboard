"""
Cross-check static_home/data JSON against live fetchers and internal consistency.

Run from repo root: python scripts/audit_static_data.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent
DATA = _REPO / "static_home" / "data"
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

TOLERANCE_PCT = 0.02  # 2% for live vs export dollar totals
TOLERANCE_ABS_SMALL = 1.0  # $1 for rounding


def load_json(name: str) -> dict[str, Any]:
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8"))


def parse_usd_display(s: str) -> float | None:
    if not s or s.strip() in ("—", "-"):
        return None
    t = s.strip().replace(",", "").replace("$", "").replace("+", "")
    m = re.match(r"^(-?[\d.]+)\s*([KMBT])?$", t, re.I)
    if not m:
        return None
    v = float(m.group(1))
    suf = (m.group(2) or "").upper()
    mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}.get(suf, 1.0)
    return v * mult


def pct_diff(a: float, b: float) -> float:
    if b == 0:
        return 0.0 if a == 0 else float("inf")
    return abs(a - b) / abs(b)


def ok(label: str, detail: str = "") -> dict[str, str]:
    return {"status": "OK", "check": label, "detail": detail}


def warn(label: str, detail: str) -> dict[str, str]:
    return {"status": "WARN", "check": label, "detail": detail}


def fail(label: str, detail: str) -> dict[str, str]:
    return {"status": "FAIL", "check": label, "detail": detail}


def audit_tmmf(results: list[dict[str, str]]) -> None:
    from rwa_league.mmf import (
        asset_distributed_value_usd,
        build_curated_mmf_dashboard_data,
    )

    live_mmfs, live_net, live_plat, live_kpis, err = build_curated_mmf_dashboard_data()
    if err:
        results.append(warn("TMMF live fetch", err))
        return

    static = load_json("rwa_tokenized_mmf.json")
    live_total = sum(asset_distributed_value_usd(a) for a in live_mmfs)
    static_kpi = parse_usd_display(
        next((k["value_display"] for k in static["kpis"] if k["label"] == "Distributed value"), "")
    )
    fund_rows = static.get("funds_table", {}).get("rows_full") or []
    static_fund_sum = sum(float(r.get("Total Value") or 0) for r in fund_rows)

    net_rows = static.get("networks", {}).get("rows_full") or []
    static_net_sum = 0.0
    for r in net_rows:
        v = r.get("Distributed Value") or r.get("Total Value")
        if isinstance(v, (int, float)):
            static_net_sum += float(v)
        elif isinstance(v, str):
            p = parse_usd_display(v)
            if p is not None:
                static_net_sum += p

    if len(live_mmfs) != 17:
        results.append(warn("TMMF fund count", f"live={len(live_mmfs)} expected 17"))
    else:
        results.append(ok("TMMF fund count", "17 curated funds on RWA.xyz"))

    if static_kpi and pct_diff(live_total, static_kpi) > TOLERANCE_PCT:
        results.append(
            fail(
                "TMMF KPI vs live",
                f"static KPI {static_kpi:,.0f} vs live {live_total:,.0f}",
            )
        )
    else:
        results.append(ok("TMMF KPI vs live RWA.xyz", f"${live_total/1e9:.2f}B"))

    if abs(static_fund_sum - live_total) > max(TOLERANCE_ABS_SMALL, live_total * TOLERANCE_PCT):
        results.append(
            fail(
                "TMMF funds table vs KPI",
                f"table sum {static_fund_sum:,.0f} vs live {live_total:,.0f}",
            )
        )
    else:
        results.append(ok("TMMF funds table sums to KPI"))

    live_net_sum = sum(r.total_value_usd for r in live_net)
    if abs(live_net_sum - live_total) > max(TOLERANCE_ABS_SMALL, live_total * 0.001):
        results.append(
            fail(
                "TMMF network rollup",
                f"networks {live_net_sum:,.0f} vs funds {live_total:,.0f}",
            )
        )
    else:
        results.append(ok("TMMF By Network sums to distributed value"))

    explore = load_json("rwa_explore_asset_type.json")
    sec = next((s for s in explore.get("sections", []) if s.get("id") == "tokenized_mmf"), None)
    if sec:
        exp_kpi = parse_usd_display(
            next((k["value_display"] for k in sec.get("kpis", []) if k["label"] == "Distributed value"), "")
        )
        if exp_kpi and static_kpi and pct_diff(exp_kpi, static_kpi) > TOLERANCE_PCT:
            results.append(
                fail("TMMF explore preview vs deep page", f"explore {exp_kpi:,.0f} vs deep {static_kpi:,.0f}")
            )
        else:
            results.append(ok("TMMF explore preview matches deep page KPI"))


def audit_etp(results: list[dict[str, str]]) -> None:
    static_kpis = load_json("etp_kpis.json")
    static_etps = load_json("etps.json")
    rows = static_etps.get("rows") or []
    static_aum = sum(float(r.get("assets_usd") or 0) for r in rows)
    kpi_aum = parse_usd_display(static_kpis.get("total_aum_display", ""))

    if kpi_aum and pct_diff(static_aum, kpi_aum) > 0.05:
        results.append(
            warn(
                "ETP total AUM",
                f"sum of table rows ${static_aum/1e9:.2f}B vs KPI {static_kpis.get('total_aum_display')} "
                "(may exclude rows without AUM)",
            )
        )
    else:
        results.append(ok("ETP KPI AUM aligns with etps.json row sum", static_kpis.get("total_aum_display", "")))

    try:
        from crypto_etps.client import fetch_crypto_etps_enriched

        live_rows, live_err = fetch_crypto_etps_enriched()
        if live_err:
            results.append(warn("ETP live StockAnalysis", str(live_err)))
        elif live_rows:
            live_aum = sum(float(r.get("assets_usd") or 0) for r in live_rows)
            if kpi_aum and pct_diff(live_aum, kpi_aum) > 0.08:
                results.append(
                    warn(
                        "ETP live vs static export",
                        f"live sum ${live_aum/1e9:.2f}B vs export KPI {static_kpis.get('total_aum_display')} "
                        "(stale export or missing AUM on some funds)",
                    )
                )
            else:
                results.append(ok("ETP live StockAnalysis vs static KPI", f"{len(live_rows)} funds"))
    except Exception as exc:
        results.append(warn("ETP live fetch skipped", str(exc)))


def audit_crypto(results: list[dict[str, str]]) -> None:
    static_kpis = load_json("crypto_kpis.json")
    static_prices = load_json("crypto_prices.json")
    rows = static_prices.get("rows") or []
    ms = static_kpis.get("market_structure") or {}
    top50_sum = float(ms.get("top50_market_cap_usd") or 0)
    row_sum = sum(float(r.get("market_cap_usd") or 0) for r in rows)
    if row_sum and pct_diff(top50_sum, row_sum) > 0.01:
        results.append(
            fail("Crypto top-50 cap", f"KPI structure {top50_sum:,.0f} vs rows {row_sum:,.0f}")
        )
    else:
        results.append(ok("Crypto table market cap sums to KPI structure"))

    try:
        from price_ticker import fetch_top_crypto_tickers

        live, live_err, _src = fetch_top_crypto_tickers(limit=50)
        if live_err:
            results.append(warn("Crypto live CoinGecko", live_err))
            return
        live_sum = sum(float(r.get("market_cap_usd") or 0) for r in live)
        if top50_sum and pct_diff(live_sum, top50_sum) > 0.05:
            results.append(
                warn(
                    "Crypto live vs static",
                    f"live top50 ${live_sum/1e12:.2f}T vs export ${top50_sum/1e12:.2f}T (refresh export)",
                )
            )
        else:
            results.append(ok("Crypto live CoinGecko vs static top-50", static_kpis["primary"]["value_display"]))
    except Exception as exc:
        results.append(warn("Crypto live fetch skipped", str(exc)))


def audit_rwa_global(results: list[dict[str, str]]) -> None:
    from rwa_league.client import fetch_rwa_home_data

    static = load_json("rwa_global_market.json")
    live_rows, live_kpis, err = fetch_rwa_home_data()
    if err:
        results.append(warn("RWA global live", err))
        return

    static_kpi = parse_usd_display(
        next((k["value_display"] for k in static.get("kpis", []) if "distributed" in k["label"].lower()), "")
    )
    live_kpi = parse_usd_display(
        next((k.value_display for k in live_kpis if "distributed" in k.label.lower()), "")
    )
    if static_kpi and live_kpi and pct_diff(static_kpi, live_kpi) > TOLERANCE_PCT:
        results.append(
            warn(
                "RWA global KPI vs live",
                f"static {static_kpi:,.0f} vs live {live_kpi:,.0f} — re-run export",
            )
        )
    else:
        results.append(ok("RWA global distributed KPI vs live RWA.xyz homepage"))

    home = load_json("rwa_onchain_home.json")
    home_kpi = parse_usd_display(
        next(
            (
                k["value_display"]
                for k in home.get("kpis", [])
                if "distributed" in str(k.get("label", "")).lower()
            ),
            "",
        )
    )
    if home_kpi and live_kpi and pct_diff(home_kpi, live_kpi) > TOLERANCE_PCT:
        results.append(warn("RWA home preview vs live", f"home {home_kpi:,.0f} vs live {live_kpi:,.0f}"))
    else:
        results.append(ok("RWA home preview KPI vs live homepage"))


def audit_rwa_deep(name: str, fetch_fn_name: str, results: list[dict[str, str]]) -> None:
    static = load_json(name)
    import rwa_league.client as c

    fetch_fn = getattr(c, fetch_fn_name)
    pack = fetch_fn()
    if len(pack) == 4:
        _net, _plat, live_kpis, err = pack
    elif len(pack) == 3:
        _rows, live_kpis, err = pack
    else:
        results.append(warn(name, "unexpected fetch return shape"))
        return
    if err and not live_kpis:
        results.append(warn(f"{name} live", err))
        return

    live_total = parse_usd_display(
        next((k.value_display for k in live_kpis if "distributed" in k.label.lower()), "")
    )
    static_total = parse_usd_display(
        next((k["value_display"] for k in static.get("kpis", []) if "distributed" in k["label"].lower()), "")
    )
    if live_total and static_total and pct_diff(live_total, static_total) > TOLERANCE_PCT:
        results.append(
            warn(f"{name} stale", f"static {static_total:,.0f} vs live {live_total:,.0f}")
        )
    else:
        results.append(ok(f"{name} KPI vs live RWA.xyz", static_total and f"${static_total/1e9:.2f}B" or "—"))


def main() -> int:
    results: list[dict[str, str]] = []
    manifest = load_json("manifest.json")
    if manifest.get("errors"):
        results.append(warn("manifest errors", "; ".join(manifest["errors"][:5])))

    audit_tmmf(results)
    audit_etp(results)
    audit_crypto(results)
    audit_rwa_global(results)
    for fname, fn in [
        ("rwa_stablecoins.json", "fetch_rwa_stablecoins_data"),
        ("rwa_us_treasuries.json", "fetch_rwa_treasuries_data"),
        ("rwa_tokenized_stocks.json", "fetch_rwa_tokenized_stocks_data"),
        ("rwa_tokenized_mmf.json", "fetch_rwa_tokenized_mmf_data"),
    ]:
        if fname == "rwa_tokenized_mmf.json":
            continue  # already audited
        audit_rwa_deep(fname, fn, results)

    audit_rwa_deep("rwa_participants_networks.json", "fetch_rwa_networks_page_data", results)
    audit_rwa_deep("rwa_participants_platforms.json", "fetch_rwa_platforms_page_data", results)
    results.append(
        ok(
            "News / articles",
            "RSS feeds — accuracy is headline freshness only; no numeric cross-check",
        )
    )

    fails = [r for r in results if r["status"] == "FAIL"]
    warns = [r for r in results if r["status"] == "WARN"]
    oks = [r for r in results if r["status"] == "OK"]

    print("=== Static data audit ===\n")
    for r in results:
        print(f"[{r['status']}] {r['check']}")
        if r["detail"]:
            print(f"       {r['detail']}")
    print(f"\nSummary: {len(oks)} OK, {len(warns)} WARN, {len(fails)} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
