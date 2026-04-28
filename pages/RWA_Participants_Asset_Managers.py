"""RWA.xyz Participants — Asset Managers: overview KPIs + Distributed tab table."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from datetime import datetime, timezone

import streamlit as st

from home_layout import ETP_FULLPAGE_AUM_LINE_CSS, STREAMLIT_TABLE_UNIFY_CSS, section_label_teal
from price_ticker import show_price_ticker


def _monthly_review_note_html(*, year: int = 2026, month: int = 4) -> str:
    last_review = datetime(year, month, 1, tzinfo=timezone.utc)
    label = last_review.strftime("%b %Y")
    age_days = max(0, (datetime.now(timezone.utc) - last_review).days)
    if age_days > 31:
        return (
            '<p style="margin:0.1rem 0 0.55rem 0;color:#b91c1c;font-size:0.78rem;">'
            f"<strong>Review due:</strong> last reviewed {label} ({age_days} days ago)."
            "</p>"
        )
    return (
        '<p style="margin:0.1rem 0 0.55rem 0;color:#3E6A7A;font-size:0.78rem;">'
        f"Reviewed monthly · Last reviewed: {label}</p>"
    )


def _participants_asset_managers_takeaway_html() -> str:
    return (
        '<div style="border:1px solid #C7D8E8;border-radius:10px;padding:0.75rem 0.95rem;'
        'margin:0.1rem 0 0.55rem;background:#ffffff;box-shadow:0 1px 3px rgba(15,23,42,0.06);">'
        '<p style="margin:0 0 0.28rem 0;font-size:0.9rem;font-weight:700;color:#021D41;">Key Observation</p>'
        '<ul style="margin:0.1rem 0 0 1.05rem;padding:0;color:#1F4C67;font-size:0.9rem;line-height:1.4;">'
        '<li><strong>Asset-manager participation remains top-heavy:</strong> a smaller set of large managers still '
        'accounts for most distributed value and often anchors category momentum.</li>'
        '<li><strong>Share shifts are usually distribution-sensitive:</strong> advisor access, custody confidence, and '
        'repeat issuance cadence are key drivers of manager-level position changes.</li>'
        "</ul></div>"
        + _monthly_review_note_html()
    )


def main() -> None:
    from rwa_league.widgets import show_rwa_participants_asset_managers_widget
    from news_feeds import (
        app_shared_layout_css,
        article_styles_markdown,
        render_subpage_sidebar,
        render_subpage_top_bar,
    )

    st.set_page_config(
        page_title="Participants — Asset Managers — JPM Digital",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_subpage_top_bar()
    if st.button("← Back", key="top_back_rwa_participants_asset_managers"):
        st.switch_page("pages/RWA_Explore_By_Market_Participant.py")
    st.markdown(article_styles_markdown(), unsafe_allow_html=True)
    st.markdown(app_shared_layout_css(), unsafe_allow_html=True)
    st.markdown(STREAMLIT_TABLE_UNIFY_CSS + ETP_FULLPAGE_AUM_LINE_CSS, unsafe_allow_html=True)
    show_price_ticker()
    render_subpage_sidebar(key_prefix="rwa_participants_asset_managers", current="rwa_participants_asset_managers")

    st.markdown(section_label_teal("Participants — Asset Managers", placement="first"), unsafe_allow_html=True)
    st.markdown(
        '<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">This page mirrors the '
        '<a href="https://app.rwa.xyz/asset-managers">RWA.xyz Asset Managers</a> view, including manager-level '
        "headline metrics and the <strong>Distributed</strong> table. Top-line <strong>30D</strong> % changes and "
        "per-manager columns match the live page.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(_participants_asset_managers_takeaway_html(), unsafe_allow_html=True)
    st.divider()

    show_rwa_participants_asset_managers_widget(home_preview=False, full_page_header=True)

    st.divider()
    st.caption(
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "RWA.xyz data · Cached up to one hour · Use **Refresh all data** on the home page to reload."
    )


main()
