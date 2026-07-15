"""Select and render dynamic Key observations."""

from __future__ import annotations

import re
from html import escape
from typing import Any, Literal

from home_layout import key_observations_disclaimer_html
from key_observations.models import ObservationCandidate
from key_observations.news import (
    apply_news_adjustments,
    collect_headlines_for_topic,
    headline_link_html,
    news_observation_candidates,
    strip_embedded_headlines,
    theme_news_strength,
)
from key_observations.interpretations import resolve_topic_key
from key_observations.topics import TOPIC_THEMES

Variant = Literal["boxed", "crypto", "inner_page"]

# Topic keys passed to weekly article matcher (section guardrails).
_PAGE_TOPIC_KEYS: dict[str, tuple[str, ...]] = {
    "tokenized_mmf": ("tokenized_mmf",),
    "stablecoins": ("stablecoins",),
    "us_treasuries": ("us_treasuries", "rwa_global"),
    "tokenized_stocks": ("tokenized_stocks", "rwa_global"),
    "rwa_global": ("rwa_global", "us_treasuries", "tokenized_stocks"),
    "participants": ("participants", "rwa_global"),
    "participants_networks": ("participants", "rwa_global"),
    "participants_platforms": ("participants", "rwa_global"),
    "participants_asset_managers": ("participants", "rwa_global"),
    "etp": ("etp",),
    "crypto": ("crypto",),
}

# Themes that express the same takeaway — keep only the highest-scoring bullet.
_OVERLAP_THEME_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"institutional_settlement", "issuer_models"}),
    frozenset({"regulation", "stablecoin_policy"}),
    frozenset({"etf_flows", "concentration"}),
    frozenset({"tokenized_treasuries", "institutional_adoption"}),
    frozenset({"chain_efficiency", "multichain"}),
)


def _bullet_html(cand: ObservationCandidate) -> str:
    if cand.lead:
        return f"<li><strong>{escape(cand.lead)}</strong> {cand.body}</li>"
    return f"<li>{cand.body}</li>"


def _themes_overlap(a: ObservationCandidate, b: ObservationCandidate) -> bool:
    if not a.themes or not b.themes:
        return False
    ta, tb = set(a.themes), set(b.themes)
    if ta.intersection(tb):
        return True
    for group in _OVERLAP_THEME_GROUPS:
        if (ta & group) and (tb & group):
            return True
    return False


def _normalize_body(body: str) -> str:
    text = strip_embedded_headlines(body or "")
    text = re.sub(r"\s+", " ", text).strip()
    if text and not text.endswith((".", "!", "?")):
        text = f"{text}."
    return text


def _attach_related_articles(
    selected: list[ObservationCandidate],
    topic: str,
    articles: list[dict[str, Any]] | None,
) -> list[ObservationCandidate]:
    """One tightly matched related article per bullet (skip weak matches)."""
    if not articles:
        return selected
    try:
        from key_observations.week_headlines import match_article_for_takeaway
    except Exception:
        return selected

    theme_key = resolve_topic_key(topic)
    topic_keys = _PAGE_TOPIC_KEYS.get(topic) or _PAGE_TOPIC_KEYS.get(theme_key) or (theme_key,)
    used_links: set[str] = set()
    out: list[ObservationCandidate] = []

    for cand in selected:
        body = _normalize_body(cand.body)
        plain = re.sub(r"<[^>]+>", " ", f"{cand.lead or ''} {body}")
        plain = re.sub(r"\s+", " ", plain).strip()
        art = match_article_for_takeaway(
            plain,
            bullet_lead=(cand.lead or "").strip().rstrip(":"),
            topic_keys=topic_keys,
            articles=articles,
            used_links=used_links,
            max_age_days=21.0,
            strict=True,
        )
        if art is not None:
            base = body.rstrip(".!? ")
            body = f"{base}. Related: {headline_link_html(art)}."
        out.append(
            ObservationCandidate(
                id=cand.id,
                lead=cand.lead,
                body=body,
                score=cand.score,
                themes=cand.themes,
                source=cand.source,
            )
        )
    return out


