"""
RWA routes — same loaders and dataframe/figure pipeline as Streamlit ``rwa_league.widgets``.
"""

from __future__ import annotations

import sys
from html import escape
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from home_layout import (
    hub_subsection_heading_html,
    monthly_review_note_html,
    rwa_xyz_mirror_footer_text,
    section_label_teal,
)
# ── RWA data + figures (page takeaway/macro HTML is lazy-imported inside handlers) ─
from rwa_league.dataframe_table import (
    build_rwa_asset_managers_page_dataframe,
    build_rwa_dataframe,
    build_rwa_networks_page_dataframe,
    build_rwa_platforms_page_dataframe,
    build_stablecoin_network_dataframe,
    build_stablecoin_platform_dataframe,
    build_tokenized_stock_network_dataframe,
    build_tokenized_stock_platform_dataframe,
    build_us_treasury_network_dataframe,
    build_us_treasury_platform_dataframe,
    filter_asset_managers_tab_rows,
    filter_platforms_tab_rows,
    filter_rows_by_network,
    filter_stablecoin_network_rows,
    filter_stablecoin_platform_rows,
    filter_tokenized_stock_network_rows,
    filter_tokenized_stock_platform_rows,
    filter_treasury_network_rows,
    filter_treasury_platform_rows,
    style_rwa_asset_managers_page_dataframe,
    style_rwa_dataframe,
    style_rwa_networks_page_dataframe,
    style_rwa_platforms_page_dataframe,
    style_stablecoin_network_dataframe,
    style_stablecoin_platform_dataframe,
    style_tokenized_stock_network_dataframe,
    style_tokenized_stock_platform_dataframe,
    style_us_treasury_network_dataframe,
    style_us_treasury_platform_dataframe,
)
from rwa_league.widgets import (
    APP_ASSET_MANAGERS,
    APP_PLATFORMS,
    APP_STOCKS,
    APP_TREASURIES,
    ASSET_MANAGERS_RWA_LINK_LABEL,
    GLOBAL_MARKET_RWA_LINK_LABEL,
    GLOBAL_MARKET_RWA_URL,
    PLATFORMS_RWA_LINK_LABEL,
    RWA_ASSET_MANAGERS_DATA_SOURCE_CAPTION,
    RWA_DATA_SOURCE_CAPTION,
    RWA_GLOBAL_MARKET_DATA_SOURCE_CAPTION,
    RWA_GMO_CHART_MAX_BARS,
    RWA_PARTICIPANTS_CHART_MAX_BARS,
    RWA_PLATFORMS_DATA_SOURCE_CAPTION,
    RWA_STABLECOINS_CHART_MAX_BARS,
    RWA_TREASURIES_CHART_MAX_BARS,
    RWA_TOKENIZED_STOCKS_CHART_MAX_BARS,
    STABLECOIN_NETWORK_CAPTION,
    STABLECOIN_PLATFORM_CAPTION,
    STABLECOINS_RWA_LINK_LABEL,
    TREASURIES_RWA_LINK_LABEL,
    TREASURY_PLATFORM_CAPTION,
    TREASURY_RWA_CAPTION,
    TOKENIZED_STOCKS_RWA_CAPTION,
    TOKENIZED_STOCKS_RWA_LINK_LABEL,
    _rwa_global_market_top_networks_bar_figure,
    _rwa_participants_asset_managers_tab_bar_figure,
    _rwa_participants_networks_tab_bar_figure,
    _rwa_participants_platforms_tab_bar_figure,
    _rwa_stablecoins_top_networks_bar_figure,
    _rwa_stablecoins_top_platforms_bar_figure,
    _rwa_tokenized_stocks_top_platforms_bar_figure,
    _rwa_treasuries_top_networks_bar_figure,
    _rwa_treasuries_top_platforms_bar_figure,
    load_rwa_asset_managers_cached,
    load_rwa_global_market_cached,
    load_rwa_league_cached,
    load_rwa_platforms_cached,
    load_rwa_stablecoins_cached,
    load_rwa_tokenized_stocks_cached,
    load_rwa_treasuries_cached,
    rwa_table_height,
)

from webapp.config import TEMPLATES
from webapp.context import html_shell_context
from webapp.formatters import (
    plotly_figure_to_div,
    rwa_explore_gateways_html,
    rwa_global_kpi_block_html,
    rwa_overview_kpi_inline_html,
    styled_dataframe_to_html,
)

router = APIRouter(tags=["rwa"])


def _rwa_response(
    request: Request,
    *,
    page_title: str,
    head_block: str,
    body_html: str,
    footer_note: str,
):
    return TEMPLATES.TemplateResponse(
        "rwa_page.html",
        html_shell_context(
            request,
            page_title=page_title,
            head_block=head_block,
            body_html=body_html,
            footer_note=footer_note,
        ),
    )


def _rwa_std_head(*, title: str, subtitle: str) -> str:
    return (
        section_label_teal(title, placement="first")
        + f'<p class="jd-hub-dek jd-hub-dek-fullbleed jd-hub-dek--large">{subtitle}</p><hr class="jd-divider" />'
    )


