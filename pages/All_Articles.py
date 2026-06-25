"""Full article list with pagination and day grouping."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from streamlit_site_parity import configure_subpage, render_subpage_footer
from streamlit_news_feeds_static import (
    get_news_feed_iframe_payloads,
    render_news_feed_body_iframe,
)


def main() -> None:
    configure_subpage(
        page_title="All digital asset headlines — Digital Assets Dashboard",
        active="news",
        style_kind="news_feed",
    )
    payloads = get_news_feed_iframe_payloads("all_articles")
    render_news_feed_body_iframe(kind="all_articles", payloads=payloads)
    render_subpage_footer(label="All headlines")


main()
