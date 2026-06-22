"""Tokenized money market funds: KPIs + network/platform aggregates from RWA.xyz fund lists."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import streamlit as st

from home_layout import ETP_FULLPAGE_AUM_LINE_CSS, STREAMLIT_TABLE_UNIFY_CSS
from news_feeds import article_styles_markdown
from rwa_league.mmf import TMMF_INNER_PAGE_SUBTITLE_HTML
from rwa_league.widgets import show_rwa_mmf_widget
from streamlit_site_parity import (
    _streamlit_page_href,
    close_subpage_layout,
    configure_subpage,
    open_subpage_layout,
    related_chips_html,
    render_subpage_back_link,
    render_subpage_footer,
)
from streamlit_tmmf_layout import STREAMLIT_TMMF_SUBPAGE_CSS, tmmf_single_block_header_html


def _mmf_takeaway_html() -> str:
    from key_observations.feeds import load_takeaway_articles
    from rwa_league.mmf import _aggregate_network_rows, collect_tokenized_mmf_assets
    from rwa_league.mmf_takeaways import build_mmf_key_observations_html

    mmfs, err = collect_tokenized_mmf_assets()
    if err or not mmfs:
        return ""
    net_rows = _aggregate_network_rows(mmfs)
    return build_mmf_key_observations_html(mmfs, net_rows, load_takeaway_articles())


def main() -> None:
    configure_subpage(
        page_title="Tokenized Money Market Funds — Digital Assets Dashboard",
        active="tmmf",
        style_kind="tmmf",
    )
    render_subpage_back_link(
        href="/?jd_scroll=tmmf",
        label="← Back to home · TMMF preview",
    )
    open_subpage_layout(style_kind="tmmf", shell_class="etp-mock-shell")
    st.markdown(
        article_styles_markdown()
        + STREAMLIT_TMMF_SUBPAGE_CSS
        + STREAMLIT_TABLE_UNIFY_CSS
        + ETP_FULLPAGE_AUM_LINE_CSS,
        unsafe_allow_html=True,
    )

    _related = related_chips_html(
        ("/?jd_scroll=tmmf", "Home TMMF preview"),
        (_streamlit_page_href("stablecoins"), "Stablecoins"),
        (_streamlit_page_href("etps"), "U.S. ETPs"),
        (_streamlit_page_href("rwa_global"), "RWA market overview"),
    )

    with st.container(border=True):
        st.markdown(
            '<span class="tmmf-single-block" hidden aria-hidden="true"></span>'
            + tmmf_single_block_header_html(
                section_id="tmmf-full",
                badge="MMF",
                title="Tokenized Money Market Funds",
                subtitle_html=TMMF_INNER_PAGE_SUBTITLE_HTML,
            ),
            unsafe_allow_html=True,
        )
        st.markdown(_related, unsafe_allow_html=True)
        show_rwa_mmf_widget(
            home_preview=False,
            full_page_header=True,
            full_page_key_observations_html=_mmf_takeaway_html(),
            flat_streamlit_layout=True,
        )

    close_subpage_layout(
        back_href="/?jd_scroll=tmmf",
        back_label="← Back to home · TMMF preview",
    )
    render_subpage_footer(label="Tokenized Money Market Funds")


main()
