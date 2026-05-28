"""Select and render dynamic Key observations."""

from __future__ import annotations

from html import escape
from typing import Any, Literal

from home_layout import key_observations_disclaimer_html
from key_observations.models import ObservationCandidate
from key_observations.news import (
    apply_news_adjustments,
    collect_headlines_for_topic,
    news_observation_candidates,
    theme_news_strength,
)
from key_observations.topics import TOPIC_THEMES

Variant = Literal["boxed", "crypto"]


def _bullet_html(cand: ObservationCandidate) -> str:
    if cand.lead:
        return f"<li><strong>{escape(cand.lead)}</strong> {cand.body}</li>"
    return f"<li>{cand.body}</li>"


def select_observations(
    candidates: list[ObservationCandidate],
    *,
    min_count: int = 3,
    max_count: int = 5,
    min_data: int = 2,
    max_news: int = 2,
) -> list[ObservationCandidate]:
    if not candidates:
        return []
    ranked = sorted(candidates, key=lambda c: c.score, reverse=True)
    data_ranked = [c for c in ranked if c.source == "data"]
    news_ranked = [c for c in ranked if c.source == "news"]

    chosen: list[ObservationCandidate] = []
    used_themes: set[str] = set()

    def _try_add(cand: ObservationCandidate, *, force: bool = False) -> bool:
        if cand in chosen:
            return False
        if (
            not force
            and cand.themes
            and used_themes.intersection(cand.themes)
            and cand.score < 72
            and len(chosen) >= min_count
        ):
            return False
        chosen.append(cand)
        used_themes.update(cand.themes)
        return True

    if data_ranked and news_ranked:
        for cand in data_ranked:
            if len([c for c in chosen if c.source == "data"]) >= min_data:
                break
            if cand.score >= 48.0:
                _try_add(cand, force=True)
        for cand in news_ranked:
            if len([c for c in chosen if c.source == "news"]) >= max_news:
                break
            _try_add(cand, force=True)

    for cand in ranked:
        if len(chosen) >= max_count:
            break
        _try_add(cand)

    if len(chosen) < min_count:
        for cand in ranked:
            if cand in chosen:
                continue
            chosen.append(cand)
            if len(chosen) >= min_count:
                break
    return chosen[:max_count]


def render_observations_html(
    selected: list[ObservationCandidate],
    *,
    context_note: str,
    variant: Variant = "boxed",
    include_disclaimer: bool = True,
) -> str:
    if not selected:
        return ""
    items = "".join(_bullet_html(c) for c in selected)
    note = (
        f'<p class="takeaways__note">{escape(context_note)} '
        "Bullets are ranked from on-page data and recent industry headlines (dashboard RSS plus Google News fallback).</p>"
    )
    review = key_observations_disclaimer_html() if include_disclaimer else ""
    if variant == "crypto":
        return (
            '<div class="takeaways">'
            '<ul class="crypto-story-callout__list">'
            f"{items}</ul>{note}{review}</div>"
        )
    return (
        '<div style="border:1px solid #C7D8E8;border-radius:10px;padding:0.75rem 0.95rem;'
        'margin:0.1rem 0 0.55rem;background:#ffffff;box-shadow:0 1px 3px rgba(15,23,42,0.06);">'
        f'<ul style="margin:0.1rem 0 0 1.05rem;padding:0;color:#1F4C67;font-size:0.9rem;line-height:1.45;">'
        f"{items}</ul>{note}</div>{review}"
    )


def build_key_observations_html(
    topic: str,
    data_candidates: list[ObservationCandidate],
    articles: list[dict[str, Any]] | None = None,
    *,
    context_note: str,
    include_disclaimer: bool = True,
    min_bullets: int = 3,
    max_bullets: int = 5,
    variant: Variant = "boxed",
    include_monthly_review: bool | None = None,
) -> str:
    """Merge data-driven and headline-driven candidates; pick the highest-scoring set."""
    themes = TOPIC_THEMES.get(topic, ())
    headlines = collect_headlines_for_topic(themes, articles) if themes else {}
    news_strength = theme_news_strength(headlines) if themes else {}

    pool = list(data_candidates)
    pool = apply_news_adjustments(pool, news_strength)
    pool.extend(news_observation_candidates(themes, headlines))

    has_news = any(c.source == "news" for c in pool)
    has_data = any(c.source == "data" for c in pool)
    min_data = 2 if has_data and has_news else 0
    max_news = 2 if has_data and has_news else max_bullets

    if include_monthly_review is not None:
        include_disclaimer = include_monthly_review

    selected = select_observations(
        pool,
        min_count=min_bullets,
        max_count=max_bullets,
        min_data=min_data,
        max_news=max_news,
    )
    return render_observations_html(
        selected,
        context_note=context_note,
        variant=variant,
        include_disclaimer=include_disclaimer,
    )