@router.get("/rwa/global", response_class=HTMLResponse)
async def rwa_global_market(request: Request, q: str = "") -> HTMLResponse:
    from pages.RWA_Global_Market_Overview import RWA_GLOBAL_MARKET_MACRO_CONTEXT_HTML  # noqa: PLC0415

    rows, kpis, err = load_rwa_global_market_cached()
    search_q = (q or "").strip()
    body_parts: list[str] = []

    if err and not rows:
        body_parts.append(f'<p class="alert warn">{escape(err)}</p>')
        body_parts.append(rwa_global_kpi_block_html(kpis, kpi_legend_name="Global Market"))
        body_parts.append(
            f'<p><a class="btn primary" href="{escape(GLOBAL_MARKET_RWA_URL, quote=True)}" '
            f'target="_blank" rel="noopener noreferrer">{escape(GLOBAL_MARKET_RWA_LINK_LABEL)}</a></p>'
        )
    elif not rows:
        body_parts.append('<p class="alert info">No network rows returned.</p>')
        body_parts.append(rwa_global_kpi_block_html(kpis, kpi_legend_name="Global Market"))
    else:
        working = filter_rows_by_network(rows, search_q)
        if search_q:
            body_parts.append(
                f'<p class="toolbar-note">Showing {len(working)} of {len(rows)} networks matching '
                f'"{escape(search_q)}".</p>'
            )
        else:
            body_parts.append(
                f'<p class="toolbar-note">Showing all {len(working)} networks from the Global Market Overview table.</p>'
            )
        body_parts.append(
            hub_subsection_heading_html("Top-Line Market Snapshot", element_id="jd-rwa-gmo-kpis")
        )
        body_parts.append(rwa_global_kpi_block_html(kpis, kpi_legend_name="Global Market", tight_bottom=False))
        body_parts.append(hub_subsection_heading_html("Key Observations", element_id="jd-rwa-gmo-ko"))
        body_parts.append(RWA_GLOBAL_MARKET_MACRO_CONTEXT_HTML + monthly_review_note_html())
        body_parts.append('<hr class="jd-rwa-gmo-soft-rule" />')
        body_parts.append(rwa_explore_gateways_html("rwa_gmo"))
        body_parts.append(
            '<form class="inline-search" method="get" action="/rwa/global">'
            '<label for="qg">Search network table</label>'
            '<input id="qg" name="q" type="search" placeholder="Filter by network name…" '
            f'value="{escape(search_q, quote=True)}" />'
            '<button type="submit" class="btn">Filter</button>'
            '<a class="btn secondary" href="/rwa/global">Clear</a>'
            "</form>"
        )
        df = build_rwa_dataframe(working)
        chart_rows = sorted(working, key=lambda r: r.total_value_usd, reverse=True)[:RWA_GMO_CHART_MAX_BARS]
        n_sync = min(RWA_GMO_CHART_MAX_BARS, len(working)) if working else max(1, len(df))
        split_h = rwa_table_height(max(1, n_sync), max_h=560)
        fig = (
            _rwa_global_market_top_networks_bar_figure(chart_rows, height=split_h)
            if chart_rows
            else None
        )
        body_parts.append('<div class="split-two">')
        body_parts.append("<div>")
        body_parts.append(
            hub_subsection_heading_html("Networks table", element_id="jd-rwa-gmo-table")
        )
        body_parts.append(styled_dataframe_to_html(style_rwa_dataframe(df), table_id="rwa-gmo-tbl"))
        body_parts.append("</div><div>")
        body_parts.append(
            hub_subsection_heading_html("Top networks by value", element_id="jd-rwa-gmo-bar")
        )
        if fig:
            body_parts.append(plotly_figure_to_div(fig))
        else:
            body_parts.append('<p class="muted">No networks match this filter; there is nothing to chart.</p>')
        body_parts.append("</div></div>")
        body_parts.append(
            '<p class="jd-hub-cta-note">The chart lists the top <strong>12</strong> networks by total value '
            "(labels include market share). Scroll the table for the full filtered list.</p>"
        )
        body_parts.append(f'<p class="caption">{RWA_GLOBAL_MARKET_DATA_SOURCE_CAPTION}</p>')
        body_parts.append(
            f'<p><a class="btn" href="{escape(GLOBAL_MARKET_RWA_URL, quote=True)}" '
            f'target="_blank" rel="noopener noreferrer">{escape(GLOBAL_MARKET_RWA_LINK_LABEL)}</a></p>'
        )

    return _rwa_response(
        request,
        page_title="RWA Global Market Overview",
        head_block=_rwa_std_head(
            title="RWA Global Market Overview",
            subtitle=(
                'RWA <strong>Global Market Overview</strong>: the same headline metrics and <strong>Networks</strong> '
                'table as the <a href="https://app.rwa.xyz/">RWA.xyz</a> <strong>Market Overview</strong> tab.'
            ),
        ),
        body_html="".join(body_parts),
        footer_note=rwa_xyz_mirror_footer_text(),
    )


