"""Home page widget: RWA.xyz Networks league table (embedded page data)."""

from __future__ import annotations

from html import escape

import streamlit as st

from home_layout import STREAMLIT_TABLE_UNIFY_CSS
from rwa_league.client import (
    RwaGlobalKpi,
    RwaNetworkLeagueRow,
    RwaStablecoinPlatformRow,
    fetch_rwa_home_data,
    fetch_rwa_stablecoins_data,
)
from rwa_league.dataframe_table import (
    build_rwa_dataframe,
    build_stablecoin_platform_dataframe,
    filter_rows_by_network,
    filter_stablecoin_platform_rows,
    style_rwa_dataframe,
    style_stablecoin_platform_dataframe,
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
.rwa-kpi-wrap {
    margin: 0.45rem 0 0.85rem 0;
}
.rwa-kpi-window-note {
    font-size: 6px;
    font-weight: 400;
    color: #94a3b8;
    margin: 0 0 0.5rem 0;
    line-height: 1.35;
}
.rwa-kpi-row {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.65rem 0.5rem;
    padding: 0.5rem 0 0.85rem 0;
    border-bottom: 1px solid #e2e8f0;
}
.rwa-kpi-cell {
    flex: 1 1 0;
    min-width: 8.5rem;
    max-width: 100%;
    text-align: center;
}
.rwa-kpi-label {
    display: block;
    font-size: 0.88rem;
    font-weight: 600;
    color: #334155;
    margin-bottom: 0.35rem;
    line-height: 1.3;
    letter-spacing: 0.01em;
}
.rwa-kpi-val {
    display: block;
    font-size: 1.05rem;
    font-weight: 700;
    color: #1E7C99;
    line-height: 1.2;
}
.rwa-kpi-delta {
    display: block;
    font-size: 0.82rem;
    font-weight: 600;
    margin-top: 0.2rem;
    line-height: 1.2;
}
.rwa-kpi-delta.up {
    color: #059669;
}
.rwa-kpi-delta.down {
    color: #dc2626;
}
.rwa-kpi-delta.neutral {
    color: #64748b;
}
</style>
"""

RWA_DATA_SOURCE_CAPTION = (
    "Source: [RWA.xyz](https://app.rwa.xyz/) homepage embedded data "
    "(Global Market Overview + Networks league **Distributed** tab; not the public API)."
)

STABLECOIN_RWA_CAPTION = (
    "Source: [RWA.xyz Stablecoins](https://app.rwa.xyz/stablecoins) embedded overview + "
    "**Platforms** league tab (market cap by issuer platform; not the public API)."
)


def _format_pct_change_30d(pct: float | None) -> tuple[str, str] | None:
    """Return (escaped_html_fragment, css_class) or None if unknown."""
    if pct is None:
        return None
    # payload: fractional change e.g. 0.075 → +7.50%
    s = f"{float(pct) * 100:+.2f}%"
    if float(pct) > 0:
        cls = "up"
    elif float(pct) < 0:
        cls = "down"
    else:
        cls = "neutral"
    return escape(s), cls


def _render_rwa_stablecoin_overview(kpis: list[RwaGlobalKpi]) -> None:
    """Stablecoins page overview: four KPI tiles (30D % change when present)."""
    if not kpis:
        return
    cells = []
    for k in kpis:
        delta_html = ""
        fd = _format_pct_change_30d(k.delta_30d_pct)
        if fd is not None:
            txt, cls = fd
            delta_html = f"<span class='rwa-kpi-delta {cls}'>{txt}</span>"
        cells.append(
            "<div class='rwa-kpi-cell'>"
            f"<span class='rwa-kpi-label'>{escape(k.label)}</span>"
            f"<span class='rwa-kpi-val'>{escape(k.value_display)}</span>"
            f"{delta_html}"
            "</div>"
        )
    row = "<div class='rwa-kpi-row'>" + "".join(cells) + "</div>"
    st.markdown(
        '<div class="rwa-kpi-wrap">'
        "<p class='rwa-kpi-window-note'>"
        "All values in this row match the <strong>Stablecoins</strong> overview on RWA.xyz "
        "(typically <strong>30D</strong> change where shown)."
        "</p>"
        f"{row}"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_rwa_global_overview(kpis: list[RwaGlobalKpi]) -> None:
    """Global Market Overview: five columns; slate titles, teal values, 30D % change (no “30D” suffix)."""
    if not kpis:
        return
    cells = []
    for k in kpis:
        delta_html = ""
        fd = _format_pct_change_30d(k.delta_30d_pct)
        if fd is not None:
            txt, cls = fd
            delta_html = f"<span class='rwa-kpi-delta {cls}'>{txt}</span>"
        cells.append(
            "<div class='rwa-kpi-cell'>"
            f"<span class='rwa-kpi-label'>{escape(k.label)}</span>"
            f"<span class='rwa-kpi-val'>{escape(k.value_display)}</span>"
            f"{delta_html}"
            "</div>"
        )
    row = "<div class='rwa-kpi-row'>" + "".join(cells) + "</div>"
    st.markdown(
        '<div class="rwa-kpi-wrap">'
        "<p class='rwa-kpi-window-note'>"
        "All values in this row are <strong>30-day (30D)</strong> Global Market data points from RWA.xyz."
        "</p>"
        f"{row}"
        "</div>",
        unsafe_allow_html=True,
    )
_SORT = "\u2195"


def rwa_table_height(num_rows: int, *, max_h: int = 520) -> int:
    header = 38
    row_h = 35
    return min(max_h, header + row_h * max(1, num_rows))


def _show_stablecoin_platform_dataframe(df, *, height: int) -> None:
    st.dataframe(
        style_stablecoin_platform_dataframe(df),
        use_container_width=True,
        height=height,
        hide_index=True,
        column_order=[
            "#",
            "Platform",
            "Link",
            "Stablecoins",
            "Total Value",
            "7D Δ value",
            "Market Share",
            "30D Δ share",
        ],
        column_config={
            "#": st.column_config.NumberColumn(
                f"# {_SORT}",
                format="%.0f",
                help="Rank on RWA.xyz Platforms tab",
            ),
            "Platform": st.column_config.TextColumn(
                f"Platform {_SORT}",
                width="medium",
                help="Issuance platform (e.g. Tether Holdings)",
            ),
            "Link": st.column_config.LinkColumn(
                f"RWA Page {_SORT}",
                display_text="��",
                validate=r"^https://",
                width="small",
                help="Open this platform on RWA.xyz",
            ),
            "Stablecoins": st.column_config.NumberColumn(
                f"Stablecoins {_SORT}",
                format="%.0f",
                help="Number of tracked stablecoin assets for this platform",
            ),
            "Total Value": st.column_config.NumberColumn(
                f"Market cap {_SORT}",
                format=None,
                width=140,
                help="Aggregate circulating market cap (USD) for this platform’s stablecoins",
            ),
            "7D Δ value": st.column_config.NumberColumn(
                f"7D Δ cap {_SORT}",
                format=None,
                width=100,
                help="7-day change in aggregate market cap (%)",
            ),
            "Market Share": st.column_config.NumberColumn(
                f"Share {_SORT}",
                format=None,
                help="Share of total stablecoin market cap (%)",
            ),
            "30D Δ share": st.column_config.NumberColumn(
                f"30D Δ share {_SORT}",
                format=None,
                width=100,
                help="Change in market share vs 30 days ago (pts)",
            ),
        },
    )


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
            "30D Δ share",
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
            "30D Δ share": st.column_config.NumberColumn(
                f"30D Δ share {_SORT}",
                format=None,
                width=100,
                help="Change in market share vs 30 days ago (percentage points; same as Stablecoins table)",
            ),
        },
    )


@st.cache_data(ttl=3600, show_spinner=False)
def load_rwa_league_cached(*, _rwa_schema: int = 4) -> tuple[list[RwaNetworkLeagueRow], list[RwaGlobalKpi], str | None]:
    """Bump ``_rwa_schema`` when homepage payload shape changes."""
    _ = _rwa_schema
    return fetch_rwa_home_data()


@st.cache_data(ttl=3600, show_spinner=False)
def load_rwa_stablecoins_cached(
    *, _stable_schema: int = 1
) -> tuple[list[RwaStablecoinPlatformRow], list[RwaGlobalKpi], str | None]:
    """Bump ``_stable_schema`` when ``/stablecoins`` embed shape changes."""
    _ = _stable_schema
    return fetch_rwa_stablecoins_data()


def clear_rwa_league_cache() -> None:
    load_rwa_league_cached.clear()
    load_rwa_stablecoins_cached.clear()


def show_rwa_stablecoins_widget(
    *,
    home_preview: bool = True,
    preview_rows: int = 8,
) -> None:
    """
    RWA.xyz Stablecoins embed: four overview KPIs + **Platforms** league.

    ``home_preview=True`` (under RWA Data on the hub): short preview + link to full page.
    ``home_preview=False``: full searchable table (use from ``pages/RWA_Stablecoins.py``).
    """
    if home_preview:
        st.divider()
        st.markdown(
            '<h3 class="home-main-heading" style="margin-top:0.35rem;font-size:1.05rem;">'
            "Stablecoins (RWA.xyz)</h3>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Overview and **Platforms** league from [app.rwa.xyz/stablecoins](https://app.rwa.xyz/stablecoins) "
            "(platform **market cap**, not network Distributed Value)."
        )
    else:
        st.markdown(WIDGET_CSS + STREAMLIT_TABLE_UNIFY_CSS, unsafe_allow_html=True)
        st.markdown(
            '<div class="rwa-league-shell">'
            '<h2 class="home-main-heading">Stablecoins</h2>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Full **Platforms** league with search. Data from the "
            "[RWA.xyz Stablecoins](https://app.rwa.xyz/stablecoins) page embed "
            "(aggregate circulating **market cap** per issuance platform)."
        )

    rows_sc, kpis_sc, err_sc = load_rwa_stablecoins_cached()

    if err_sc and not rows_sc:
        st.warning(escape(err_sc))
        _render_rwa_stablecoin_overview(kpis_sc)
        st.link_button(
            "Open Stablecoins on RWA.xyz",
            "https://app.rwa.xyz/stablecoins",
            use_container_width=True,
            key="rwa_sc_rwa_link_err_home" if home_preview else "rwa_sc_rwa_link_err_full",
        )
        return

    if not rows_sc:
        st.info("No platform rows returned for Stablecoins.")
        _render_rwa_stablecoin_overview(kpis_sc)
        st.link_button(
            "Open Stablecoins on RWA.xyz",
            "https://app.rwa.xyz/stablecoins",
            use_container_width=True,
            key="rwa_sc_rwa_link_empty_home" if home_preview else "rwa_sc_rwa_link_empty_full",
        )
        return

    _render_rwa_stablecoin_overview(kpis_sc)

    if home_preview:
        n = max(1, min(preview_rows, len(rows_sc)))
        working = rows_sc[:n]
        st.caption(
            f"Preview: top **{n}** platforms by market cap (**Platforms** tab). "
            "Other tabs on RWA.xyz: Networks, Managers, Jurisdiction."
        )
        table_h = rwa_table_height(len(working))
    else:
        q = st.text_input(
            "Search platform",
            "",
            key="rwa_stablecoin_search_full",
            placeholder="Filter by platform name…",
        )
        working = filter_stablecoin_platform_rows(rows_sc, q)
        if q.strip():
            st.caption(
                f"Showing {len(working)} of {len(rows_sc)} platforms matching “{escape(q.strip())}”."
            )
        else:
            st.caption(f"Showing all {len(working)} platforms (Stablecoins · Platforms tab).")
        table_h = rwa_table_height(len(working), max_h=900)

    df_sc = build_stablecoin_platform_dataframe(working)
    _show_stablecoin_platform_dataframe(df_sc, height=table_h)
    st.caption(STABLECOIN_RWA_CAPTION)

    if home_preview:
        if st.button(
            "Open full Stablecoins table",
            key="see_full_rwa_stablecoins",
            use_container_width=True,
            type="primary",
        ):
            st.switch_page("pages/RWA_Stablecoins.py")
        st.link_button(
            "Open Stablecoins on RWA.xyz",
            "https://app.rwa.xyz/stablecoins",
            use_container_width=True,
            key="rwa_sc_rwa_link_home",
        )
    else:
        st.link_button(
            "Open Stablecoins on RWA.xyz",
            "https://app.rwa.xyz/stablecoins",
            use_container_width=True,
            key="rwa_sc_rwa_link_full",
        )


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
            '<h2 class="home-main-heading">RWA Data</h2></div>',
            unsafe_allow_html=True,
        )
        st.warning(escape(err))
        _render_rwa_global_overview(kpis)
        if home_preview:
            show_rwa_stablecoins_widget(home_preview=True, preview_rows=preview_rows)
        return

    if not rows:
        st.info("No network rows returned.")
        return

    st.markdown(
        '<div class="rwa-league-shell">'
        '<h2 class="home-main-heading">RWA Data</h2>'
        "</div>",
        unsafe_allow_html=True,
    )

    _render_rwa_global_overview(kpis)

    working = list(rows)
    if home_preview:
        n = max(1, min(preview_rows, len(working)))
        working = working[:n]
        st.caption(
            f"Preview: top **{n}** networks by Distributed Value from the league embed. "
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
            st.caption(f"Showing all {len(working)} networks (Distributed Value only).")

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

    if home_preview:
        show_rwa_stablecoins_widget(home_preview=True, preview_rows=preview_rows)
