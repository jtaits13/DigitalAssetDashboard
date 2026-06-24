"""Smoke checks for Streamlit news-feed static iframe pages."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    from streamlit_news_feeds_static import (
        NEWS_FEED_SPECS,
        build_news_feed_body_iframe_html,
    )

    sample = {
        "all_articles.json": {
            "items": [
                {
                    "title": "Sample headline",
                    "link": "https://example.com/a",
                    "source": "Test",
                    "published": "2026-06-01T12:00:00+00:00",
                    "summary": "Summary text.",
                }
            ]
        }
    }
    html = build_news_feed_body_iframe_html(kind="all_articles", payloads=sample)
    checks = [
        ("page-article-feed-iframe" in html, "iframe body class"),
        ("js-article-feed-list" in html, "article feed list"),
        ("full-article-feed-page" in html or "function init" in html, "feed boot js"),
        ("__NEWS_FEED_PAYLOADS" in html, "embedded payloads"),
        ("measureNewsFeedContentHeight" in html, "height measure"),
        ("window.loadJson" in html, "loadJson override"),
    ]
    for ok, label in checks:
        if not ok:
            print(f"FAIL: {label}")
            return 1

    etf_html = build_news_feed_body_iframe_html(
        kind="etf_news",
        payloads={"etf_news.json": sample["all_articles.json"]},
    )
    if "js-etf-news-list" not in etf_html or "page-etp" not in etf_html:
        print("FAIL: etf news iframe markup")
        return 1

    if len(NEWS_FEED_SPECS) != 4:
        print("FAIL: expected four news feed specs")
        return 1

    from streamlit_site_parity import _deep_iframe_subpage_css_blob

    if "streamlit-news-feed-iframe-page" not in _deep_iframe_subpage_css_blob():
        print("FAIL: news feed host CSS marker")
        return 1

    print("verify_news_feeds_static: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
