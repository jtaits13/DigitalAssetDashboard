"""Smoke checks for nav-iframe back pills and body iframe deduplication."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    from streamlit_site_parity import (
        HOME_IFRAME_HEIGHT_SYNC_JS,
        _nav_chrome_back_link_html,
        _subpage_nav_back_defaults,
        build_home_nav_iframe_html,
        deep_iframe_back_link_clickable_css,
        iframe_home_nav_height_script,
    )

    body_css = deep_iframe_back_link_clickable_css(scope="body.page-rwa-deep-mmf")
    nav_html = build_home_nav_iframe_html(
        active="tmmf",
        back_href="/?jd_scroll=tmmf",
        back_label="← Back to home · TMMF preview",
    )
    back_row = _nav_chrome_back_link_html(href="/?jd_scroll=tmmf", label="← Back to home · TMMF preview")
    tmmf_defaults = _subpage_nav_back_defaults("tmmf")
    checks = [
        ("display: none" in body_css, "body iframe back link hidden"),
        ("nav-chrome-back-row" in nav_html, "nav iframe includes back row"),
        ("nav-chrome-back-pill" in nav_html, "nav iframe back pill class"),
        ("nav-chrome-back-row" in back_row, "back row helper markup"),
        (tmmf_defaults is not None and tmmf_defaults[0] == "/?jd_scroll=tmmf", "tmmf default back href"),
        ("nav-chrome-back-row" in iframe_home_nav_height_script(), "nav height observes back row"),
        (".nav-chrome-back-row" in HOME_IFRAME_HEIGHT_SYNC_JS, "host height measures back row"),
        ("if (!sourceFrame || sourceFrame !== frame) return;" in HOME_IFRAME_HEIGHT_SYNC_JS, "nav ignores foreign heights"),
    ]
    for ok, label in checks:
        if not ok:
            print(f"FAIL: {label}")
            return 1
    print("verify_subpage_back_links: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
