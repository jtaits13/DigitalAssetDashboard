"""Full U.S. crypto ETP list (same data as home widget)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from crypto_etps.widgets import get_etp_user_agent_from_secrets, resolve_etp_user_agent
from streamlit_site_parity import (
    _streamlit_page_href,
    configure_subpage,
    related_chips_html,
    render_subpage_footer,
)
from streamlit_etps_static import (
    _cached_etp_iframe_payloads,
    render_etps_body_iframe,
)


def main() -> None:
    configure_subpage(
        page_title="U.S. Digital Asset ETPs — Digital Assets Dashboard",
        active="etps",
        style_kind="etp",
    )
    ua = resolve_etp_user_agent(get_etp_user_agent_from_secrets())
    related = related_chips_html(
        ("/?jd_scroll=markets", "Home ETP preview"),
        (_streamlit_page_href("crypto"), "Crypto prices"),
        (_streamlit_page_href("etf_news"), "All ETF/ETP headlines"),
        (_streamlit_page_href("tmmf"), "Tokenized MMFs"),
    )

    payloads = _cached_etp_iframe_payloads(ua)
    render_etps_body_iframe(payloads=payloads, related_chips=related)

    render_subpage_footer(label="U.S. ETPs")


main()
