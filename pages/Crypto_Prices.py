"""Full crypto prices page (top 50 snapshot)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from datetime import datetime, timezone

import streamlit as st

from crypto_prices.widgets import show_crypto_prices_page
from news_feeds import render_subpage_top_bar
from streamlit_site_parity import home_zone_close, home_zone_open, inject_site_styles


def main() -> None:
    st.set_page_config(
        page_title="Crypto Prices — Digital Assets Dashboard",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    render_subpage_top_bar(active="crypto")
    inject_site_styles(include_static=False)

    if st.button("← Back to home · Crypto preview", key="top_home_crypto"):
        st.switch_page("streamlit_app.py")

    st.markdown('<div class="page-shell site-experience">', unsafe_allow_html=True)
    home_zone_open(
        section_id="crypto-full",
        badge="CRY",
        title="Crypto Prices — Top 50 Snapshot",
        subtitle=(
            "Top-line crypto market snapshot with a KPI strip and searchable top-50 spot-price table. "
            "Sources: CoinPaprika (total cap), CoinGecko (top 50; CoinCap fallback)."
        ),
        zone_class="home-zone--crypto",
        related_chips=(
            '<div class="home-related-chips" aria-label="Related pages">'
            '<span class="home-related-chips__label">Related</span>'
            '<a class="home-chip" href="/?jd_scroll=crypto">Home crypto preview</a>'
            '<a class="home-chip" href="/US_Crypto_ETPs">U.S. ETPs</a>'
            '<a class="home-chip" href="/RWA_Stablecoins">Stablecoins</a>'
            '<a class="home-chip" href="/?jd_scroll=news">News Hub</a>'
            "</div>"
        ),
    )
    show_crypto_prices_page(zone_layout=True)
    home_zone_close()
    st.markdown("</div>", unsafe_allow_html=True)

    st.caption(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC · CoinGecko/CoinCap · CoinPaprika")


if __name__ == "__main__":
    main()
