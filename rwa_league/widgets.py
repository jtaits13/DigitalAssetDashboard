"""Home page widget: RWA.xyz Networks league table (embedded page data)."""

from __future__ import annotations

from html import escape

import streamlit as st

from home_layout import STREAMLIT_TABLE_UNIFY_CSS
from rwa_league.client import RwaNetworkLeagueRow, fetch_rwa_network_league
from rwa_league.dataframe_table import build_rwa_dataframe, style_rwa_dataframe

WIDGET_CSS = """
<style>
.rwa-league-shell {
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.75rem 1rem 1rem 1rem;
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.rwa-league-shell h2.home-main-heading {
    margin-bottom: 0.35rem;
}
</style>
"""

_SORT = "\u2195"


def rwa_table_height(num_rows: int, *, max_h: int = 520) -> int:
    header = 38
    row_h = 35
    return min(max_h, header + row_h * max(1, num_rows))


def _show_rwa_dataframe(df, *, height: int) -> None:
    st.dataframe(
        style_rwa_dataframe(df),
        use_container_width=True,
        height=height,
        hide_index=True,
        column_order=[
            "#",
            "Network",
            "Link",
            "RWA Count",
            "Total Value",
            "7D Δ value",
            "Market Share",
        ],
        column_config={
            "#": st.column_config.NumberColumn(
                f"# {_SORT}",
                format="%.0f",
                help="Ascending: lowest rank first · Descending: highest rank first",
            ),
            "Network": st.column_config.TextColumn(
                f"Network {_SORT}",
                width="medium",
                help="Ascending: A→Z · Descending: Z→A",
            ),
            "Link": st.column_config.LinkColumn(
                f"Link {_SORT}",
                display_text="↗",
                validate=r"^https://",
                width="small",
                help="Open network on RWA.xyz",
            ),
            "RWA Count": st.column_config.NumberColumn(
                f"RWA Count {_SORT}",
                format="%.0f",
                help="Ascending: lowest first · Descending: highest first",
            ),
            "Total Value": st.column_config.NumberColumn(
                f"Total Value {_SORT}",
                format=None,
                help="Ascending: smallest USD first",
            ),
            "7D Δ value": st.column_config.NumberColumn(
                f"7D Δ value {_SORT}",
                format=None,
                help="7-day change in total value (%) · Ascending: lowest first",
            ),
            "Market Share": st.column_config.NumberColumn(
                f"Market Share {_SORT}",
                format="%.2f%%",
                help="Ascending: lowest first · Descending: highest first",
            ),
        },
    )


@st.cache_data(ttl=3600, show_spinner=False)
def load_rwa_league_cached() -> tuple[list[RwaNetworkLeagueRow], str | None]:
    return fetch_rwa_network_league()


def clear_rwa_league_cache() -> None:
    load_rwa_league_cached.clear()


def show_rwa_league_widget() -> None:
    st.markdown(WIDGET_CSS + STREAMLIT_TABLE_UNIFY_CSS, unsafe_allow_html=True)
    rows, err = load_rwa_league_cached()

    if err and not rows:
        st.markdown(
            '<div class="rwa-league-shell">'
            '<h2 class="home-main-heading">RWA League Table · Networks (All)</h2></div>',
            unsafe_allow_html=True,
        )
        st.warning(escape(err))
        return

    if not rows:
        st.info("No network rows returned.")
        return

    st.markdown(
        '<div class="rwa-league-shell">'
        '<h2 class="home-main-heading">RWA League Table · Networks (All)</h2>'
        "</div>",
        unsafe_allow_html=True,
    )

    df = build_rwa_dataframe(rows)
    _show_rwa_dataframe(df, height=rwa_table_height(len(df)))
