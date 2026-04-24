"""RWA.xyz **Networks**, **Platforms**, and **Asset Managers** embeds (``__NEXT_DATA__`` from ``/networks``, ``/platforms``, ``/asset-managers``)."""

from __future__ import annotations

from html import escape

import streamlit as st

from home_layout import (
    KPI_WINDOW_NOTE_CSS,
    STREAMLIT_TABLE_UNIFY_CSS,
    hub_section_anchor,
    hub_subsection_heading_html,
)
from rwa_league.client import (
    APP_ASSET_MANAGERS,
    APP_NETWORKS,
    APP_PLATFORMS,
    APP_STOCKS,
    APP_TREASURIES,
    RwaAssetManagersTabRow,
    RwaGlobalKpi,
    RwaNetworksTabRow,
    RwaPlatformsTabRow,
    RwaTokenizedStockNetworkRow,
    RwaStablecoinPlatformRow,
    RwaTokenizedStockPlatformRow,
    RwaTreasuryDistributedNetworkRow,
    RwaTreasuryPlatformRow,
    fetch_rwa_asset_managers_page_data,
    fetch_rwa_networks_page_data,
    fetch_rwa_platforms_page_data,
    fetch_rwa_stablecoins_data,
    fetch_rwa_tokenized_stocks_data,
    fetch_rwa_treasuries_data,
)
from rwa_league.dataframe_table import (
    build_rwa_asset_managers_page_dataframe,
    build_rwa_dataframe,
    build_rwa_networks_page_dataframe,
    build_rwa_platforms_page_dataframe,
    build_tokenized_stock_network_dataframe,
    build_stablecoin_platform_dataframe,
    build_tokenized_stock_platform_dataframe,
    build_us_treasury_network_dataframe,
    build_us_treasury_platform_dataframe,
    filter_rows_by_network,
    filter_asset_managers_tab_rows,
    filter_platforms_tab_rows,
    filter_tokenized_stock_network_rows,
    filter_stablecoin_platform_rows,
    filter_tokenized_stock_platform_rows,
    filter_treasury_network_rows,
    filter_treasury_platform_rows,
    style_rwa_dataframe,
    style_rwa_networks_page_dataframe,
    style_rwa_asset_managers_page_dataframe,
    style_rwa_platforms_page_dataframe,
    style_tokenized_stock_network_dataframe,
    style_stablecoin_platform_dataframe,
    style_tokenized_stock_platform_dataframe,
    style_us_treasury_network_dataframe,
    style_us_treasury_platform_dataframe,
)

