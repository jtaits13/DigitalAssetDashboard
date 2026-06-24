"""Smoke checks for Streamlit U.S. ETPs static iframe page."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    from etp_live_cache import bundle_from_static_exports
    from streamlit_etps_static import build_etps_body_iframe_html

    seeded = bundle_from_static_exports(REPO / "static_home" / "data")
    if not seeded:
        print("FAIL: no static ETP seed bundle")
        return 1
    payloads = seeded["payloads"]
    html = build_etps_body_iframe_html(
        payloads=payloads,
        related_chips='<div class="home-related-chips"></div>',
    )
    checks = [
        ("page-etp-iframe" in html, "etp iframe body class"),
        ('data-methodology="etp"' in html, "methodology attr"),
        ("js-etp-kpi" in html, "kpi strip"),
        ("aum-chart" in html, "aum chart host"),
        ("js-etp-tbody" in html, "fund table"),
        ("st-tmmf-fullscreen-postmessage" in html, "fullscreen patch"),
        ("measureEtpContentHeight" in html, "height measure"),
        ("__ETP_PAGE_PAYLOADS" in html, "embedded payloads"),
    ]
    for ok, label in checks:
        if not ok:
            print(f"FAIL: {label}")
            return 1

    from streamlit_site_parity import _deep_iframe_subpage_css_blob

    if "streamlit-etps-iframe-page" not in _deep_iframe_subpage_css_blob():
        print("FAIL: etps host CSS marker")
        return 1

    print("verify_etps_static: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