@router.get("/rwa/stablecoins", response_class=HTMLResponse)
async def rwa_stablecoins(
    request: Request,
    net_q: str = "",
    plat_q: str = "",
) -> HTMLResponse:
    rows_net, rows_plat, kpis, err = load_rwa_stablecoins_cached()
    nq = (net_q or "").strip()
    pq = (plat_q or "").strip()
    parts: list[str] = []

    if err and not rows_net and not rows_plat:
        parts.append(f'<p class="alert warn">{escape(err)}</p>')
        parts.append(rwa_overview_kpi_inline_html(kpis, overview_title="Stablecoins"))
        parts.append(
            f'<p><a class="btn primary" href="https://app.rwa.xyz/stablecoins" target="_blank" '
            f'rel="noopener noreferrer">{escape(STABLECOINS_RWA_LINK_LABEL)}</a></p>'
        )
    elif not rows_net and not rows_plat:
        parts.append('<p class="alert info">No Stablecoins league rows returned.</p>')
        parts.append(rwa_overview_kpi_inline_html(kpis, overview_title="Stablecoins"))
        parts.append(
            f'<p><a class="btn" href="https://app.rwa.xyz/stablecoins" target="_blank" '
            f'rel="noopener noreferrer">{escape(STABLECOINS_RWA_LINK_LABEL)}</a></p>'
        )
    else:
        parts.append(hub_subsection_heading_html("Top-Line Market Snapshot"))
        parts.append(rwa_overview_kpi_inline_html(kpis, overview_title="Stablecoins"))
        parts.append(hub_subsection_heading_html("Key Observations"))
        from pages.RWA_Stablecoins import _stablecoins_takeaway_html  # noqa: PLC0415

        parts.append(_stablecoins_takeaway_html())
        parts.append('<hr class="jd-rwa-gmo-soft-rule" />')
        # Networks block
        if rows_net:
            working_n = filter_stablecoin_network_rows(rows_net, nq)
            parts.append(
                '<form class="inline-search" method="get" action="/rwa/stablecoins">'
                '<input type="hidden" name="plat_q" '
                f'value="{escape(pq, quote=True)}" />'
                '<label for="net_q">Search network table</label>'
                '<input id="net_q" name="net_q" type="search" placeholder="Filter by network name…" '
                f'value="{escape(nq, quote=True)}" />'
                '<button type="submit" class="btn">Filter</button></form>'
            )
            parts.append(
                hub_subsection_heading_html("By network (Stablecoins · Networks)")
            )
            chart_rows_n = sorted(working_n, key=lambda r: r.total_value_usd, reverse=True)[
                :RWA_STABLECOINS_CHART_MAX_BARS
            ]
            n_sync_n = (
                min(RWA_STABLECOINS_CHART_MAX_BARS, len(working_n)) if working_n else max(1, len(working_n))
            )
            split_h_n = rwa_table_height(max(1, n_sync_n), max_h=560)
            df_n = build_stablecoin_network_dataframe(working_n)
            fig_n = (
                _rwa_stablecoins_top_networks_bar_figure(chart_rows_n, height=split_h_n) if chart_rows_n else None
            )
            parts.append('<div class="split-two">')
            parts.append("<div>")
            parts.append(hub_subsection_heading_html("Networks table"))
            parts.append(styled_dataframe_to_html(style_stablecoin_network_dataframe(df_n)))
            parts.append(f'<p class="caption">{STABLECOIN_NETWORK_CAPTION}</p>')
            parts.append("</div><div>")
            parts.append(hub_subsection_heading_html("Top networks by value"))
            parts.append(plotly_figure_to_div(fig_n) if fig_n else "<p>No chart data.</p>")
            parts.append("</div></div>")
        # Platforms block
        if rows_plat:
            working_p = filter_stablecoin_platform_rows(rows_plat, pq)
            parts.append('<hr class="jd-divider" />')
            parts.append(
                '<form class="inline-search" method="get" action="/rwa/stablecoins">'
                '<input type="hidden" name="net_q" '
                f'value="{escape(nq, quote=True)}" />'
                '<label for="plat_q">Search platform table</label>'
                '<input id="plat_q" name="plat_q" type="search" placeholder="Filter by platform name…" '
                f'value="{escape(pq, quote=True)}" />'
                '<button type="submit" class="btn">Filter</button></form>'
            )
            parts.append(
                hub_subsection_heading_html("By platform (Stablecoins · Platforms)")
            )
            chart_rows_p = sorted(working_p, key=lambda r: r.total_value_usd, reverse=True)[
                :RWA_STABLECOINS_CHART_MAX_BARS
            ]
            n_sync_p = (
                min(RWA_STABLECOINS_CHART_MAX_BARS, len(working_p)) if working_p else max(1, len(working_p))
            )
            split_h_p = rwa_table_height(max(1, n_sync_p), max_h=560)
            df_p = build_stablecoin_platform_dataframe(working_p)
            fig_p = (
                _rwa_stablecoins_top_platforms_bar_figure(chart_rows_p, height=split_h_p) if chart_rows_p else None
            )
            parts.append('<div class="split-two">')
            parts.append("<div>")
            parts.append(hub_subsection_heading_html("Platforms table"))
            parts.append(styled_dataframe_to_html(style_stablecoin_platform_dataframe(df_p)))
            parts.append(f'<p class="caption">{STABLECOIN_PLATFORM_CAPTION}</p>')
            parts.append("</div><div>")
            parts.append(hub_subsection_heading_html("Top platforms by value"))
            parts.append(plotly_figure_to_div(fig_p) if fig_p else "<p>No chart data.</p>")
            parts.append("</div></div>")
        parts.append(
            f'<p><a class="btn" href="https://app.rwa.xyz/stablecoins" target="_blank" '
            f'rel="noopener noreferrer">{escape(STABLECOINS_RWA_LINK_LABEL)}</a></p>'
        )

    return _rwa_response(
        request,
        page_title="Stablecoins",
        head_block=_rwa_std_head(
            title="Stablecoins",
            subtitle=(
                'Mirrors <a href="https://app.rwa.xyz/stablecoins">RWA.xyz Stablecoins</a> — '
                "<strong>30D</strong> % changes plus Networks and Platforms tables."
            ),
        ),
        body_html="".join(parts),
        footer_note=rwa_xyz_mirror_footer_text(),
    )


