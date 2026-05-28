"""Load headline pool for Key observations (Streamlit + export)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from news_feeds import DEFAULT_FEEDS, dedupe_articles, load_all_feeds

_STATIC_DEFIANT_RSS = "https://thedefiant.io/feed"
_STATIC_DEFIANT_FEED: tuple[str, str] = ("The Defiant", _STATIC_DEFIANT_RSS)


@lru_cache(maxsize=1)
def load_takeaway_articles(*, max_items: int = 200) -> list[dict[str, Any]]:
    """RSS pool used to rank and refresh Key observation bullets."""
    articles, _errs = load_all_feeds(list(DEFAULT_FEEDS) + [_STATIC_DEFIANT_FEED])
    return dedupe_articles(articles, max_items=max_items)


def merge_takeaway_pools(*pools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for pool in pools:
        if pool:
            merged.extend(pool)
    return dedupe_articles(merged, max_items=220)
