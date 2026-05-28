"""Industry headline context for Key observations (RSS pool + Google News fallback)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html import escape
from typing import Any
from urllib.parse import quote_plus

import feedparser

from key_observations.interpretations import page_theme_interpretation, resolve_topic_key
from key_observations.models import ObservationCandidate, TopicTheme

_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
_MAX_ARTICLE_AGE_DAYS = 21
_PREFERRED_SOURCES = (
    "coindesk",
    "cointelegraph",
    "the block",
    "bloomberg",
    "reuters",
    "financial times",
    "wsj",
    "sec.gov",
    "blackrock",
)


def _article_age_days(article: dict[str, Any]) -> float | None:
    pub = article.get("published")
    if not isinstance(pub, datetime):
        return None
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - pub).total_seconds() / 86400.0)


def _article_text(article: dict[str, Any]) -> str:
    return " ".join(
        str(article.get(k) or "")
        for k in ("title", "summary", "source", "category")
    ).lower()


def _article_sort_key(article: dict[str, Any]) -> tuple[int, float, float]:
    src = str(article.get("source") or "").lower()
    pref = 0
    for i, needle in enumerate(_PREFERRED_SOURCES):
        if needle in src:
            pref = len(_PREFERRED_SOURCES) - i
            break
    pub = article.get("published")
    ts = pub.timestamp() if isinstance(pub, datetime) and hasattr(pub, "timestamp") else 0.0
    age = _article_age_days(article)
    recency = -(age if age is not None else 999.0)
    return (pref, ts, recency)


def _matches_theme(article: dict[str, Any], theme: TopicTheme) -> bool:
    text = _article_text(article)
    for kw in theme.keywords:
        if " " in kw:
            if kw in text:
                return True
        elif re.search(rf"\b{re.escape(kw)}\b", text):
            return True
    return False


def collect_headlines_for_topic(
    themes: tuple[TopicTheme, ...],
    articles: list[dict[str, Any]] | None,
    *,
    google_fallback: bool = True,
    max_per_theme: int = 4,
) -> dict[str, list[dict[str, Any]]]:
    """Headlines grouped by theme id (deduped by title)."""
    pool = list(articles or [])
    by_theme: dict[str, list[dict[str, Any]]] = {t.id: [] for t in themes}
    seen_titles: set[str] = set()

    for theme in themes:
        hits = [a for a in pool if _matches_theme(a, theme)]
        hits.sort(key=_article_sort_key, reverse=True)
        for art in hits:
            title = str(art.get("title") or "").strip().lower()
            if not title or title in seen_titles:
                continue
            age = _article_age_days(art)
            if age is not None and age > _MAX_ARTICLE_AGE_DAYS:
                continue
            seen_titles.add(title)
            by_theme[theme.id].append(art)
            if len(by_theme[theme.id]) >= max_per_theme:
                break

    if google_fallback:
        for theme in themes:
            if len(by_theme[theme.id]) >= 2:
                continue
            for query in theme.google_queries[:2]:
                try:
                    feed = feedparser.parse(_GOOGLE_NEWS_RSS.format(query=quote_plus(query)))
                except Exception:
                    continue
                for entry in getattr(feed, "entries", [])[:6]:
                    title = str(getattr(entry, "title", "") or "").strip()
                    link = str(getattr(entry, "link", "") or "").strip()
                    if not title:
                        continue
                    key = title.lower()
                    if key in seen_titles:
                        continue
                    if not _matches_theme({"title": title, "summary": "", "source": "", "category": ""}, theme):
                        continue
                    seen_titles.add(key)
                    by_theme[theme.id].append(
                        {
                            "title": title,
                            "link": link,
                            "source": "Google News",
                            "published": datetime.now(timezone.utc),
                        }
                    )
                    if len(by_theme[theme.id]) >= max_per_theme:
                        break
                if len(by_theme[theme.id]) >= 2:
                    break
    return by_theme


def theme_news_strength(headlines_by_theme: dict[str, list[dict[str, Any]]]) -> dict[str, float]:
    """0–1 strength per theme from headline count and recency."""
    out: dict[str, float] = {}
    for theme_id, items in headlines_by_theme.items():
        if not items:
            out[theme_id] = 0.0
            continue
        score = min(1.0, len(items) / 3.0)
        ages = [_article_age_days(a) for a in items]
        ages = [a for a in ages if a is not None]
        if ages:
            score *= max(0.35, 1.0 - min(ages) / 14.0)
        out[theme_id] = score
    return out


def _headline_link_html(article: dict[str, Any]) -> str:
    title = escape(str(article.get("title") or "").strip())
    link = str(article.get("link") or "").strip()
    src = escape(str(article.get("source") or "").strip())
    if link:
        title = f'<a href="{escape(link, quote=True)}" target="_blank" rel="noopener noreferrer">{title}</a>'
    if src:
        return f"{title} ({src})"
    return title


def news_observation_candidates(
    topic: str,
    themes: tuple[TopicTheme, ...],
    headlines_by_theme: dict[str, list[dict[str, Any]]],
    *,
    min_strength: float = 0.42,
) -> list[ObservationCandidate]:
    """Headline-driven bullets when a theme is active in recent news."""
    out: list[ObservationCandidate] = []
    for theme in themes:
        items = headlines_by_theme.get(theme.id) or []
        if len(items) < 2:
            continue
        strength = theme_news_strength({theme.id: items}).get(theme.id, 0.0)
        if strength < min_strength:
            continue
        cites = "; ".join(_headline_link_html(a) for a in items[:2])
        interpretation = page_theme_interpretation(topic, theme.id)
        body = f"Recent coverage includes {cites}. {interpretation}"
        score = 52.0 + strength * 38.0
        out.append(
            ObservationCandidate(
                id=f"news_{theme.id}",
                lead=f"Industry headlines emphasize {theme.label}",
                body=body,
                score=score,
                themes=(theme.id,),
                source="news",
            )
        )
    return out


def apply_news_adjustments(
    candidates: list[ObservationCandidate],
    theme_strength: dict[str, float],
    *,
    boost: float = 18.0,
    penalty: float = 12.0,
    min_news_to_boost: float = 0.45,
) -> list[ObservationCandidate]:
    """Boost data bullets that match active news; penalize stale themes with hot news elsewhere."""
    if not theme_strength:
        return candidates
    hot = {tid for tid, s in theme_strength.items() if s >= min_news_to_boost}
    adjusted: list[ObservationCandidate] = []
    for cand in candidates:
        score = cand.score
        if cand.themes and any(t in hot for t in cand.themes):
            score += boost
        elif cand.themes and hot and not any(t in hot for t in cand.themes):
            if max(theme_strength.get(t, 0.0) for t in cand.themes) < 0.2:
                score -= penalty
        adjusted.append(
            ObservationCandidate(
                id=cand.id,
                lead=cand.lead,
                body=cand.body,
                score=max(0.0, score),
                themes=cand.themes,
                source=cand.source,
            )
        )
    return adjusted
