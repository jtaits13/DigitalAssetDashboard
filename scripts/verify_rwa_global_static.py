"""Smoke checks for Streamlit RWA Global Market static iframe page."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    from streamlit_rwa_global_static import build_rwa_global_body_iframe_html

    sample = {
        "rwa_global_market.json": {
            "page_subtitle_html": "Test dek",
            "kpis": [{"label": "Total RWA", "value_display": "$1B", "delta_30d_pct": 1.2}],
            "kpi_window_note": "30D",
            "columns": ["Network", "Total Value"],
            "rows": [{"Network": "Ethereum", "Total Value": 1000000000}],
            "total_networks": 1,
            "chart_max_bars": 5,
            "chart_height_px": 286,
            "links": {},
        }
    }
    html = build_rwa_global_body_iframe_html(
        payloads=sample,
        related_chips='<div class="home-related-chips"></div>',
    )
    checks = [
        ("page-rwa-global-iframe" in html, "iframe body class"),
        ("mock-rwa-global-inner" in html, "mock parity class"),
        ('data-methodology="rwa-global"' in html, "methodology attr"),
        ("js-rwa-global-kpis" in html, "kpi strip"),
        ("js-rwa-global-split" in html, "networks table host"),
        ("st-tmmf-fullscreen-postmessage" in html, "fullscreen patch"),
        ("measureRwaGlobalContentHeight" in html, "height measure"),
        ("__RWA_GLOBAL_PAGE_PAYLOADS" in html, "embedded payloads"),
        ("plotly" in html.lower(), "plotly script"),
    ]
    for ok, label in checks:
        if not ok:
            print(f"FAIL: {label}")
            return 1

    from streamlit_site_parity import _deep_iframe_subpage_css_blob

    if "streamlit-rwa-global-iframe-page" not in _deep_iframe_subpage_css_blob():
        print("FAIL: rwa global host CSS marker")
        return 1

    import rwa_global_page_payloads as payload_mod

    if "scripts.export_static_site_data" in open(payload_mod.__file__, encoding="utf-8").read():
        print("FAIL: payload module must not import scripts.export_static_site_data")
        return 1

    print("verify_rwa_global_static: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
