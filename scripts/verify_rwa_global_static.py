"""Smoke checks for Streamlit RWA Global Market static iframe page."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    from streamlit_rwa_global_static import build_rwa_global_server_iframe_html

    sample = {
        "page_subtitle_html": "Test dek",
        "kpis": [{"label": "Total RWA", "value_display": "$1B", "delta_30d_pct": 1.2}],
        "kpi_window_note": "30D",
        "scope_note": "Scope: all RWA assets excluding stablecoins.",
        "columns": ["Network", "Total Value", "Market Share"],
        "rows": [
            {
                "Network": "Ethereum",
                "Total Value": 1000000000,
                "Market Share": 42.5,
                "30D Δ share": 1.2,
            }
        ],
        "total_networks": 1,
        "macro_observations_html": "<ul><li>Test observation</li></ul>",
        "explore_gateways_html": '<nav class="home-explore-compact"></nav>',
        "caption_html": "Source: RWA.xyz",
        "links": {"global_market_on_rwa_xyz": "https://app.rwa.xyz/networks"},
        "footer_note": "test",
    }
    html = build_rwa_global_server_iframe_html(
        payload=sample,
        related_chips='<div class="home-related-chips"></div>',
    )
    checks = [
        ("page-rwa-global-iframe" in html, "iframe body class"),
        ("mock-rwa-global-inner" in html, "mock parity class"),
        ('data-methodology="rwa-global"' in html, "methodology attr"),
        ("rwa-kpi-row--home-grid" in html, "server-rendered KPI strip"),
        ("rwa-global-net-wrap" in html, "server-rendered networks table"),
        ("js-rwa-global-dashboard-chart" in html, "dashboard chart host"),
        ("__RWA_GLOBAL_SERVER_CHART" in html, "chart boot config"),
        ("rwa-global-gh-canvas-override" in html, "canvas override"),
        ("deep_iframe_rwa_zone_seam" in html or "home-explore-compact__btn" in html, "zone seam flatten"),
        ("measureRwaGlobalContentHeight" in html, "height measure"),
        ("plotly" in html.lower(), "plotly script"),
        ("rwa-global-page.js" not in html, "no legacy hydration boot"),
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
