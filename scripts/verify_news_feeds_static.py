"""Smoke checks for Streamlit news-feed static iframe pages."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    from streamlit_news_feeds_static import (
        NEWS_FEED_SPECS,
        build_news_server_iframe_html,
        news_host_canvas_override_css,
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
    html = build_news_server_iframe_html(
        kind="all_articles",
        payloads=sample,
        related_chips='<div class="home-related-chips"></div>',
    )
    checks = [
        ("page-article-feed-iframe" in html, "iframe body class"),
        ("etp-mock-shell" in html, "mock shell"),
        ("etp-mock-zone" in html, "mock zone"),
        ("js-article-feed-list" in html, "article feed list"),
        ("news-gh-canvas-override" in html, "canvas override css"),
        ("paintNewsFeedPanels" in html, "canvas override js"),
        ("__NEWS_FEED_PAYLOADS" in html, "embedded payloads"),
        ("measureNewsFeedContentHeight" in html, "height measure"),
        ("window.loadJson" in html, "loadJson override"),
        ("data-methodology=\"news\"" in html, "methodology attr"),
    ]
    for ok, label in checks:
        if not ok:
            print(f"FAIL: {label}")
            return 1

    etf_html = build_news_server_iframe_html(
        kind="etf_news",
        payloads={"etf_news.json": sample["all_articles.json"]},
        related_chips='<div class="home-related-chips"></div>',
    )
    etf_checks = [
        ("js-etf-news-list" in etf_html, "etf list host"),
        ("mock-etp-inner" in etf_html, "etf mock body class"),
        ("zone--etp" in etf_html, "etp zone class"),
        ('data-methodology="etp"' in etf_html, "etp methodology"),
        ("news-gh-canvas-override-v1-etp" in etf_html, "etp canvas override id"),
    ]
    for ok, label in etf_checks:
        if not ok:
            print(f"FAIL: etf {label}")
            return 1

    if len(NEWS_FEED_SPECS) != 4:
        print("FAIL: expected four news feed specs")
        return 1

    if "streamlit-news-feed-iframe-page" not in news_host_canvas_override_css():
        print("FAIL: news host canvas override marker")
        return 1

    from streamlit_site_parity import DEEP_IFRAME_HOST_RESET_JS, _deep_iframe_subpage_css_blob

    if "resetDeepIframeHostChrome" not in DEEP_IFRAME_HOST_RESET_JS:
        print("FAIL: deep iframe host reset script")
        return 1

    if "streamlit-news-feed-iframe-page" not in _deep_iframe_subpage_css_blob():
        print("FAIL: news feed host CSS marker")
        return 1

    print("verify_news_feeds_static: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
