"""Full crypto prices page (top 50 snapshot)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from streamlit_site_parity import (
    _streamlit_page_href,
    configure_subpage,
    related_chips_html,
    render_subpage_footer,
)
from streamlit_crypto_prices_static import (
    _cached_crypto_prices_iframe_payloads,
    render_crypto_prices_body_iframe,
)


def main() -> None:
    configure_subpage(
        page_title="Crypto Prices — Digital Assets Dashboard",
        active="crypto",
        style_kind="crypto",
    )
    related = related_chips_html(
        ("/?jd_scroll=crypto", "Home crypto preview"),
        (_streamlit_page_href("etps"), "U.S. ETPs"),
        (_streamlit_page_href("stablecoins"), "Stablecoins"),
        ("/?jd_scroll=news", "News Hub"),
    )

    payloads = _cached_crypto_prices_iframe_payloads()
    render_crypto_prices_body_iframe(payloads=payloads, related_chips=related)

    render_subpage_footer(label="Crypto Prices")


main()