WIDGET_CSS = """
<style>
.jd-hub-subsection-head {
    margin: 0.4rem 0 0.55rem 0;
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
#jd-rwa-participants,
#jd-rwa-participants-networks,
#jd-rwa-participants-platforms,
#jd-rwa-participants-asset-managers,
#jd-rwa-explore-asset-type,
#jd-rwa-explore-market-participant,
#jd-rwa-platforms-overview,
#jd-rwa-asset-managers-overview,
#jd-rwa-market,
#jd-rwa-stablecoins,
#jd-rwa-treasuries,
#jd-rwa-tokenized-stocks {
    scroll-margin-top: 5.5rem;
}
.jd-rwa-participants-eyebrow {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #25809C;
    margin: 0 0 0.35rem 0;
    padding: 0;
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
    "Source: [RWA.xyz Networks](https://app.rwa.xyz/networks) embedded **__NEXT_DATA__** "
    "(`listQueryResponse` + per-network `asset_class_stats` and `transferability`); not the public API. "
    "**RWA count** and **RWA total (excl. stablecoins)** use non-stablecoin rows in `asset_class_stats` (same as the on-site table). "
    "**RWA value (distributed)** = `transferability.transferable`; **(represented)** = `non_transferable`; "
    "**% distributed** = distributed ÷ that total. Top-line **%** are **30D**; **7D Δ** uses `transferable_30d`."
)

RWA_PLATFORMS_DATA_SOURCE_CAPTION = (
    "Source: [RWA.xyz Platforms](https://app.rwa.xyz/platforms) embedded **__NEXT_DATA__** "
    "(`listQueryResponse` issuer rows). The table matches the on-site **Distributed** Platforms league: when "
    "`tokenization_type_stats` is present, **distributed** / **represented** USD and RWA counts use the "
    "`distributed` / `represented` buckets (represented-only issuers are omitted); otherwise non-stablecoin "
    "`asset_class_stats` bridged/circulating sums apply. **RWA total (excl. stablecoins)** = distributed + represented "
    "when both buckets exist. Top-line **%** are **30D**; **7D Δ** uses distributed-bucket `val` vs `val_30d`, or "
    "top-level `bridged_token_value` when the bucket list is empty."
)

RWA_ASSET_MANAGERS_DATA_SOURCE_CAPTION = (
    "Source: [RWA.xyz Asset Managers](https://app.rwa.xyz/asset-managers) embedded **__NEXT_DATA__** "
    "(`listQueryResponse`). The table matches the on-site **Distributed** tab: **RWA value (distributed)** / "
    "**(represented)** use `distributed_value` and `represented_value`; **RWA count** uses `rwa_asset_count` when "
    "present. Managers with no distributed value are omitted. Top-line **%** are **30D**; **7D Δ** uses "
    "`distributed_value.val` vs `val_30d`."
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


def _render_rwa_global_overview(
    kpis: list[RwaGlobalKpi],
    *,
    kpi_legend_name: str = "Global Market",
) -> None:
    """Global / Networks overview: KPI tiles; slate titles, teal values, 30D % change (no “30D” suffix on labels)."""
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
        f"{_rwa_kpi_window_note_html(overview_title=kpi_legend_name)}"
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


def _rank_column_label(*, by_metric: str) -> str:
    """Rank column header: '# by <primary sort metric>' then the sort affordance (matches RWA.xyz ordering)."""
    return f"# by {by_metric} {_SORT}"


_LINK_ARROW = "\u2197"  # Northeast arrow for RWA.xyz LinkColumn (Unicode U+2197)
STABLECOINS_RWA_LINK_LABEL = "See Stablecoins on RWA.xyz"
RWA_GLOBAL_MARKET_OVERVIEW_HEADING = "RWA Global Market Overview"
# Full-page Participants — Networks: hub-style heading above the KPI row (like “Stablecoin overview”).
RWA_NETWORKS_SUBPAGE_OVERVIEW_HEADING = "Networks overview"
RWA_PLATFORMS_SUBPAGE_OVERVIEW_HEADING = "Platforms overview"
RWA_ASSET_MANAGERS_SUBPAGE_OVERVIEW_HEADING = "Asset Managers overview"
GLOBAL_MARKET_RWA_LINK_LABEL = "See RWA Networks on RWA.xyz"
GLOBAL_MARKET_RWA_URL = APP_NETWORKS
PLATFORMS_RWA_LINK_LABEL = "See RWA Platforms on RWA.xyz"
PLATFORMS_RWA_URL = APP_PLATFORMS
ASSET_MANAGERS_RWA_LINK_LABEL = "See RWA Asset Managers on RWA.xyz"
ASSET_MANAGERS_RWA_URL = APP_ASSET_MANAGERS


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
                _rank_column_label(by_metric="Market cap"),
                format="%.0f",
                help="Rank on RWA.xyz Platforms tab (by aggregate stablecoin market cap)",
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
                _rank_column_label(by_metric="Total Value"),
                format="%.0f",
                help="Rank order from RWA.xyz (by network Total Value, USD)",
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


def _show_rwa_networks_page_dataframe(df, *, height: int) -> None:
    """RWA [Networks](https://app.rwa.xyz/networks) table — see :func:`build_rwa_networks_page_dataframe`."""
    st.dataframe(
        style_rwa_networks_page_dataframe(df),
        use_container_width=True,
        height=height,
        hide_index=True,
        column_order=[
            "#",
            "Network",
            "Link",
            "RWA Count",
            "RWA value (distributed)",
            "RWA value (represented)",
            "% distributed",
            "RWA total (excl. stablecoins)",
            "7D Δ value",
            "Market Share",
            "30D Δ share",
        ],
        column_config={
            "#": st.column_config.NumberColumn(
                _rank_column_label(by_metric="RWA value (distributed)"),
                format="%.0f",
                help="Rank by RWA value (distributed), largest first (transferability.transferable, USD).",
            ),
            "Network": st.column_config.TextColumn(
                f"Network {_SORT}",
                width="medium",
            ),
            "Link": st.column_config.LinkColumn(
                f"RWA Page {_SORT}",
                display_text=_LINK_ARROW,
                validate=r"^https://",
                width="small",
                help="Open this network on RWA.xyz",
            ),
            "RWA Count": st.column_config.NumberColumn(
                f"RWA count {_SORT}",
                format="%.0f",
                help="Count of RWA assets excluding the Stablecoin class (sum of non-stable `asset_count` in `asset_class_stats`).",
            ),
            "RWA value (distributed)": st.column_config.NumberColumn(
                f"RWA value (distributed) {_SORT}",
                format=None,
                width=150,
                help="`transferability.transferable` (same *Distributed* column as RWA.xyz).",
            ),
            "RWA value (represented)": st.column_config.NumberColumn(
                f"RWA value (represented) {_SORT}",
                format=None,
                width=150,
                help="`transferability.non_transferable` (RWA *Represented* on RWA.xyz).",
            ),
            "% distributed": st.column_config.NumberColumn(
                f"% distributed {_SORT}",
                format=None,
                width=110,
                help="distributed ÷ RWA total (excl. stablecoins) from per-class `bridged_token_value` sums.",
            ),
            "RWA total (excl. stablecoins)": st.column_config.NumberColumn(
                f"RWA total (excl. stables) {_SORT}",
                format=None,
                width=180,
                help="Sum of `bridged_token_value_dollar` in `asset_class_stats` excluding Stablecoins (RWA *Total Excl. Stablecoins*).",
            ),
            "7D Δ value": st.column_config.NumberColumn(
                f"7D Δ value {_SORT}",
                format=None,
                width=100,
                help="(transferable−transferable_30d) / transferable_30d (same as homepage value_7d_change).",
            ),
            "Market Share": st.column_config.NumberColumn(
                f"Market Share {_SORT}",
                format=None,
                help="This network’s share of Σ RWA value (distributed) in this list.",
            ),
            "30D Δ share": st.column_config.NumberColumn(
                f"30D Δ share {_SORT}",
                format=None,
                width=100,
                help="Change in market share (percentage points) using current vs 30D-ago transferable totals.",
            ),
        },
    )


def _show_rwa_platforms_page_dataframe(df, *, height: int) -> None:
    """RWA [Platforms](https://app.rwa.xyz/platforms) issuer table — :func:`build_rwa_platforms_page_dataframe`."""
    st.dataframe(
        style_rwa_platforms_page_dataframe(df),
        use_container_width=True,
        height=height,
        hide_index=True,
        column_order=[
            "#",
            "Platform",
            "Link",
            "RWA Count",
            "RWA value (distributed)",
            "RWA value (represented)",
            "% distributed",
            "RWA total (excl. stablecoins)",
            "7D Δ value",
            "Market Share",
            "30D Δ share",
        ],
        column_config={
            "#": st.column_config.NumberColumn(
                _rank_column_label(by_metric="RWA value (distributed)"),
                format="%.0f",
                help="Rank by RWA value (distributed), largest first (Σ non-stable bridged value, USD).",
            ),
            "Platform": st.column_config.TextColumn(
                f"Platform {_SORT}",
                width="medium",
            ),
            "Link": st.column_config.LinkColumn(
                f"RWA Page {_SORT}",
                display_text=_LINK_ARROW,
                validate=r"^https://",
                width="small",
                help="Open this issuer on RWA.xyz",
            ),
            "RWA Count": st.column_config.NumberColumn(
                f"RWA count {_SORT}",
                format="%.0f",
                help="Non-stablecoin asset_count sum in asset_class_stats.",
            ),
            "RWA value (distributed)": st.column_config.NumberColumn(
                f"RWA value (distributed) {_SORT}",
                format=None,
                width=150,
                help="Σ non-stable bridged_token_value (issuer distributed bucket).",
            ),
            "RWA value (represented)": st.column_config.NumberColumn(
                f"RWA value (represented) {_SORT}",
                format=None,
                width=150,
                help="max(0, total excl. stables − distributed) for this issuer.",
            ),
            "% distributed": st.column_config.NumberColumn(
                f"% distributed {_SORT}",
                format=None,
                width=110,
                help="distributed ÷ RWA total (excl. stablecoins).",
            ),
            "RWA total (excl. stablecoins)": st.column_config.NumberColumn(
                f"RWA total (excl. stables) {_SORT}",
                format=None,
                width=180,
                help="Σ non-stable circulating_asset_value in asset_class_stats.",
            ),
            "7D Δ value": st.column_config.NumberColumn(
                f"7D Δ value {_SORT}",
                format=None,
                width=100,
                help="(bridged val − val_30d) / val_30d on issuer-level bridged_token_value_dollar.",
            ),
            "Market Share": st.column_config.NumberColumn(
                f"Market Share {_SORT}",
                format=None,
                help="This issuer’s share of Σ distributed in this table.",
            ),
            "30D Δ share": st.column_config.NumberColumn(
                f"30D Δ share {_SORT}",
                format=None,
                width=100,
                help="Change in market share (percentage points) using distributed vs 30D-ago distributed cohort totals.",
            ),
        },
    )


def _show_rwa_asset_managers_page_dataframe(df, *, height: int) -> None:
    """RWA [Asset Managers](https://app.rwa.xyz/asset-managers) table — :func:`build_rwa_asset_managers_page_dataframe`."""
    st.dataframe(
        style_rwa_asset_managers_page_dataframe(df),
        use_container_width=True,
        height=height,
        hide_index=True,
        column_order=[
            "#",
            "Asset manager",
            "Link",
            "RWA Count",
            "RWA value (distributed)",
            "RWA value (represented)",
            "% distributed",
            "RWA total (excl. stablecoins)",
            "7D Δ value",
            "Market Share",
            "30D Δ share",
        ],
        column_config={
            "#": st.column_config.NumberColumn(
                _rank_column_label(by_metric="RWA value (distributed)"),
                format="%.0f",
                help="Rank by RWA value (distributed), largest first (USD from distributed_value on RWA.xyz).",
            ),
            "Asset manager": st.column_config.TextColumn(
                f"Asset manager {_SORT}",
                width="medium",
            ),
            "Link": st.column_config.LinkColumn(
                f"RWA Page {_SORT}",
                display_text=_LINK_ARROW,
                validate=r"^https://",
                width="small",
                help="Open this manager on RWA.xyz",
            ),
            "RWA Count": st.column_config.NumberColumn(
                f"RWA count {_SORT}",
                format="%.0f",
                help="rwa_asset_count from the asset managers embed (fallback: asset_count).",
            ),
            "RWA value (distributed)": st.column_config.NumberColumn(
                f"RWA value (distributed) {_SORT}",
                format=None,
                width=150,
                help="distributed_value.val (USD).",
            ),
            "RWA value (represented)": st.column_config.NumberColumn(
                f"RWA value (represented) {_SORT}",
                format=None,
                width=150,
                help="represented_value.val (USD).",
            ),
            "% distributed": st.column_config.NumberColumn(
                f"% distributed {_SORT}",
                format=None,
                width=110,
                help="distributed ÷ (distributed + represented) for this manager.",
            ),
            "RWA total (excl. stablecoins)": st.column_config.NumberColumn(
                f"RWA total (excl. stables) {_SORT}",
                format=None,
                width=180,
                help="Sum of distributed and represented value (USD).",
            ),
            "7D Δ value": st.column_config.NumberColumn(
                f"7D Δ value {_SORT}",
                format=None,
                width=100,
                help="(distributed_value val − val_30d) / val_30d (same 30D baseline as other Participants tables).",
            ),
            "Market Share": st.column_config.NumberColumn(
                f"Market Share {_SORT}",
                format=None,
                help="This manager’s share of Σ distributed in this table.",
            ),
            "30D Δ share": st.column_config.NumberColumn(
                f"30D Δ share {_SORT}",
                format=None,
                width=100,
                help="Change in market share (percentage points) using distributed val vs val_30d cohort totals.",
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
                _rank_column_label(by_metric="Total Value"),
                format="%.0f",
                help="Rank on RWA.xyz Distributed · Platforms tab (by Total Value, USD)",
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
                _rank_column_label(by_metric="Distributed Value"),
                format="%.0f",
                help="Rank order from RWA.xyz (by Distributed Value on this network, USD)",
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
                _rank_column_label(by_metric="Distributed Value"),
                format="%.0f",
                help="Rank on RWA.xyz Distributed · Platforms tab (by Distributed Value, USD)",
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
                _rank_column_label(by_metric="Distributed Value"),
                format="%.0f",
                help="Rank on RWA.xyz Distributed · Networks tab (by Distributed Value, USD)",
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
def load_rwa_league_cached(*, _rwa_schema: int = 7) -> tuple[list[RwaNetworksTabRow], list[RwaGlobalKpi], str | None]:
    """Bump ``_rwa_schema`` when ``/networks`` or ``__NEXT_DATA__`` shape or row field definitions change."""
    _ = _rwa_schema
    return fetch_rwa_networks_page_data()


@st.cache_data(ttl=3600, show_spinner=False)
def load_rwa_platforms_cached(*, _platforms_schema: int = 2) -> tuple[list[RwaPlatformsTabRow], list[RwaGlobalKpi], str | None]:
    """Bump ``_platforms_schema`` when ``/platforms`` ``__NEXT_DATA__`` shape or row mapping changes."""
    _ = _platforms_schema
    return fetch_rwa_platforms_page_data()


@st.cache_data(ttl=3600, show_spinner=False)
def load_rwa_asset_managers_cached(
    *, _asset_managers_schema: int = 1
) -> tuple[list[RwaAssetManagersTabRow], list[RwaGlobalKpi], str | None]:
    """Bump ``_asset_managers_schema`` when ``/asset-managers`` ``__NEXT_DATA__`` shape or row mapping changes."""
    _ = _asset_managers_schema
    return fetch_rwa_asset_managers_page_data()


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
    load_rwa_platforms_cached.clear()
    load_rwa_asset_managers_cached.clear()
    load_rwa_stablecoins_cached.clear()
    load_rwa_treasuries_cached.clear()
    load_rwa_tokenized_stocks_cached.clear()


def show_rwa_stablecoins_widget(
    *,
    home_preview: bool = True,
    preview_rows: int = 8,
    full_page_header: bool = False,
) -> None:
    """
    RWA.xyz Stablecoins embed: four overview KPIs + **Platforms** league.

    ``home_preview=True`` (under **On-chain Data** on the hub): short preview + link to full page.
    ``home_preview=False``: full searchable table (use from ``pages/RWA_Stablecoins.py``).
    ``full_page_header=True``: page supplies the teal major title; use a hub-style overview subsection
    (``hub_subsection_heading_html``) instead of repeating the asset name + long caption.
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
        if not full_page_header:
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
        else:
            st.markdown(
                hub_subsection_heading_html(
                    "Stablecoin overview",
                    element_id="jd-rwa-stablecoins",
                ),
                unsafe_allow_html=True,
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
    full_page_header: bool = False,
) -> None:
    """
    RWA.xyz US Treasuries embed: overview KPIs + **Distributed** · **Networks** league (Distributed Value).

    ``home_preview=True``: teaser under **On-chain Data** on the hub. ``home_preview=False``: full searchable table
    (``pages/RWA_US_Treasuries.py``).
    ``full_page_header=True``: page supplies the teal major title; use an overview subsection instead of
    repeating the asset name + long caption.
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
        if not full_page_header:
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
        else:
            st.markdown(
                hub_subsection_heading_html(
                    "Treasury overview",
                    element_id="jd-rwa-treasuries",
                ),
                unsafe_allow_html=True,
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
    full_page_header: bool = False,
) -> None:
    """
    RWA.xyz Tokenized Stocks embed: overview KPIs + **Distributed** · **Platforms** league.

    ``home_preview=True``: teaser on home page. ``home_preview=False``: full searchable table
    (``pages/RWA_Tokenized_Stocks.py``).
    ``full_page_header=True``: page supplies the teal major title; use an overview subsection instead of
    repeating the asset name + long caption.
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
        if not full_page_header:
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
        else:
            st.markdown(
                hub_subsection_heading_html(
                    "Tokenized equity overview",
                    element_id="jd-rwa-tokenized-stocks",
                ),
                unsafe_allow_html=True,
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


def _rwa_global_market_status(
    rows: list[RwaNetworksTabRow],
    kpis: list[RwaGlobalKpi],
    err: str | None,
    *,
    home_preview: bool,
    preview_rows: int,
) -> str:
    """
    Hub block: **RWA Global Market Overview** (heading) + top-line **Networks** overview KPIs + the **Networks** table
    (from ``/networks`` ``__NEXT_DATA__``, not the smaller homepage **parent_networks** league only).

    Returns ``"STOP"`` (abort rest of On-chain bundle), ``"ERR_HOME"`` (fetch error on hub — caller may still add
    Explore gateway columns), or ``"OK"`` (caller may add **Explore by Asset Type** / **Market Participant** gateways).
    """
    h2_cls = "home-widget-heading" if home_preview else "home-main-heading"

    if err and not rows:
        st.warning(escape(err))
        st.markdown(
            f'<div class="jd-hub-subsection-head" id="jd-rwa-market">'
            f'<h2 class="{h2_cls}">{RWA_GLOBAL_MARKET_OVERVIEW_HEADING}</h2></div>',
            unsafe_allow_html=True,
        )
        _render_rwa_global_overview(kpis, kpi_legend_name="Networks")
        st.link_button(
            GLOBAL_MARKET_RWA_LINK_LABEL,
            GLOBAL_MARKET_RWA_URL,
            use_container_width=True,
            key="rwa_global_market_err_home" if home_preview else "rwa_global_market_err_full",
        )
        return "ERR_HOME" if home_preview else "STOP"

    if not rows:
        st.markdown(hub_section_anchor("jd-rwa-market"), unsafe_allow_html=True)
        st.info("No network rows returned.")
        return "STOP"

    st.markdown(
        f'<div class="jd-hub-subsection-head" id="jd-rwa-market">'
        f'<h2 class="{h2_cls}">{RWA_GLOBAL_MARKET_OVERVIEW_HEADING}</h2></div>',
        unsafe_allow_html=True,
    )
    _render_rwa_global_overview(kpis, kpi_legend_name="Networks")

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
                f"Showing all {len(working)} networks (see caption below for RWA / **Networks** column definitions; "
                f"headline **%** above: **30D**)."
            )

    df = build_rwa_networks_page_dataframe(working)
    _show_rwa_networks_page_dataframe(df, height=rwa_table_height(len(df), max_h=900))
    if not home_preview:
        st.caption(RWA_DATA_SOURCE_CAPTION)

    if home_preview and st.button(
        "Open full RWA Market Overview table",
        key="see_full_rwa_league",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/RWA_Participants_Networks.py")

    st.link_button(
        GLOBAL_MARKET_RWA_LINK_LABEL,
        GLOBAL_MARKET_RWA_URL,
        use_container_width=True,
        key="rwa_global_market_home" if home_preview else "rwa_global_market_full",
    )
    return "OK"


def _show_rwa_participants_networks_home_footer(
    rows: list[RwaNetworksTabRow],
    kpis: list[RwaGlobalKpi],
    *,
    preview_rows: int,
) -> None:
    """
    Hub-only tail: **Participants → Networks** with the same **Networks overview** KPI row + table preview
    (mirrors Stablecoins / Treasuries / Stocks home sections).
    """
    if not rows:
        return
    st.divider()
    st.markdown(
        '<p class="jd-rwa-participants-eyebrow" id="jd-rwa-participants">Participants</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="jd-hub-subsection-head" id="jd-rwa-participants-networks">'
        '<h2 class="home-widget-heading">Networks</h2></div>',
        unsafe_allow_html=True,
    )
    _render_rwa_global_overview(kpis, kpi_legend_name="Networks")
    st.caption(
        "Preview of the **Networks** table from the [RWA.xyz Networks](https://app.rwa.xyz/networks) embed "
        "(same totals as **RWA Global Market** above, formatted here under **Participants**)."
    )
    n = max(1, min(preview_rows, len(rows)))
    working = list(rows)[:n]
    df = build_rwa_networks_page_dataframe(working)
    _show_rwa_networks_page_dataframe(df, height=rwa_table_height(len(df), max_h=900))

    if st.button(
        "Open full Participants — Networks page",
        key="see_full_rwa_participants_networks_footer",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/RWA_Participants_Networks.py")
    st.link_button(
        "See Networks on RWA.xyz",
        "https://app.rwa.xyz/networks",
        use_container_width=True,
        key="rwa_participants_rwa_networks_link_home_footer",
    )


def _show_rwa_participants_platforms_home_footer(
    rows: list[RwaPlatformsTabRow],
    kpis: list[RwaGlobalKpi],
    *,
    preview_rows: int,
) -> None:
    """Hub tail under **Participants**: **Platforms** KPI row + table (same layout as Networks)."""
    if not rows:
        return
    st.divider()
    st.markdown(
        '<div class="jd-hub-subsection-head" id="jd-rwa-participants-platforms">'
        '<h2 class="home-widget-heading">Platforms</h2></div>',
        unsafe_allow_html=True,
    )
    _render_rwa_global_overview(kpis, kpi_legend_name="Platforms")
    st.caption(
        "Preview of the **Distributed** Platforms issuer table from the [RWA.xyz Platforms](https://app.rwa.xyz/platforms) embed."
    )
    n = max(1, min(preview_rows, len(rows)))
    working = list(rows)[:n]
    df = build_rwa_platforms_page_dataframe(working)
    _show_rwa_platforms_page_dataframe(df, height=rwa_table_height(len(df), max_h=900))

    if st.button(
        "Open full Participants — Platforms page",
        key="see_full_rwa_participants_platforms_footer",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/RWA_Participants_Platforms.py")
    st.link_button(
        PLATFORMS_RWA_LINK_LABEL,
        PLATFORMS_RWA_URL,
        use_container_width=True,
        key="rwa_participants_rwa_platforms_link_home_footer",
    )


def _show_rwa_participants_asset_managers_home_footer(
    rows: list[RwaAssetManagersTabRow],
    kpis: list[RwaGlobalKpi],
    *,
    preview_rows: int,
) -> None:
    """Hub tail under **Participants**: **Asset Managers** KPI row + Distributed-tab table preview."""
    if not rows:
        return
    st.divider()
    st.markdown(
        '<div class="jd-hub-subsection-head" id="jd-rwa-participants-asset-managers">'
        '<h2 class="home-widget-heading">Asset Managers</h2></div>',
        unsafe_allow_html=True,
    )
    _render_rwa_global_overview(kpis, kpi_legend_name="Asset Managers")
    st.caption(
        "Preview of the **Distributed** Asset Managers table from the "
        "[RWA.xyz Asset Managers](https://app.rwa.xyz/asset-managers) embed."
    )
    n = max(1, min(preview_rows, len(rows)))
    working = list(rows)[:n]
    df = build_rwa_asset_managers_page_dataframe(working)
    _show_rwa_asset_managers_page_dataframe(df, height=rwa_table_height(len(df), max_h=900))

    if st.button(
        "Open full Participants — Asset Managers page",
        key="see_full_rwa_participants_asset_managers_footer",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/RWA_Participants_Asset_Managers.py")
    st.link_button(
        ASSET_MANAGERS_RWA_LINK_LABEL,
        ASSET_MANAGERS_RWA_URL,
        use_container_width=True,
        key="rwa_participants_rwa_asset_managers_link_home_footer",
    )


def show_rwa_participants_networks_widget(
    *,
    home_preview: bool = False,
    full_page_header: bool = False,
) -> None:
    """
    **Full page only** (``home_preview=False``): **Participants — Networks** with Global Market KPIs + league table.

    On the hub, use :func:`show_rwa_league_widget` instead (Global Market first, asset teasers, then this block’s
    footer via :func:`_show_rwa_participants_networks_home_footer`).
    """
    if home_preview:
        raise ValueError("show_rwa_participants_networks_widget is only for full pages; use show_rwa_league_widget on the hub.")

    st.markdown(
        WIDGET_CSS + KPI_WINDOW_NOTE_CSS + STREAMLIT_TABLE_UNIFY_CSS,
        unsafe_allow_html=True,
    )

    rows, kpis, err = load_rwa_league_cached()

    if err and not rows:
        st.warning(escape(err))
        st.markdown(
            f'<div class="jd-hub-subsection-head" id="jd-rwa-market">'
            f'<h2 class="home-main-heading">{escape(RWA_NETWORKS_SUBPAGE_OVERVIEW_HEADING)}</h2></div>',
            unsafe_allow_html=True,
        )
        _render_rwa_global_overview(kpis, kpi_legend_name="Networks")
        st.link_button(
            GLOBAL_MARKET_RWA_LINK_LABEL,
            GLOBAL_MARKET_RWA_URL,
            use_container_width=True,
            key="rwa_pn_rwa_link_err_full",
        )
        return

    if not rows:
        st.markdown(hub_section_anchor("jd-rwa-market"), unsafe_allow_html=True)
        st.info("No network rows returned.")
        return

    if full_page_header:
        st.markdown(
            hub_subsection_heading_html(
                RWA_NETWORKS_SUBPAGE_OVERVIEW_HEADING,
                element_id="jd-rwa-market",
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="jd-hub-subsection-head" id="jd-rwa-participants-networks">'
            '<h2 class="home-main-heading">Networks</h2></div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Searchable table from the [RWA.xyz Networks](https://app.rwa.xyz/networks) embed. "
            "RWA value columns use the same **transferability** fields as the on-site list; top-line **%** are **30D**."
        )

    _render_rwa_global_overview(kpis, kpi_legend_name="Networks")

    q = st.text_input(
        "Search network",
        "",
        key="rwa_participants_networks_search_full",
        placeholder="Filter by network name…",
    )
    working = filter_rows_by_network(rows, q)
    if q.strip():
        st.caption(
            f"Showing {len(working)} of {len(rows)} networks matching “{escape(q.strip())}”."
        )
    else:
        st.caption(
            f"Showing all {len(working)} networks. Headline KPI **%** are **30D**; see the table caption for column definitions."
        )

    st.markdown(
        '<div class="jd-hub-subsection-head">'
        '<h2 class="home-main-heading">Networks table</h2></div>',
        unsafe_allow_html=True,
    )
    df = build_rwa_networks_page_dataframe(working)
    _show_rwa_networks_page_dataframe(df, height=rwa_table_height(len(df), max_h=900))
    st.caption(RWA_DATA_SOURCE_CAPTION)

    st.link_button(
        GLOBAL_MARKET_RWA_LINK_LABEL,
        GLOBAL_MARKET_RWA_URL,
        use_container_width=True,
        key="rwa_participants_rwa_link_full",
    )


def show_rwa_participants_platforms_widget(
    *,
    home_preview: bool = False,
    full_page_header: bool = False,
) -> None:
    """
    **Full page only**: **Participants — Platforms** with the /platforms overview KPIs + issuer table.
    """
    if home_preview:
        raise ValueError(
            "show_rwa_participants_platforms_widget is only for full pages; use show_rwa_league_widget on the hub."
        )

    st.markdown(
        WIDGET_CSS + KPI_WINDOW_NOTE_CSS + STREAMLIT_TABLE_UNIFY_CSS,
        unsafe_allow_html=True,
    )

    rows, kpis, err = load_rwa_platforms_cached()

    if err and not rows:
        st.warning(escape(err))
        st.markdown(
            f'<div class="jd-hub-subsection-head" id="jd-rwa-platforms-overview">'
            f'<h2 class="home-main-heading">{escape(RWA_PLATFORMS_SUBPAGE_OVERVIEW_HEADING)}</h2></div>',
            unsafe_allow_html=True,
        )
        _render_rwa_global_overview(kpis, kpi_legend_name="Platforms")
        st.link_button(
            PLATFORMS_RWA_LINK_LABEL,
            PLATFORMS_RWA_URL,
            use_container_width=True,
            key="rwa_pp_rwa_link_err_full",
        )
        return

    if not rows:
        st.info("No platform rows returned.")
        return

    if full_page_header:
        st.markdown(
            hub_subsection_heading_html(
                RWA_PLATFORMS_SUBPAGE_OVERVIEW_HEADING,
                element_id="jd-rwa-platforms-overview",
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="jd-hub-subsection-head" id="jd-rwa-participants-platforms">'
            '<h2 class="home-main-heading">Platforms</h2></div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Searchable **Distributed** Platforms issuer table from the [RWA.xyz Platforms](https://app.rwa.xyz/platforms) embed."
        )

    _render_rwa_global_overview(kpis, kpi_legend_name="Platforms")

    q = st.text_input(
        "Search platform",
        "",
        key="rwa_participants_platforms_search_full",
        placeholder="Filter by issuer / platform name…",
    )
    working = filter_platforms_tab_rows(rows, q)
    if q.strip():
        st.caption(
            f"Showing {len(working)} of {len(rows)} platforms matching “{escape(q.strip())}”."
        )
    else:
        st.caption(
            f"Showing all {len(working)} platforms. Headline KPI **%** are **30D**; see the table caption for columns."
        )

    st.markdown(
        '<div class="jd-hub-subsection-head">'
        '<h2 class="home-main-heading">Platforms table</h2></div>',
        unsafe_allow_html=True,
    )
    df = build_rwa_platforms_page_dataframe(working)
    _show_rwa_platforms_page_dataframe(df, height=rwa_table_height(len(df), max_h=900))
    st.caption(RWA_PLATFORMS_DATA_SOURCE_CAPTION)

    st.link_button(
        PLATFORMS_RWA_LINK_LABEL,
        PLATFORMS_RWA_URL,
        use_container_width=True,
        key="rwa_participants_platforms_rwa_link_full",
    )


def show_rwa_participants_asset_managers_widget(
    *,
    home_preview: bool = False,
    full_page_header: bool = False,
) -> None:
    """
    **Full page only**: **Participants — Asset Managers** with /asset-managers overview KPIs + Distributed table.
    """
    if home_preview:
        raise ValueError(
            "show_rwa_participants_asset_managers_widget is only for full pages; use show_rwa_league_widget on the hub."
        )

    st.markdown(
        WIDGET_CSS + KPI_WINDOW_NOTE_CSS + STREAMLIT_TABLE_UNIFY_CSS,
        unsafe_allow_html=True,
    )

    rows, kpis, err = load_rwa_asset_managers_cached()

    if err and not rows:
        st.warning(escape(err))
        st.markdown(
            f'<div class="jd-hub-subsection-head" id="jd-rwa-asset-managers-overview">'
            f'<h2 class="home-main-heading">{escape(RWA_ASSET_MANAGERS_SUBPAGE_OVERVIEW_HEADING)}</h2></div>',
            unsafe_allow_html=True,
        )
        _render_rwa_global_overview(kpis, kpi_legend_name="Asset Managers")
        st.link_button(
            ASSET_MANAGERS_RWA_LINK_LABEL,
            ASSET_MANAGERS_RWA_URL,
            use_container_width=True,
            key="rwa_pam_rwa_link_err_full",
        )
        return

    if not rows:
        st.info("No asset manager rows returned.")
        return

    if full_page_header:
        st.markdown(
            hub_subsection_heading_html(
                RWA_ASSET_MANAGERS_SUBPAGE_OVERVIEW_HEADING,
                element_id="jd-rwa-asset-managers-overview",
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="jd-hub-subsection-head" id="jd-rwa-participants-asset-managers">'
            '<h2 class="home-main-heading">Asset Managers</h2></div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Searchable **Distributed** Asset Managers table from the "
            "[RWA.xyz Asset Managers](https://app.rwa.xyz/asset-managers) embed."
        )

    _render_rwa_global_overview(kpis, kpi_legend_name="Asset Managers")

    q = st.text_input(
        "Search asset manager",
        "",
        key="rwa_participants_asset_managers_search_full",
        placeholder="Filter by manager name…",
    )
    working = filter_asset_managers_tab_rows(rows, q)
    if q.strip():
        st.caption(
            f"Showing {len(working)} of {len(rows)} asset managers matching “{escape(q.strip())}”."
        )
    else:
        st.caption(
            f"Showing all {len(working)} asset managers. Headline KPI **%** are **30D**; see the table caption for columns."
        )

    st.markdown(
        '<div class="jd-hub-subsection-head">'
        '<h2 class="home-main-heading">Asset Managers table</h2></div>',
        unsafe_allow_html=True,
    )
    df = build_rwa_asset_managers_page_dataframe(working)
    _show_rwa_asset_managers_page_dataframe(df, height=rwa_table_height(len(df), max_h=900))
    st.caption(RWA_ASSET_MANAGERS_DATA_SOURCE_CAPTION)

    st.link_button(
        ASSET_MANAGERS_RWA_LINK_LABEL,
        ASSET_MANAGERS_RWA_URL,
        use_container_width=True,
        key="rwa_participants_asset_managers_rwa_link_full",
    )


def show_rwa_onchain_explore_gateways(*, preview_rows: int = 8) -> None:
    """
    Home hub row under **RWA Global Market Overview**: two bordered columns with blurbs and **Explore** navigation
    to the asset-type and market-participant index pages.
    """
    _ = preview_rows
    st.divider()
    c1, c2 = st.columns(2, gap="medium", border=True)
    with c1:
        st.markdown(hub_section_anchor("jd-rwa-explore-asset-type"), unsafe_allow_html=True)
        st.markdown("### Explore by Asset Type")
        st.markdown(
            '<div class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-explore-blurb">'
            "<p>Short previews of on-chain data for:</p>"
            "<ul>"
            "<li>Stablecoins</li>"
            "<li>US Treasuries</li>"
            "<li>Tokenized stocks</li>"
            "</ul>"
            '<p class="jd-hub-explore-blurb--tail">Use <strong>Explore</strong> to open the hub and go deeper on the next pages.</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button(
            "Explore",
            key="hub_onchain_explore_asset_type",
            type="primary",
            use_container_width=True,
        ):
            st.switch_page("pages/RWA_Explore_By_Asset_Type.py")
    with c2:
        st.markdown(hub_section_anchor("jd-rwa-explore-market-participant"), unsafe_allow_html=True)
        st.markdown("### Explore by Market Participant")
        st.markdown(
            '<div class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-explore-blurb">'
            "<p>Short previews organized by who is in the market:</p>"
            "<ul>"
            "<li>Networks</li>"
            "<li>Platforms</li>"
            "<li>Asset managers</li>"
            "</ul>"
            '<p class="jd-hub-explore-blurb--tail">Use <strong>Explore</strong> to open the hub and go deeper on the next pages.</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button(
            "Explore",
            key="hub_onchain_explore_market_participant",
            type="primary",
            use_container_width=True,
        ):
            st.switch_page("pages/RWA_Explore_By_Market_Participant.py")


def show_rwa_explore_by_asset_type_widget(*, preview_rows: int = 8) -> None:
    """Index page: Stablecoins, US Treasuries, and Tokenized Stocks hub previews (``home_preview=True``)."""
    st.markdown(WIDGET_CSS + KPI_WINDOW_NOTE_CSS + STREAMLIT_TABLE_UNIFY_CSS, unsafe_allow_html=True)
    show_rwa_stablecoins_widget(home_preview=True, preview_rows=preview_rows)
    show_rwa_treasuries_widget(home_preview=True, preview_rows=preview_rows)
    show_rwa_tokenized_stocks_widget(home_preview=True, preview_rows=preview_rows)


def show_rwa_explore_by_market_participant_widget(*, preview_rows: int = 8) -> None:
    """Index page: Networks, Platforms, and Asset Managers hub previews (same blocks as the former home tail)."""
    st.markdown(WIDGET_CSS + KPI_WINDOW_NOTE_CSS + STREAMLIT_TABLE_UNIFY_CSS, unsafe_allow_html=True)
    rows, kpis, err = load_rwa_league_cached()
    if err and not rows:
        st.warning(escape(err))
        st.link_button(
            GLOBAL_MARKET_RWA_LINK_LABEL,
            GLOBAL_MARKET_RWA_URL,
            use_container_width=True,
            key="rwa_explore_mp_global_err",
        )
        return
    if not rows:
        st.info("No network rows returned; Participants previews need Global Market data.")
        return
    _show_rwa_participants_networks_home_footer(rows, kpis, preview_rows=preview_rows)
    plat_rows, plat_kpis, _plat_err = load_rwa_platforms_cached()
    if plat_rows:
        _show_rwa_participants_platforms_home_footer(plat_rows, plat_kpis, preview_rows=preview_rows)
    am_rows, am_kpis, _am_err = load_rwa_asset_managers_cached()
    if am_rows:
        _show_rwa_participants_asset_managers_home_footer(am_rows, am_kpis, preview_rows=preview_rows)


def show_rwa_league_widget(
    *,
    home_preview: bool = False,
    preview_rows: int = 8,
) -> None:
    """
    On-chain Data hub: **RWA Global Market Overview** (KPIs + Networks table), then **Explore by Asset Type** /
    **Explore by Market Participant** gateway columns when ``home_preview=True``. Full standalone Global Market uses
    ``home_preview=False`` (searchable table only).
    """
    st.markdown(WIDGET_CSS + KPI_WINDOW_NOTE_CSS + STREAMLIT_TABLE_UNIFY_CSS, unsafe_allow_html=True)
    rows, kpis, err = load_rwa_league_cached()
    status = _rwa_global_market_status(rows, kpis, err, home_preview=home_preview, preview_rows=preview_rows)
    if status == "STOP" and not home_preview:
        return
    if home_preview:
        show_rwa_onchain_explore_gateways(preview_rows=preview_rows)
