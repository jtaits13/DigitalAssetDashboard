"""Home page widget: RWA.xyz Networks league table (embedded page data)."""

from __future__ import annotations

from html import escape

import streamlit as st

from home_layout import KPI_WINDOW_NOTE_CSS, STREAMLIT_TABLE_UNIFY_CSS
from rwa_league.client import (
    APP_STOCKS,
    APP_TREASURIES,
    RwaGlobalKpi,
    RwaNetworkLeagueRow,
    RwaTokenizedStockNetworkRow,
    RwaStablecoinPlatformRow,
    RwaTokenizedStockPlatformRow,
    RwaTreasuryDistributedNetworkRow,
    RwaTreasuryPlatformRow,
    fetch_rwa_home_data,
    fetch_rwa_stablecoins_data,
    fetch_rwa_tokenized_stocks_data,
    fetch_rwa_treasuries_data,
)
from rwa_league.dataframe_table import (
    build_rwa_dataframe,
    build_tokenized_stock_network_dataframe,
    build_stablecoin_platform_dataframe,
    build_tokenized_stock_platform_dataframe,
    build_us_treasury_network_dataframe,
    build_us_treasury_platform_dataframe,
    filter_rows_by_network,
    filter_tokenized_stock_network_rows,
    filter_stablecoin_platform_rows,
    filter_tokenized_stock_platform_rows,
    filter_treasury_network_rows,
    filter_treasury_platform_rows,
    style_rwa_dataframe,
    style_tokenized_stock_network_dataframe,
    style_stablecoin_platform_dataframe,
    style_tokenized_stock_platform_dataframe,
    style_us_treasury_network_dataframe,
    style_us_treasury_platform_dataframe,
)

WIDGET_CSS = """
<style>
.jd-hub-subsection-head {
    margin: 0.65rem 0 0.5rem 0;
    padding: 0 0 0.45rem 0;
    border-bottom: 1px solid #C7D8E8;
    background: transparent;
    box-shadow: none;
}
.jd-hub-subsection-head h2.home-main-heading,
.jd-hub-subsection-head h2.home-widget-heading {
    margin: 0 !important;
    padding: 0;
}
#jd-rwa-market,
#jd-rwa-stablecoins,
#jd-rwa-treasuries,
#jd-rwa-tokenized-stocks {
    scroll-margin-top: 5.5rem;
}
.rwa-kpi-wrap {
    margin: 0.45rem 0 0.85rem 0;
}
.rwa-kpi-row {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.65rem 0.5rem;
    padding: 0.5rem 0 0.85rem 0;
    border-bottom: 1px solid #C7D8E8;
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
    color: #1F4C67;
    margin-bottom: 0.35rem;
    line-height: 1.3;
    letter-spacing: 0.01em;
}
.rwa-kpi-val {
    display: block;
    font-size: 1.05rem;
    font-weight: 700;
    color: #25809C;
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
    color: #28794E;
}
.rwa-kpi-delta.down {
    color: #dc2626;
}
.rwa-kpi-delta.neutral {
    color: #3E6A7A;
}
</style>
"""

RWA_DATA_SOURCE_CAPTION = (
    "Source: [RWA.xyz](https://app.rwa.xyz/) homepage embedded data "
    "(Global Market Overview + Networks league **Distributed** tab; not the public API). "
    "Overview **% changes** are **30-day (30D)**; **Distributed Value** in the table is a level."
)

STABLECOIN_RWA_CAPTION = (
    "Source: [RWA.xyz Stablecoins](https://app.rwa.xyz/stablecoins) embedded overview + "
    "**Platforms** league tab (market cap by issuer platform; not the public API). "
    "Overview **% changes** are **30-day (30D)**; **market cap** figures are levels."
)

TREASURY_RWA_CAPTION = (
    "Source: [RWA.xyz US Treasuries](https://app.rwa.xyz/treasuries) embedded overview + "
    "**Distributed** · **Networks** league (Distributed Value; not the public API). "
    "Overview **% changes** are **30-day (30D)**; **Distributed Value** is a level."
)

