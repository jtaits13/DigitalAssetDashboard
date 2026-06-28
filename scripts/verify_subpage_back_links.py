"""Smoke checks for subpage back-link interactivity and nav layout."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    from streamlit_site_parity import (
        SUBPAGE_NAV_HEADER_EST_PX,
        SUBPAGE_NAV_HEIGHT_SLACK_PX,
        SUBPAGE_NAV_IFRAME_INITIAL_HEIGHT,
        SUBPAGE_STREAMLIT_CSS,
        build_home_nav_iframe_html,
        deep_iframe_back_link_clickable_css,
        iframe_home_nav_height_script,
        iframe_internal_link_script,
        STREAMLIT_SITE_NAV_ROUTER_JS,
    )

    css = deep_iframe_back_link_clickable_css(scope="body.page-rwa-deep-mmf")
    nav_html = build_home_nav_iframe_html(active="rwa_global")
    host_css = SUBPAGE_STREAMLIT_CSS.replace("SUBPAGE_NAV_DROPDOWN_WELL_PLACEHOLDER", "188")
    checks = [
        ("padding-top:" not in css, "no body padding clearance"),
        ("pointer-events: auto" in css, "back-link pointer events"),
        ('class="home-nav-dropdown-well"' not in nav_html, "no static nav dropdown well"),
        ("bindDropdownResize" in iframe_home_nav_height_script(), "dynamic nav height on hover"),
        ("watchInternalLinks" in iframe_internal_link_script(), "iframe link observer"),
        ("bindIframeBackLinks" in STREAMLIT_SITE_NAV_ROUTER_JS, "host iframe back-link binder"),
        ("margin-top: -188px" not in host_css and "margin-top: -SUBPAGE_NAV_DROPDOWN_WELL" not in host_css, "no body iframe pull-up"),
        (
            SUBPAGE_NAV_IFRAME_INITIAL_HEIGHT
            == SUBPAGE_NAV_HEADER_EST_PX + SUBPAGE_NAV_HEIGHT_SLACK_PX,
            "nav iframe initial height is header-only",
        ),
    ]
    for ok, label in checks:
        if not ok:
            print(f"FAIL: {label}")
            return 1
    print("verify_subpage_back_links: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
