"""Streamlit widget: regulatory headlines on digital assets (RSS, global)."""

from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any, Optional

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
    max_items: Optional[int] = None,
) -> str:
    """Home regulatory column: same hub panel system as market news (matched readability)."""
    from news_feeds import hub_news_panel_header_html, render_hub_news_lane_item_html

    limit = REGULATORY_HEADLINE_COUNT if max_items is None else max(1, max_items)
    hid = "jd-hub-news-regulatory-h2"
    parts: list[str] = [
        f'<section class="jd-hub-news-panel" aria-labelledby="{hid}">',
        hub_news_panel_header_html(
            eyebrow="Regulatory wire",
            title="Regulatory & Legal Headlines",
            heading_id=hid,
        ),
    ]
    if not articles:
        parts.append(
            '<p class="jd-hub-news-empty">No regulatory headlines matched the filters yet. '
            "Try <strong>Refresh all data</strong> on the home page.</p>"
        )
    else:
        parts.append('<ol class="jd-hub-news-list" role="list">')
        for i, item in enumerate(articles[:limit], start=1):
            parts.append(render_hub_news_lane_item_html(item, i, show_country=True))
        parts.append("</ol>")
        if len(articles) <= limit:
            parts.append(
                '<p class="jd-hub-news-footnote">Most recent from the regulatory RSS list.</p>'
            )
    parts.append("</section>")
    return "".join(parts)


# `streamlit_app` imports this name (same builder as `build_home_regulatory_column_html`).
build_home_regulatory_lane_body_html = build_home_regulatory_column_html
