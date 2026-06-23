"""Back-compat shim — TMMF layout lives in ``streamlit_site_parity``."""

from streamlit_site_parity import (
    STREAMLIT_TMMF_SUBPAGE_CSS,
    TMMF_ZONE_CARD_KEY,
    tmmf_github_zone_header_html,
    tmmf_single_block_header_html,
)

__all__ = (
    "STREAMLIT_TMMF_SUBPAGE_CSS",
    "TMMF_ZONE_CARD_KEY",
    "tmmf_github_zone_header_html",
    "tmmf_single_block_header_html",
)
