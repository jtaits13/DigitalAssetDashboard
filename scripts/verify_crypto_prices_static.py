"""Smoke checks for Streamlit Crypto Prices static iframe page."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    from streamlit_crypto_prices_static import build_crypto_prices_body_iframe_html

    html = build_crypto_prices_body_iframe_html(
        payloads={
            "crypto_kpis.json": {
                "generated_at": "2026-01-01T00:00:00Z",
                "primary": {"label": "Total market cap", "value_display": "$1T"},
            },
            "crypto_prices.json": {"rows": [{"symbol": "BTC", "name": "Bitcoin", "price_usd": 1}]},
            "crypto_market_cap_series.json": {"symbol": "CRYPTOCAP:TOTAL"},
        },
        related_chips='<div class="home-related-chips"></div>',
    )
    checks = [
        ("page-crypto-iframe" in html, "crypto iframe body class"),
        ('data-methodology="crypto"' in html, "methodology attr"),
        ("mock-crypto-inner" in html, "crypto inner mock class"),
        ("rwa-kpi-panel-static" in html, "server-rendered KPI strip"),
        ("js-crypto-cap-mix" in html, "cap mix section"),
        ("crypto-market-cap-chart" in html, "chart host"),
        ("js-crypto-tbody" in html, "server-rendered table body"),
        ("st-tmmf-fullscreen-postmessage" in html, "fullscreen patch"),
        ("measureCryptoContentHeight" in html, "height measure"),
        ("__CRYPTO_PAGE_PAYLOADS" in html, "embedded payloads for chart boot"),
        ("crypto-page.js" in html or "crypto-page" in html, "crypto page boot"),
    ]
    for ok, label in checks:
        if not ok:
            print(f"FAIL: {label}")
            return 1

    from streamlit_site_parity import _deep_iframe_subpage_css_blob

    blob = _deep_iframe_subpage_css_blob()
    if "streamlit-crypto-iframe-page" not in blob:
        print("FAIL: crypto host CSS marker")
        return 1

    print("verify_crypto_prices_static: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
