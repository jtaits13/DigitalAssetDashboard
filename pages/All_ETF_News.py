"""Full ETF/ETP RSS headline list (same layout as All Articles / All Regulatory)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from streamlit_site_parity import configure_subpage, render_subpage_footer
from streamlit_news_feeds_static import (
    _cached_news_feed_iframe_payloads,
    render_news_feed_body_iframe,
)


def main() -> None:
    configure_subpage(
        page_title="ETF & ETP headlines — Digital Assets Dashboard",
        active="etps",
        style_kind="news_feed",
    )
    payloads = _cached_news_feed_iframe_payloads("etf_news")
    render_news_feed_body_iframe(kind="etf_news", payloads=payloads)
    render_subpage_footer(label="ETF/ETP News")


main()