def select_observations(
    candidates: list[ObservationCandidate],
    *,
    min_count: int = 3,
    max_count: int = 5,
    min_data: int = 2,
    max_news: int = 2,
    pin_candidate_ids: tuple[str, ...] = (),
) -> list[ObservationCandidate]:
    if not candidates:
        return []
    ranked = sorted(candidates, key=lambda c: c.score, reverse=True)
    by_id = {c.id: c for c in candidates}
    data_ranked = [c for c in ranked if c.source == "data"]
    news_ranked = [c for c in ranked if c.source == "news"]

    chosen: list[ObservationCandidate] = []
    used_themes: set[str] = set()

    for pin_id in pin_candidate_ids:
        cand = by_id.get(pin_id)
        if cand and cand not in chosen:
            chosen.append(cand)
            used_themes.update(cand.themes)

    def _blocks_overlap(cand: ObservationCandidate) -> bool:
        for picked in chosen:
            if not _themes_overlap(cand, picked):
                continue
            # One news angle per theme cluster; avoid headline pile-up.
            if cand.source == "news" or picked.source == "news":
                return True
            # WoW KPI read can sit beside a different data cut on the same theme.
            if picked.id.startswith("wow_") or cand.id.startswith("wow_"):
                continue
            if any(
                g & set(cand.themes) & set(picked.themes) for g in _OVERLAP_THEME_GROUPS
            ):
                return True
            if set(cand.themes) == set(picked.themes):
                return True
        return False

    def _try_add(cand: ObservationCandidate, *, force: bool = False) -> bool:
        if cand in chosen:
            return False
        if not force and _blocks_overlap(cand):
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
            if _blocks_overlap(cand):
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
    intro_dek_html: str = "",
) -> str:
    if not selected:
        return ""
    items = "".join(_bullet_html(c) for c in selected)
    note_text = (
        f"{escape(context_note)} "
        "Bullets combine on-page data with recent industry headlines."
    )
    note = f'<p class="takeaways__note">{note_text}</p>'
    review = key_observations_disclaimer_html() if include_disclaimer else ""
    if variant == "inner_page":
        dek = (
            f'<p class="crypto-story-callout__dek">{intro_dek_html.strip()}</p>'
            if intro_dek_html.strip()
            else ""
        )
        return (
            '<aside class="crypto-story-callout" aria-labelledby="key-obs-callout-title">'
            '<p class="crypto-story-callout__title" role="heading" aria-level="3" '
            'id="key-obs-callout-title">Key observations</p>'
            f"{dek}"
            f'<ul class="crypto-story-callout__list">{items}</ul>'
            f'<p class="crypto-story-callout__note">{note_text}</p>'
            "</aside>"
            f"{review}"
        )
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
    pin_candidate_ids: tuple[str, ...] = (),
    intro_dek_html: str = "",
) -> str:
    """Merge data-driven and headline-driven candidates; pick the highest-scoring set."""
    theme_key = resolve_topic_key(topic)
    themes = TOPIC_THEMES.get(theme_key, TOPIC_THEMES.get(topic, ()))
    headlines = collect_headlines_for_topic(themes, articles) if themes else {}
    news_strength = theme_news_strength(headlines) if themes else {}

    pool = list(data_candidates)
    pool = apply_news_adjustments(pool, news_strength)
    pool.extend(news_observation_candidates(topic, themes, headlines))

    has_news = any(c.source == "news" for c in pool)
    has_data = any(c.source == "data" for c in pool)
    min_data = 2 if has_data and has_news else 0
    max_news = 1 if has_data and has_news else max_bullets

    if include_monthly_review is not None:
        include_disclaimer = include_monthly_review

    selected = select_observations(
        pool,
        min_count=min_bullets,
        max_count=max_bullets,
        min_data=min_data,
        max_news=max_news,
        pin_candidate_ids=pin_candidate_ids,
    )
    selected = _attach_related_articles(selected, topic, articles)
    return render_observations_html(
        selected,
        context_note=context_note,
        variant=variant,
        include_disclaimer=include_disclaimer,
        intro_dek_html=intro_dek_html,
    )