TREASURY_PLATFORM_CAPTION = (
    "Tokenized Treasury league — **Distributed** · **Platforms** tab (issuer totals from **RWA.xyz**). "
    "**Value** totals are levels; **7-day** % change uses this embed’s `value_7d_change` "
    "(RWA.xyz may label similar columns **30D** in the UI)."
)
TOKENIZED_STOCKS_RWA_CAPTION = (
    "Source: [RWA.xyz Tokenized Stocks](https://app.rwa.xyz/stocks) embedded overview + "
    "**Distributed** · **Platforms** league (Distributed Value by platform; not the public API). "
    "Overview **% changes** are **30-day (30D)**; **Distributed Value** in the tables are levels."
)

TREASURIES_RWA_LINK_LABEL = "See US Treasuries on RWA.xyz"
TOKENIZED_STOCKS_RWA_LINK_LABEL = "See Tokenized Stocks on RWA.xyz"


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


def _rwa_kpi_window_note_html(*, overview_title: str) -> str:
    """Legend under RWA overview KPI tiles (same sentence pattern as Global Market)."""
    return (
        "<p class=\"jd-kpi-window-note\">"
        "All % changes in this row are <strong>30-day (30D)</strong> (<strong>RWA.xyz</strong>). "
        f"Headline totals from the <strong>RWA.xyz</strong> <strong>{escape(overview_title)}</strong> overview."
        "</p>"
    )


def _render_rwa_stablecoin_overview(
    kpis: list[RwaGlobalKpi],
    *,
    show_kpi_legend: bool = True,
) -> None:
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
    legend = _rwa_kpi_window_note_html(overview_title="Stablecoins") if show_kpi_legend else ""
    st.markdown(
        '<div class="rwa-kpi-wrap">'
        f"{legend}"
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
        f"{_rwa_kpi_window_note_html(overview_title='Global Market')}"
        f"{row}"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_rwa_treasuries_overview(
    kpis: list[RwaGlobalKpi],
    *,
    overview_title: str = "US Treasuries",
    show_kpi_legend: bool = True,
) -> None:
    """Overview KPI row for US Treasuries or Tokenized Stocks embed (same tile layout as Global Market)."""
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
    legend = _rwa_kpi_window_note_html(overview_title=overview_title) if show_kpi_legend else ""
    st.markdown(
        '<div class="rwa-kpi-wrap">'
        f"{legend}"
        f"{row}"
        "</div>",
        unsafe_allow_html=True,
    )


_SORT = "\u2195"
_LINK_ARROW = "\u2197"  # Northeast arrow for RWA.xyz LinkColumn (Unicode U+2197)
STABLECOINS_RWA_LINK_LABEL = "See Stablecoins on RWA.xyz"
GLOBAL_MARKET_RWA_LINK_LABEL = "See Global Market Overview on RWA.xyz"
GLOBAL_MARKET_RWA_URL = "https://app.rwa.xyz/"


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
                display_text=_LINK_ARROW,
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
                display_text=_LINK_ARROW,
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


def _show_us_treasury_platform_dataframe(df, *, height: int) -> None:
    """Tokenized Treasury league: **Distributed** → **Platforms** (RWA.xyz table layout)."""
    st.dataframe(
        style_us_treasury_platform_dataframe(df),
        use_container_width=True,
        height=height,
        hide_index=True,
        column_order=[
            "#",
            "Platform",
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
                help="Rank on RWA.xyz Distributed · Platforms tab",
            ),
            "Platform": st.column_config.TextColumn(
                f"Platform {_SORT}",
                width="medium",
                help="Issuance platform (e.g. Circle, Ondo)",
            ),
            "Link": st.column_config.LinkColumn(
                f"RWA Page {_SORT}",
                display_text=_LINK_ARROW,
                validate=r"^https://",
                width="small",
                help="Open this platform on RWA.xyz",
            ),
            "RWA Count": st.column_config.NumberColumn(
                f"RWA Count {_SORT}",
                format="%.0f",
                help="Number of tokenized Treasury / RWA assets for this platform",
            ),
            "Total Value": st.column_config.NumberColumn(
                f"Total Value {_SORT}",
                format=None,
                width=140,
                help="Aggregate value (USD) for this platform’s tokenized Treasuries",
            ),
            "7D Δ value": st.column_config.NumberColumn(
                f"7D Δ value {_SORT}",
                format=None,
                width=100,
                help="7-day change in total value (%) — RWA.xyz embed uses 7D; site UI may label % columns differently",
            ),
            "Market Share": st.column_config.NumberColumn(
                f"Market Share {_SORT}",
                format=None,
                help="Share of tokenized Treasury market (%)",
            ),
            "30D Δ share": st.column_config.NumberColumn(
                f"30D Δ share {_SORT}",
                format=None,
                width=100,
                help="Change in market share vs 30 days ago (percentage points)",
            ),
        },
    )


