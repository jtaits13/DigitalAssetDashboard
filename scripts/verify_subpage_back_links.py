"""Smoke checks for body-iframe back pills on deep subpages."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    from streamlit_site_parity import (
        HOME_IFRAME_HEIGHT_SYNC_JS,
        build_home_nav_iframe_html,
        deep_iframe_back_link_clickable_css,
        iframe_home_nav_height_script,
    )
    from streamlit_tmmf_static import build_tmmf_body_iframe_html

    body_css = deep_iframe_back_link_clickable_css(scope="body.page-rwa-deep-mmf")
    nav_html = build_home_nav_iframe_html(active="tmmf")
    tmmf_html = build_tmmf_body_iframe_html(
        payload={"title": "Tokenized Money Market Funds"},
        related_chips="",
    )
    checks = [
        ("pointer-events: auto" in body_css, "body iframe back link clickable"),
        ("display: none" not in body_css, "body iframe back link visible"),
        ("nav-chrome-back-row" not in nav_html, "nav iframe excludes back row"),
        ("page-back-below-header" in tmmf_html, "body iframe includes back row"),
        ("nav-chrome-back-row" not in iframe_home_nav_height_script(), "nav height ignores back row"),
        (".nav-chrome-back-row" not in HOME_IFRAME_HEIGHT_SYNC_JS, "host height ignores back row"),
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
