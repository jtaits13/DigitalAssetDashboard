"""Smoke checks for Streamlit home full-screen table buttons."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    from streamlit_home_static import build_home_body_iframe_html

    html = build_home_body_iframe_html(
        news_rail='<div class="home-news-rail"></div>',
        mmf_kpis=[],
        mmf_funds=[],
        stable_kpis=[],
        stable_df=None,
        rwa_kpis=[],
        rwa_df=None,
        etp_rows=[],
        crypto_rows=[],
        crypto_paprika={},
    )
    checks = [
        ("View table full screen" in html, "fullscreen button label"),
        ("st-home-fullscreen-postmessage" in html, "home patch marker"),
        ('data-home-fullscreen-key="js-home-tmmf"' in html, "tmmf button key"),
        ('data-home-fullscreen-key="js-home-etp"' in html, "etp button key"),
        ("__HOME_FULLSCREEN_TABLES" in html, "embedded full table payload"),
        ("jpm-table-fullscreen-open" in html, "postMessage open type"),
    ]
    for ok, label in checks:
        if not ok:
            print(f"FAIL: {label}")
            return 1

    from streamlit_site_parity import STREAMLIT_TMMF_FULLSCREEN_HOST_JS

    if "jpm-table-fullscreen-open" not in STREAMLIT_TMMF_FULLSCREEN_HOST_JS:
        print("FAIL: host listener missing unified message type")
        return 1

    print("verify_home_fullscreen_patch: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