def _show_us_treasury_network_dataframe(df, *, height: int) -> None:
    """US Treasuries **Distributed** · **Networks** table; value column is **Distributed Value**."""
    st.dataframe(
        style_us_treasury_network_dataframe(df),
        use_container_width=True,
        height=height,
        hide_index=True,
        column_order=[
            "#",
            "Network",
            "Link",
            "RWA Count",
            "Distributed Value",
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
                display_text=_LINK_ARROW,
                validate=r"^https://",
                width="small",
                help="Open this network on RWA.xyz",
            ),
            "RWA Count": st.column_config.NumberColumn(
                f"RWA Count {_SORT}",
                format="%.0f",
                help="Ascending: lowest first · Descending: highest first",
            ),
            "Distributed Value": st.column_config.NumberColumn(
                f"Distributed Value {_SORT}",
                format=None,
                width=150,
                help="Tokenized US Treasuries Distributed Value (USD) on this network",
            ),
            "7D Δ value": st.column_config.NumberColumn(
                f"7D Δ value {_SORT}",
                format=None,
                width=100,
                help="7-day change in Distributed Value (%) · Ascending: lowest first",
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
                help="Change in market share vs 30 days ago (percentage points)",
            ),
        },
    )


def _show_tokenized_stock_platform_dataframe(df, *, height: int) -> None:
    """Tokenized Stocks **Distributed** · **Platforms** table (sorted by platform on full page)."""
    st.dataframe(
        style_tokenized_stock_platform_dataframe(df),
        use_container_width=True,
        height=height,
        hide_index=True,
        column_order=[
            "#",
            "Platform",
            "Link",
            "RWA Count",
            "Distributed Value",
            "7D Δ value",
            "Market Share",
            "30D Δ share",
        ],
        column_config={
            "#": st.column_config.NumberColumn(
                f"# {_SORT}",
                format="%.0f",
                help="Rank on RWA.xyz Distributed · Platforms tab",
            ),
            "Platform": st.column_config.TextColumn(
                f"Platform {_SORT}",
                width="medium",
                help="Issuance platform (e.g. Backed, Dinari, Ondo)",
            ),
            "Link": st.column_config.LinkColumn(
                f"RWA Page {_SORT}",
                display_text=_LINK_ARROW,
                validate=r"^https://",
                width="small",
                help="Open this platform on RWA.xyz",
            ),
            "RWA Count": st.column_config.NumberColumn(
                f"RWA Count {_SORT}",
                format="%.0f",
                help="Number of tokenized stock / ETF RWAs for this platform",
            ),
            "Distributed Value": st.column_config.NumberColumn(
                f"Distributed Value {_SORT}",
                format=None,
                width=150,
                help="Tokenized stocks Distributed Value (USD) for this platform",
            ),
            "7D Δ value": st.column_config.NumberColumn(
                f"7D Δ value {_SORT}",
                format=None,
                width=100,
                help="7-day change in Distributed Value (%)",
            ),
            "Market Share": st.column_config.NumberColumn(
                f"Market Share {_SORT}",
                format=None,
                help="Current platform market share (%)",
            ),
            "30D Δ share": st.column_config.NumberColumn(
                f"30D Δ share {_SORT}",
                format=None,
                width=100,
                help="Change in market share vs 30 days ago (percentage points)",
            ),
        },
    )


