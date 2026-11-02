"""
Newsletter-only weekly takeaways (first cut).

Prefer meaningful WoW/30D KPI moves and recent on-topic news over page Key
observation templates. Track last-shipped leads so the same structural line
does not repeat every week unless nothing fresher exists.

Kill switch (restore page-KO bullets):
  NEWSLETTER_WEEKLY_TAKEAWAYS=0
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
COOLDOWN_PATH = ROOT / "logs" / "newsletter-takeaway-cooldown.json"

# Default ON; set env to 0/false/no to revert to page KO scraping.
def weekly_takeaways_enabled() -> bool:
    raw = (os.environ.get("NEWSLETTER_WEEKLY_TAKEAWAYS") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


_WOW_THRESHOLD = 2.0  # percentage points; mirrors newsletter rail-flat threshold
_LEAD_NORM_RE = re.compile(r"[^a-z0-9\s]+")
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class WeeklyTakeaway:
    lead: str
    body: str
    kind: str  # wow | news | flat | soft | launch | launch_none
    article: dict[str, Any] | None = None
    lead_key: str = ""


@dataclass
class SectionKpiMove:
    label: str
    value_display: str
    delta_pct: float | None
    delta_display: str


SECTION_NEWS_FAMILIES: dict[str, tuple[str, ...]] = {
    # Keep TMMF tight — "tokenization" is too broad and pulls crypto/policy noise.
    "tmmf": ("tmmf",),
    "stablecoins": ("stablecoins",),
    "rwa": ("tokenization",),
    "etp": ("etp_flows", "etp"),
    "crypto": ("infrastructure", "macro", "general"),
}


def normalize_lead(lead: str) -> str:
    t = _LEAD_NORM_RE.sub(" ", (lead or "").lower())
    return _WS_RE.sub(" ", t).strip()


def _pct_value(raw: Any, *, unit: str = "percent") -> float | None:
    """Return percentage points (e.g. 2.7 for +2.7%).

    Explore/RWA deltas are stored as fractions; crypto and ETP deltas are
    already percentage points. Callers must identify the unit explicitly.
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        n = float(raw)
    else:
        s = str(raw).strip().replace("%", "").replace("+", "")
        if not s or s == "—":
            return None
        try:
            n = float(s)
        except ValueError:
            return None
    if unit == "fraction":
        n *= 100.0
    return n


def _fmt_pct(delta: float | None) -> str:
    if delta is None:
        return "—"
    return f"{delta:+.1f}%"


def _move_verb(delta: float) -> str:
    if delta >= _WOW_THRESHOLD:
        return "rose"
    if delta <= -_WOW_THRESHOLD:
        return "fell"
    return "held roughly steady"


def _signed_level(display: str) -> int:
    """+1 for a printed inflow, -1 for a printed outflow, 0 when the sign is unknown."""
    raw = (display or "").replace("\u2212", "-").replace("–", "-").strip()
    if raw.startswith("+"):
        return 1
    if raw.startswith("-"):
        return -1
    return 0


_SNAPSHOT_PATH = ROOT / "static_home" / "data" / "newsletter_kpi_snapshot.json"
_PRIOR_KEY = {
    "tmmf": "tmmf",
    "stablecoins": "stable",
    "rwa": "rwa",
    "crypto": "crypto",
    "etp": "etp",
}
_LEVEL_NAME = {
    "tmmf": "Distributed value",
    "stablecoins": "Stablecoin market cap",
    "rwa": "Distributed asset value",
    "crypto": "Total market cap",
    "etp": "Aggregate AUM",
}
_FAMILY_SECTION = {
    "stablecoins": "stablecoins",
    "tokenization": "rwa",
    "tmmf": "tmmf",
    "etp": "etp",
    "etp_flows": "etp",
    "infrastructure": "crypto",
    "macro": "crypto",
    "general": "crypto",
}
_MONEY_RE = re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*([KMBT])?", re.I)


@dataclass
class WeekContext:
    """This week's printed levels plus the previous newsletter reading."""

    current_week: date | None
    prior: dict[str, tuple[date, str]]
    explore: dict[str, dict[str, Any]]
    etp: dict[str, Any] | None
    crypto: dict[str, Any] | None
    levels: dict[str, str]


