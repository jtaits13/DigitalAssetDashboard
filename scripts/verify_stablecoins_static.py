"""Smoke checks for Streamlit Stablecoins static iframe page."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    from streamlit_stablecoins_static import build_stablecoins_body_iframe_html

    html = build_stablecoins_body_iframe_html(
        payload={
            "page_title": "Stablecoins",
            "band_label": "Stablecoins",
            "networks": None,
            "platforms": None,
        },
        related_chips='<div class="home-related-chips"></div>',
    )
    checks = [
        ("page-rwa-deep-stablecoins" in html, "stable body class"),
        ("data-methodology=\"rwa-stablecoins\"" in html, "methodology attr"),
        ("js-deep-dashboard" in html, "dashboard section"),
        ("rwa-kpi-panel-static" in html, "server-rendered KPI strip"),
        ("st-tmmf-fullscreen-postmessage" in html, "fullscreen patch"),
        ("measureStableContentHeight" in html, "height measure"),
        ("data-rwa-deep-json" not in html, "no JS hydration boot"),
    ]
    for ok, label in checks:
        if not ok:
            print(f"FAIL: {label}")
            return 1

    from streamlit_site_parity import _deep_iframe_subpage_css_blob

    if "streamlit-stablecoins-iframe-page" not in _deep_iframe_subpage_css_blob():
        print("FAIL: stablecoins host CSS marker")
        return 1

    print("verify_stablecoins_static: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
