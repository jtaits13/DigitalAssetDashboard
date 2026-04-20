"""Streamlit widget: regulatory headlines on digital assets (RSS, global)."""

from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

REGULATORY_HEADLINE_COUNT = 5


def clear_regulatory_cache() -> None:
    from regulatory_news.client import load_regulatory_articles

    load_regulatory_articles.clear()


def render_regulatory_card_html(item: dict[str, Any]) -> str:
    pub = item.get("published")
    pub_s = pub.strftime("%b %d, %Y · %H:%M UTC") if isinstance(pub, datetime) else "Date unknown"
    title_esc = escape(item.get("title") or "Untitled")
    link = item.get("link") or "#"
    href = escape(str(link), quote=True)
    summary = (item.get("summary") or "").strip()
    sum_html = ""
    if summary:
        sum_html = f'<div class="news-summary">{escape(summary)}</div>'
    country = escape(str(item.get("country") or "Global"))
    return (
        f'<div class="news-card">'
        f'<div class="news-meta">{escape(str(item.get("source", "")))} · {escape(pub_s)}</div>'
        f'<div class="news-title"><a href="{href}" target="_blank" rel="noopener noreferrer">{title_esc}</a></div>'
        f'<div class="news-country">{country}</div>'
        f"{sum_html}"
        f"</div>"
    )


def build_home_regulatory_column_html(
    articles: list[dict[str, Any]],
    *,
    max_items: int | None = None,
) -> str:
    """Single HTML block for the home regulatory column (equal-height lane shell)."""
    limit = REGULATORY_HEADLINE_COUNT if max_items is None else max(1, max_items)
    parts = [
        '<div class="jd-news-column-shell">',
        '<div class="jd-news-column-inner">',
        '<h2 class="home-lane-heading">Regulatory & Legal Headlines</h2>',
    ]
    if not articles:
        parts.append(
            '<p class="jd-news-column-footnote">No regulatory headlines matched the filters yet. '
            "Try <strong>Refresh feeds</strong> in the sidebar.</p>"
        )
    else:
        for item in articles[:limit]:
            parts.append(render_regulatory_card_html(item))
        if len(articles) <= limit:
            parts.append(
                '<p class="jd-news-column-footnote">Showing the most recent regulatory headlines '
                "from the combined RSS list.</p>"
            )
    parts.append("</div></div>")
    return "".join(parts)


# `streamlit_app` imports this name (same builder as `build_home_regulatory_column_html`).
build_home_regulatory_lane_body_html = build_home_regulatory_column_html
