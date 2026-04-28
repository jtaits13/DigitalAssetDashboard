"""Full RWA.xyz US Treasuries page: overview KPIs + Distributed · Networks league (Distributed Value)."""

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


def _treasuries_takeaway_html() -> str:
    from rwa_league.widgets import load_rwa_treasuries_cached

    nets, plats, _kpis, _err = load_rwa_treasuries_cached()
    if not nets:
        bullet = "Live Treasuries network snapshot is unavailable right now."
    else:
        ranked_n = sorted(nets, key=lambda r: float(r.total_value_usd), reverse=True)
        leader_n = ranked_n[0]
        total_b = sum(float(r.total_value_usd) for r in ranked_n) / 1e9
        leader_share = float(leader_n.market_share_raw) * 100.0
        if plats:
            leader_p = max(plats, key=lambda r: float(r.total_value_usd))
            bullet = (
                f"Live snapshot: distributed Treasury value is <strong>${total_b:.1f}B</strong>; "
                f"<strong>{leader_n.network}</strong> leads networks at <strong>{leader_share:.1f}%</strong> share, "
                f"while <strong>{leader_p.platform}</strong> is the top platform by distributed value."
            )
        else:
            bullet = (
                f"Live snapshot: distributed Treasury value is <strong>${total_b:.1f}B</strong>; "
                f"<strong>{leader_n.network}</strong> leads networks at <strong>{leader_share:.1f}%</strong> share."
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
    from rwa_league.widgets import TREASURY_RWA_CAPTION, show_rwa_treasuries_widget

    st.set_page_config(
        page_title="US Treasuries — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Back", key="top_back_rwa_treasuries"):
        st.switch_page("pages/RWA_Explore_By_Asset_Type.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_us_treasuries", current="rwa_treasuries")

    st.markdown(section_label_teal("US Treasuries", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">Tokenized U.S. Treasuries: overview <strong>30-day (30D)</strong> % changes from '
        "<strong>RWA.xyz</strong> and <strong>Distributed</strong> leagues with search: <strong>Networks</strong> "
        "then <strong>Platforms</strong> (tokenized Treasury by issuer). <strong>Distributed Value</strong> columns "
        'are levels — <a href="https://app.rwa.xyz/treasuries">RWA.xyz US Treasuries</a>.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(_treasuries_takeaway_html(), unsafe_allow_html=True)
    st.divider()

    show_rwa_treasuries_widget(home_preview=False, full_page_header=True)

    st.divider()
    st.caption(TREASURY_RWA_CAPTION)
    st.caption(
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "RWA.xyz embed · Cached up to one hour · Use **Refresh all data** on the home page to reload."
    )


main()
