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
from datetime import datetime, timezone
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
    kind: str  # wow | news | flat | soft
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


def _pct_value(raw: Any) -> float | None:
    """Return percentage points (e.g. 2.7 for +2.7%), matching newsletter `_fmt_pct`."""
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
    # Explore KPIs often store fractions (0.027 -> 2.7pp).
    if abs(n) <= 1.5 and n != 0:
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
    delta = _pct_value(picked.get("delta_30d_pct"))
    return SectionKpiMove(
        label=str(picked.get("label") or "KPI"),
        value_display=str(picked.get("value_display") or "—"),
        delta_pct=delta,
        delta_display=_fmt_pct(delta),
    )


def _wow_takeaway(move: SectionKpiMove, *, lane: str) -> WeeklyTakeaway | None:
    if move.delta_pct is None:
        return None
    if abs(move.delta_pct) < _WOW_THRESHOLD:
        return None
    verb = _move_verb(move.delta_pct)
    mag = f"{abs(move.delta_pct):.1f}%"
    lead = f"{lane} {move.label.lower()} {verb} {mag} over 30D"
    body = (
        f"Printed dashboard level: {move.value_display}. "
        "This is the clearest near-term move in the lane strip - treat it as the week's "
        "data signal unless a launch or policy story overrides it."
    )
    return WeeklyTakeaway(
        lead=lead.rstrip(".!?…:"),
        body=body,
        kind="wow",
        lead_key=normalize_lead(lead),
    )


def _flat_takeaway(move: SectionKpiMove | None, *, lane: str) -> WeeklyTakeaway:
    if move and move.delta_pct is not None:
        lead = f"{lane} printed metrics were roughly flat this week"
        body = (
            f"{move.label} held near {move.value_display} ({move.delta_display} 30D). "
            "With no material WoW move, the section takeaway leans on news rather than "
            "repeating a structural market narrative."
        )
    else:
        lead = f"{lane} printed metrics did not show a clear weekly move"
        body = (
            "KPI deltas were missing or soft in this export, so this lane's takeaway "
            "prioritizes recent coverage over standing page observations."
        )
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
            "Watch whether the story reinforces institutional cash rails, new fund launches, "
            "or distribution partnerships versus a change in aggregate TMMF AUM."
        ),
        "stablecoins": (
            "Ask whether reserves, bank rails, or issuer policy shifted—or if the print is "
            "mostly narrative without a market-cap move."
        ),
        "rwa": (
            "Map the headline to tokenization plumbing: issuance, distribution, collateral, "
            "or regulation—not just a one-off product mention."
        ),
        "etp": (
            "Compare the news with listed-access signals—flows, filings, or product pipeline—"
            "rather than price alone."
        ),
        "crypto": (
            "Use the story as market context for the KPI strip; separate structural plumbing "
            "news from short-horizon price chatter."
        ),
    }.get(
        section_id,
        "Read the story against this section's KPIs before treating it as a structural shift.",
    )


def _pick_section_article(
    section_id: str,
    articles: list[dict[str, Any]] | None,
    week_headlines: list[Any],
    *,
    used_links: set[str],
) -> dict[str, Any] | None:
    families = SECTION_NEWS_FAMILIES.get(section_id, ())
    try:
        from key_observations.week_headlines import pick_brief_family_article
    except Exception:
        pick_brief_family_article = None  # type: ignore[assignment]

    # Prefer the stricter brief-family picker first (especially TMMF).
    if pick_brief_family_article:
        for family in families:
            art = pick_brief_family_article(
                articles, family, exclude_links=used_links, max_age_days=7.0
            )
            if art:
                return art

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
        return {
            "title": title,
            "link": link,
            "source": str(getattr(pick, "source", "") or "").strip(),
            "summary": "",
        }
    return None


