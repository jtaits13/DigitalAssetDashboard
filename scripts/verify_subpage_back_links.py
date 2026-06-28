"""Smoke checks for subpage back-link clearance and nav routing hooks."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    from streamlit_site_parity import (
        SUBPAGE_NAV_DROPDOWN_WELL_PX,
        SUBPAGE_NAV_HEIGHT_SLACK_PX,
        deep_iframe_back_link_clickable_css,
        iframe_internal_link_script,
        STREAMLIT_SITE_NAV_ROUTER_JS,
    )

    css = deep_iframe_back_link_clickable_css(scope="body.page-rwa-deep-mmf")
    clearance = SUBPAGE_NAV_DROPDOWN_WELL_PX + SUBPAGE_NAV_HEIGHT_SLACK_PX
    checks = [
        (f"padding-top: {clearance}px" in css, "back-link nav clearance"),
        ("pointer-events: auto" in css, "back-link pointer events"),
        ("watchInternalLinks" in iframe_internal_link_script(), "iframe link observer"),
        ("bindIframeBackLinks" in STREAMLIT_SITE_NAV_ROUTER_JS, "host iframe back-link binder"),
        ("jpm-navigate" in STREAMLIT_SITE_NAV_ROUTER_JS, "nav router message handler"),
    ]
    for ok, label in checks:
        if not ok:
            print(f"FAIL: {label}")
            return 1
    print("verify_subpage_back_links: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
