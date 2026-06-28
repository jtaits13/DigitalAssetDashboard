"""Smoke checks for Streamlit RWA Explore static iframe pages."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def _check_kind(kind: str, *, page_class: str, iframe_class: str, host_class: str, payload_key: str) -> int:
    from streamlit_rwa_explore_static import build_rwa_explore_server_iframe_html

    sample = {
        "page_subtitle_html": "Test dek",
        "intro_html": "<p>Intro</p>",
        "sections": [
            {
                "id": "treasuries",
                "title": "US Treasuries",
                "anchor_id": "jd-rwa-treasuries",
                "kpi_window_note": "30D",
                "kpis": [{"label": "Total", "value_display": "$1B", "delta_30d_pct": 1.2}],
                "columns": ["Network", "Total Value"],
                "rows": [{"Network": f"Net{i}", "Total Value": i} for i in range(8)],
                "rows_full": [{"Network": f"Net{i}", "Total Value": i} for i in range(23)],
                "preview_note": "Preview: first 8 of 23 networks.",
                "cta": [
                    {
                        "href": "/RWA_US_Treasuries",
                        "label": "Open full overview",
                        "variant": "primary",
                        "internal": True,
                    }
                ],
            },
            {
                "id": "tokenized_stocks",
                "title": "Tokenized Stocks",
                "anchor_id": "jd-rwa-tokenized-stocks",
                "kpi_window_note": "30D",
                "kpis": [{"label": "Total", "value_display": "$1B", "delta_30d_pct": 1.2}],
                "columns": ["Network", "Total Value"],
                "rows": [{"Network": "Ethereum", "Total Value": 1000000000}],
                "rows_full": [{"Network": "Ethereum", "Total Value": 1000000000}],
                "preview_note": "Preview: first 1 of 1 networks.",
                "cta": [],
            },
        ],
        "footer_note": "test",
        "links": {"rwa_global": "/RWA_Global_Market_Overview"},
    }
    html = build_rwa_explore_server_iframe_html(
        kind=kind,
        payload=sample,
        related_chips='<div class="home-related-chips"></div>',
    )
    treasuries_body = html.split('id="explore-treasuries-wrap"', 1)[1].split("</table>", 1)[0]
    treasuries_tr_count = treasuries_body.count("<tr>") - 1
    checks = [
        (iframe_class in html, "iframe body class"),
        (page_class in html, "page parity class"),
        ("rwa-explore-preview" in html, "server-rendered section"),
        ("explore-treasuries-wrap" in html, "server-rendered preview table"),
        ("jd-rwa-tokenized-stocks" in html, "tokenized stocks section"),
        (treasuries_tr_count == 8, f"treasuries preview rows (got {treasuries_tr_count})"),
        ("Showing 8 of 23 networks (preview)." in html, "treasuries preview count note"),
        ("js-exat-jump" in html, "jump nav"),
        ("rwa-explore-gh-canvas-override" in html, "canvas override"),
        ("measureRwaExploreContentHeight" in html, "height measure"),
        (f'data-explore-json="{payload_key}"' in html, "explore json attr"),
        ("rwa-explore-asset-type-page.js" not in html, "no legacy hydration boot"),
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
    import rwa_explore_page_payloads as payload_mod

    if "scripts.export_static_site_data" in open(payload_mod.__file__, encoding="utf-8").read():
        print("FAIL: payload module must not import scripts.export_static_site_data")
        return 1

    for kind, page_class, iframe_class, host_class, payload_key in (
        ("explore_asset", "page-rwa-explore-at", "page-rwa-explore-at-iframe",
         "streamlit-rwa-explore-at-iframe-page", "rwa_explore_asset_type.json"),
        ("explore_participant", "page-rwa-explore-mp", "page-rwa-explore-mp-iframe",
         "streamlit-rwa-explore-mp-iframe-page", "rwa_explore_market_participant.json"),
    ):
        code = _check_kind(
            kind,
            page_class=page_class,
            iframe_class=iframe_class,
            host_class=host_class,
            payload_key=payload_key,
        )
        if code:
            return code

    print("verify_rwa_explore_static: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
