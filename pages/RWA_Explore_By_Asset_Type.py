"""RWA.xyz hub index: Stablecoins, US Treasuries, and Tokenized Stocks previews."""

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
from streamlit_rwa_explore_static import (
    get_rwa_explore_iframe_payloads,
    render_rwa_explore_body_iframe,
)


def main() -> None:
    configure_subpage(
        page_title="Explore by Asset Type — Digital Assets Dashboard",
        active="explore_asset",
        style_kind="rwa_explore_at",
    )
    related = related_chips_html(
        (_streamlit_page_href("rwa_global"), "RWA market overview"),
        (_streamlit_page_href("explore_participant"), "Explore by participant"),
        (_streamlit_page_href("stablecoins"), "Stablecoins"),
        (_streamlit_page_href("treasuries"), "U.S. Treasuries"),
        ("/?jd_scroll=onchain", "Home on-chain preview"),
    )

    payloads = get_rwa_explore_iframe_payloads("explore_asset")
    render_rwa_explore_body_iframe(
        kind="explore_asset",
        payloads=payloads,
        related_chips=related,
        back_href=_streamlit_page_href("rwa_global"),
        back_label="← RWA Global Market Overview",
    )

    render_subpage_footer(label="Explore by Asset Type")


main()
