"""Helpers for per-page Key observations (Streamlit + export)."""

from __future__ import annotations

from typing import Any

from key_observations import build_key_observations_html
from key_observations.feeds import load_takeaway_articles
from key_observations.legacy import legacy_candidates_for_topic
from key_observations.models import ObservationCandidate

_CONTEXT = "Context only—not investment advice."


def build_legacy_page_ko(
    topic: str,
    articles: list[dict[str, Any]] | None = None,
) -> str:
    """Editorial baselines + headline ranking for static RWA deep pages."""
    pool = articles if articles is not None else load_takeaway_articles()
    return build_key_observations_html(
        topic,
        legacy_candidates_for_topic(topic),
        pool,
        context_note=_CONTEXT,
        min_bullets=2,
        max_bullets=4,
    )


def build_dynamic_page_ko(
    topic: str,
    data_candidates: list[ObservationCandidate],
    articles: list[dict[str, Any]] | None = None,
    *,
    context_note: str = _CONTEXT,
    min_bullets: int = 3,
    max_bullets: int = 5,
) -> str:
    pool = articles if articles is not None else load_takeaway_articles()
    return build_key_observations_html(
        topic,
        data_candidates,
        pool,
        context_note=context_note,
        min_bullets=min_bullets,
        max_bullets=max_bullets,
    )
