"""Helpers for per-page Key observations (Streamlit + export)."""

from __future__ import annotations

from typing import Any

from key_observations import build_key_observations_html
from key_observations.feeds import load_takeaway_articles
from key_observations.legacy import legacy_candidates_for_topic
from key_observations.models import ObservationCandidate
from key_observations.page_blend import blend_page_ko_candidates

_CONTEXT = "Context only—not investment advice."


def build_legacy_page_ko(
    topic: str,
    articles: list[dict[str, Any]] | None = None,
    *,
    explore: dict[str, dict[str, Any]] | None = None,
    etp: dict[str, Any] | None = None,
    crypto: dict[str, Any] | None = None,
) -> str:
    """Editorial baselines + WoW/news ranking for static RWA deep pages."""
    pool = articles if articles is not None else load_takeaway_articles()
    framing = legacy_candidates_for_topic(topic)
    data, pins = blend_page_ko_candidates(
        topic, framing, explore=explore, etp=etp, crypto=crypto
    )
    return build_key_observations_html(
        topic,
        data,
        pool,
        context_note=_CONTEXT,
        min_bullets=2,
        max_bullets=4,
        pin_candidate_ids=pins,
    )


def build_dynamic_page_ko(
    topic: str,
    data_candidates: list[ObservationCandidate],
    articles: list[dict[str, Any]] | None = None,
    *,
    context_note: str = _CONTEXT,
    min_bullets: int = 3,
    max_bullets: int = 5,
    explore: dict[str, dict[str, Any]] | None = None,
    etp: dict[str, Any] | None = None,
    crypto: dict[str, Any] | None = None,
    pin_candidate_ids: tuple[str, ...] = (),
) -> str:
    pool = articles if articles is not None else load_takeaway_articles()
    data, blend_pins = blend_page_ko_candidates(
        topic, data_candidates, explore=explore, etp=etp, crypto=crypto
    )
    pins = blend_pins + tuple(pid for pid in pin_candidate_ids if pid not in blend_pins)
    return build_key_observations_html(
        topic,
        data,
        pool,
        context_note=context_note,
        min_bullets=min_bullets,
        max_bullets=max_bullets,
        pin_candidate_ids=pins,
    )
