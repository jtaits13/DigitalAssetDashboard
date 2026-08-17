"""Weekly newsletter charts for TMMF, stablecoins, ETPs, crypto, and RWA.

Stablecoin history is backfilled from DefiLlama. Crypto total market cap is
backfilled from CoinPaprika. TMMF stores Monday RWA.xyz snapshots. U.S. crypto
ETPs use the dashboard aggregate AUM weekly series. RWA on-chain uses DefiLlama
RWA protocol TVL (top protocols) as a two-month weekly path. Charts are PNG
files Outlook can display.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "static_home" / "data"
CHART_DIR = ROOT / "static_home" / "mockups" / "newsletter-charts"
SERIES_PATH = DATA / "newsletter_weekly_series.json"

DEFILLAMA_STABLE_CHARTS = "https://stablecoins.llama.fi/stablecoincharts/all"
DEFILLAMA_PROTOCOLS_URL = "https://api.llama.fi/protocols"
DEFILLAMA_PROTOCOL_URL = "https://api.llama.fi/protocol/{slug}"
COINPAPRIKA_TOTAL_30D_URL = "https://coinpaprika.com/market-overview/data/total/30d/"
COINPAPRIKA_TOTAL_1Y_URL = "https://coinpaprika.com/market-overview/data/total/1y/"
USER_AGENT = (
    "Digital-Assets-Dashboard/1.0 (weekly newsletter charts; "
    "https://github.com/jtaits13/DigitalAssetDashboard)"
)

TMMF_SERIES = "tmmf"
STABLE_SERIES = "stablecoins"
CHART_LOOKBACK_DAYS = 30  # last ~1 month, matching the 30D KPI window
RWA_LLAMA_TOP_N = 20
# Real dashboard exports before the JSON freeze (same curated TMMF table).
TMMF_GIT_SNAPSHOTS: tuple[dict[str, Any], ...] = (
    {"week_end": "2026-07-13", "value": 13291670555.06899, "source": "git_snapshot"},
    {"week_end": "2026-07-20", "value": 12953855021.563791, "source": "git_snapshot"},
)

NEWSLETTER_CHART_FILES: dict[str, Path] = {
    "tmmf-weekly": CHART_DIR / "tmmf-weekly.png",
    "stablecoins-weekly": CHART_DIR / "stablecoins-weekly.png",
    "etp-weekly": CHART_DIR / "etp-weekly.png",
    "crypto-weekly": CHART_DIR / "crypto-weekly.png",
    "rwa-weekly": CHART_DIR / "rwa-weekly.png",
}

_COLOR_INK = "#1a3d5c"
_COLOR_LINE = "#1a3d5c"
_COLOR_FILL = "#d6e4ee"
_COLOR_GRID = "#e2e8f0"
_COLOR_MUTED = "#5c6b7a"
_COLOR_BG = "#ffffff"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parse_usd_compact(raw: object) -> float | None:
    s = str(raw or "").strip().replace(",", "").replace("$", "")
    if not s or s in ("-", "—"):
        return None
    s = s.upper()
    mult = 1.0
    if s[-1] in "KMBT":
        suffix = s[-1]
        s = s[:-1]
        mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[suffix]
    try:
        return float(s) * mult
    except ValueError:
        return None


def _monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _dates_in_30d_kpi_window(by_date: dict[date, float], week_end: date) -> list[date]:
    """Last observation on or before 30 days before the latest point, through latest.

    Matches the dashboard 30D method (prior point on or before end-30d vs latest).
    """
    if not by_date:
        return []
    end = min(week_end, max(by_date))
    cut = end - timedelta(days=CHART_LOOKBACK_DAYS)
    prior = [d for d in by_date if d <= cut]
    start = max(prior) if prior else min(d for d in by_date if d <= end)
    return [d for d in sorted(by_date) if start <= d <= end]


def _kpi_from_explore(section_id: str, label_match: str) -> dict[str, Any]:
    explore = _read_json(DATA / "rwa_explore_asset_type.json")
    needle = label_match.lower()
    for sec in explore.get("sections") or []:
        if str(sec.get("id") or "") != section_id:
            continue
        for kpi in sec.get("kpis") or []:
            if needle in str(kpi.get("label") or "").lower():
                return kpi if isinstance(kpi, dict) else {}
    return {}


def _upsert_point(points: list[dict[str, Any]], week_end: date, value: float, source: str) -> list[dict[str, Any]]:
    key = week_end.isoformat()
    kept = [p for p in points if str(p.get("week_end") or "") != key]
    kept.append({"week_end": key, "value": float(value), "source": source})
    kept.sort(key=lambda p: str(p.get("week_end") or ""))
    return kept


def _tmmf_distributed_kpi() -> dict[str, Any]:
    try:
        from newsletter_live_kpis import tmmf_distributed_kpi

        live = tmmf_distributed_kpi(live_only=True)
        if live and live.get("value_display"):
            return live
    except Exception:
        pass
    return {}


def _tmmf_snapshot(week_end: date, series: dict[str, Any]) -> dict[str, Any]:
    points = list(series.get("points") or [])
    for snap in TMMF_GIT_SNAPSHOTS:
        try:
            snap_day = date.fromisoformat(str(snap.get("week_end") or ""))
            snap_val = float(snap.get("value"))
        except (TypeError, ValueError):
            continue
        points = _upsert_point(points, snap_day, snap_val, str(snap.get("source") or "git_snapshot"))
    history: list[dict[str, Any]] = []
    try:
        from newsletter_live_kpis import tmmf_history_points

        history = tmmf_history_points()
    except Exception:
        history = []
    for row in history:
        if not isinstance(row, dict):
            continue
        try:
            day = date.fromisoformat(str(row.get("week_end") or ""))
            value = float(row.get("value"))
        except (TypeError, ValueError):
            continue
        points = _upsert_point(points, day, value, str(row.get("source") or "rwa_xyz"))
    points = [p for p in points if str(p.get("source") or "") != "rwa_30d_implied"]
    if not any(str(p.get("week_end") or "") == week_end.isoformat() for p in points):
        kpi = _tmmf_distributed_kpi()
        value = parse_usd_compact(kpi.get("value_display"))
        if value is not None:
            points = _upsert_point(points, week_end, value, "rwa_xyz")
    points.sort(key=lambda p: str(p.get("week_end") or ""))
    return {
        "title": "Tokenized MMF distributed value",
        "unit": "usd",
        "source": "RWA.xyz curated TMMF snapshots",
        "points": points,
    }


def _defillama_stable_points(week_end: date) -> list[dict[str, Any]]:
    resp = requests.get(
        DEFILLAMA_STABLE_CHARTS,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    rows = resp.json()
    if not isinstance(rows, list):
        return []
    by_monday: dict[date, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            ts = int(row.get("date") or 0)
        except (TypeError, ValueError):
            continue
        if ts <= 0:
            continue
        day = datetime.fromtimestamp(ts, tz=timezone.utc).date()
        if day > week_end:
            continue
        circulating = row.get("totalCirculatingUSD") or {}
        if not isinstance(circulating, dict):
            continue
        total = 0.0
        for raw in circulating.values():
            try:
                total += float(raw)
            except (TypeError, ValueError):
                continue
        if total <= 0:
            continue
        by_monday[_monday_of(day)] = total
    mondays = _dates_in_30d_kpi_window(by_monday, week_end)
    return [
        {"week_end": d.isoformat(), "value": by_monday[d], "source": "defillama"}
        for d in mondays
    ]


def _stablecoin_snapshot(week_end: date, series: dict[str, Any]) -> dict[str, Any]:
    points = list(series.get("points") or [])
    try:
        filled = _defillama_stable_points(week_end)
        if filled:
            points = filled
    except (requests.RequestException, ValueError, json.JSONDecodeError):
        kpi = _kpi_from_explore("stablecoins", "market cap")
        value = parse_usd_compact(kpi.get("value_display"))
        if value is not None:
            points = _upsert_point(points, week_end, value, "rwa_xyz")
    return {
        "title": "Stablecoin circulating USD",
        "unit": "usd",
        "source": "DefiLlama stablecoin charts (weekly)",
        "points": points,
    }


def update_weekly_series(week_end: date | None = None) -> dict[str, Any]:
    monday = week_end or _monday_of(date.today())
    payload = _read_json(SERIES_PATH)
    payload["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    payload[TMMF_SERIES] = _tmmf_snapshot(monday, payload.get(TMMF_SERIES) or {})
    payload[STABLE_SERIES] = _stablecoin_snapshot(monday, payload.get(STABLE_SERIES) or {})
    _write_json(SERIES_PATH, payload)
    return payload


def _usd_axis_label(value: float, _pos: object = None) -> str:
    abs_v = abs(value)
    if abs_v >= 1e12:
        return f"${value / 1e12:.2f}T"
    if abs_v >= 1e9:
        return f"${value / 1e9:.1f}B"
    if abs_v >= 1e6:
        return f"${value / 1e6:.1f}M"
    if abs_v >= 1e3:
        return f"${value / 1e3:.0f}K"
    return f"${value:.0f}"


def _parsed_points(series: dict[str, Any]) -> list[tuple[date, float]]:
    out: list[tuple[date, float]] = []
    for row in series.get("points") or []:
        if not isinstance(row, dict):
            continue
        try:
            day = date.fromisoformat(str(row.get("week_end") or ""))
            value = float(row.get("value"))
        except (TypeError, ValueError):
            continue
        if value <= 0:
            continue
        out.append((day, value))
    out.sort(key=lambda item: item[0])
    return out


def render_series_png(series: dict[str, Any], dest: Path) -> bool:
    points = _parsed_points(series)
    if len(points) < 2:
        return False
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
        from matplotlib.ticker import FuncFormatter
    except ImportError:
        return False

    xs = [datetime(p[0].year, p[0].month, p[0].day) for p in points]
    ys = [p[1] for p in points]
    dest.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10.2, 3.15), dpi=140)
    fig.patch.set_facecolor(_COLOR_BG)
    ax.set_facecolor(_COLOR_BG)
    ax.plot(xs, ys, color=_COLOR_LINE, linewidth=2.15, zorder=3)
    ax.fill_between(xs, ys, color=_COLOR_FILL, alpha=0.55, zorder=2)
    ax.scatter(xs, ys, color=_COLOR_LINE, s=22, zorder=4)
    ax.yaxis.set_major_formatter(FuncFormatter(_usd_axis_label))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    if len(xs) <= 6:
        ax.set_xticks(xs)
    else:
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=7))
    ax.grid(axis="y", color=_COLOR_GRID, linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(_COLOR_GRID)
    ax.spines["bottom"].set_color(_COLOR_GRID)
    ax.tick_params(colors=_COLOR_MUTED, labelsize=8.5, length=0)
    ymin = min(ys)
    ymax = max(ys)
    pad = max((ymax - ymin) * 0.18, ymax * 0.02)
    ax.set_ylim(max(0.0, ymin - pad), ymax + pad)
    ax.margins(x=0.02)
    fig.tight_layout(pad=0.35)
    fig.savefig(dest, dpi=140, facecolor=_COLOR_BG, bbox_inches="tight")
    plt.close(fig)
    return dest.is_file()


def _tmmf_caption(series: dict[str, Any]) -> str:
    sources = {str(p.get("source") or "") for p in (series.get("points") or [])}
    if sources & {"rwa_xyz_val_7d", "rwa_xyz_val_30d", "git_snapshot"}:
        return (
            "Curated TMMF distributed value from RWA.xyz. "
            "Live points are the current total plus the public 7D-ago and 30D-ago token values; "
            "13 Jul and 20 Jul are dashboard snapshots taken before the feed froze. "
            "RWA.xyz public pages do not publish a daily series, so some weeks are missing."
        )
    if "rwa_30d_implied" in sources:
        return (
            "Weekly snapshots of curated TMMF distributed value (RWA.xyz). "
            "The first point is the RWA.xyz 30-day-ago level; later Mondays fill in from dashboard snapshots."
        )
    return "Weekly snapshots of curated TMMF distributed value (RWA.xyz)."


def _stable_caption(series: dict[str, Any]) -> str:
    sources = {str(p.get("source") or "") for p in (series.get("points") or [])}
    if sources == {"rwa_xyz"}:
        return "Weekly stablecoin market cap snapshots (RWA.xyz)."
    return (
        "Weekly circulating stablecoin USD (DefiLlama). "
        "Headline KPI above is RWA.xyz and can differ slightly from this series."
    )


def _chart_img_html(cid: str, *, outlook: bool, alt: str) -> str:
    src = f"cid:{cid}" if outlook else f"newsletter-charts/{cid}.png"
    return (
        f'<img src="{src}" width="1100" alt="{alt}" '
        f'style="display:block;width:100%;max-width:1100px;height:auto;border:0;outline:none;text-decoration:none;" />'
    )


def _etp_weekly_series(week_end: date) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    try:
        from newsletter_live_kpis import live_etp_aum_series

        live_series = live_etp_aum_series()
        if live_series:
            payload = {"series": live_series}
    except Exception:
        payload = {}
    if not payload.get("series"):
        payload = _read_json(DATA / "aum_series.json")
    by_monday: dict[date, float] = {}
    for row in payload.get("series") or []:
        if not isinstance(row, dict):
            continue
        try:
            day = datetime.fromisoformat(str(row.get("date") or "")).date()
            aum_b = float(row.get("aum_billions"))
        except (TypeError, ValueError):
            continue
        if day > week_end or aum_b <= 0:
            continue
        by_monday[_monday_of(day)] = aum_b * 1e9
    mondays = _dates_in_30d_kpi_window(by_monday, week_end)
    return {
        "title": "U.S. crypto ETP aggregate AUM",
        "unit": "usd",
        "source": "Yahoo-scaled listed AUM (weekly)",
        "points": [
            {"week_end": d.isoformat(), "value": by_monday[d], "source": "yahoo_scaled"}
            for d in mondays
        ],
    }


def _etp_caption() -> str:
    return (
        "30D path of estimated aggregate AUM (Yahoo prices scaled from current reported AUM). "
        "The Aggregate AUM % above uses this same series."
    )


def _paprika_payload_to_daily(payload: object, week_end: date) -> dict[date, float]:
    usd: list[Any] = []
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        raw = payload[0].get("usd")
        if isinstance(raw, list):
            usd = raw
    by_day: dict[date, float] = {}
    for point in usd:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        try:
            ts = float(point[0])
            value = float(point[1])
        except (TypeError, ValueError):
            continue
        if ts > 1e12:
            ts /= 1000.0
        if ts <= 0 or value <= 0:
            continue
        day = datetime.fromtimestamp(ts, tz=timezone.utc).date()
        if day > week_end:
            continue
        by_day[day] = value
    return by_day


def _weekly_chart_dates(by_day: dict[date, float], week_end: date) -> list[date]:
    window = _dates_in_30d_kpi_window(by_day, week_end)
    if not window:
        return []
    start, end = window[0], window[-1]
    mondays = [d for d in window if d.weekday() == 0]
    return sorted(set(mondays + [start, end]))


def _crypto_weekly_series(week_end: date) -> dict[str, Any]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    by_day: dict[date, float] = {}
    for url in (COINPAPRIKA_TOTAL_30D_URL, COINPAPRIKA_TOTAL_1Y_URL):
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        by_day = _paprika_payload_to_daily(resp.json(), week_end)
        if by_day:
            break
    dates = _weekly_chart_dates(by_day, week_end)
    return {
        "title": "Crypto total market cap",
        "unit": "usd",
        "source": "CoinPaprika total market cap (30D)",
        "points": [
            {"week_end": d.isoformat(), "value": by_day[d], "source": "coinpaprika"}
            for d in dates
        ],
    }


def _crypto_caption() -> str:
    return (
        "30D CoinPaprika total market cap (weekly points, same window as the KPI above)."
    )


def _primary_from_series(series: dict[str, Any]) -> dict[str, Any] | None:
    points = _parsed_points(series)
    if len(points) < 2:
        return None
    first = points[0][1]
    last = points[-1][1]
    if first <= 0:
        return None
    from crypto_etps.client import format_usd_compact

    return {
        "value_display": format_usd_compact(last),
        "delta_pct": (last - first) / first * 100.0,
    }


def _llama_headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT, "Accept": "application/json"}


def _fetch_protocol_tvl_days(slug: str) -> list[tuple[date, float]]:
    resp = requests.get(
        DEFILLAMA_PROTOCOL_URL.format(slug=slug),
        headers=_llama_headers(),
        timeout=25,
    )
    resp.raise_for_status()
    payload = resp.json()
    rows = payload.get("tvl") if isinstance(payload, dict) else None
    by_day: dict[date, float] = {}
    if not isinstance(rows, list):
        return []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            ts = int(row.get("date") or 0)
            value = float(row.get("totalLiquidityUSD"))
        except (TypeError, ValueError):
            continue
        if ts <= 0 or value <= 0:
            continue
        by_day[datetime.fromtimestamp(ts, tz=timezone.utc).date()] = value
    return list(by_day.items())


def _defillama_rwa_weekly_series(week_end: date) -> dict[str, Any]:
    resp = requests.get(DEFILLAMA_PROTOCOLS_URL, headers=_llama_headers(), timeout=40)
    resp.raise_for_status()
    protocols = resp.json()
    if not isinstance(protocols, list):
        return {"title": "RWA distributed value", "points": []}
    rwa = [
        p
        for p in protocols
        if isinstance(p, dict) and str(p.get("category") or "") == "RWA" and p.get("slug")
    ]
    rwa.sort(key=lambda p: float(p.get("tvl") or 0), reverse=True)
    slugs = [str(p.get("slug")) for p in rwa[:RWA_LLAMA_TOP_N]]
    by_day: dict[date, float] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(_fetch_protocol_tvl_days, slug) for slug in slugs]
        for fut in as_completed(futs):
            try:
                days = fut.result()
            except (requests.RequestException, ValueError, json.JSONDecodeError):
                continue
            for day, value in days:
                if day > week_end:
                    continue
                by_day[day] = by_day.get(day, 0.0) + value
    by_monday: dict[date, float] = {}
    for day, value in sorted(by_day.items()):
        by_monday[_monday_of(day)] = value
    mondays = _dates_in_30d_kpi_window(by_monday, week_end)
    return {
        "title": "RWA distributed value",
        "unit": "usd",
        "source": "DefiLlama RWA protocol TVL (weekly)",
        "points": [
            {"week_end": d.isoformat(), "value": by_monday[d], "source": "defillama"}
            for d in mondays
        ],
    }


def _rwa_caption() -> str:
    return (
        "Weekly RWA protocol TVL (DefiLlama, largest protocols). "
        "Headline KPI above is RWA.xyz distributed asset value and can differ."
    )


def _chart_block_html(
    *,
    cid: str,
    title: str,
    caption: str,
    outlook: bool,
) -> str:
    png = NEWSLETTER_CHART_FILES.get(cid)
    if png is None or not png.is_file():
        return ""
    img = _chart_img_html(cid, outlook=outlook, alt=title)
    if outlook:
        return (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="margin:0 0 16px;border-collapse:collapse;border:1px solid #e2e8f0;">'
            f'<tr><td style="padding:10px 10px 4px;font-size:12px;line-height:1.4;'
            f'mso-line-height-rule:exactly;font-weight:700;color:{_COLOR_INK};'
            f"font-family:Calibri,Arial,sans-serif;\">{title}</td></tr>"
            f'<tr><td style="padding:0 8px;">{img}</td></tr>'
            f'<tr><td style="padding:4px 10px 10px;font-size:11px;line-height:1.45;'
            f'mso-line-height-rule:exactly;color:{_COLOR_MUTED};'
            f"font-family:Calibri,Arial,sans-serif;\">{caption}</td></tr></table>"
        )
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="margin:0 0 1rem;border-collapse:collapse;border:1px solid #e2e8f0;border-radius:8px;">'
        f'<tr><td style="padding:0.55rem 0.7rem 0.2rem;font-size:12px;font-weight:700;'
        f'color:{_COLOR_INK};">{title}</td></tr>'
        f'<tr><td style="padding:0 0.45rem;">{img}</td></tr>'
        f'<tr><td style="padding:0.2rem 0.7rem 0.65rem;font-size:11px;line-height:1.45;'
        f'color:{_COLOR_MUTED};">{caption}</td></tr></table>'
    )


def prepare_newsletter_charts(*, week_end: date, outlook: bool = False) -> tuple[dict[str, str], dict[str, Any]]:
    """Update series, render PNGs, return HTML snippets and same-source KPI overlays."""
    payload = update_weekly_series(week_end)
    tmmf = payload.get(TMMF_SERIES) or {}
    stable = payload.get(STABLE_SERIES) or {}
    tmmf_html = ""
    stable_html = ""
    etp_html = ""
    if render_series_png(tmmf, NEWSLETTER_CHART_FILES["tmmf-weekly"]):
        tmmf_html = _chart_block_html(
            cid="tmmf-weekly",
            title=str(tmmf.get("title") or "Tokenized MMF distributed value"),
            caption=_tmmf_caption(tmmf),
            outlook=outlook,
        )
    if render_series_png(stable, NEWSLETTER_CHART_FILES["stablecoins-weekly"]):
        stable_html = _chart_block_html(
            cid="stablecoins-weekly",
            title=str(stable.get("title") or "Stablecoin circulating USD"),
            caption=_stable_caption(stable),
            outlook=outlook,
        )
    etp = _etp_weekly_series(week_end)
    if render_series_png(etp, NEWSLETTER_CHART_FILES["etp-weekly"]):
        etp_html = _chart_block_html(
            cid="etp-weekly",
            title=str(etp.get("title") or "U.S. crypto ETP aggregate AUM"),
            caption=_etp_caption(),
            outlook=outlook,
        )
    crypto_html = ""
    crypto_series: dict[str, Any] = {"points": []}
    try:
        crypto_series = _crypto_weekly_series(week_end)
    except (requests.RequestException, ValueError, json.JSONDecodeError):
        crypto_series = {"points": []}
    if render_series_png(crypto_series, NEWSLETTER_CHART_FILES["crypto-weekly"]):
        crypto_html = _chart_block_html(
            cid="crypto-weekly",
            title=str(crypto_series.get("title") or "Crypto total market cap"),
            caption=_crypto_caption(),
            outlook=outlook,
        )
    rwa_html = ""
    try:
        rwa_series = _defillama_rwa_weekly_series(week_end)
    except (requests.RequestException, ValueError, json.JSONDecodeError):
        rwa_series = {"points": []}
    if render_series_png(rwa_series, NEWSLETTER_CHART_FILES["rwa-weekly"]):
        rwa_html = _chart_block_html(
            cid="rwa-weekly",
            title=str(rwa_series.get("title") or "RWA distributed value"),
            caption=_rwa_caption(),
            outlook=outlook,
        )
    html = {
        "tmmf": tmmf_html,
        "stablecoins": stable_html,
        "etp": etp_html,
        "crypto": crypto_html,
        "rwa": rwa_html,
    }
    aligned: dict[str, Any] = {}
    crypto_primary = _primary_from_series(crypto_series)
    if crypto_primary:
        aligned["crypto_primary"] = crypto_primary
    etp_primary = _primary_from_series(etp)
    if etp_primary:
        aligned["etp_aggregate"] = etp_primary
    return html, aligned


def main() -> None:
    payload = update_weekly_series()
    tmmf = payload.get(TMMF_SERIES) or {}
    stable = payload.get(STABLE_SERIES) or {}
    tmmf_ok = render_series_png(tmmf, NEWSLETTER_CHART_FILES["tmmf-weekly"])
    stable_ok = render_series_png(stable, NEWSLETTER_CHART_FILES["stablecoins-weekly"])
    etp = _etp_weekly_series(_monday_of(date.today()))
    etp_ok = render_series_png(etp, NEWSLETTER_CHART_FILES["etp-weekly"])
    try:
        crypto_series = _crypto_weekly_series(_monday_of(date.today()))
    except Exception as exc:
        crypto_series = {"points": []}
        print(f"Crypto series skipped: {exc}")
    crypto_ok = render_series_png(crypto_series, NEWSLETTER_CHART_FILES["crypto-weekly"])
    try:
        rwa_series = _defillama_rwa_weekly_series(_monday_of(date.today()))
    except Exception as exc:
        rwa_series = {"points": []}
        print(f"RWA series skipped: {exc}")
    rwa_ok = render_series_png(rwa_series, NEWSLETTER_CHART_FILES["rwa-weekly"])
    print(f"Wrote {SERIES_PATH}")
    print(f"TMMF points: {len(tmmf.get('points') or [])} png={tmmf_ok}")
    print(f"Stablecoin points: {len(stable.get('points') or [])} png={stable_ok}")
    print(f"ETP points: {len(etp.get('points') or [])} png={etp_ok}")
    print(f"Crypto points: {len(crypto_series.get('points') or [])} png={crypto_ok}")
    print(f"RWA points: {len(rwa_series.get('points') or [])} png={rwa_ok}")


if __name__ == "__main__":
    main()