@router.get("/rwa/treasuries", response_class=HTMLResponse)
async def rwa_treasuries(
    request: Request,
    net_q: str = "",
    plat_q: str = "",
) -> HTMLResponse:
    rows_tr, plat_tr, kpis_tr, err_tr = load_rwa_treasuries_cached()
    nq = (net_q or "").strip()
    pq = (plat_q or "").strip()
    parts: list[str] = []

    if err_tr and not rows_tr and not plat_tr:
        parts.append(f'<p class="alert warn">{escape(err_tr)}</p>')
        parts.append(rwa_overview_kpi_inline_html(kpis_tr, overview_title="US Treasuries"))
        parts.append(
            f'<p><a class="btn primary" href="{escape(APP_TREASURIES, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(TREASURIES_RWA_LINK_LABEL)}</a></p>'
        )
    elif not rows_tr and not plat_tr:
        parts.append('<p class="alert info">No US Treasuries league rows returned.</p>')
        parts.append(rwa_overview_kpi_inline_html(kpis_tr, overview_title="US Treasuries"))
        parts.append(
            f'<p><a class="btn" href="{escape(APP_TREASURIES, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(TREASURIES_RWA_LINK_LABEL)}</a></p>'
        )
    else:
        parts.append(hub_subsection_heading_html("Top-Line Market Snapshot"))
        parts.append(rwa_overview_kpi_inline_html(kpis_tr, overview_title="US Treasuries"))
        parts.append(hub_subsection_heading_html("Key Observations"))
        from pages.RWA_US_Treasuries import _treasuries_takeaway_html  # noqa: PLC0415

        parts.append(_treasuries_takeaway_html())
        parts.append('<hr class="jd-rwa-gmo-soft-rule" />')
        if rows_tr:
            working = filter_treasury_network_rows(rows_tr, nq)
            parts.append(
                '<form class="inline-search" method="get" action="/rwa/treasuries">'
                '<input type="hidden" name="plat_q" '
                f'value="{escape(pq, quote=True)}" />'
                '<label for="tnq">Search network table</label>'
                '<input id="tnq" name="net_q" type="search" '
                f'value="{escape(nq, quote=True)}" />'
                '<button type="submit" class="btn">Filter</button></form>'
            )
            parts.append(
                hub_subsection_heading_html("By network (Distributed · Networks)")
            )
            chart_rows = sorted(working, key=lambda r: r.total_value_usd, reverse=True)[:RWA_TREASURIES_CHART_MAX_BARS]
            split_h = rwa_table_height(max(1, min(RWA_TREASURIES_CHART_MAX_BARS, len(working))), max_h=560)
            df_tr = build_us_treasury_network_dataframe(working)
            fig = _rwa_treasuries_top_networks_bar_figure(chart_rows, height=split_h) if chart_rows else None
            parts.append('<div class="split-two">')
            parts.append("<div>")
            parts.append(hub_subsection_heading_html("Networks table"))
            parts.append(
                styled_dataframe_to_html(
                    style_us_treasury_network_dataframe(df_tr),
                )
            )
            parts.append(f'<p class="caption">{TREASURY_RWA_CAPTION}</p>')
            parts.append("</div><div>")
            parts.append(hub_subsection_heading_html("Top networks by value"))
            parts.append(plotly_figure_to_div(fig) if fig else "<p>No chart.</p>")
            parts.append("</div></div>")
        if plat_tr:
            working_p = filter_treasury_platform_rows(plat_tr, pq)
            parts.append('<hr class="jd-divider" />')
            parts.append(
                '<form class="inline-search" method="get" action="/rwa/treasuries">'
                '<input type="hidden" name="net_q" '
                f'value="{escape(nq, quote=True)}" />'
                '<label for="tpq">Search platform table</label>'
                '<input id="tpq" name="plat_q" type="search" '
                f'value="{escape(pq, quote=True)}" />'
                '<button type="submit" class="btn">Filter</button></form>'
            )
            parts.append(
                hub_subsection_heading_html("By platform (Distributed · Platforms)")
            )
            chart_rows_p = sorted(working_p, key=lambda r: r.total_value_usd, reverse=True)[
                :RWA_TREASURIES_CHART_MAX_BARS
            ]
            split_hp = rwa_table_height(
                max(1, min(RWA_TREASURIES_CHART_MAX_BARS, len(working_p))),
                max_h=560,
            )
            df_p = build_us_treasury_platform_dataframe(working_p)
            fig_p = (
                _rwa_treasuries_top_platforms_bar_figure(chart_rows_p, height=split_hp) if chart_rows_p else None
            )
            parts.append('<div class="split-two">')
            parts.append("<div>")
            parts.append(hub_subsection_heading_html("Platforms table"))
            parts.append(styled_dataframe_to_html(style_us_treasury_platform_dataframe(df_p)))
            parts.append(f'<p class="caption">{TREASURY_PLATFORM_CAPTION}</p>')
            parts.append("</div><div>")
            parts.append(hub_subsection_heading_html("Top platforms by value"))
            parts.append(plotly_figure_to_div(fig_p) if fig_p else "<p>No chart.</p>")
            parts.append("</div></div>")
        parts.append(
            f'<p><a class="btn" href="{escape(APP_TREASURIES, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(TREASURIES_RWA_LINK_LABEL)}</a></p>'
        )

    return _rwa_response(
        request,
        page_title="US Treasuries",
        head_block=_rwa_std_head(
            title="US Treasuries",
            subtitle=(
                f'Mirrors <a href="{APP_TREASURIES}">RWA.xyz US Treasuries</a> — Distributed Networks and Platforms.'
            ),
        ),
        body_html="".join(parts),
        footer_note=rwa_xyz_mirror_footer_text(),
    )