def _parse_compact_usd(text: str) -> float | None:
    match = _MONEY_RE.search(text or "")
    if not match:
        return None
    try:
        number = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    unit = (match.group(2) or "").upper()
    scale = {"": 1.0, "K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
    return number * scale[unit]


def _signed_pct(pct: float) -> str:
    if abs(pct) < 0.05:
        return "flat"
    return f"{pct:+.1f}%"


def _read_snapshot_payload() -> dict[str, Any] | None:
    if not _SNAPSHOT_PATH.is_file():
        return None
    try:
        payload = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _prior_display(row: dict[str, Any], key: str) -> str:
    levels = row.get("levels") if isinstance(row.get("levels"), dict) else {}
    display = str(levels.get(key) or "").strip()
    if display:
        return display
    fingerprint = str((row.get("fingerprints") or {}).get(key) or "")
    return fingerprint.split("|", 1)[0].strip()


def prior_prints_from_snapshot(payload: dict[str, Any] | None) -> tuple[date | None, dict[str, tuple[date, str]]]:
    """Latest saved reading before the snapshot's current week, keyed by section id."""
    if not isinstance(payload, dict):
        return None, {}
    try:
        current = date.fromisoformat(str(payload.get("week_end") or ""))
    except ValueError:
        current = None
    chosen: dict[str, tuple[date, str]] = {}
    best: date | None = None
    best_row: dict[str, Any] | None = None
    for row in payload.get("history") or []:
        if not isinstance(row, dict):
            continue
        try:
            day = date.fromisoformat(str(row.get("week_end") or ""))
        except ValueError:
            continue
        if current is not None and day >= current:
            continue
        if best is None or day > best:
            best = day
            best_row = row
    if best is None or best_row is None:
        return current, {}
    for section_id, key in _PRIOR_KEY.items():
        display = _prior_display(best_row, key)
        if _parse_compact_usd(display) is not None:
            chosen[section_id] = (best, display)
    return current, chosen


def make_week_context(
    explore: dict[str, dict[str, Any]] | None,
    etp: dict[str, Any] | None,
    crypto: dict[str, Any] | None,
    *,
    snapshot: dict[str, Any] | None = None,
) -> WeekContext:
    payload = snapshot if snapshot is not None else _read_snapshot_payload()
    current_week, prior = prior_prints_from_snapshot(payload)
    explore = explore or {}
    levels = {
        "tmmf": str(_kpi_display(explore, "tokenized_mmf", "distributed") or ""),
        "stablecoins": str(_kpi_display(explore, "stablecoins", "market cap") or ""),
        "rwa": str(_kpi_display(explore, "rwa_global", "distributed asset") or ""),
        "crypto": str(((crypto or {}).get("primary") or {}).get("value_display") or ""),
        "etp": str((etp or {}).get("total_aum_display") or ""),
    }
    return WeekContext(
        current_week=current_week,
        prior=prior,
        explore=explore,
        etp=etp,
        crypto=crypto,
        levels=levels,
    )


def load_week_context_from_snapshot() -> WeekContext:
    payload = _read_snapshot_payload() or {}
    latest = payload.get("latest") if isinstance(payload.get("latest"), dict) else {}
    explore = {
        "tokenized_mmf": {"kpis": list(latest.get("tmmf_kpis") or [])},
        "stablecoins": {"kpis": list(latest.get("stable_kpis") or [])},
        "rwa_global": {"kpis": list(latest.get("rwa_kpis") or [])},
    }
    crypto = latest.get("crypto") if isinstance(latest.get("crypto"), dict) else {}
    etp = latest.get("etp") if isinstance(latest.get("etp"), dict) else {}
    return make_week_context(explore, etp, crypto, snapshot=payload)


def _kpi_display(explore: dict[str, dict[str, Any]], section_id: str, label_match: str) -> str:
    move = explore_kpi_move(explore, section_id, label_match=label_match)
    return move.value_display if move else ""


def _when_phrase(prior_day: date, current_week: date | None) -> str:
    label = f"{prior_day.day} {prior_day.strftime('%b')}"
    if current_week is None:
        return f"since the {label} reading"
    gap = (current_week - prior_day).days
    if gap <= 10:
        return f"since last week's {label} reading"
    return f"since the {label} reading"


def _since_clause(section_id: str, ctx: WeekContext, move: SectionKpiMove | None) -> str:
    key = section_id
    metric = _LEVEL_NAME.get(section_id, "The level")
    current = ctx.levels.get(section_id) or ""
    if section_id == "etp" and move is not None and "flow" in (move.label or "").lower():
        metric = "Aggregate AUM"
        current = ctx.levels.get("etp") or current
    elif move is not None and _parse_compact_usd(move.value_display) is not None and "flow" not in (move.label or "").lower():
        current = move.value_display
        metric = str(move.label or metric)
    prior = ctx.prior.get(key)
    current_value = _parse_compact_usd(current)
    if prior is None or current_value is None:
        return ""
    prior_day, prior_display = prior
    prior_value = _parse_compact_usd(prior_display)
    if prior_value is None or prior_value <= 0:
        return ""
    change = _signed_pct((current_value - prior_value) / prior_value * 100.0)
    when = _when_phrase(prior_day, ctx.current_week)
    same_level = (
        move is not None
        and _parse_compact_usd(move.value_display) is not None
        and abs((_parse_compact_usd(move.value_display) or 0) - current_value) < 1.0
    )
    reading = f"the {prior_day.day} {prior_day.strftime('%b')} reading of {prior_display}"
    if same_level:
        if change == "flat":
            return f"That is unchanged from {reading}"
        return f"That is {change} from {reading}"
    if change == "flat":
        return f"{metric} is unchanged from {prior_display} {when}"
    return f"{metric} went from {prior_display} to {current} ({change}) {when}"


def _percent_points(raw: object, *, fraction: bool) -> float | None:
    if raw is None:
        return None
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return None
    if fraction:
        number *= 100.0
    return number


def _delta_text(points: float, *, share: bool) -> str:
    if share:
        return f"{points:+.1f} pp over 30D"
    return f"{points:+.1f}% over 30D"


def _companion_clause(section_id: str, ctx: WeekContext) -> str:
    if section_id == "crypto":
        return _crypto_companion(ctx.crypto)
    if section_id == "etp":
        return _etp_companion(ctx.etp)
    if section_id == "tmmf":
        return _share_companion(ctx.explore, "tokenized_mmf", "network share")
    if section_id == "stablecoins":
        return _largest_kpi_companion(
            ctx.explore,
            "stablecoins",
            skip=("market cap",),
        )
    if section_id == "rwa":
        return _largest_kpi_companion(
            ctx.explore,
            "rwa_global",
            skip=("distributed asset", "stablecoin"),
        )
    return ""


def _share_companion(explore: dict[str, dict[str, Any]], section_id: str, label_match: str) -> str:
    sec = explore.get(section_id) or {}
    needle = label_match.lower()
    for kpi in sec.get("kpis") or []:
        if needle not in str(kpi.get("label") or "").lower():
            continue
        points = _percent_points(kpi.get("delta_30d_pct"), fraction=True)
        display = str(kpi.get("value_display") or "").strip()
        if points is None or not display:
            return ""
        return f"{kpi.get('label')} is {display}, {_delta_text(points, share=True)}"
    return ""


def _largest_kpi_companion(
    explore: dict[str, dict[str, Any]],
    section_id: str,
    *,
    skip: tuple[str, ...],
) -> str:
    sec = explore.get(section_id) or {}
    best: tuple[float, str] | None = None
    for kpi in sec.get("kpis") or []:
        label = str(kpi.get("label") or "")
        lowered = label.lower()
        if any(part in lowered for part in skip):
            continue
        share = "share" in lowered
        points = _percent_points(kpi.get("delta_30d_pct"), fraction=True)
        display = str(kpi.get("value_display") or "").strip()
        if points is None or not display:
            continue
        if best is None or abs(points) > best[0]:
            verb = "are" if label.lower().endswith("s") else "is"
            best = (abs(points), f"{label} {verb} {display}, {_delta_text(points, share=share)}")
    return best[1] if best else ""


def _crypto_companion(crypto: dict[str, Any] | None) -> str:
    crypto = crypto or {}
    btc = crypto.get("btc") if isinstance(crypto.get("btc"), dict) else {}
    eth = crypto.get("eth") if isinstance(crypto.get("eth"), dict) else {}
    btc_pct = _percent_points((btc.get("delta") or {}).get("pct"), fraction=False)
    eth_pct = _percent_points((eth.get("delta") or {}).get("pct"), fraction=False)
    btc_display = str(btc.get("value_display") or "").strip()
    eth_display = str(eth.get("value_display") or "").strip()
    if btc_display and eth_display and btc_pct is not None and eth_pct is not None:
        return (
            f"BTC is {btc_display} ({btc_pct:+.1f}% over 30D) and "
            f"ETH is {eth_display} ({eth_pct:+.1f}% over 30D)"
        )
    return ""


def _etp_companion(etp: dict[str, Any] | None) -> str:
    etp = etp or {}
    parts: list[str] = []
    for key, name in (("ibit", "IBIT"), ("etha", "ETHA")):
        row = etp.get(key) if isinstance(etp.get(key), dict) else {}
        display = str(row.get("aum_display") or "").strip()
        points = _percent_points((row.get("delta") or {}).get("pct"), fraction=False)
        if display and points is not None:
            parts.append(f"{name} is {display} ({points:+.1f}% over 30D)")
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return parts[0] if parts else ""


def _dynamic_tail(section_id: str, ctx: WeekContext | None, move: SectionKpiMove | None = None) -> str:
    if ctx is None:
        return ""
    parts = [
        part.strip().rstrip(".")
        for part in (_since_clause(section_id, ctx, move), _companion_clause(section_id, ctx))
        if part and part.strip()
    ]
    if not parts:
        return ""
    return ". ".join(parts) + "."


def _join_read(opening: str, tail: str) -> str:
    opening = opening.strip().rstrip(".")
    tail = tail.strip()
    if not tail:
        return opening + "."
    return f"{opening}. {tail if tail.endswith('.') else tail + '.'}"


def _largest_prior_section(ctx: WeekContext) -> str | None:
    best_section = None
    best_abs = -1.0
    for section_id in _PRIOR_KEY:
        prior = ctx.prior.get(section_id)
        current = _parse_compact_usd(ctx.levels.get(section_id) or "")
        if prior is None or current is None:
            continue
        prior_value = _parse_compact_usd(prior[1])
        if prior_value is None or prior_value <= 0:
            continue
        change = abs((current - prior_value) / prior_value * 100.0)
        if change > best_abs:
            best_abs = change
            best_section = section_id
    return best_section


def headline_so_what(pick: Any, *, context: WeekContext | None = None) -> str:
    """Story pointer plus the week-to-week move for that story's market."""
    ctx = context if context is not None else load_week_context_from_snapshot()
    family = str(getattr(pick, "theme_family", "") or "")
    section_id = _FAMILY_SECTION.get(family) or _largest_prior_section(ctx)
    title = _headline_hook(str(getattr(pick, "title", "") or ""), max_len=72)
    words = title.split()
    pointer = " ".join(words[:8])
    if len(words) > 8:
        pointer += "…"
    tail = _dynamic_tail(section_id, ctx) if section_id else ""
    if not pointer:
        return tail
    if not tail:
        return pointer
    return f"{pointer}: {tail}"


def load_cooldown() -> dict[str, Any]:
    if not COOLDOWN_PATH.is_file():
        return {"leads_by_section": {}, "history": []}
    try:
        data = json.loads(COOLDOWN_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"leads_by_section": {}, "history": []}
    if not isinstance(data, dict):
        return {"leads_by_section": {}, "history": []}
    data.setdefault("leads_by_section", {})
    data.setdefault("history", [])
    return data


def recent_cooled_leads(section_id: str, *, weeks: int = 2) -> set[str]:
    state = load_cooldown()
    cooled: set[str] = set()
    by_sec = state.get("leads_by_section") or {}
    for key in by_sec.get(section_id) or []:
        if isinstance(key, str) and key:
            cooled.add(key)
    history = state.get("history") or []
    for row in history[-weeks:]:
        if not isinstance(row, dict):
            continue
        sec_map = row.get("leads_by_section") or {}
        for key in sec_map.get(section_id) or []:
            if isinstance(key, str) and key:
                cooled.add(key)
    return cooled


def record_shipped_leads(
    *,
    week_label: str,
    leads_by_section: dict[str, list[str]],
) -> None:
    """Persist normalized leads used in this build (for next week's cooldown)."""
    COOLDOWN_PATH.parent.mkdir(parents=True, exist_ok=True)
    prior = load_cooldown()
    snapshot = {
        "week_label": week_label,
        "leads_by_section": {
            sid: [normalize_lead(x) for x in leads if str(x).strip()]
            for sid, leads in leads_by_section.items()
        },
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    history = list(prior.get("history") or [])
    history.append(snapshot)
    history = history[-6:]
    payload = {
        "week_label": week_label,
        "leads_by_section": snapshot["leads_by_section"],
        "history": history,
        "updated_at": snapshot["recorded_at"],
    }
    COOLDOWN_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def explore_kpi_move(
    explore: dict[str, dict[str, Any]],
    section_id: str,
    *,
    label_match: str,
) -> SectionKpiMove | None:
    sec = explore.get(section_id) or {}
    kpis = sec.get("kpis") or []
    needle = label_match.lower()
    picked = None
    for kpi in kpis:
        if needle in str(kpi.get("label") or "").lower():
            picked = kpi
            break
    if picked is None and kpis:
        picked = kpis[0]
    if not picked:
        return None
    delta = _pct_value(picked.get("delta_30d_pct"), unit="fraction")
    return SectionKpiMove(
        label=str(picked.get("label") or "KPI"),
        value_display=str(picked.get("value_display") or "—"),
        delta_pct=delta,
        delta_display=_fmt_pct(delta),
    )


def _wow_opening(section_id: str, move: SectionKpiMove) -> str:
    """Level and direction only. The week-to-week comparison is appended separately."""
    up = (move.delta_pct or 0) >= 0
    level = move.value_display
    metric = (move.label or "metric").lower()
    mag = f"{abs(move.delta_pct or 0):.1f}%"
    higher = "higher" if up else "lower"

    if section_id == "tmmf":
        return f"With distributed value at {level} ({mag} {higher} over 30D)"
    if section_id == "stablecoins":
        if "market cap" in metric or "cap" in metric:
            return f"Stablecoin market cap at {level} ({mag} {higher} over 30D)"
        verb = "moving up to" if up else "softening to"
        return f"{move.label} {verb} {level} ({mag} over 30D)"
    if section_id == "rwa":
        return f"On-chain RWA distributed value at {level} ({mag} {higher} over 30D)"
    if section_id == "etp":
        if "flow" in metric:
            level_sign = _signed_level(level)
            if level_sign > 0 and not up:
                return (
                    f"Listed-product flows at {level} ({mag} vs prior 30D) are still a net inflow, "
                    "smaller than the prior 30 days"
                )
            if level_sign < 0 and up:
                return (
                    f"Listed-product flows at {level} ({mag} vs prior 30D) are still a net outflow, "
                    "narrower than the prior 30 days"
                )
            if level_sign > 0:
                return (
                    f"Listed-product flows at {level} ({mag} vs prior 30D) are a larger net inflow "
                    "than the prior 30 days"
                )
            return f"Listed-product flows at {level} ({mag} vs prior 30D) are a net outflow"
        return f"Aggregate ETP AUM at {level} ({mag} {higher} over 30D)"
    if section_id == "crypto":
        return f"Total crypto market cap at {level} ({mag} {higher} over 30D)"
    return f"{move.label} at {level} is {higher} by {mag} over 30D"


def _wow_market_read(
    section_id: str,
    move: SectionKpiMove,
    context: WeekContext | None = None,
) -> str:
    return _join_read(_wow_opening(section_id, move), _dynamic_tail(section_id, context, move))


def _flat_market_read(
    section_id: str,
    move: SectionKpiMove | None,
    context: WeekContext | None = None,
) -> str:
    if move and move.delta_pct is not None:
        level = move.value_display
        delta = move.delta_display
        metric = move.label
    else:
        level, delta, metric = "—", "—", "KPIs"
    opening = f"{metric} near {level} ({delta} 30D)"
    return _join_read(opening, _dynamic_tail(section_id, context, move))


def _wow_takeaway(
    move: SectionKpiMove,
    *,
    lane: str,
    section_id: str,
    context: WeekContext | None = None,
) -> WeeklyTakeaway | None:
    if move.delta_pct is None:
        return None
    if abs(move.delta_pct) < _WOW_THRESHOLD:
        return None
    verb = _move_verb(move.delta_pct)
    if (
        section_id == "etp"
        and "flow" in (move.label or "").lower()
        and _signed_level(move.value_display) > 0
        and move.delta_pct < 0
    ):
        verb = "slowed"
    mag = f"{abs(move.delta_pct):.1f}%"
    window = (
        "vs prior 30D"
        if section_id == "etp" and "flow" in (move.label or "").lower()
        else "over 30D"
    )
    lead = f"{lane} {move.label.lower()} {verb} {mag} {window}"
    body = _wow_market_read(section_id, move, context)
    return WeeklyTakeaway(
        lead=lead.rstrip(".!?…:"),
        body=body,
        kind="wow",
        lead_key=normalize_lead(lead),
    )


def _flat_takeaway(
    move: SectionKpiMove | None,
    *,
    lane: str,
    section_id: str,
    context: WeekContext | None = None,
) -> WeeklyTakeaway:
    lead = f"{lane} printed metrics were roughly flat this week"
    if move is None or move.delta_pct is None:
        lead = f"{lane} printed metrics did not show a clear weekly move"
    body = _flat_market_read(section_id, move, context)
    return WeeklyTakeaway(
        lead=lead.rstrip(".!?…:"),
        body=body,
        kind="flat",
        lead_key=normalize_lead(lead),
    )


def _headline_hook(title: str, *, max_len: int = 72) -> str:
    t = re.sub(r"\s+", " ", (title or "").strip())
    t = re.sub(r"^(?:breaking:|update:|report:|analysis:)\s*", "", t, flags=re.I)
    if len(t) <= max_len:
        return t
    cut = t[: max_len - 1].rsplit(" ", 1)[0]
    return (cut or t[: max_len - 1]) + "…"


def _news_so_what(section_id: str) -> str:
    return {
        "tmmf": (
            "Institutional adoption of on-chain cash rails still matters more than any "
            "short-term yield trade in tokenized money markets."
        ),
        "stablecoins": (
            "Payment rails, reserve quality, and how easily dollars move on-chain remain "
            "the main stablecoin drivers for broader crypto liquidity."
        ),
        "rwa": (
            "TradFi balance sheets are still the open variable for tokenized treasuries, "
            "funds, and credit wrappers."
        ),
        "etp": (
            "Traditional channels remain the main path for institutional crypto beta when "
            "listed products stay open and liquid."
        ),
        "crypto": (
            "Liquidity and institutional plumbing still set risk appetite more than any "
            "single venue or product headline."
        ),
    }.get(
        section_id,
        "Plumbing and policy still lead prices and flows until a clearer regime shift shows up "
        "in the printed market.",
    )


def _article_theme_flags(text: str) -> set[str]:
    t = (text or "").lower()
    flags: set[str] = set()
    if re.search(r"\b(launch|launches|launched|debut|unveil|rolls? out|announc)\b", t):
        flags.add("launch")
    if re.search(r"\b(partner|ties up|teams up|integration|distribution deal)\b", t):
        flags.add("partnership")
    if re.search(r"\b(reserve|banking|bank rail|payments?|remittance|card network)\b", t):
        flags.add("payments")
    if re.search(r"\b(etf|etp|inflow|outflow|filing|sec approval|spot bitcoin|spot ether)\b", t):
        flags.add("listed_access")
    if re.search(r"\b(outflow|redemption|selloff|sell-off|net selling|withdrawals?)\b", t):
        flags.add("flow_out")
    if re.search(r"\b(inflow|creation|net buying|subscriptions?)\b", t):
        flags.add("flow_in")
    if re.search(r"\b(regulat|sec\b|cftc|legislation|policy|oversight|compliance)\b", t):
        flags.add("policy")
    if re.search(r"\b(tokeniz|rwa|treasury|treasuries|money market|mmf|buidl)\b", t):
        flags.add("tokenization")
    if re.search(r"\b(aum|assets under management|raised \$|funding|series [a-c])\b", t):
        flags.add("capital")
    if re.search(r"\b(hack|exploit|breach|outage|lawsuit|probe|investigation|downgrade)\b", t):
        flags.add("risk")
    return flags


def _interpret_news_for_market(section_id: str, title: str, blurb: str) -> str:
    """Direct market-impact copy for readers (no meta framing or title paraphrase)."""
    flags = _article_theme_flags(f"{title} {blurb}")
    lane = {
        "tmmf": "tokenized money-market",
        "stablecoins": "stablecoin",
        "rwa": "tokenized RWA",
        "etp": "listed crypto ETP",
        "crypto": "broader crypto",
    }.get(section_id, "digital-asset")

    # Bias by section so a payments-flavored article in the ETP lane still reads as ETP.
    if section_id == "etp":
        if "risk" in flags:
            return (
                "Stress around listed crypto products usually weighs on risk appetite and can "
                "slow creations until spot-liquidity confidence returns."
            )
        etf_story = bool(
            re.search(r"\b(etf|etps?|spot bitcoin|spot ether)\b", f"{title} {blurb}", re.I)
        )
        if "flow_out" in flags and "flow_in" not in flags and etf_story:
            return (
                "Risk is leaving the regulated channel through listed outflows, which can "
                "soften spot liquidity even while longer-term AUM stays large."
            )
        if "flow_in" in flags:
            return (
                "Traditional channels are still absorbing crypto beta through listed inflows, "
                "supporting primary-market creations and secondary liquidity in the majors."
            )
        if "policy" in flags:
            return (
                "Clearer oversight tends to open new listings and advisor adoption; ambiguity "
                "keeps more allocators on the sidelines."
            )
        if "listed_access" in flags or "launch" in flags or "capital" in flags:
            return (
                "More capital can still reach crypto beta through U.S. listed wrappers when "
                "product pipelines and traditional-channel access keep expanding."
            )
        return (
            "Listed wrappers remain the preferred on-ramp for many institutions versus spot "
            "and offshore venues when access stays clean."
        )
    if section_id == "tmmf":
        if "risk" in flags:
            return (
                "Collateral and counterparty caution rises in tokenized cash markets: institutions "
                "may keep using TMMFs, but onboarding and size checks get tighter."
            )
        if "launch" in flags or "partnership" in flags or "tokenization" in flags:
            return (
                "New wrappers and distribution rails expand who can hold on-chain cash, even "
                "before aggregate TMMF AUM jumps again."
            )
        return (
            "Institutional cash keeps leaning on TMMFs as operational liquidity infrastructure "
            "rather than a niche yield sleeve."
        )

    if "risk" in flags:
        return (
            f"Due diligence usually tightens across {lane} markets after this kind of setback, "
            "and new allocations can slow until counterparties look cleaner again."
        )
    if "policy" in flags:
        return (
            f"Clearer rules can unlock balance-sheet adoption in {lane} markets, while ambiguity "
            "keeps more institutions on the sidelines."
        )
    if "flow_out" in flags and "flow_in" not in flags:
        return (
            f"Money leaving listed or primary {lane} channels usually marks de-risking and can "
            "tighten secondary liquidity until creations resume."
        )
    if "listed_access" in flags:
        return (
            "Risk capital still prefers crypto beta through listed wrappers when traditional "
            "channels stay open, not only through spot or offshore venues."
        )
    if "payments" in flags:
        return (
            f"If payment and banking rails keep expanding, {lane} demand becomes more structural "
            "and less dependent on speculative risk cycles."
        )
    if "launch" in flags or "partnership" in flags:
        return (
            f"More wrappers and counterparties widen who can hold {lane} exposure, even before "
            "aggregate AUM jumps."
        )
    if "capital" in flags:
        return (
            f"Build-out capital is still funding {lane} infrastructure, not only trading beta."
        )
    if "tokenization" in flags:
        return (
            "Tokenized cash and real-world assets keep pulling TradFi balance sheets into "
            "on-chain plumbing alongside crypto-native cycles."
        )
    return _news_so_what(section_id)


def _first_sentence(text: str, *, limit: int = 220) -> str:
    cleaned = _strip_html_text(text)
    if len(cleaned) < 40:
        return ""
    sentence = _SENTENCE_SPLIT_RE.split(cleaned, maxsplit=1)[0].strip()
    if len(sentence) > limit:
        sentence = sentence[: limit - 1].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
    return sentence


def _compose_news_body(
    section_id: str,
    article: dict[str, Any],
    context: WeekContext | None = None,
) -> str:
    """Article's own first sentence, then this week's change versus the prior reading."""
    summary = _first_sentence(str(article.get("summary") or ""))
    tail = _dynamic_tail(section_id, context)
    parts = [part for part in (summary, tail) if part]
    if parts:
        return " ".join(parts)
    title = str(article.get("title") or "").strip()
    return title


_META_DESC_RE = re.compile(
    r'<meta[^>]+(?:name|property)=["\'](?:description|og:description|twitter:description)["\'][^>]+'
    r'content=["\']([^"\']+)["\']',
    re.I,
)
_META_DESC_RE_ALT = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\'](?:description|og:description)["\']',
    re.I,
)
_P_TAG_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_COMPRESS_RE = re.compile(r"\s+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _strip_html_text(html: str) -> str:
    from html import unescape

    text = _TAG_RE.sub(" ", html or "")
    text = unescape(text)
    return _WS_COMPRESS_RE.sub(" ", text).strip()


def _fetch_article_blurb(url: str, *, timeout: float = 6.0) -> str:
    """Best-effort page fetch for a short article blurb (meta / lead paragraphs)."""
    link = (url or "").strip()
    if not link.startswith("http"):
        return ""
    try:
        from urllib.request import Request, urlopen

        req = Request(
            link,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; DigitalAssetDashboard/1.0; "
                    "+https://github.com/jtaits13/DigitalAssetDashboard)"
                ),
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read(180_000)
        html = raw.decode("utf-8", errors="replace")
    except Exception:
        return ""

    for rx in (_META_DESC_RE, _META_DESC_RE_ALT):
        m = rx.search(html)
        if m:
            desc = _strip_html_text(m.group(1))
            if len(desc) >= 40:
                return desc[:600]

    paras: list[str] = []
    for m in _P_TAG_RE.finditer(html):
        p = _strip_html_text(m.group(1))
        if len(p) < 60:
            continue
        if re.search(r"cookie|subscribe|sign up|advertisement|newsletter", p, re.I):
            continue
        paras.append(p)
        if len(paras) >= 3:
            break
    return " ".join(paras)[:800]


def _tmmf_no_launch_takeaway(context: WeekContext | None = None) -> WeeklyTakeaway:
    # Renderer appends the terminal period; keep leads unpunctuated like WoW/flat.
    lead = "No TMMF fund launches this week"
    tail = _dynamic_tail("tmmf", context)
    body = "No new fund launch was in this week's coverage."
    if tail:
        body = f"{body} {tail}"
    return WeeklyTakeaway(
        lead=lead,
        body=body,
        kind="launch_none",
        article=None,
        lead_key=normalize_lead(lead),
    )


def _tmmf_fund_launch_takeaway(
    articles: list[dict[str, Any]] | None,
    *,
    cooled: set[str],
    used_links: set[str],
    context: WeekContext | None = None,
) -> WeeklyTakeaway:
    """Second TMMF bullet: fund launch this week (notable preferred), or an explicit none."""
    try:
        from key_observations.week_headlines import (
            pick_tmmf_fund_launch,
            tmmf_launch_takeaway_copy,
        )
    except Exception:
        return _tmmf_no_launch_takeaway(context)

    pool = [
        art
        for art in (articles or [])
        if str(art.get("link") or "").strip() not in used_links
    ]
    # Broader than headline gates: any TMMF launch qualifies; major issuers rank first.
    launch = pick_tmmf_fund_launch(pool, max_age_days=7.0)
    if not launch:
        return _tmmf_no_launch_takeaway(context)

    lead, body = tmmf_launch_takeaway_copy(launch)
    lead = lead.strip().rstrip(".!?…:")
    tail = _dynamic_tail("tmmf", context)
    if tail and tail not in body:
        body = f"{body.rstrip()} {tail}"
    key = normalize_lead(lead)
    if key in cooled:
        return _tmmf_no_launch_takeaway(context)

    return WeeklyTakeaway(
        lead=lead,
        body=body,
        kind="launch",
        article={
            "title": launch.title,
            "link": launch.link,
            "source": launch.source,
            "summary": launch.summary,
        },
        lead_key=key,
    )


def _news_takeaway(
    section_id: str,
    article: dict[str, Any],
    *,
    cooled: set[str],
    context: WeekContext | None = None,
) -> WeeklyTakeaway | None:
    title = str(article.get("title") or "").strip()
    if not title:
        return None
    blob = f"{title} {article.get('summary') or ''}"
    if section_id == "rwa" and not re.search(
        r"tokeniz|\brwa\b|real[-\s]?world|treasur|private credit|securitiz|on[-\s]?chain|bond",
        blob,
        re.I,
    ):
        return None
    if section_id == "tmmf" and not re.search(
        r"money market|tmmf|buidl|benji|tokenized (?:fund|cash)|mmf\b",
        blob,
        re.I,
    ):
        return None
    lead = _headline_hook(title).rstrip(".!?…:")
    key = normalize_lead(lead)
    if key in cooled:
        return None
    body = _compose_news_body(section_id, article, context)
    return WeeklyTakeaway(
        lead=lead,
        body=body,
        kind="news",
        article=article,
        lead_key=key,
    )


def _pick_section_article(
    section_id: str,
    articles: list[dict[str, Any]] | None,
    week_headlines: list[Any],
    *,
    used_links: set[str],
    topic_keys: tuple[str, ...] = (),
    force_matcher: bool = False,
) -> dict[str, Any] | None:
    families = SECTION_NEWS_FAMILIES.get(section_id, ())
    try:
        from key_observations.week_headlines import (
            match_article_for_takeaway,
            pick_brief_family_article,
        )
    except Exception:
        match_article_for_takeaway = None  # type: ignore[assignment]
        pick_brief_family_article = None  # type: ignore[assignment]

    if not force_matcher and pick_brief_family_article:
        for family in families:
            art = pick_brief_family_article(
                articles, family, exclude_links=used_links, max_age_days=7.0
            )
            if art:
                return art

    if not force_matcher:
        for pick in week_headlines:
            family = str(getattr(pick, "theme_family", "") or "")
            if family not in families:
                continue
            link = str(getattr(pick, "link", "") or "").strip()
            if link and link in used_links:
                continue
            title = str(getattr(pick, "title", "") or "").strip()
            if not title:
                continue
            # Prefer the richer RSS row when available (summary helps article takeaways).
            for row in articles or []:
                if str(row.get("link") or "").strip() == link and str(row.get("title") or "").strip():
                    return row
            return {
                "title": title,
                "link": link,
                "source": str(getattr(pick, "source", "") or "").strip(),
                "summary": "",
            }

    if match_article_for_takeaway and topic_keys:
        probe = {
            "tmmf": "tokenized money market fund settlement cash rails BUIDL",
            "stablecoins": "stablecoin reserves payments bank issuer USDC",
            "rwa": "RWA tokenization real-world assets treasuries on-chain",
            "etp": "bitcoin ether ETF ETP flows filing AUM",
            "crypto": "bitcoin ethereum crypto market structure dominance",
        }.get(section_id, section_id)
        art = match_article_for_takeaway(
            probe,
            bullet_lead=probe,
            bullet_html=probe,
            topic_keys=topic_keys,
            articles=articles,
            used_links=used_links,
            strict=True,
        )
        if art:
            return art
    return None


def select_weekly_section_takeaways(
    section_id: str,
    *,
    explore: dict[str, dict[str, Any]],
    etp: dict[str, Any] | None = None,
    crypto: dict[str, Any] | None = None,
    articles: list[dict[str, Any]] | None = None,
    week_headlines: list[Any] | None = None,
    used_links: set[str] | None = None,
    max_items: int = 2,
    skip_fund_launch_slot: bool = False,
    topic_keys: tuple[str, ...] = (),
) -> list[WeeklyTakeaway]:
    """
    Build up to ``max_items`` weekly takeaways for one newsletter section.

    Default stack when space allows:
      1) data takeaway (meaningful WoW, else flat note)
      2) TMMF: fund launch (major issuers preferred), or an explicit none; other sections: news + article
      3) optional extra section news when max_items > 2

    Structural page KO leads are not used. Cooled news/launch leads are skipped when possible.
    """
    # TMMF owns its launch bullet inside this selector; do not reserve an outer slot for it.
    skip_outer_launch = bool(skip_fund_launch_slot) and section_id != "tmmf"
    slots = max(0, max_items - (1 if skip_outer_launch else 0))
    if slots <= 0:
        return []

    links = used_links if used_links is not None else set()
    cooled = recent_cooled_leads(section_id)
    headlines = list(week_headlines or [])
    out: list[WeeklyTakeaway] = []
    context = make_week_context(explore, etp, crypto)

    move = _section_kpi_move(section_id, explore, etp=etp, crypto=crypto)
    wow = (
        _wow_takeaway(move, lane=_lane_label(section_id), section_id=section_id, context=context)
        if move
        else None
    )
    # Keep current KPI moves even if a similar lead shipped last week; cooldown is for news.
    data_tw = wow or _flat_takeaway(
        move, lane=_lane_label(section_id), section_id=section_id, context=context
    )

    def _pick_news(*, extra_cooled: set[str]) -> WeeklyTakeaway | None:
        for _ in range(4):
            art = _pick_section_article(
                section_id,
                articles,
                headlines,
                used_links=links,
                topic_keys=topic_keys,
            )
            if not art:
                break
            cand = _news_takeaway(section_id, art, cooled=extra_cooled, context=context)
            link = str(art.get("link") or "").strip()
            if link:
                links.add(link)
            if cand:
                return cand
        art = _pick_section_article(
            section_id,
            articles,
            headlines,
            used_links=links,
            topic_keys=topic_keys,
            force_matcher=True,
        )
        if not art:
            return None
        cand = _news_takeaway(section_id, art, cooled=extra_cooled, context=context)
        link = str(art.get("link") or "").strip()
        if link:
            links.add(link)
        return cand

    if section_id == "tmmf":
        out.append(data_tw)
        if slots >= 2:
            launch_tw = _tmmf_fund_launch_takeaway(
                articles,
                cooled=cooled | {data_tw.lead_key},
                used_links=links,
                context=context,
            )
            link = str((launch_tw.article or {}).get("link") or "").strip()
            if link:
                links.add(link)
            out.append(launch_tw)
        if slots >= 3:
            news_tw = _pick_news(extra_cooled=cooled | {t.lead_key for t in out})
            if news_tw:
                out.append(news_tw)
        return out[:slots]

    news_tw = _pick_news(extra_cooled=cooled | {data_tw.lead_key})

    if slots == 1:
        # With only one slot (outer fund-launch already used the other), prefer news+article.
        return [news_tw or data_tw]

    out.append(data_tw)
    if news_tw:
        out.append(news_tw)
    return out[:slots]


def _lane_label(section_id: str) -> str:
    return {
        "tmmf": "TMMF",
        "stablecoins": "Stablecoin",
        "rwa": "RWA",
        "etp": "U.S. ETP",
        "crypto": "Crypto",
    }.get(section_id, section_id.upper())


def _section_kpi_move(
    section_id: str,
    explore: dict[str, dict[str, Any]],
    *,
    etp: dict[str, Any] | None,
    crypto: dict[str, Any] | None,
) -> SectionKpiMove | None:
    if section_id == "tmmf":
        return explore_kpi_move(explore, "tokenized_mmf", label_match="distributed")
    if section_id == "stablecoins":
        return explore_kpi_move(explore, "stablecoins", label_match="market cap")
    if section_id == "rwa":
        # Match the newsletter section's all-RWA (ex-stablecoin) KPI strip.
        move = explore_kpi_move(explore, "rwa_global", label_match="distributed asset")
        if move:
            return move
        move = explore_kpi_move(explore, "treasuries", label_match="distributed")
        if move:
            return move
        return explore_kpi_move(explore, "tokenized_stocks", label_match="distributed")
    if section_id == "etp" and etp:
        # Prefer 30D net flow signal when present; else aggregate AUM %.
        flow = _pct_value(etp.get("net_flow_1m_pct"), unit="percent")
        if flow is not None and abs(flow) >= _WOW_THRESHOLD:
            return SectionKpiMove(
                label="30D net flow",
                value_display=str(etp.get("net_flow_1m_display") or "—"),
                delta_pct=flow,
                delta_display=_fmt_pct(flow),
            )
        agg = _pct_value(etp.get("aggregate_pct"), unit="percent")
        return SectionKpiMove(
            label="Aggregate AUM",
            value_display=str(etp.get("total_aum_display") or "—"),
            delta_pct=agg,
            delta_display=_fmt_pct(agg),
        )
    if section_id == "crypto" and crypto:
        primary = crypto.get("primary") or {}
        delta = _pct_value((primary.get("delta") or {}).get("pct"), unit="percent")
        return SectionKpiMove(
            label=str(primary.get("label") or "Total market cap"),
            value_display=str(primary.get("value_display") or "—"),
            delta_pct=delta,
            delta_display=_fmt_pct(delta),
        )
    return None
