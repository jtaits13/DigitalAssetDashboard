"""
Blend newsletter-style WoW dynamics into page Key observations.

Page KOs keep structural framing (legacy / domain candidates) and theme news,
but pin a fresh KPI read first and lightly weave the current 30D print into the
top framing bullet so sections stay dynamic without losing broader market context.
"""

from __future__ import annotations

from typing import Any

from key_observations.models import ObservationCandidate

# Page topic -> newsletter section_id used for WoW copy.
_TOPIC_SECTION: dict[str, str] = {
    "tokenized_mmf": "tmmf",
    "stablecoins": "stablecoins",
    "us_treasuries": "rwa",
    "tokenized_stocks": "rwa",
    "rwa_global": "rwa",
    "etp": "etp",
    "crypto": "crypto",
}


_WOW_THEMES: dict[str, tuple[str, ...]] = {
    "tmmf": ("institutional_settlement", "tokenization_growth"),
    "stablecoins": ("stablecoin_policy", "bank_integration"),
    "rwa": ("tokenized_treasuries", "institutional_adoption"),
    "etp": ("etf_flows", "launch_pipeline"),
    "crypto": ("market_structure",),
}


def explore_sections_from_payload(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Map explore JSON ``sections`` list to ``{section_id: section}``."""
    out: dict[str, dict[str, Any]] = {}
    for sec in (payload or {}).get("sections") or []:
        sid = sec.get("id")
        if sid:
            out[str(sid)] = sec
    return out


def _move_for_topic(
    topic: str,
    section_id: str,
    *,
    explore: dict[str, dict[str, Any]] | None,
    etp: dict[str, Any] | None,
    crypto: dict[str, Any] | None,
):
    from key_observations.newsletter_week import _section_kpi_move, explore_kpi_move

    # Stocks page should not inherit the Treasuries KPI just because both map to "rwa".
    if topic == "tokenized_stocks":
        return explore_kpi_move(explore or {}, "tokenized_stocks", label_match="distributed")
    return _section_kpi_move(section_id, explore or {}, etp=etp, crypto=crypto)


def _wow_candidate(
    topic: str,
    section_id: str,
    *,
    explore: dict[str, dict[str, Any]] | None,
    etp: dict[str, Any] | None,
    crypto: dict[str, Any] | None,
) -> ObservationCandidate | None:
    try:
        from key_observations.newsletter_week import (
            _flat_takeaway,
            _lane_label,
            _wow_takeaway,
        )
    except Exception:
        return None

    move = _move_for_topic(topic, section_id, explore=explore, etp=etp, crypto=crypto)
    if topic == "tokenized_stocks":
        lead, body = _tokenized_stocks_wow_copy(move)
    else:
        tw = None
        if move is not None:
            tw = _wow_takeaway(move, lane=_lane_label(section_id), section_id=section_id)
        if tw is None:
            tw = _flat_takeaway(move, lane=_lane_label(section_id), section_id=section_id)
        lead = (tw.lead or "").strip().rstrip(".!?…:")
        body = (tw.body or "").strip()

    if body and not body.endswith((".", "!", "?")):
        body = f"{body}."

    cand_id = f"wow_{topic}" if topic == "tokenized_stocks" else f"wow_{section_id}"
    return ObservationCandidate(
        id=cand_id,
        lead=f"{lead}:",
        body=body,
        score=92.0,
        themes=_WOW_THEMES.get(section_id, ()),
        source="data",
    )


def _tokenized_stocks_wow_copy(move) -> tuple[str, str]:
    from key_observations.newsletter_week import _WOW_THRESHOLD, _move_verb

    if move is None or move.delta_pct is None:
        return (
            "Tokenized stocks printed metrics did not show a clear weekly move",
            "Distributed value stayed near prior levels, so the lane still looks early-stage "
            "and plumbing-led rather than AUM-led",
        )
    if abs(move.delta_pct) < _WOW_THRESHOLD:
        return (
            "Tokenized stocks printed metrics were roughly flat this week",
            f"{move.label} near {move.value_display} ({move.delta_display} 30D) keeps the lane "
            "in a holding pattern—liquidity and platform concentration still dominate",
        )
    verb = _move_verb(move.delta_pct)
    mag = f"{abs(move.delta_pct):.1f}%"
    lead = f"Tokenized stocks {move.label.lower()} {verb} {mag} over 30D"
    if move.delta_pct >= 0:
        body = (
            f"Tokenized equity distributed value at {move.value_display} ({mag} higher over 30D) "
            "shows the early lane still adding balance sheet on a small set of platforms"
        )
    else:
        body = (
            f"Tokenized equity distributed value at {move.value_display} ({mag} lower over 30D) "
            "points to softer platform balances even while listings and plumbing news continue"
        )
    return lead, body


def _weave_framing_with_move(
    framing: list[ObservationCandidate],
    topic: str,
    section_id: str,
    *,
    explore: dict[str, dict[str, Any]] | None,
    etp: dict[str, Any] | None,
    crypto: dict[str, Any] | None,
) -> list[ObservationCandidate]:
    """Anchor the strongest framing bullet to the current 30D print when meaningful."""
    if not framing:
        return framing
    try:
        from key_observations.newsletter_week import _WOW_THRESHOLD
    except Exception:
        return framing

    move = _move_for_topic(topic, section_id, explore=explore, etp=etp, crypto=crypto)
    if move is None or move.delta_pct is None or abs(move.delta_pct) < _WOW_THRESHOLD:
        return framing

    verb = "firmer" if move.delta_pct >= 0 else "softer"
    mag = f"{abs(move.delta_pct):.1f}%"
    metric = (move.label or "30D KPIs").strip()
    anchor = (
        f"Against a {verb} {metric.lower()} print ({mag} over 30D), "
    )

    # Prefer the highest-scoring framing candidate for the weave.
    ranked = sorted(enumerate(framing), key=lambda pair: pair[1].score, reverse=True)
    idx, top = ranked[0]
    body = (top.body or "").strip()
    if body:
        body = body[0].lower() + body[1:] if body[0].isupper() else body
        woven = f"{anchor}{body}"
    else:
        woven = anchor.rstrip(", ") + "."

    out = list(framing)
    out[idx] = ObservationCandidate(
        id=top.id,
        lead=top.lead,
        body=woven,
        score=min(88.0, float(top.score) + 8.0),
        themes=top.themes,
        source=top.source,
    )
    return out


def blend_page_ko_candidates(
    topic: str,
    framing_candidates: list[ObservationCandidate],
    *,
    explore: dict[str, dict[str, Any]] | None = None,
    etp: dict[str, Any] | None = None,
    crypto: dict[str, Any] | None = None,
) -> tuple[list[ObservationCandidate], tuple[str, ...]]:
    """
    Merge WoW/flat dynamics with structural framing for page KOs.

    Returns ``(candidates, pin_candidate_ids)``. When a WoW/flat candidate exists,
    it is pinned first; framing stays in the pool (woven to the current print when
    the move is meaningful).
    """
    section_id = _TOPIC_SECTION.get(topic)
    framing = list(framing_candidates)
    if not section_id:
        return framing, ()

    wow = _wow_candidate(
        topic, section_id, explore=explore, etp=etp, crypto=crypto
    )
    if wow is None:
        framing = _weave_framing_with_move(
            framing, topic, section_id, explore=explore, etp=etp, crypto=crypto
        )
        return framing, ()

    framing = [c for c in framing if c.id != wow.id]
    if topic == "tokenized_mmf":
        framing = [c for c in framing if c.id != "mmf_settlement"]
    return [wow, *framing], (wow.id,)
