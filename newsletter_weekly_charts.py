"""Weekly newsletter charts for TMMF, stablecoins, ETPs, crypto, and RWA.

Each section has a repeatable weekly refresh. If that refresh fails, the last
committed series is reused and a do-not-send issue is raised.

- TMMF: freeze this week's printed RWA.xyz figure (no public daily series).
- Stablecoins: refetch DefiLlama circulating USD (Mondays).
- RWA chart: refetch DefiLlama RWA protocol TVL. Headline KPI is RWA.xyz.
- Crypto: refetch CoinPaprika 30D total market cap (same series as the KPI).
- U.S. crypto ETPs: refetch the dashboard aggregate AUM weekly series.

Charts are PNG files Outlook can display.
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
CRYPTO_SERIES = "crypto"
ETP_SERIES = "etp"
RWA_SERIES = "rwa"
CHART_LOOKBACK_DAYS = 30  # last ~1 month, matching the 30D KPI window
# Last point may trail week_end (T-1 APIs / weekends). TMMF must be this Monday.
CHART_MAX_LAG_DAYS = {
    TMMF_SERIES: 0,
    STABLE_SERIES: 8,
    CRYPTO_SERIES: 4,
    RWA_SERIES: 8,
}
_CHART_ISSUES: list[str] = []
RWA_LLAMA_TOP_N = 20
# Recovered curated TMMF totals: git dashboard exports, plus Wayback copies of
# app.rwa.xyz/treasuries (same fund allowlist). Archive timestamps: 20260727104342,
# 20260731124452, 20260805094824.
TMMF_ARCHIVAL_SNAPSHOTS: tuple[dict[str, Any], ...] = (
    {"week_end": "2026-07-13", "value": 13291670555.06899, "source": "git_snapshot"},
    {"week_end": "2026-07-20", "value": 12953855021.563791, "source": "git_snapshot"},
    {"week_end": "2026-07-27", "value": 13177150147.0, "source": "wayback_rwa_xyz"},
    {"week_end": "2026-07-31", "value": 13168063688.0, "source": "wayback_rwa_xyz"},
    {"week_end": "2026-08-05", "value": 13214277873.0, "source": "wayback_rwa_xyz"},
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


_TMMF_FILL_SOURCES = frozenset({"rwa_xyz_val_7d", "rwa_xyz_val_30d"})


def _upsert_point(points: list[dict[str, Any]], week_end: date, value: float, source: str) -> list[dict[str, Any]]:
    key = week_end.isoformat()
    kept = [p for p in points if str(p.get("week_end") or "") != key]
    kept.append({"week_end": key, "value": float(value), "source": source})
    kept.sort(key=lambda p: str(p.get("week_end") or ""))
    return kept


def _point_on(points: list[dict[str, Any]], week_end: date) -> dict[str, Any] | None:
    key = week_end.isoformat()
    for row in points:
        if str(row.get("week_end") or "") == key:
            return row
    return None


def _upsert_fill(points: list[dict[str, Any]], week_end: date, value: float, source: str) -> list[dict[str, Any]]:
    """Add a rolling 7D/30D point only when that date is still empty."""
    if _point_on(points, week_end) is not None:
        return points
    return _upsert_point(points, week_end, value, source)


def _upsert_frozen(points: list[dict[str, Any]], week_end: date, value: float, source: str) -> list[dict[str, Any]]:
    """Keep printed/archival weekly values; replace fill-only dates."""
    existing = _point_on(points, week_end)
    if existing is not None and str(existing.get("source") or "") not in _TMMF_FILL_SOURCES:
        return points
    return _upsert_point(points, week_end, value, source)


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
    printed: list[dict[str, Any]] = []
    try:
        from newsletter_live_kpis import tmmf_newsletter_weekly_points

        printed = tmmf_newsletter_weekly_points()
    except Exception:
        printed = []
    for row in printed:
        if not isinstance(row, dict):
            continue
        try:
            day = date.fromisoformat(str(row.get("week_end") or ""))
            value = float(row.get("value"))
        except (TypeError, ValueError):
            continue
        points = _upsert_frozen(points, day, value, "newsletter")
    for snap in TMMF_ARCHIVAL_SNAPSHOTS:
        try:
            snap_day = date.fromisoformat(str(snap.get("week_end") or ""))
            snap_val = float(snap.get("value"))
        except (TypeError, ValueError):
            continue
        points = _upsert_frozen(points, snap_day, snap_val, str(snap.get("source") or "git_snapshot"))
    history: list[dict[str, Any]] = []
    try:
        from newsletter_live_kpis import tmmf_history_points

        history = tmmf_history_points()
    except Exception:
        history = []
    current_live: float | None = None
    for row in history:
        if not isinstance(row, dict):
            continue
        try:
            day = date.fromisoformat(str(row.get("week_end") or ""))
            value = float(row.get("value"))
        except (TypeError, ValueError):
            continue
        source = str(row.get("source") or "rwa_xyz")
        if source in _TMMF_FILL_SOURCES:
            points = _upsert_fill(points, day, value, source)
            continue
        if day == week_end:
            current_live = value
            continue
        points = _upsert_fill(points, day, value, "newsletter")
    points = [p for p in points if str(p.get("source") or "") != "rwa_30d_implied"]
    if current_live is None:
        kpi = _tmmf_distributed_kpi()
        current_live = parse_usd_compact(kpi.get("value_display"))
    if current_live is not None:
        points = _upsert_point(points, week_end, current_live, "newsletter")
    elif _point_on(points, week_end) is not None:
        existing = _point_on(points, week_end) or {}
        if str(existing.get("source") or "") in {"rwa_xyz", ""}:
            points = _upsert_point(
                points, week_end, float(existing.get("value")), "newsletter"
            )
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


def _stablecoin_live_series(week_end: date) -> dict[str, Any]:
    points = _defillama_stable_points(week_end)
    return {
        "title": "Stablecoin circulating USD",
        "unit": "usd",
        "source": "DefiLlama stablecoin charts (weekly)",
        "points": points,
    }


def chart_refresh_issues() -> list[str]:
    return list(_CHART_ISSUES)


def _set_chart_issues(issues: list[str]) -> None:
    global _CHART_ISSUES
    _CHART_ISSUES = [str(item) for item in issues if str(item).strip()]


def _series_lag_issue(
    label: str,
    series: dict[str, Any],
    week_end: date,
    max_lag_days: int,
) -> str | None:
    points = _parsed_points(series)
    if len(points) < 2:
        return f"{label}: chart does not have a usable series for week ending {week_end.isoformat()}."
    last = points[-1][0]
    lag = (week_end - last).days
    if lag > max_lag_days:
        return (
            f"{label}: chart last point is {last.isoformat()}, "
            f"more than {max_lag_days} days before week ending {week_end.isoformat()}."
        )
    return None


def _with_previous_series(
    *,
    label: str,
    live: dict[str, Any],
    previous: dict[str, Any],
    week_end: date,
    max_lag_days: int | None,
) -> tuple[dict[str, Any], str | None]:
    live_pts = _parsed_points(live)
    prev_pts = _parsed_points(previous)
    if len(live_pts) >= 2:
        if max_lag_days is None:
            return live, None
        return live, _series_lag_issue(label, live, week_end, max_lag_days)
    if len(prev_pts) >= 2:
        return previous, (
            f"{label}: chart did not refresh for week ending {week_end.isoformat()}; "
            "using last week's series."
        )
    chosen = live if live_pts else previous
    if _parsed_points(chosen):
        return chosen, (
            f"{label}: chart does not have a usable series for week ending {week_end.isoformat()}."
        )
    return chosen or {"points": []}, f"{label}: chart fetch failed this week."


def update_weekly_series(week_end: date | None = None) -> dict[str, Any]:
    monday = week_end or _monday_of(date.today())
    payload = _read_json(SERIES_PATH)
    payload["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    issues: list[str] = []
    _set_chart_issues([])

    tmmf = _tmmf_snapshot(monday, payload.get(TMMF_SERIES) or {})
    payload[TMMF_SERIES] = tmmf
    lag = _series_lag_issue("TMMF", tmmf, monday, CHART_MAX_LAG_DAYS[TMMF_SERIES])
    if lag:
        issues.append(lag)

    try:
        stable_live = _stablecoin_live_series(monday)
    except (requests.RequestException, ValueError, json.JSONDecodeError):
        stable_live = {"points": []}
    stable, stable_issue = _with_previous_series(
        label="Stablecoins",
        live=stable_live,
        previous=payload.get(STABLE_SERIES) or {},
        week_end=monday,
        max_lag_days=CHART_MAX_LAG_DAYS[STABLE_SERIES],
    )
    payload[STABLE_SERIES] = stable
    if stable_issue:
        issues.append(stable_issue)

    try:
        crypto_live = _crypto_weekly_series(monday)
    except (requests.RequestException, ValueError, json.JSONDecodeError):
        crypto_live = {"points": []}
    crypto, crypto_issue = _with_previous_series(
        label="Crypto",
        live=crypto_live,
        previous=payload.get(CRYPTO_SERIES) or {},
        week_end=monday,
        max_lag_days=CHART_MAX_LAG_DAYS[CRYPTO_SERIES],
    )
    payload[CRYPTO_SERIES] = crypto
    if crypto_issue:
        issues.append(crypto_issue)

    try:
        rwa_live = _defillama_rwa_weekly_series(monday)
    except (requests.RequestException, ValueError, json.JSONDecodeError):
        rwa_live = {"points": []}
    rwa, rwa_issue = _with_previous_series(
        label="RWA",
        live=rwa_live,
        previous=payload.get(RWA_SERIES) or {},
        week_end=monday,
        max_lag_days=CHART_MAX_LAG_DAYS[RWA_SERIES],
    )
    payload[RWA_SERIES] = rwa
    if rwa_issue:
        issues.append(rwa_issue)

    etp_live = _etp_weekly_series(monday)
    etp, etp_issue = _with_previous_series(
        label="U.S. crypto ETPs",
        live=etp_live,
        previous=payload.get(ETP_SERIES) or {},
        week_end=monday,
        max_lag_days=None,
    )
    payload[ETP_SERIES] = etp
    if etp_issue:
        issues.append(etp_issue)

    _set_chart_issues(issues)
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
    if sources & {"rwa_xyz_val_7d", "rwa_xyz_val_30d", "git_snapshot", "wayback_rwa_xyz"}:
        return (
            "Curated TMMF distributed value from RWA.xyz. "
            "Latest / 7D / 30D are live token totals; 13 Jul and 20 Jul are dashboard snapshots; "
            "27 Jul, 31 Jul, and 5 Aug are Wayback captures of the RWA.xyz Treasuries page "
            "(same fund list). Later Mondays are that week's printed newsletter figure. "
            "Public pages do not publish a daily series."
        )
    if "rwa_30d_implied" in sources:
        return (
            "Weekly snapshots of curated TMMF distributed value (RWA.xyz). "
            "The first point is the RWA.xyz 30-day-ago level; later Mondays fill in from dashboard snapshots."
        )
    return (
        "Weekly snapshots of curated TMMF distributed value (RWA.xyz). "
        "Each Monday is the figure printed in that week's newsletter."
    )


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
    issues = chart_refresh_issues()
    tmmf = payload.get(TMMF_SERIES) or {}
    stable = payload.get(STABLE_SERIES) or {}
    etp = payload.get(ETP_SERIES) or {}
    crypto_series = payload.get(CRYPTO_SERIES) or {}
    rwa_series = payload.get(RWA_SERIES) or {}

    tmmf_html = ""
    if render_series_png(tmmf, NEWSLETTER_CHART_FILES["tmmf-weekly"]):
        tmmf_html = _chart_block_html(
            cid="tmmf-weekly",
            title=str(tmmf.get("title") or "Tokenized MMF distributed value"),
            caption=_tmmf_caption(tmmf),
            outlook=outlook,
        )
    elif len(_parsed_points(tmmf)) >= 2:
        issues.append("TMMF: chart image did not render.")

    stable_html = ""
    if render_series_png(stable, NEWSLETTER_CHART_FILES["stablecoins-weekly"]):
        stable_html = _chart_block_html(
            cid="stablecoins-weekly",
            title=str(stable.get("title") or "Stablecoin circulating USD"),
            caption=_stable_caption(stable),
            outlook=outlook,
        )
    elif len(_parsed_points(stable)) >= 2:
        issues.append("Stablecoins: chart image did not render.")

    etp_html = ""
    if render_series_png(etp, NEWSLETTER_CHART_FILES["etp-weekly"]):
        etp_html = _chart_block_html(
            cid="etp-weekly",
            title=str(etp.get("title") or "U.S. crypto ETP aggregate AUM"),
            caption=_etp_caption(),
            outlook=outlook,
        )
    elif len(_parsed_points(etp)) >= 2:
        issues.append("U.S. crypto ETPs: chart image did not render.")

    crypto_html = ""
    if render_series_png(crypto_series, NEWSLETTER_CHART_FILES["crypto-weekly"]):
        crypto_html = _chart_block_html(
            cid="crypto-weekly",
            title=str(crypto_series.get("title") or "Crypto total market cap"),
            caption=_crypto_caption(),
            outlook=outlook,
        )
    elif len(_parsed_points(crypto_series)) >= 2:
        issues.append("Crypto: chart image did not render.")

    rwa_html = ""
    if render_series_png(rwa_series, NEWSLETTER_CHART_FILES["rwa-weekly"]):
        rwa_html = _chart_block_html(
            cid="rwa-weekly",
            title=str(rwa_series.get("title") or "RWA distributed value"),
            caption=_rwa_caption(),
            outlook=outlook,
        )
    elif len(_parsed_points(rwa_series)) >= 2:
        issues.append("RWA: chart image did not render.")

    _set_chart_issues(issues)
    try:
        from newsletter_live_kpis import append_refresh_issues

        append_refresh_issues(issues)
    except Exception:
        pass

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
    etp = payload.get(ETP_SERIES) or {}
    crypto_series = payload.get(CRYPTO_SERIES) or {}
    rwa_series = payload.get(RWA_SERIES) or {}
    tmmf_ok = render_series_png(tmmf, NEWSLETTER_CHART_FILES["tmmf-weekly"])
    stable_ok = render_series_png(stable, NEWSLETTER_CHART_FILES["stablecoins-weekly"])
    etp_ok = render_series_png(etp, NEWSLETTER_CHART_FILES["etp-weekly"])
    crypto_ok = render_series_png(crypto_series, NEWSLETTER_CHART_FILES["crypto-weekly"])
    rwa_ok = render_series_png(rwa_series, NEWSLETTER_CHART_FILES["rwa-weekly"])
    print(f"Wrote {SERIES_PATH}")
    print(f"TMMF points: {len(tmmf.get('points') or [])} png={tmmf_ok}")
    print(f"Stablecoin points: {len(stable.get('points') or [])} png={stable_ok}")
    print(f"ETP points: {len(etp.get('points') or [])} png={etp_ok}")
    print(f"Crypto points: {len(crypto_series.get('points') or [])} png={crypto_ok}")
    print(f"RWA points: {len(rwa_series.get('points') or [])} png={rwa_ok}")
    for item in chart_refresh_issues():
        print(f"Chart issue: {item}")


if __name__ == "__main__":
    main()