def _news_takeaway(
    section_id: str,
    article: dict[str, Any],
    *,
    cooled: set[str],
) -> WeeklyTakeaway | None:
    title = str(article.get("title") or "").strip()
    if not title:
        return None
    blob = f"{title} {article.get('summary') or ''}"
    if section_id == "rwa" and not re.search(
        r"tokeniz|\brwa\b|real[-\s]?world|treasur|private credit|securitiz|on[-\s]?chain",
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
    src = str(article.get("source") or "").strip()
    src_bit = f" ({src})" if src else ""
    body = f"This week's on-topic coverage centers on that story{src_bit}. {_news_so_what(section_id)}"
    return WeeklyTakeaway(
        lead=lead,
        body=body,
        kind="news",
        article=article,
        lead_key=key,
    )


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
) -> list[WeeklyTakeaway]:
    """
    Build up to ``max_items`` weekly takeaways for one newsletter section.

    Priority: meaningful WoW → news → flat-week note. Structural page KO leads
    are not used. Cooled leads from recent weeks are skipped when possible.
    """
    slots = max(0, max_items - (1 if skip_fund_launch_slot else 0))
    if slots <= 0:
        return []

    links = used_links if used_links is not None else set()
    cooled = recent_cooled_leads(section_id)
    headlines = list(week_headlines or [])
    out: list[WeeklyTakeaway] = []

    move = _section_kpi_move(section_id, explore, etp=etp, crypto=crypto)
    wow = _wow_takeaway(move, lane=_lane_label(section_id)) if move else None
    if wow and wow.lead_key not in cooled:
        out.append(wow)

    art = _pick_section_article(section_id, articles, headlines, used_links=links)
    if art and len(out) < slots:
        news = _news_takeaway(section_id, art, cooled=cooled | {t.lead_key for t in out})
        if news:
            link = str(art.get("link") or "").strip()
            if link:
                links.add(link)
            out.append(news)

    # If still empty or news missing under flat conditions, add an explicit flat note
    # rather than recycling page KO templates.
    if len(out) < slots:
        # Prefer news second if wow already taken but news missed cooldown.
        if not any(t.kind == "news" for t in out):
            art2 = _pick_section_article(section_id, articles, headlines, used_links=links)
            if art2:
                news2 = _news_takeaway(
                    section_id, art2, cooled=cooled | {t.lead_key for t in out}
                )
                if news2:
                    link = str(art2.get("link") or "").strip()
                    if link:
                        links.add(link)
                    out.append(news2)
        if len(out) < slots and not any(t.kind == "wow" for t in out):
            flat = _flat_takeaway(move, lane=_lane_label(section_id))
            if flat.lead_key not in cooled and flat.lead_key not in {t.lead_key for t in out}:
                out.append(flat)
            elif flat.lead_key not in {t.lead_key for t in out}:
                # Cooldown exhausted: allow flat once as last resort.
                out.append(flat)

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
        # Prefer treasuries distributed; fall back to first rwa explore strip if needed.
        move = explore_kpi_move(explore, "treasuries", label_match="distributed")
        if move:
            return move
        return explore_kpi_move(explore, "tokenized_stocks", label_match="distributed")
    if section_id == "etp" and etp:
        # Prefer 30D net flow signal when present; else aggregate AUM %.
        flow = _pct_value(etp.get("net_flow_1m_pct"))
        if flow is not None and abs(flow) >= _WOW_THRESHOLD:
            return SectionKpiMove(
                label="30D net flow",
                value_display=str(etp.get("net_flow_1m_display") or "—"),
                delta_pct=flow,
                delta_display=_fmt_pct(flow),
            )
        agg = _pct_value(etp.get("aggregate_pct"))
        return SectionKpiMove(
            label="Aggregate AUM",
            value_display=str(etp.get("total_aum_display") or "—"),
            delta_pct=agg,
            delta_display=_fmt_pct(agg),
        )
    if section_id == "crypto" and crypto:
        primary = crypto.get("primary") or {}
        delta = _pct_value((primary.get("delta") or {}).get("pct"))
        return SectionKpiMove(
            label=str(primary.get("label") or "Total market cap"),
            value_display=str(primary.get("value_display") or "—"),
            delta_pct=delta,
            delta_display=_fmt_pct(delta),
        )
    return None
