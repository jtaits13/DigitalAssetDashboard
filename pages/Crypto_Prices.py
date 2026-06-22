"""Full crypto prices page (top 50 snapshot)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import streamlit as st

from crypto_prices.widgets import show_crypto_prices_page
from streamlit_site_parity import (
    close_subpage_layout,
    configure_subpage,
    inner_page_zone_close,
    inner_page_zone_open,
    open_subpage_layout,
    related_chips_html,
    render_subpage_back_link,
    render_subpage_footer,
)


def main() -> None:
    configure_subpage(
        page_title="Crypto Prices — Digital Assets Dashboard",
        active="crypto",
        style_kind="crypto",
    )
    render_subpage_back_link(
        href="/?jd_scroll=crypto",
        label="← Back to home · Crypto preview",
    )
    open_subpage_layout(style_kind="crypto", shell_class="etp-mock-shell")
    inner_page_zone_open(
        section_id="crypto-full",
        badge="CRY",
        title="Crypto Prices — Top 50 Snapshot",
        subtitle_html=(
            "Top-line crypto market snapshot with a KPI strip, a 12-month total market-cap trend chart, category "
            "filters, and a searchable <strong>top 50</strong> spot-price table. Sources: "
            '<a href="https://coinpaprika.com/" target="_blank" rel="noopener noreferrer">CoinPaprika</a> '
            "(total cap), "
            '<a href="https://www.coingecko.com/" target="_blank" rel="noopener noreferrer">CoinGecko</a> '
            "(top 50; CoinCap fallback)."
        ),
        zone_classes="zone--crypto home-zone home-zone--crypto etp-mock-zone",
        related_chips=related_chips_html(
            ("/?jd_scroll=crypto", "Home crypto preview"),
            ("/US_Crypto_ETPs", "U.S. ETPs"),
            ("/?jd_scroll=news", "News Hub"),
        ),
        body_class="inner-rich-zone__body etp-mock-zone__body",
    )
    show_crypto_prices_page(zone_layout=True)
    inner_page_zone_close()
    close_subpage_layout(
        back_href="/?jd_scroll=crypto",
        back_label="← Back to home · Crypto preview",
    )
    render_subpage_footer(label="Crypto Prices")


if __name__ == "__main__":
    main()