_PREVIEW = 8


@router.get("/rwa/tokenized-stocks", response_class=HTMLResponse)
async def rwa_tokenized_stocks(
    request: Request,
    net_q: str = "",
    plat_q: str = "",
) -> HTMLResponse:
    rows_net, rows_plat, kpis_st, err_st = load_rwa_tokenized_stocks_cached()
    nq = (net_q or "").strip()
    pq = (plat_q or "").strip()
    parts: list[str] = []

    if err_st and not rows_net and not rows_plat:
        parts.append(f'<p class="alert warn">{escape(err_st)}</p>')
        parts.append(rwa_overview_kpi_inline_html(kpis_st, overview_title="Tokenized Stocks"))
        parts.append(
            f'<p><a class="btn primary" href="{escape(APP_STOCKS, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(TOKENIZED_STOCKS_RWA_LINK_LABEL)}</a></p>'
        )
    elif not rows_net and not rows_plat:
        parts.append('<p class="alert info">No Tokenized Stocks league rows returned.</p>')
        parts.append(rwa_overview_kpi_inline_html(kpis_st, overview_title="Tokenized Stocks"))
        parts.append(
            f'<p><a class="btn" href="{escape(APP_STOCKS, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(TOKENIZED_STOCKS_RWA_LINK_LABEL)}</a></p>'
        )
    else:
        parts.append(hub_subsection_heading_html("Top-Line Market Snapshot"))
        parts.append(rwa_overview_kpi_inline_html(kpis_st, overview_title="Tokenized Stocks"))
        parts.append(hub_subsection_heading_html("Key Observations"))
        from pages.RWA_Tokenized_Stocks import _tokenized_stocks_takeaway_html  # noqa: PLC0415

        parts.append(_tokenized_stocks_takeaway_html())
        parts.append('<hr class="jd-rwa-gmo-soft-rule" />')
        if rows_net:
            working_n = filter_tokenized_stock_network_rows(rows_net, nq)
            working_n = sorted(working_n, key=lambda r: int(r.rank))
            parts.append(
                '<form class="inline-search" method="get" action="/rwa/tokenized-stocks">'
                '<input type="hidden" name="plat_q" '
                f'value="{escape(pq, quote=True)}" />'
                '<label for="stnq">Search network table</label>'
                '<input id="stnq" name="net_q" type="search" '
                f'value="{escape(nq, quote=True)}" />'
                '<button type="submit" class="btn">Filter</button></form>'
            )
            parts.append(
                hub_subsection_heading_html("By Network (Distributed · Networks)")
            )
            chart_rows_n = sorted(working_n, key=lambda r: r.total_value_usd, reverse=True)[
                :RWA_TOKENIZED_STOCKS_CHART_MAX_BARS
            ]
            split_hn = rwa_table_height(
                max(1, min(RWA_TOKENIZED_STOCKS_CHART_MAX_BARS, len(working_n))),
                max_h=560,
            )
            df_n = build_tokenized_stock_network_dataframe(working_n)
            fig_n = (
                _rwa_global_market_top_networks_bar_figure(chart_rows_n, height=split_hn) if chart_rows_n else None
            )
            parts.append('<div class="split-two">')
            parts.append("<div>")
            parts.append(hub_subsection_heading_html("Networks table"))
            parts.append(styled_dataframe_to_html(style_tokenized_stock_network_dataframe(df_n)))
            parts.append("</div><div>")
            parts.append(hub_subsection_heading_html("Top networks by value"))
            parts.append(plotly_figure_to_div(fig_n) if fig_n else "<p>No chart.</p>")
            parts.append("</div></div>")
        if rows_plat:
            parts.append('<hr class="jd-divider" />')
            working_p = filter_tokenized_stock_platform_rows(rows_plat, pq)
            parts.append(
                '<form class="inline-search" method="get" action="/rwa/tokenized-stocks">'
                '<input type="hidden" name="net_q" '
                f'value="{escape(nq, quote=True)}" />'
                '<label for="stpq">Search platform table</label>'
                '<input id="stpq" name="plat_q" type="search" '
                f'value="{escape(pq, quote=True)}" />'
                '<button type="submit" class="btn">Filter</button></form>'
            )
            parts.append(
                hub_subsection_heading_html("By Platform (Distributed · Platforms)")
            )
            chart_rows_p = sorted(working_p, key=lambda r: r.total_value_usd, reverse=True)[
                :RWA_TOKENIZED_STOCKS_CHART_MAX_BARS
            ]
            split_hp = rwa_table_height(
                max(1, min(RWA_TOKENIZED_STOCKS_CHART_MAX_BARS, len(working_p))),
                max_h=560,
            )
            df_p = build_tokenized_stock_platform_dataframe(working_p)
            fig_p = (
                _rwa_tokenized_stocks_top_platforms_bar_figure(chart_rows_p, height=split_hp)
                if chart_rows_p
                else None
            )
            parts.append('<div class="split-two">')
            parts.append("<div>")
            parts.append(hub_subsection_heading_html("Platforms table"))
            parts.append(styled_dataframe_to_html(style_tokenized_stock_platform_dataframe(df_p)))
            parts.append(f'<p class="caption">{TOKENIZED_STOCKS_RWA_CAPTION}</p>')
            parts.append("</div><div>")
            parts.append(hub_subsection_heading_html("Top platforms by value"))
            parts.append(plotly_figure_to_div(fig_p) if fig_p else "<p>No chart.</p>")
            parts.append("</div></div>")
        parts.append(
            f'<p><a class="btn" href="{escape(APP_STOCKS, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(TOKENIZED_STOCKS_RWA_LINK_LABEL)}</a></p>'
        )

    return _rwa_response(
        request,
        page_title="Tokenized Stocks",
        head_block=_rwa_std_head(
            title="Tokenized Stocks",
            subtitle=f'Mirrors <a href="{APP_STOCKS}">RWA.xyz Tokenized Stocks</a> — Networks and Platforms.',
        ),
        body_html="".join(parts),
        footer_note=rwa_xyz_mirror_footer_text(),
    )


