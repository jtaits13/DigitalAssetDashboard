"""Home page widget: RWA.xyz Networks league table (embedded page data)."""

from __future__ import annotations

from html import escape

import streamlit as st

from home_layout import STREAMLIT_TABLE_UNIFY_CSS
from rwa_league.client import (
    RwaGlobalKpi,
    RwaNetworkLeagueRow,
    fetch_rwa_home_data,
)
from rwa_league.dataframe_table import (
    build_rwa_dataframe,
    filter_rows_by_network,
    style_rwa_dataframe,
)

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
.rwa-kpi-line {
    font-size: 0.9rem;
    font-weight: 600;
    color: #0f172a;
    margin: 0.35rem 0 0.65rem 0;
    line-height: 1.45;
}
.rwa-kpi-line .rwa-kpi-item {
    display: inline-block;
    margin-right: 0.35rem;
}
</style>
"""

RWA_DATA_SOURCE_CAPTION = (
    "Source: [RWA.xyz](https://app.rwa.xyz/) homepage embedded data "
    "(Global Market Overview + Networks · All; not the public API)."
)


def _format_kpi_delta(pct: float | None) -> str | None:
    if pct is None:
        return None
    # payload is fractional change (e.g. 0.075 → +7.50%)
    return f"{pct * 100:+.2f}% (30d)"


def _render_rwa_global_overview(kpis: list[RwaGlobalKpi]) -> None:
    """One block under the heading, similar weight to the ETP total AUM line."""
    if not kpis:
        return
    parts: list[str] = []
    for k in kpis:
        delta = _format_kpi_delta(k.delta_30d_pct)
        extra = f" <span class='rwa-kpi-delta'>({escape(delta)})</span>" if delta else ""
        parts.append(
            f"<span class='rwa-kpi-item'><strong>{escape(k.label)}:</strong> "
            f"{escape(k.value_display)}{extra}</span>"
        )
    inner = " <span style='color:#94a3b8'>·</span> ".join(parts)
    st.markdown(
        f'<p class="rwa-kpi-line">{inner}</p>',
        unsafe_allow_html=True,
    )
_SORT = "\u2195"


def rwa_table_height(num_rows: int, *, max_h: int = 520) -> int:
    header = 38
    row_h = 35
    return min(max_h, header + row_h * max(1, num_rows))


def _show_rwa_dataframe(df, *, height: int) -> None:
    """Render styled dataframe (sortable Glide table)."""
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
                f"RWA Page {_SORT}",
                display_text="↗",
                validate=r"^https://",
                width="small",
                help="Open this network on RWA.xyz",
            ),
            "RWA Count": st.column_config.NumberColumn(
                f"RWA Count {_SORT}",
                format="%.0f",
                help="Ascending: lowest first · Descending: highest first",
            ),
            "Total Value": st.column_config.NumberColumn(
                f"Total Value {_SORT}",
                format=None,
                width=140,
                help="Ascending: smallest USD first",
            ),
            "7D Δ value": st.column_config.NumberColumn(
                f"7D Δ value {_SORT}",
                format=None,
                width=100,
                help="7-day change in total value (%) · Ascending: lowest first",
            ),
            "Market Share": st.column_config.NumberColumn(
                f"Market Share {_SORT}",
                format=None,
                help="Current network share (%)",
            ),
        },
    )


@st.cache_data(ttl=3600, show_spinner=False)
def load_rwa_league_cached(*, _rwa_schema: int = 2) -> tuple[list[RwaNetworkLeagueRow], list[RwaGlobalKpi], str | None]:
    """Bump ``_rwa_schema`` when homepage payload shape changes."""
    _ = _rwa_schema
    return fetch_rwa_home_data()


def clear_rwa_league_cache() -> None:
    load_rwa_league_cached.clear()


def show_rwa_league_widget(
    *,
    home_preview: bool = False,
    preview_rows: int = 8,
) -> None:
    """
    RWA.xyz networks league table. ``home_preview=True`` shows only the top N rows (no search)
    with a link to the full page — similar to a CoinDesk section teaser.
    """
    st.markdown(WIDGET_CSS + STREAMLIT_TABLE_UNIFY_CSS, unsafe_allow_html=True)
    rows, kpis, err = load_rwa_league_cached()

    if err and not rows:
        st.markdown(
            '<div class="rwa-league-shell">'
            '<h2 class="home-main-heading">RWA League Table · Networks (All)</h2></div>',
            unsafe_allow_html=True,
        )
        st.warning(escape(err))
        _render_rwa_global_overview(kpis)
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

    _render_rwa_global_overview(kpis)

    working = list(rows)
    if home_preview:
        n = max(1, min(preview_rows, len(working)))
        working = working[:n]
        st.caption(
            f"Preview: top **{n}** networks from the league embed. "
            "Open the full page to search and see every network."
        )
    else:
        q = st.text_input(
            "Search network",
            "",
            key="rwa_search_home",
            placeholder="Filter by network name…",
        )
        working = filter_rows_by_network(rows, q)
        if q.strip():
            st.caption(
                f"Showing {len(working)} of {len(rows)} networks matching “{escape(q.strip())}”."
            )
        else:
            st.caption(f"Showing all {len(working)} networks.")

    df = build_rwa_dataframe(working)
    _show_rwa_dataframe(df, height=rwa_table_height(len(df)))
    st.caption(RWA_DATA_SOURCE_CAPTION)

    if home_preview and st.button(
        "Open full RWA league table",
        key="see_full_rwa_league",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/RWA_League.py")
