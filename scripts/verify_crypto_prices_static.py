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
            "crypto_kpis.json": {"generated_at": "2026-01-01T00:00:00Z"},
            "crypto_prices.json": {"rows": []},
            "crypto_market_cap_series.json": {"symbol": "CRYPTOCAP:TOTAL"},
        },
        related_chips='<div class="home-related-chips"></div>',
    )
    checks = [
        ("page-crypto-iframe" in html, "crypto iframe body class"),
        ('data-methodology="crypto"' in html, "methodology attr"),
        ("js-crypto-kpi" in html, "kpi strip"),
        ("crypto-market-cap-chart" in html, "chart host"),
        ("st-tmmf-fullscreen-postmessage" in html, "fullscreen patch"),
        ("measureCryptoContentHeight" in html, "height measure"),
        ("__CRYPTO_PAGE_PAYLOADS" in html, "embedded payloads"),
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