@router.get("/rwa/participants/networks", response_class=HTMLResponse)
async def rwa_participants_networks(request: Request, q: str = "") -> HTMLResponse:
    rows, kpis, err = load_rwa_league_cached()
    sq = (q or "").strip()
    parts: list[str] = []
    if err and not rows:
        parts.append(f'<p class="alert warn">{escape(err)}</p>')
        parts.append(rwa_global_kpi_block_html(kpis, kpi_legend_name="Networks"))
        parts.append(
            f'<p><a class="btn" href="{escape(GLOBAL_MARKET_RWA_URL, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(GLOBAL_MARKET_RWA_LINK_LABEL)}</a></p>'
        )
    elif not rows:
        parts.append('<p class="alert info">No network rows returned.</p>')
    else:
        parts.append(hub_subsection_heading_html("Top-Line Market Snapshot"))
        parts.append(rwa_global_kpi_block_html(kpis, kpi_legend_name="Networks"))
        parts.append(hub_subsection_heading_html("Key Observations"))
        from pages.RWA_Participants_Networks import (  # noqa: PLC0415
            _participants_networks_takeaway_html,
        )

        parts.append(_participants_networks_takeaway_html())
        parts.append('<hr class="jd-rwa-gmo-soft-rule" />')
        working = filter_rows_by_network(rows, sq)
        parts.append(
            '<form class="inline-search" method="get" action="/rwa/participants/networks">'
            '<label for="pnq">Search network table</label>'
            f'<input id="pnq" name="q" type="search" value="{escape(sq, quote=True)}" />'
            '<button type="submit" class="btn">Filter</button></form>'
        )
        df = build_rwa_networks_page_dataframe(working)
        chart_rows = sorted(working, key=lambda r: r.distributed_usd, reverse=True)[:RWA_PARTICIPANTS_CHART_MAX_BARS]
        split_h = rwa_table_height(max(1, min(RWA_PARTICIPANTS_CHART_MAX_BARS, len(working))), max_h=560)
        fig = _rwa_participants_networks_tab_bar_figure(chart_rows, height=split_h) if chart_rows else None
        parts.append('<div class="split-two">')
        parts.append("<div>")
        parts.append(hub_subsection_heading_html("Networks table"))
        parts.append(styled_dataframe_to_html(style_rwa_networks_page_dataframe(df)))
        parts.append("</div><div>")
        parts.append(hub_subsection_heading_html("Top networks by distributed value"))
        parts.append(plotly_figure_to_div(fig) if fig else "<p>No chart.</p>")
        parts.append("</div></div>")
        parts.append(f'<p class="caption">{RWA_DATA_SOURCE_CAPTION}</p>')
        parts.append(
            f'<p><a class="btn" href="{escape(GLOBAL_MARKET_RWA_URL, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(GLOBAL_MARKET_RWA_LINK_LABEL)}</a></p>'
        )
    return _rwa_response(
        request,
        page_title="Participants — Networks",
        head_block=_rwa_std_head(
            title="Participants — Networks",
            subtitle='Mirrors <a href="https://app.rwa.xyz/networks">RWA.xyz Networks</a> — Distributed Networks league.',
        ),
        body_html="".join(parts),
        footer_note=rwa_xyz_mirror_footer_text(),
    )


