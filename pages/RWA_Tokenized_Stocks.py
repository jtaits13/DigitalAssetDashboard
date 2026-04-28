"""Full RWA.xyz Tokenized Stocks page: overview KPIs + Distributed · Platforms league."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from datetime import datetime, timezone

import streamlit as st

from home_layout import ETP_FULLPAGE_AUM_LINE_CSS, STREAMLIT_TABLE_UNIFY_CSS, section_label_teal
from news_feeds import (
    app_shared_layout_css,
    article_styles_markdown,
    render_subpage_sidebar,
    render_subpage_top_bar,
)
from price_ticker import show_price_ticker
from rwa_league.widgets import TOKENIZED_STOCKS_RWA_CAPTION, show_rwa_tokenized_stocks_widget
from rwa_league.widgets import load_rwa_tokenized_stocks_cached


def _tokenized_stocks_takeaway_html() -> str:
    nets, plats, _kpis, _err = load_rwa_tokenized_stocks_cached()
    if not plats:
        bullet = "Live tokenized-stocks platform snapshot is unavailable right now."
    else:
        ranked_p = sorted(plats, key=lambda r: float(r.total_value_usd), reverse=True)
        leader = ranked_p[0]
        total_b = sum(float(r.total_value_usd) for r in ranked_p) / 1e9
        top3_share = sum(float(r.market_share_raw) for r in ranked_p[:3]) * 100.0
        if nets:
            leader_n = max(nets, key=lambda r: float(r.total_value_usd))
            bullet = (
                f"Live snapshot: tokenized-stocks distributed value is <strong>${total_b:.2f}B</strong>; "
                f"the top 3 platforms account for <strong>{top3_share:.1f}%</strong> of value, and "
                f"<strong>{leader_n.network}</strong> currently leads on the network view."
            )
        else:
            bullet = (
                f"Live snapshot: tokenized-stocks distributed value is <strong>${total_b:.2f}B</strong>; "
                f"the top 3 platforms account for <strong>{top3_share:.1f}%</strong> of value."
            )
    return (
        '<div style="border:1px solid #C7D8E8;border-radius:10px;padding:0.75rem 0.95rem;'
        'margin:0.1rem 0 0.55rem;background:#ffffff;box-shadow:0 1px 3px rgba(15,23,42,0.06);">'
        '<p style="margin:0 0 0.28rem 0;font-size:0.9rem;font-weight:700;color:#021D41;">Key Observation</p>'
        '<ul style="margin:0.1rem 0 0 1.05rem;padding:0;color:#1F4C67;font-size:0.9rem;line-height:1.4;">'
        f"<li>{bullet}</li>"
        "</ul></div>"
    )


def main() -> None:
    st.set_page_config(
        page_title="Tokenized Stocks — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Back", key="top_back_rwa_tokenized_stocks"):
        st.switch_page("pages/RWA_Explore_By_Asset_Type.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_tokenized_stocks", current="rwa_tokenized_stocks")

    st.markdown(section_label_teal("Tokenized Stocks", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">Tokenized public equities: overview <strong>30-day (30D)</strong> % changes and '
        "<strong>Distributed Value</strong> breakdowns (levels) by platform and network. Full "
        "<strong>Distributed</strong> · <strong>Platforms</strong> league with search — "
        '<a href="https://app.rwa.xyz/stocks">RWA.xyz Tokenized Stocks</a>.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(_tokenized_stocks_takeaway_html(), unsafe_allow_html=True)
    st.divider()

    show_rwa_tokenized_stocks_widget(home_preview=False, full_page_header=True)

    st.divider()
    st.caption(TOKENIZED_STOCKS_RWA_CAPTION)
    st.caption(
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "RWA.xyz embed · Cached up to one hour · Use **Refresh all data** on the home page to reload."
    )


main()
