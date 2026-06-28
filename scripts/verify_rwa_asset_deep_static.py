"""Smoke checks for Streamlit US Treasuries / Tokenized Stocks iframe pages."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def _check_kind(kind: str, *, body_class: str, mock_class: str, host_class: str, methodology: str) -> int:
    from streamlit_rwa_asset_deep_static import build_rwa_asset_deep_server_iframe_html

    html = build_rwa_asset_deep_server_iframe_html(
        kind=kind,
        payload={
            "page_title": "Test",
            "band_label": "Test",
            "networks": None,
            "platforms": None,
        },
        related_chips='<div class="home-related-chips"></div>',
    )
    checks = [
        (body_class in html, "body class"),
        (mock_class in html, "mock inner class"),
        (f'data-methodology="{methodology}"' in html, "methodology attr"),
        ("js-deep-dashboard" in html, "dashboard section"),
        ("deep-net-wrap" in html, "networks table host"),
        ("measureStableContentHeight" in html, "height measure"),
        ("rwa-asset-deep-page.js" not in html, "no legacy hydration boot"),
    ]
    for ok, label in checks:
        if not ok:
            print(f"FAIL [{kind}]: {label}")
            return 1

    from streamlit_site_parity import _deep_iframe_subpage_css_blob

    if host_class not in _deep_iframe_subpage_css_blob():
        print(f"FAIL [{kind}]: host CSS marker")
        return 1
    return 0


def main() -> int:
    for kind, body, mock, host, methodology in (
        ("treasuries", "page-rwa-deep-treasuries", "mock-treasuries-inner", "streamlit-treasuries-iframe-page", "rwa-treasuries"),
        ("stocks", "page-rwa-deep-stocks", "mock-stocks-inner", "streamlit-stocks-iframe-page", "rwa-tokenized-stocks"),
    ):
        code = _check_kind(kind, body_class=body, mock_class=mock, host_class=host, methodology=methodology)
        if code:
            return code
    print("verify_rwa_asset_deep_static: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