@router.get("/rwa/participants/platforms", response_class=HTMLResponse)
async def rwa_participants_platforms(request: Request, q: str = "") -> HTMLResponse:
    rows, kpis, err = load_rwa_platforms_cached()
    sq = (q or "").strip()
    parts: list[str] = []
    if err and not rows:
        parts.append(f'<p class="alert warn">{escape(err)}</p>')
        parts.append(rwa_global_kpi_block_html(kpis, kpi_legend_name="Platforms"))
        parts.append(
            f'<p><a class="btn" href="{escape(APP_PLATFORMS, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(PLATFORMS_RWA_LINK_LABEL)}</a></p>'
        )
    elif not rows:
        parts.append('<p class="alert info">No platform rows returned.</p>')
    else:
        parts.append(hub_subsection_heading_html("Top-Line Market Snapshot"))
        parts.append(rwa_global_kpi_block_html(kpis, kpi_legend_name="Platforms"))
        parts.append(hub_subsection_heading_html("Key Observations"))
        from pages.RWA_Participants_Platforms import (  # noqa: PLC0415
            _participants_platforms_takeaway_html,
        )

        parts.append(_participants_platforms_takeaway_html())
        parts.append('<hr class="jd-rwa-gmo-soft-rule" />')
        working = filter_platforms_tab_rows(rows, sq)
        df = build_rwa_platforms_page_dataframe(working)
        chart_rows = sorted(working, key=lambda r: r.distributed_usd, reverse=True)[:RWA_PARTICIPANTS_CHART_MAX_BARS]
        split_h = rwa_table_height(max(1, min(RWA_PARTICIPANTS_CHART_MAX_BARS, len(working))), max_h=560)
        fig = _rwa_participants_platforms_tab_bar_figure(chart_rows, height=split_h) if chart_rows else None
        parts.append(
            '<form class="inline-search" method="get" action="/rwa/participants/platforms">'
            '<label for="ppq">Search platform</label>'
            f'<input id="ppq" name="q" type="search" value="{escape(sq, quote=True)}" />'
            '<button type="submit" class="btn">Filter</button></form>'
        )
        parts.append('<div class="split-two">')
        parts.append("<div>")
        parts.append(hub_subsection_heading_html("Platforms table"))
        parts.append(styled_dataframe_to_html(style_rwa_platforms_page_dataframe(df)))
        parts.append("</div><div>")
        parts.append(hub_subsection_heading_html("Top platforms by value"))
        parts.append(plotly_figure_to_div(fig) if fig else "<p>No chart.</p>")
        parts.append("</div></div>")
        parts.append(f'<p class="caption">{RWA_PLATFORMS_DATA_SOURCE_CAPTION}</p>')
        parts.append(
            f'<p><a class="btn" href="{escape(APP_PLATFORMS, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(PLATFORMS_RWA_LINK_LABEL)}</a></p>'
        )
    return _rwa_response(
        request,
        page_title="Participants — Platforms",
        head_block=_rwa_std_head(
            title="Participants — Platforms",
            subtitle='Mirrors <a href="https://app.rwa.xyz/platforms">RWA.xyz Platforms</a> — Distributed Platforms league.',
        ),
        body_html="".join(parts),
        footer_note=rwa_xyz_mirror_footer_text(),
    )


@router.get("/rwa/participants/asset-managers", response_class=HTMLResponse)
async def rwa_participants_asset_managers(request: Request, q: str = "") -> HTMLResponse:
    rows, kpis, err = load_rwa_asset_managers_cached()
    sq = (q or "").strip()
    parts: list[str] = []
    if err and not rows:
        parts.append(f'<p class="alert warn">{escape(err)}</p>')
        parts.append(rwa_global_kpi_block_html(kpis, kpi_legend_name="Asset Managers"))
        parts.append(
            f'<p><a class="btn" href="{escape(APP_ASSET_MANAGERS, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(ASSET_MANAGERS_RWA_LINK_LABEL)}</a></p>'
        )
    elif not rows:
        parts.append('<p class="alert info">No asset manager rows returned.</p>')
    else:
        parts.append(hub_subsection_heading_html("Top-Line Market Snapshot"))
        parts.append(rwa_global_kpi_block_html(kpis, kpi_legend_name="Asset Managers"))
        parts.append(hub_subsection_heading_html("Key Observations"))
        from pages.RWA_Participants_Asset_Managers import (  # noqa: PLC0415
            _participants_asset_managers_takeaway_html,
        )

        parts.append(_participants_asset_managers_takeaway_html())
        parts.append('<hr class="jd-rwa-gmo-soft-rule" />')
        working = filter_asset_managers_tab_rows(rows, sq)
        df = build_rwa_asset_managers_page_dataframe(working)
        chart_rows = sorted(working, key=lambda r: r.distributed_usd, reverse=True)[:RWA_PARTICIPANTS_CHART_MAX_BARS]
        split_h = rwa_table_height(max(1, min(RWA_PARTICIPANTS_CHART_MAX_BARS, len(working))), max_h=560)
        fig = _rwa_participants_asset_managers_tab_bar_figure(chart_rows, height=split_h) if chart_rows else None
        parts.append(
            '<form class="inline-search" method="get" action="/rwa/participants/asset-managers">'
            '<label for="amq">Search asset managers</label>'
            f'<input id="amq" name="q" type="search" value="{escape(sq, quote=True)}" />'
            '<button type="submit" class="btn">Filter</button></form>'
        )
        parts.append('<div class="split-two">')
        parts.append("<div>")
        parts.append(hub_subsection_heading_html("Asset Managers table"))
        parts.append(styled_dataframe_to_html(style_rwa_asset_managers_page_dataframe(df)))
        parts.append("</div><div>")
        parts.append(hub_subsection_heading_html("Top asset managers by value"))
        parts.append(plotly_figure_to_div(fig) if fig else "<p>No chart.</p>")
        parts.append("</div></div>")
        parts.append(f'<p class="caption">{RWA_ASSET_MANAGERS_DATA_SOURCE_CAPTION}</p>')
        parts.append(
            f'<p><a class="btn" href="{escape(APP_ASSET_MANAGERS, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(ASSET_MANAGERS_RWA_LINK_LABEL)}</a></p>'
        )
    return _rwa_response(
        request,
        page_title="Participants — Asset Managers",
        head_block=_rwa_std_head(
            title="Participants — Asset Managers",
            subtitle='Mirrors <a href="https://app.rwa.xyz/asset-managers">RWA.xyz Asset Managers</a>.',
        ),
        body_html="".join(parts),
        footer_note=rwa_xyz_mirror_footer_text(),
    )