def _show_tokenized_stock_network_dataframe(df, *, height: int) -> None:
    """Tokenized Stocks **Distributed** · **Networks** table."""
    st.dataframe(
        style_tokenized_stock_network_dataframe(df),
        use_container_width=True,
        height=height,
        hide_index=True,
        column_order=[
            "#",
            "Network",
            "Link",
            "RWA Count",
            "Distributed Value",
            "7D Δ value",
            "Market Share",
            "30D Δ share",
        ],
        column_config={
            "#": st.column_config.NumberColumn(
                f"# {_SORT}",
                format="%.0f",
                help="Rank on RWA.xyz Distributed · Networks tab",
            ),
            "Network": st.column_config.TextColumn(
                f"Network {_SORT}",
                width="medium",
                help="Blockchain network for tokenized stocks RWAs",
            ),
            "Link": st.column_config.LinkColumn(
                f"RWA Page {_SORT}",
                display_text=_LINK_ARROW,
                validate=r"^https://",
                width="small",
                help="Open this network on RWA.xyz",
            ),
            "RWA Count": st.column_config.NumberColumn(
                f"RWA Count {_SORT}",
                format="%.0f",
                help="Number of tokenized stock / ETF RWAs on this network",
            ),
            "Distributed Value": st.column_config.NumberColumn(
                f"Distributed Value {_SORT}",
                format=None,
                width=150,
                help="Tokenized stocks Distributed Value (USD) for this network",
            ),
            "7D Δ value": st.column_config.NumberColumn(
                f"7D Δ value {_SORT}",
                format=None,
                width=100,
                help="7-day change in Distributed Value (%)",
            ),
            "Market Share": st.column_config.NumberColumn(
                f"Market Share {_SORT}",
                format=None,
                help="Current network market share (%)",
            ),
            "30D Δ share": st.column_config.NumberColumn(
                f"30D Δ share {_SORT}",
                format=None,
                width=100,
                help="Change in market share vs 30 days ago (percentage points)",
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


@st.cache_data(ttl=3600, show_spinner=False)
def load_rwa_treasuries_cached(
    *, _treasury_schema: int = 4
) -> tuple[
    list[RwaTreasuryDistributedNetworkRow],
    list[RwaTreasuryPlatformRow],
    list[RwaGlobalKpi],
    str | None,
]:
    """Bump ``_treasury_schema`` when ``/treasuries`` embed shape changes."""
    _ = _treasury_schema
    return fetch_rwa_treasuries_data()


@st.cache_data(ttl=3600, show_spinner=False)
def load_rwa_tokenized_stocks_cached(
    *, _stocks_schema: int = 2
) -> tuple[
    list[RwaTokenizedStockNetworkRow],
    list[RwaTokenizedStockPlatformRow],
    list[RwaGlobalKpi],
    str | None,
]:
    """Bump ``_stocks_schema`` when ``/stocks`` embed shape changes."""
    _ = _stocks_schema
    return fetch_rwa_tokenized_stocks_data()


def clear_rwa_league_cache() -> None:
    load_rwa_league_cached.clear()
    load_rwa_stablecoins_cached.clear()
    load_rwa_treasuries_cached.clear()
    load_rwa_tokenized_stocks_cached.clear()


def show_rwa_stablecoins_widget(
    *,
    home_preview: bool = True,
    preview_rows: int = 8,
) -> None:
    """
    RWA.xyz Stablecoins embed: four overview KPIs + **Platforms** league.

    ``home_preview=True`` (under **On-chain Data** on the hub): short preview + link to full page.
    ``home_preview=False``: full searchable table (use from ``pages/RWA_Stablecoins.py``).
    """
    h2_sub = "home-widget-heading" if home_preview else "home-main-heading"
    if home_preview:
        st.divider()
        st.markdown(
            f'<div class="jd-hub-subsection-head" id="jd-rwa-stablecoins">'
            f'<h2 class="{h2_sub}">Stablecoins</h2></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(WIDGET_CSS + KPI_WINDOW_NOTE_CSS + STREAMLIT_TABLE_UNIFY_CSS, unsafe_allow_html=True)
        st.markdown(
            '<div class="jd-hub-subsection-head" id="jd-rwa-stablecoins">'
            '<h2 class="home-main-heading">Stablecoins</h2>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Full **Platforms** league with search from the "
            "[RWA.xyz Stablecoins](https://app.rwa.xyz/stablecoins) embed. "
            "Overview **% changes** are **30-day (30D)**; each row’s **market cap** is a level."
        )

    rows_sc, kpis_sc, err_sc = load_rwa_stablecoins_cached()

    if err_sc and not rows_sc:
        st.warning(escape(err_sc))
        _render_rwa_stablecoin_overview(kpis_sc)
        st.link_button(
            STABLECOINS_RWA_LINK_LABEL,
            "https://app.rwa.xyz/stablecoins",
            use_container_width=True,
            key="rwa_sc_rwa_link_err_home" if home_preview else "rwa_sc_rwa_link_err_full",
        )
        return

    if not rows_sc:
        st.info("No platform rows returned for Stablecoins.")
        _render_rwa_stablecoin_overview(kpis_sc)
        st.link_button(
            STABLECOINS_RWA_LINK_LABEL,
            "https://app.rwa.xyz/stablecoins",
            use_container_width=True,
            key="rwa_sc_rwa_link_empty_home" if home_preview else "rwa_sc_rwa_link_empty_full",
        )
        return

    _render_rwa_stablecoin_overview(kpis_sc)

    if home_preview:
        n = max(1, min(preview_rows, len(rows_sc)))
        working = rows_sc[:n]
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
    if not home_preview:
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
            STABLECOINS_RWA_LINK_LABEL,
            "https://app.rwa.xyz/stablecoins",
            use_container_width=True,
            key="rwa_sc_rwa_link_home",
        )
    else:
        st.link_button(
            STABLECOINS_RWA_LINK_LABEL,
            "https://app.rwa.xyz/stablecoins",
            use_container_width=True,
            key="rwa_sc_rwa_link_full",
        )


def show_rwa_treasuries_widget(
    *,
    home_preview: bool = True,
    preview_rows: int = 8,
) -> None:
    """
    RWA.xyz US Treasuries embed: overview KPIs + **Distributed** · **Networks** league (Distributed Value).

    ``home_preview=True``: teaser under **On-chain Data** on the hub. ``home_preview=False``: full searchable table
    (``pages/RWA_US_Treasuries.py``).
    """
    h2_sub = "home-widget-heading" if home_preview else "home-main-heading"
    if home_preview:
        st.divider()
        st.markdown(
            f'<div class="jd-hub-subsection-head" id="jd-rwa-treasuries">'
            f'<h2 class="{h2_sub}">US Treasuries</h2></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(WIDGET_CSS + KPI_WINDOW_NOTE_CSS + STREAMLIT_TABLE_UNIFY_CSS, unsafe_allow_html=True)
        st.markdown(
            '<div class="jd-hub-subsection-head" id="jd-rwa-treasuries">'
            '<h2 class="home-main-heading">US Treasuries</h2>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Full **Distributed** leagues with search: **Networks** then **Platforms** "
            f"(Tokenized Treasury by issuer). Overview **% changes** are **30-day (30D)**; "
            f"**Distributed Value** columns are levels — [RWA.xyz US Treasuries]({APP_TREASURIES})."
        )

    rows_tr, plat_tr, kpis_tr, err_tr = load_rwa_treasuries_cached()

    if err_tr and not rows_tr and not plat_tr:
        st.warning(escape(err_tr))
        _render_rwa_treasuries_overview(kpis_tr)
        st.link_button(
            TREASURIES_RWA_LINK_LABEL,
            APP_TREASURIES,
            use_container_width=True,
            key="rwa_tr_rwa_link_err_home" if home_preview else "rwa_tr_rwa_link_err_full",
        )
        return

    if not rows_tr and not plat_tr:
        st.info("No US Treasuries league rows returned.")
        _render_rwa_treasuries_overview(kpis_tr)
        st.link_button(
            TREASURIES_RWA_LINK_LABEL,
            APP_TREASURIES,
            use_container_width=True,
            key="rwa_tr_rwa_link_empty_home" if home_preview else "rwa_tr_rwa_link_empty_full",
        )
        return

    _render_rwa_treasuries_overview(kpis_tr)

    if rows_tr:
        if home_preview:
            n = max(1, min(preview_rows, len(rows_tr)))
            working = rows_tr[:n]
            table_h = rwa_table_height(len(working))
        else:
            q = st.text_input(
                "Search network",
                "",
                key="rwa_treasury_search_full",
                placeholder="Filter by network name…",
            )
            working = filter_treasury_network_rows(rows_tr, q)
            if q.strip():
                st.caption(
                    f"Showing {len(working)} of {len(rows_tr)} networks matching “{escape(q.strip())}”."
                )
            else:
                st.caption(
                    f"Showing all {len(working)} networks (US Treasuries · Distributed · Networks)."
                )
            table_h = rwa_table_height(len(working), max_h=900)

        _bn_h2 = "home-widget-heading" if home_preview else "home-main-heading"
        st.markdown(
            f'<div class="jd-hub-subsection-head">'
            f'<h2 class="{_bn_h2}">By network (Distributed · Networks)</h2></div>',
            unsafe_allow_html=True,
        )
        df_tr = build_us_treasury_network_dataframe(working)
        _show_us_treasury_network_dataframe(df_tr, height=table_h)
        if not home_preview:
            st.caption(TREASURY_RWA_CAPTION)
    elif not home_preview:
        st.info(
            "The **Networks** league was not present in the embed; the **Platforms** table below may still load."
        )

    if not home_preview and plat_tr:
        st.divider()
        st.markdown(
            '<div class="jd-hub-subsection-head">'
            '<h2 class="home-main-heading">By platform (Tokenized Treasury league)</h2></div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "**Distributed** · **Platforms** — issuer totals from **RWA.xyz**. "
            "**Value** columns are levels; **7-day** change uses the embed field `value_7d_change` "
            "(the site may label related moves **30D** in other views)."
        )
        qp = st.text_input(
            "Search platform",
            "",
            key="rwa_treasury_platform_search_full",
            placeholder="Filter by platform name…",
        )
        working_p = filter_treasury_platform_rows(plat_tr, qp)
        if qp.strip():
            st.caption(
                f"Showing {len(working_p)} of {len(plat_tr)} platforms matching “{escape(qp.strip())}”."
            )
        else:
            st.caption(
                f"Showing all {len(working_p)} platforms (US Treasuries · Distributed · Platforms)."
            )
        table_ph = rwa_table_height(len(working_p), max_h=900)
        df_p = build_us_treasury_platform_dataframe(working_p)
        _show_us_treasury_platform_dataframe(df_p, height=table_ph)
        st.caption(TREASURY_PLATFORM_CAPTION)
    elif not home_preview and not plat_tr:
        st.divider()
        st.info("No **Platforms** league rows were returned for US Treasuries in this embed.")

    if home_preview:
        if st.button(
            "Open full US Treasuries table",
            key="see_full_rwa_treasuries",
            use_container_width=True,
            type="primary",
        ):
            st.switch_page("pages/RWA_US_Treasuries.py")
        st.link_button(
            TREASURIES_RWA_LINK_LABEL,
            APP_TREASURIES,
            use_container_width=True,
            key="rwa_tr_rwa_link_home",
        )
    else:
        st.link_button(
            TREASURIES_RWA_LINK_LABEL,
            APP_TREASURIES,
            use_container_width=True,
            key="rwa_tr_rwa_link_full",
        )


def show_rwa_tokenized_stocks_widget(
    *,
    home_preview: bool = True,
    preview_rows: int = 8,
) -> None:
    """
    RWA.xyz Tokenized Stocks embed: overview KPIs + **Distributed** · **Platforms** league.

    ``home_preview=True``: teaser on home page. ``home_preview=False``: full searchable table
    (``pages/RWA_Tokenized_Stocks.py``).
    """
    h2_sub = "home-widget-heading" if home_preview else "home-main-heading"
    if home_preview:
        st.divider()
        st.markdown(
            f'<div class="jd-hub-subsection-head" id="jd-rwa-tokenized-stocks">'
            f'<h2 class="{h2_sub}">Tokenized Stocks</h2></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(WIDGET_CSS + KPI_WINDOW_NOTE_CSS + STREAMLIT_TABLE_UNIFY_CSS, unsafe_allow_html=True)
        st.markdown(
            '<div class="jd-hub-subsection-head" id="jd-rwa-tokenized-stocks">'
            '<h2 class="home-main-heading">Tokenized Stocks</h2>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Full **Distributed** · **Platforms** league with search. "
            f"Overview **% changes** are **30-day (30D)**; **Distributed Value** columns are levels — "
            f"[RWA.xyz Tokenized Stocks]({APP_STOCKS})."
        )

    rows_st_net, rows_st_plat, kpis_st, err_st = load_rwa_tokenized_stocks_cached()

    if err_st and not rows_st_net and not rows_st_plat:
        st.warning(escape(err_st))
        _render_rwa_treasuries_overview(
            kpis_st,
            overview_title="Tokenized Stocks",
        )
        st.link_button(
            TOKENIZED_STOCKS_RWA_LINK_LABEL,
            APP_STOCKS,
            use_container_width=True,
            key="rwa_stocks_rwa_link_err_home" if home_preview else "rwa_stocks_rwa_link_err_full",
        )
        return

    if not rows_st_net and not rows_st_plat:
        st.info("No Tokenized Stocks league rows returned.")
        _render_rwa_treasuries_overview(
            kpis_st,
            overview_title="Tokenized Stocks",
        )
        st.link_button(
            TOKENIZED_STOCKS_RWA_LINK_LABEL,
            APP_STOCKS,
            use_container_width=True,
            key="rwa_stocks_rwa_link_empty_home" if home_preview else "rwa_stocks_rwa_link_empty_full",
        )
        return

    _render_rwa_treasuries_overview(
        kpis_st,
        overview_title="Tokenized Stocks",
    )

    if rows_st_plat and home_preview:
        n = max(1, min(preview_rows, len(rows_st_plat)))
        working = rows_st_plat[:n]
        table_h = rwa_table_height(len(working))
        df_st = build_tokenized_stock_platform_dataframe(working)
        _show_tokenized_stock_platform_dataframe(df_st, height=table_h)
    elif rows_st_plat and not home_preview:
        q = st.text_input(
            "Search platform",
            "",
            key="rwa_tokenized_stocks_search_full",
            placeholder="Filter by platform name…",
        )
        working = filter_tokenized_stock_platform_rows(rows_st_plat, q)
        # Keep full-page order aligned with the on-screen rank column.
        working = sorted(working, key=lambda r: int(r.rank))
        if q.strip():
            st.caption(
                f"Showing {len(working)} of {len(rows_st_plat)} platforms matching “{escape(q.strip())}”."
            )
        else:
            st.caption(
                f"Showing all {len(working)} platforms (Tokenized Stocks · Distributed · Platforms), sorted by #."
            )
        table_h = rwa_table_height(len(working), max_h=900)
        st.markdown(
            '<div class="jd-hub-subsection-head">'
            '<h2 class="home-main-heading">By platform (Distributed · Platforms)</h2></div>',
            unsafe_allow_html=True,
        )
        df_st = build_tokenized_stock_platform_dataframe(working)
        _show_tokenized_stock_platform_dataframe(df_st, height=table_h)
    elif home_preview:
        st.info("No Tokenized Stocks platform rows returned.")
    else:
        st.info("No Tokenized Stocks Distributed · Platforms rows were returned.")

    if not home_preview:
        st.divider()
        st.markdown(
            '<div class="jd-hub-subsection-head">'
            '<h2 class="home-main-heading">By network (Distributed · Networks)</h2></div>',
            unsafe_allow_html=True,
        )
        if rows_st_net:
            qn = st.text_input(
                "Search network",
                "",
                key="rwa_tokenized_stocks_network_search_full",
                placeholder="Filter by network name…",
            )
            working_n = filter_tokenized_stock_network_rows(rows_st_net, qn)
            working_n = sorted(working_n, key=lambda r: int(r.rank))
            if qn.strip():
                st.caption(
                    f"Showing {len(working_n)} of {len(rows_st_net)} networks matching “{escape(qn.strip())}”."
                )
            else:
                st.caption(
                    f"Showing all {len(working_n)} networks (Tokenized Stocks · Distributed · Networks), sorted by #."
                )
            table_hn = rwa_table_height(len(working_n), max_h=900)
            df_n = build_tokenized_stock_network_dataframe(working_n)
            _show_tokenized_stock_network_dataframe(df_n, height=table_hn)
        else:
            st.info("No Tokenized Stocks Distributed · Networks rows were returned.")

    if not home_preview:
        st.caption(TOKENIZED_STOCKS_RWA_CAPTION)

    if home_preview:
        if st.button(
            "Open full Tokenized Stocks table",
            key="see_full_rwa_tokenized_stocks",
            use_container_width=True,
            type="primary",
        ):
            st.switch_page("pages/RWA_Tokenized_Stocks.py")
        st.link_button(
            TOKENIZED_STOCKS_RWA_LINK_LABEL,
            APP_STOCKS,
            use_container_width=True,
            key="rwa_stocks_rwa_link_home",
        )
    else:
        st.link_button(
            TOKENIZED_STOCKS_RWA_LINK_LABEL,
            APP_STOCKS,
            use_container_width=True,
            key="rwa_stocks_rwa_link_full",
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
    st.markdown(WIDGET_CSS + KPI_WINDOW_NOTE_CSS + STREAMLIT_TABLE_UNIFY_CSS, unsafe_allow_html=True)
    rows, kpis, err = load_rwa_league_cached()
    h2_cls = "home-widget-heading" if home_preview else "home-main-heading"

    if err and not rows:
        st.warning(escape(err))
        st.markdown(
            f'<div class="jd-hub-subsection-head" id="jd-rwa-market">'
            f'<h2 class="{h2_cls}">Global Market Overview</h2></div>',
            unsafe_allow_html=True,
        )
        _render_rwa_global_overview(kpis)
        st.link_button(
            GLOBAL_MARKET_RWA_LINK_LABEL,
            GLOBAL_MARKET_RWA_URL,
            use_container_width=True,
            key="rwa_global_market_err_home" if home_preview else "rwa_global_market_err_full",
        )
        if home_preview:
            show_rwa_stablecoins_widget(home_preview=True, preview_rows=preview_rows)
            show_rwa_treasuries_widget(home_preview=True, preview_rows=preview_rows)
            show_rwa_tokenized_stocks_widget(home_preview=True, preview_rows=preview_rows)
        return

    if not rows:
        st.markdown(
            '<div id="jd-rwa-market" style="scroll-margin-top: 5.5rem;"></div>',
            unsafe_allow_html=True,
        )
        st.info("No network rows returned.")
        return

    st.markdown(
        f'<div class="jd-hub-subsection-head" id="jd-rwa-market">'
        f'<h2 class="{h2_cls}">Global Market Overview</h2></div>',
        unsafe_allow_html=True,
    )
    _render_rwa_global_overview(kpis)

    working = list(rows)
    if home_preview:
        n = max(1, min(preview_rows, len(working)))
        working = working[:n]
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
            st.caption(
                f"Showing all {len(working)} networks (**Distributed Value** levels; overview above: **30D** %)."
            )

    df = build_rwa_dataframe(working)
    _show_rwa_dataframe(df, height=rwa_table_height(len(df)))
    if not home_preview:
        st.caption(RWA_DATA_SOURCE_CAPTION)

    if home_preview and st.button(
        "Open full RWA league table",
        key="see_full_rwa_league",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/RWA_League.py")

    st.link_button(
        GLOBAL_MARKET_RWA_LINK_LABEL,
        GLOBAL_MARKET_RWA_URL,
        use_container_width=True,
        key="rwa_global_market_home" if home_preview else "rwa_global_market_full",
    )

    if home_preview:
        show_rwa_stablecoins_widget(home_preview=True, preview_rows=preview_rows)
        show_rwa_treasuries_widget(home_preview=True, preview_rows=preview_rows)
        show_rwa_tokenized_stocks_widget(home_preview=True, preview_rows=preview_rows)
