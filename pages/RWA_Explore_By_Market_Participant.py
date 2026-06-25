"""RWA.xyz hub index: Networks, Platforms, and Asset Managers previews."""

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
        page_title="Explore by Market Participant — Digital Assets Dashboard",
        active="explore_participant",
        style_kind="rwa_explore_mp",
    )
    related = related_chips_html(
        (_streamlit_page_href("rwa_global"), "RWA market overview"),
        (_streamlit_page_href("explore_asset"), "Explore by asset type"),
        (_streamlit_page_href("networks"), "Networks"),
        (_streamlit_page_href("platforms"), "Platforms"),
        (_streamlit_page_href("asset_managers"), "Asset Managers"),
        ("/?jd_scroll=onchain", "Home on-chain preview"),
    )

    payloads = get_rwa_explore_iframe_payloads("explore_participant")
    render_rwa_explore_body_iframe(
        kind="explore_participant",
        payloads=payloads,
        related_chips=related,
        back_href=_streamlit_page_href("rwa_global"),
        back_label="← RWA Global Market Overview",
    )

    render_subpage_footer(label="Explore by Market Participant")


main()