@router.get("/rwa/explore/asset-type", response_class=HTMLResponse)
async def rwa_explore_asset_type(request: Request) -> HTMLResponse:
    sc_net, sc_plat, sc_kpis, sc_err = load_rwa_stablecoins_cached()
    tr_rows, tr_plat, tr_kpis, tr_err = load_rwa_treasuries_cached()
    st_net, st_plat, st_kpis, st_err = load_rwa_tokenized_stocks_cached()
    blocks: list[str] = []
    # Stablecoins — platforms preview (matches Streamlit hub)
    blocks.append("<h3>Stablecoins</h3>")
    if sc_err and not sc_plat:
        blocks.append(f'<p class="alert warn">{escape(sc_err)}</p>')
    elif sc_plat:
        prev = sc_plat[:_PREVIEW]
        df = build_stablecoin_platform_dataframe(prev)
        blocks.append(styled_dataframe_to_html(style_stablecoin_platform_dataframe(df)))
    else:
        blocks.append('<p class="muted"><em>No platform rows.</em></p>')
    blocks.append('<p><a class="btn primary" href="/rwa/stablecoins">Full Stablecoins view</a></p>')
    # Treasuries — networks preview
    blocks.append("<h3>US Treasuries</h3>")
    if tr_err and not tr_rows:
        blocks.append(f'<p class="alert warn">{escape(tr_err)}</p>')
    elif tr_rows:
        prev = tr_rows[:_PREVIEW]
        df = build_us_treasury_network_dataframe(prev)
        blocks.append(styled_dataframe_to_html(style_us_treasury_network_dataframe(df)))
    else:
        blocks.append("<p><em>No treasury network rows.</em></p>")
    blocks.append('<p><a class="btn primary" href="/rwa/treasuries">Full US Treasuries view</a></p>')
    # Tokenized stocks — platforms preview
    blocks.append("<h3>Tokenized Stocks</h3>")
    if st_err and not st_plat:
        blocks.append(f'<p class="alert warn">{escape(st_err)}</p>')
    elif st_plat:
        prev = st_plat[:_PREVIEW]
        df = build_tokenized_stock_platform_dataframe(prev)
        blocks.append(styled_dataframe_to_html(style_tokenized_stock_platform_dataframe(df)))
    else:
        blocks.append("<p><em>No tokenized stock platform rows.</em></p>")
    blocks.append('<p><a class="btn primary" href="/rwa/tokenized-stocks">Full Tokenized Stocks view</a></p>')
    return _rwa_response(
        request,
        page_title="Explore by Asset Type",
        head_block=_rwa_std_head(
            title="Explore by Asset Type",
            subtitle="Hub previews — open a section for the full searchable tables and charts.",
        ),
        body_html="".join(blocks),
        footer_note=rwa_xyz_mirror_footer_text(),
    )


@router.get("/rwa/explore/participant", response_class=HTMLResponse)
async def rwa_explore_participant(request: Request) -> HTMLResponse:
    net_rows, net_kpis, net_err = load_rwa_league_cached()
    plat_rows, plat_kpis, plat_err = load_rwa_platforms_cached()
    am_rows, am_kpis, am_err = load_rwa_asset_managers_cached()
    blocks: list[str] = []
    blocks.append("<h3>Networks</h3>")
    if net_err and not net_rows:
        blocks.append(f'<p class="alert warn">{escape(net_err)}</p>')
    elif net_rows:
        prev = net_rows[:_PREVIEW]
        df = build_rwa_networks_page_dataframe(prev)
        blocks.append(styled_dataframe_to_html(style_rwa_networks_page_dataframe(df)))
    else:
        blocks.append("<p><em>No rows.</em></p>")
    blocks.append('<p><a class="btn primary" href="/rwa/participants/networks">Full Networks view</a></p>')
    blocks.append("<h3>Platforms</h3>")
    if plat_err and not plat_rows:
        blocks.append(f'<p class="alert warn">{escape(plat_err)}</p>')
    elif plat_rows:
        prev = plat_rows[:_PREVIEW]
        df = build_rwa_platforms_page_dataframe(prev)
        blocks.append(styled_dataframe_to_html(style_rwa_platforms_page_dataframe(df)))
    else:
        blocks.append("<p><em>No rows.</em></p>")
    blocks.append('<p><a class="btn primary" href="/rwa/participants/platforms">Full Platforms view</a></p>')
    blocks.append("<h3>Asset Managers</h3>")
    if am_err and not am_rows:
        blocks.append(f'<p class="alert warn">{escape(am_err)}</p>')
    elif am_rows:
        prev = am_rows[:_PREVIEW]
        df = build_rwa_asset_managers_page_dataframe(prev)
        blocks.append(styled_dataframe_to_html(style_rwa_asset_managers_page_dataframe(df)))
    else:
        blocks.append("<p><em>No rows.</em></p>")
    blocks.append(
        '<p><a class="btn primary" href="/rwa/participants/asset-managers">Full Asset Managers view</a></p>'
    )
    return _rwa_response(
        request,
        page_title="Explore by Market Participant",
        head_block=_rwa_std_head(
            title="Explore by Market Participant",
            subtitle="Hub previews — open a section for the full searchable tables and charts.",
        ),
        body_html="".join(blocks),
        footer_note=rwa_xyz_mirror_footer_text(),
    )
