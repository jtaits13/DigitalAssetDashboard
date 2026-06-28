"""Server-rendered deep RWA pages for Streamlit (mock-parity markup, no JS hydration)."""

from __future__ import annotations

import math
import re
from html import escape
from typing import Any

from crypto_etps.client import format_usd_compact

_NUM_COLS = frozenset(
    {
        "Price",
        "1Y %",
        "1Y Flow",
        "Assets (B)",
        "Total Value",
        "Distributed Value",
        "Market Cap",
        "1M %",
        "Market Share",
        "30D Δ share",
        "7D Δ value",
        "Rank",
        "RWA Count",
        "Stablecoins",
        "Holders",
        "#",
    }
)
_HTML_COLS = frozenset({"Networks", "Terms"})
_NAME_LINK_COLS = frozenset({"Fund Name", "Network", "Platform", "Asset manager"})
_TMMF_MOCK_FUND_COLUMNS = (
    "#",
    "Fund Name",
    "Ticker",
    "Platform",
    "Networks",
    "Total Value",
    "7D Δ value",
    "Holders",
)


def _delta30_html(frac: float | None) -> str:
    if frac is None or (isinstance(frac, float) and math.isnan(frac)):
        return '<span class="rwa-kpi-delta rwa-kpi-delta--placeholder" aria-hidden="true">&nbsp;</span>'
    pct = float(frac) * 100.0
    cls = "up" if pct > 0 else "down" if pct < 0 else "neutral"
    sign = "+" if pct > 0 else ""
    return f'<span class="rwa-kpi-delta {cls}">{sign}{pct:.2f}%</span>'


def kpis_html_from_payload(kpis: list[dict[str, Any]], *, note: str = "") -> str:
    if not kpis:
        return ""
    cells: list[str] = []
    for k in kpis:
        delta = k.get("delta_30d_pct")
        cells.append(
            "<div class='rwa-kpi-cell'>"
            f"<span class='rwa-kpi-label'>{escape(str(k.get('label') or ''))}</span>"
            f"<span class='rwa-kpi-val'>{escape(str(k.get('value_display') or ''))}</span>"
            f"{_delta30_html(float(delta) if delta is not None else None)}"
            "</div>"
        )
    legend = (
        f'<p class="jd-kpi-window-note rwa-onchain-kpi-legend">{escape(note)}</p>' if note else ""
    )
    return (
        '<section class="etp-mock-snapshot" id="js-deep-snapshot" aria-labelledby="js-deep-snap-h">'
        '<h2 class="subsection-head u-vh" id="js-deep-snap-h">Top-line snapshot</h2>'
        '<div id="js-deep-kpis" aria-label="Headline KPI strip">'
        '<div class="rwa-kpi-panel-static">'
        f"{legend}"
        f"<div class=\"rwa-kpi-row rwa-kpi-row--home-grid\">{''.join(cells)}</div>"
        "</div></div></section>"
    )


def _fmt_pct_pts(val: Any) -> tuple[str, str]:
    try:
        n = float(val)
        cls = " num up" if n > 0 else " num down" if n < 0 else " num"
        sign = "+" if n > 0 else ""
        return f"{sign}{n:.2f}%", cls
    except (TypeError, ValueError):
        return "—", " num"


def _fmt_pct_level(val: Any) -> tuple[str, str]:
    try:
        return f"{float(val):.2f}%", " num"
    except (TypeError, ValueError):
        return "—", " num"


def _link_href_for_row(col: str, row: dict[str, Any]) -> str:
    if col == "Fund Name":
        return str(row.get("Fund Link") or row.get("Link") or "").strip()
    if col == "Platform":
        return str(row.get("Platform Link") or row.get("Link") or "").strip()
    return str(row.get("Link") or "").strip()


def _deep_cell_html(col: str, val: Any, row: dict[str, Any]) -> tuple[str, str]:
    if col == "Link":
        href = str(val or row.get("Link") or "").strip()
        if not href.startswith("http"):
            return "—", " num"
        return (
            f'<a class="rwa-table-link" href="{escape(href)}" target="_blank" '
            f'rel="noopener noreferrer" aria-label="Open RWA.xyz">↗</a>',
            " num",
        )
    if col in _HTML_COLS and val is not None and "<" in str(val):
        return str(val), "data-table__text"
    if col in _NAME_LINK_COLS:
        label = str(val or "—")
        href = _link_href_for_row(col, row)
        if href.startswith("http"):
            return (
                f'<a class="sym sym--link" href="{escape(href)}" target="_blank" '
                f'rel="noopener noreferrer">{escape(label)}</a>',
                "",
            )
        return f'<span class="sym">{escape(label)}</span>', ""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "—", ""
    if col in ("Total Value", "Distributed Value", "Market Cap", "Assets (B)"):
        try:
            return escape(format_usd_compact(float(val))), " num"
        except (TypeError, ValueError):
            return escape(str(val)), " num"
    if col in ("7D Δ value", "30D Δ share"):
        txt, cls = _fmt_pct_pts(val)
        return txt, cls
    if col == "Market Share":
        txt, cls = _fmt_pct_level(val)
        return txt, cls
    if col == "Holders":
        try:
            return escape(f"{int(val):,}"), " num"
        except (TypeError, ValueError):
            return escape(str(val)), " num"
    if col in _NUM_COLS:
        try:
            if col == "#":
                return escape(str(int(val))), ""
            fv = float(val)
            return escape(str(int(fv) if fv.is_integer() else val)), " num"
        except (TypeError, ValueError):
            return escape(str(val)), " num"
    return escape(str(val)), ""


def _table_body_html(columns: list[str], rows: list[dict[str, Any]], *, empty_msg: str) -> str:
    thead = "".join(
        f'<th scope="col"{" class=\"num\"" if c in _NUM_COLS or c == "Link" else ""}>'
        f'{"↗" if c == "Link" else escape(c)}</th>'
        for c in columns
    )
    if not rows:
        tbody = f'<tr><td colspan="{len(columns)}">{escape(empty_msg)}</td></tr>'
    else:
        body_rows: list[str] = []
        for row in rows:
            tds: list[str] = []
            for c in columns:
                txt, cls = _deep_cell_html(c, row.get(c), row)
                tds.append(f'<td class="{cls.strip()}">{txt}</td>')
            body_rows.append(f"<tr>{''.join(tds)}</tr>")
        tbody = "".join(body_rows)
    return f"<thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody>"


def _conc_bar_rows(items: list[tuple[str, float]]) -> str:
    if not items:
        return ""
    max_pct = max(p for _, p in items)
    parts: list[str] = []
    for label, pct in items:
        width = (pct / max_pct * 100.0) if max_pct > 0 else 0.0
        parts.append(
            '<div class="etp-mock-conc__row">'
            f'<span class="etp-mock-conc__sym">{escape(label)}</span>'
            f'<span class="etp-mock-conc__track"><span class="etp-mock-conc__fill" '
            f'style="width:{width:.1f}%"></span></span>'
            f'<span class="etp-mock-conc__pct">{pct:.1f}%</span></div>'
        )
    return "".join(parts)


def tmmf_mock_insights_html(payload: dict[str, Any]) -> str:
    net = payload.get("networks") or {}
    funds = payload.get("funds_table") or {}
    net_rows = sorted(
        list(net.get("rows_full") or []),
        key=lambda r: -(float(r.get("Market Share") or 0)),
    )
    fund_rows = list(funds.get("rows_full") or [])
    if not net_rows:
        return ""
    top5 = [
        (
            (str(r.get("Network") or "—"))[:8],
            float(r.get("Market Share") or 0),
        )
        for r in net_rows[:5]
    ]
    top_fund = max(fund_rows, key=lambda r: float(r.get("Total Value") or 0), default=None)
    if top_fund:
        tv = float(top_fund.get("Total Value") or 0)
        fund_label = f"{top_fund.get('Ticker') or '—'} ({format_usd_compact(tv)})"
    else:
        fund_label = "—"
    return (
        '<section class="etp-mock-insights" id="js-deep-insights" aria-labelledby="js-deep-insights-h">'
        '<h2 class="u-vh" id="js-deep-insights-h">Market structure</h2>'
        '<div class="etp-mock-insights__panel etp-mock-insights__panel--conc">'
        '<h3 class="etp-mock-insights__head">Network share (top 5)</h3>'
        '<p class="etp-mock-conc__dek">Share of aggregated distributed value by chain (RWA.xyz snapshot).</p>'
        f'<div class="etp-mock-conc__rows" role="img" aria-label="Top five networks by distributed value share">'
        f"{_conc_bar_rows(top5)}"
        '</div></div><div class="etp-mock-insights__panel etp-mock-insights__panel--glance">'
        '<h3 class="etp-mock-insights__head">At a glance</h3>'
        '<div class="etp-mock-stats">'
        '<div class="etp-mock-stat"><span class="etp-mock-stat__lbl">Curated funds</span>'
        f'<span class="etp-mock-stat__val">{len(fund_rows)}</span></div>'
        '<div class="etp-mock-stat"><span class="etp-mock-stat__lbl">Active networks</span>'
        f'<span class="etp-mock-stat__val">{len(net_rows)}</span></div>'
        '<div class="etp-mock-stat"><span class="etp-mock-stat__lbl">Largest fund</span>'
        f'<span class="etp-mock-stat__val etp-mock-stat__val--ticker">{escape(fund_label)}</span>'
        "</div></div></div></section>"
    )


def _league_table_prefix(wrap_id: str) -> str:
    return wrap_id.replace("-wrap", "")


def _export_cell_value(col: str, val: Any, row: dict[str, Any]) -> Any:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    if col in _HTML_COLS:
        return re.sub(r"<[^>]+>", " ", str(val)).replace("\n", " ").strip()
    if col in ("Total Value", "7D Δ value", "Holders", "Distributed Value", "Market Cap"):
        try:
            return float(val)
        except (TypeError, ValueError):
            return str(val)
    if col in ("Networks", "Terms"):
        return re.sub(r"<[^>]+>", " ", str(val)).replace("\n", " ").strip()
    return str(val)


def _funds_export_columns(funds: dict[str, Any]) -> list[str]:
    cols = [str(c) for c in funds.get("columns") or []]
    if "#" not in cols:
        cols.insert(0, "#")
    return cols


def _ranked_fund_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(rows, key=lambda r: -(float(r.get("Total Value") or 0)))
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(ranked, start=1):
        item = dict(row)
        item["#"] = idx
        out.append(item)
    return out


def funds_export_data(funds: dict[str, Any] | None) -> dict[str, Any]:
    if not funds:
        return {"sheetName": "TMMF Funds", "headers": [], "rows": []}
    cols = _funds_export_columns(funds)
    rows = _ranked_fund_rows(list(funds.get("rows_full") or []))
    return {
        "sheetName": "TMMF Funds",
        "headers": cols,
        "rows": [[_export_cell_value(c, row.get(c), row) for c in cols] for row in rows],
    }


def league_export_data(league: dict[str, Any] | None) -> dict[str, Any]:
    if not league or not league.get("columns"):
        return {"sheetName": "RWA table", "headers": [], "rows": []}
    cols = [str(c) for c in league["columns"]]
    title = str(league.get("table_heading") or league.get("block_heading") or "RWA table")
    rows = league.get("rows_full") or []
    return {
        "sheetName": title[:31],
        "headers": cols,
        "rows": [[_export_cell_value(c, row.get(c), row) for c in cols] for row in rows],
    }


def build_tmmf_server_export_config(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "funds": funds_export_data(payload.get("funds_table")),
        "deep-net": league_export_data(payload.get("networks")),
        "deep-plat": league_export_data(payload.get("platforms")),
    }


def build_stablecoins_server_export_config(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "deep-net": league_export_data(payload.get("networks")),
        "deep-plat": league_export_data(payload.get("platforms")),
    }


def stablecoins_methodology_panel_html() -> str:
    """Collapsible Data sources panel (matches static_home/js/page-methodology.js rwa-stablecoins)."""
    from rwa_league.client import APP_STABLECOINS

    rwa = (
        '<a href="https://app.rwa.xyz/" target="_blank" rel="noopener noreferrer">RWA.xyz</a>'
    )
    stablecoins = (
        f'<a href="{APP_STABLECOINS}" target="_blank" rel="noopener noreferrer">Stablecoins</a>'
    )
    bullets = (
        f"<li><strong>Source</strong> — {rwa} {stablecoins} (Networks and Platforms tabs).</li>"
        "<li><strong>KPI strip</strong> — overview totals; colored <strong>%</strong> are typically "
        "<strong>30-day (30D)</strong>.</li>"
        "<li><strong>Networks table</strong> — <strong>Total Value</strong> is aggregate stablecoin "
        "market cap on that network; <strong>7D Δ value</strong> uses <code>value_7d_change</code> "
        "from the embed.</li>"
        "<li><strong>Platforms table</strong> — issuer-level stablecoin market cap with the same "
        "7D / 30D conventions.</li>"
    )
    return (
        '<details class="methodology-panel">'
        "<summary>Data sources &amp; definitions</summary>"
        f'<div class="methodology-panel__body"><ul>{bullets}</ul></div>'
        "</details>"
    )


def stablecoins_kpis_html(kpis: list[dict[str, Any]], *, note: str = "") -> str:
    """KPI strip plus collapsible Data sources panel."""
    block = kpis_html_from_payload(kpis, note=note)
    panel = stablecoins_methodology_panel_html()
    if not block:
        return panel
    if block.endswith("</section>"):
        return f"{block[:-len('</section>')]}{panel}</section>"
    return f"{block}{panel}"


def stablecoins_mock_insights_html(payload: dict[str, Any]) -> str:
    """Issuer concentration panel (platform share bars)."""
    plat = payload.get("platforms") or {}
    rows = sorted(
        list(plat.get("rows_full") or []),
        key=lambda r: -(float(r.get("Market Share") or 0)),
    )
    if not rows:
        return ""
    top3 = rows[:3]
    top3_sum = sum(float(r.get("Market Share") or 0) for r in top3)
    items: list[tuple[str, float]] = [
        (str(r.get("Platform") or "—"), float(r.get("Market Share") or 0)) for r in top3
    ]
    other_pct = max(0.0, 100.0 - top3_sum)
    if other_pct > 0.15:
        items.append(("Other", other_pct))
    return (
        '<section class="etp-mock-insights etp-mock-insights--crypto-full" id="js-deep-insights" '
        'aria-labelledby="js-deep-insights-h">'
        '<h2 class="u-vh" id="js-deep-insights-h">Market structure</h2>'
        '<div class="etp-mock-insights__panel etp-mock-insights__panel--conc">'
        '<h3 class="etp-mock-insights__head">Issuer concentration (platforms)</h3>'
        '<p class="etp-mock-conc__dek">Share of aggregate stablecoin market cap by platform '
        "(RWA.xyz snapshot).</p>"
        '<div class="etp-mock-conc__rows etp-mock-conc__rows--grid" role="img" '
        'aria-label="Top platforms by stablecoin market cap share">'
        f"{_conc_bar_rows(items)}"
        "</div></div></section>"
    )


def stablecoins_share_movers_html(payload: dict[str, Any]) -> str:
    """Largest 30D share shifts list for the dashboard movers panel."""
    net = payload.get("networks") or {}
    rows = list(net.get("rows_full") or [])
    if not rows:
        return ""
    name_col = str(net.get("name_column") or "Network")
    val_col = str(net.get("value_column") or "Total Value")
    top_networks = sorted(rows, key=lambda r: -(float(r.get(val_col) or 0)))[:15]
    movers = [
        r
        for r in top_networks
        if r.get("30D Δ share") is not None and math.isfinite(float(r.get("30D Δ share")))
    ]
    movers.sort(key=lambda r: abs(float(r.get("30D Δ share") or 0)), reverse=True)
    movers = movers[:4]
    if not movers:
        return (
            '<ul class="crypto-top-movers__list"></ul>'
            '<p class="crypto-story-callout__note"><strong>30D Δ share</strong> is 30-day change in '
            "market share (%). Top 15 networks by stablecoin value.</p>"
        )
    items: list[str] = []
    for row in movers:
        n = float(row["30D Δ share"])
        cls = "up" if n >= 0 else "down"
        sign = "+" if n > 0 else ""
        d7 = row.get("7D Δ value")
        if d7 is not None and math.isfinite(float(d7)):
            d7f = float(d7)
            ctx = (
                f"7D value {'+' if d7f >= 0 else ''}{d7f:.2f}% · "
                f"{float(row.get('Market Share') or 0):.1f}% market share"
            )
        else:
            ctx = f"{float(row.get('Market Share') or 0):.1f}% market share"
        label = escape(str(row.get(name_col) or "—"))
        items.append(
            '<li class="crypto-top-mover"><div class="crypto-top-mover__row">'
            f'<span class="crypto-top-mover__label"><strong>{label}</strong></span>'
            f'<span class="crypto-top-mover__pct pct {cls}">{sign}{n:.2f}%</span></div>'
            f'<p class="crypto-top-mover__ctx">{escape(ctx)}</p></li>'
        )
    return (
        '<ul class="crypto-top-movers__list">'
        f"{''.join(items)}"
        "</ul>"
        '<p class="crypto-story-callout__note"><strong>30D Δ share</strong> is 30-day change in '
        "market share (%). Top 15 networks by stablecoin value.</p>"
    )


def stablecoins_dashboard_html(payload: dict[str, Any]) -> str:
    """Chart host + pre-rendered share movers (chart drawn by Plotly boot script)."""
    net = payload.get("networks") or {}
    if not net.get("rows_full"):
        return ""
    movers = stablecoins_share_movers_html(payload)
    return (
        '<section class="etp-mock-dashboard" id="js-deep-dashboard" aria-labelledby="js-deep-dashboard-h">'
        '<h2 class="u-vh" id="js-deep-dashboard-h">Chart and share movers</h2>'
        '<div class="etp-mock-dash__panel etp-mock-dash__panel--chart">'
        '<h3 class="etp-mock-dash__head">Stablecoin market cap by network</h3>'
        '<div class="stable-dash-chart-body">'
        '<div id="js-deep-dashboard-chart" class="aum-chart-host" role="img" '
        'aria-label="Stablecoin market cap by network"></div>'
        "</div>"
        '<p class="etp-mock-chart__cap">'
        "Top <strong>5</strong> networks plus <strong>Other</strong> (remaining networks); "
        "market shares sum to <strong>100%</strong>. Bar length uses total value; labels show share."
        "</p>"
        '<p class="etp-mock-chart__method">'
        "Plotly horizontal bars synced to the searchable networks table below."
        "</p></div>"
        '<div class="etp-mock-dash__panel etp-mock-dash__panel--movers">'
        '<h3 class="etp-mock-dash__head">Largest 30D share shifts (networks)</h3>'
        f'<div id="js-stable-share-movers">{movers}</div>'
        "</div></section>"
    )


def build_stablecoins_server_zone_html(
    *,
    payload: dict[str, Any],
    related_chips: str,
) -> str:
    """Server-rendered Stablecoins zone body (mock-parity markup, filled at build time)."""
    title = str(payload.get("page_title") or "Stablecoins")
    title = title.replace(" — Digital Assets Dashboard", "").strip()
    band = str(payload.get("band_label") or "Stablecoins")
    subtitle = str(payload.get("page_subtitle_html") or "")
    footer = str(payload.get("footer_note") or "")
    err = str(payload.get("error") or payload.get("error_detail") or "").strip()
    banner = (
        f'<div class="data-banner" id="js-deep-banner" role="status">{escape(err)}</div>'
        if err
        else '<div class="data-banner" id="js-deep-banner" role="status" hidden></div>'
    )
    cta = payload.get("bottom_cta") or {}
    cta_href = str(cta.get("href") or "").strip()
    cta_label = str(cta.get("label") or "See Stablecoins on RWA.xyz")
    cta_html = (
        f'<div class="cta-row rwa-deep-page-cta" id="js-deep-bottom-cta">'
        f'<a class="btn btn-primary" href="{escape(cta_href)}" target="_blank" rel="noopener noreferrer">'
        f"{escape(cta_label)}</a></div>"
        if cta_href
        else '<div class="cta-row rwa-deep-page-cta" id="js-deep-bottom-cta"></div>'
    )
    has_net = bool((payload.get("networks") or {}).get("rows_full"))
    has_plat = bool((payload.get("platforms") or {}).get("rows_full"))
    mid_rule = (
        '<hr class="jd-divider" id="js-deep-rule-mid" aria-hidden="true" />'
        if has_net and has_plat
        else '<hr class="jd-divider" id="js-deep-rule-mid" hidden aria-hidden="true" />'
    )
    between_ko = str(payload.get("between_ko_and_leagues_html") or "").strip()
    between_html = (
        f'<div id="js-deep-extra-before-leagues" class="rwa-deep-optional-msg">{between_ko}</div>'
        if between_ko
        else '<div id="js-deep-extra-before-leagues" class="rwa-deep-optional-msg" hidden></div>'
    )
    after_net = str(payload.get("after_network_block_html") or "").strip()
    after_net_html = (
        f'<div id="js-deep-extra-after-network" class="rwa-deep-optional-msg">{after_net}</div>'
        if after_net
        else '<div id="js-deep-extra-after-network" class="rwa-deep-optional-msg" hidden></div>'
    )
    return (
        '<main class="page-shell etp-mock-shell">'
        '<article class="hub-section hub-section--panel inner-rich-zone zone--stable home-zone home-zone--stable etp-mock-zone">'
        '<div class="home-zone__stripe" aria-hidden="true"></div>'
        '<header class="home-zone__head">'
        '<span class="home-zone__badge" aria-hidden="true">SC</span>'
        '<div class="home-zone__titles">'
        f'<p class="band-label teal" id="js-deep-band">{escape(band)}</p>'
        f'<h1 class="page-intro__title" id="js-deep-title">{escape(title)}</h1>'
        f'<div class="section-dek section-dek--wide page-intro__dek" id="js-deep-subtitle">{subtitle}</div>'
        "</div></header>"
        '<div class="home-zone__body inner-rich-zone__body etp-mock-zone__body">'
        f"{related_chips.strip()}"
        f"{banner}"
        f"{stablecoins_kpis_html(list(payload.get('kpis') or []), note=str(payload.get('kpi_window_note') or ''))}"
        f"{key_observations_html(str(payload.get('key_observations_html') or ''))}"
        f"{stablecoins_mock_insights_html(payload)}"
        f"{stablecoins_dashboard_html(payload)}"
        f"{between_html}"
        f"{league_table_html(payload.get('networks'), wrap_id='deep-net-wrap', is_network=True)}"
        f"{after_net_html}"
        f"{mid_rule}"
        f"{league_table_html(payload.get('platforms'), wrap_id='deep-plat-wrap', is_network=False)}"
        f"{cta_html}"
        f'<p class="timestamp-foot" id="js-deep-footer-note">{escape(footer)}</p>'
        "</div></article></main>"
    )


def league_table_html(
    league: dict[str, Any] | None,
    *,
    wrap_id: str,
    is_network: bool,
) -> str:
    if not league or not league.get("columns"):
        return ""
    prefix = _league_table_prefix(wrap_id)
    columns = [str(c) for c in league["columns"]]
    rows = league.get("rows_full") or []
    heading = str(league.get("table_heading") or league.get("block_heading") or "RWA table")
    intro = str(league.get("section_intro_html") or "").strip()
    caption = str(league.get("caption_html") or "").strip()
    search_label = str(league.get("search_label") or "Search table")
    search_placeholder = str(league.get("search_placeholder") or "Filter table…")
    entity_plural = str(league.get("filter_note_entity_plural") or ("networks" if is_network else "platforms"))
    host_class = "rwa-deep-league-panel etp-mock-table-block"
    if is_network:
        host_class += " tmmf-mock-league-block stable-mock-league-block"
    intro_html = f'<p class="tmmf-mock-league-intro">{intro}</p>' if intro else ""
    cap_html = (
        f'<div class="rwa-table-footnote-row"><p class="source-cap rwa-table-footnote-row__cap">{caption}</p></div>'
        if caption
        else ""
    )
    table_html = _table_body_html(columns, rows, empty_msg="No rows available.")
    count_note = f"Showing all {len(rows)} {entity_plural}."
    return (
        f'<div id="{escape(wrap_id)}" class="{host_class}">'
        '<div class="rwa-split-table-head inner-table-head">'
        f'<h2 class="subsection-head rwa-split-table-head__title">{escape(heading)}</h2>'
        f'<div class="rwa-split-table-head__actions" id="{escape(prefix)}-table-actions"></div>'
        "</div>"
        f"{intro_html}"
        '<label class="search-field etp-mock-table-search">'
        f'<span class="search-field__label">{escape(search_label)}</span>'
        f'<input id="{escape(prefix)}-q" type="search" class="search-field__input" autocomplete="off" '
        f'placeholder="{escape(search_placeholder)}" /></label>'
        '<div class="etp-mock-table-meta" aria-live="polite">'
        f'<p class="etp-mock-table-meta__count toolbar-note" id="{escape(prefix)}-note">'
        f"{escape(count_note)}</p>"
        f'<div class="rwa-table-actions" id="{escape(prefix)}-meta-actions"></div>'
        "</div>"
        '<div class="table-wrap table-wrap--scroll rwa-split-table-scroll" '
        f'data-fullscreen-title="{escape(heading)}">'
        f'<table class="data-table data-table--dense data-table--sortable" aria-label="{escape(heading)}">'
        f"{table_html}</table></div>"
        f"{cap_html}</div>"
    )


def funds_table_html(funds: dict[str, Any] | None) -> str:
    if not funds or not funds.get("columns"):
        return ""
    all_columns = [str(c) for c in funds["columns"]]
    columns = [c for c in _TMMF_MOCK_FUND_COLUMNS if c in all_columns]
    if not columns:
        columns = all_columns
    rows = funds.get("rows_full") or []
    heading = str(funds.get("table_heading") or "Tokenized money market fund population")
    intro = (
        "Curated fund population (fixed list aligned to RWA.xyz). "
        "Population may not include all TMMFs in the market."
    )
    table_html = _table_body_html(rows=rows, columns=columns, empty_msg="No funds available.")
    footnote = (
        "Ranked by total value. Full production table includes eligibility, domicile, "
        "regulatory framework, and custodian columns (available in full-screen view and Excel export)."
    )
    count_note = f"Showing all {len(rows)} funds."
    return (
        '<section id="js-deep-extra-before-leagues" '
        'class="rwa-deep-league-panel etp-mock-table-block etp-mock-table-block--funds" '
        'aria-labelledby="funds-heading">'
        '<div class="rwa-split-table-head inner-table-head">'
        f'<h2 class="subsection-head rwa-split-table-head__title" id="funds-heading">{escape(heading)}</h2>'
        '<div class="rwa-split-table-head__actions" id="tmmf-funds-table-actions"></div>'
        "</div>"
        f'<p class="tmmf-mock-funds-intro">{escape(intro)}</p>'
        '<label class="search-field etp-mock-table-search">'
        '<span class="search-field__label">Search funds</span>'
        '<input id="tmmf-funds-q" type="search" class="search-field__input" autocomplete="off" '
        'placeholder="Filter funds…" /></label>'
        '<div class="etp-mock-table-meta" aria-live="polite">'
        f'<p class="etp-mock-table-meta__count toolbar-note" id="tmmf-funds-note">{escape(count_note)}</p>'
        '<div class="rwa-table-actions" id="tmmf-funds-meta-actions"></div>'
        "</div>"
        '<div class="table-wrap table-wrap--scroll rwa-split-table-scroll tmmf-funds-table-wrap" '
        'data-fullscreen-title="Tokenized Money Market Fund Population">'
        f'<table class="data-table data-table--dense data-table--sortable" '
        f'aria-label="{escape(heading)}">{table_html}</table></div>'
        f'<div class="rwa-table-footnote-row"><p class="source-cap rwa-table-footnote-row__cap">'
        f"{escape(footnote)}</p></div></section>"
    )


def key_observations_html(raw: str) -> str:
    """Match ``renderKeyObservationsCallout`` from ``rwa-onchain-home.js``."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    cleaned = re.sub(r"<style[^>]*>.*?</style>", "", raw, flags=re.IGNORECASE | re.DOTALL)
    ul_match = re.search(r"<ul[^>]*>(.*?)</ul>", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if not ul_match:
        return (
            '<div class="inner-rich-block etp-mock-key-obs-block" id="js-deep-ko-section" '
            'aria-labelledby="js-deep-ko-h">'
            f'<div id="js-deep-ko">{cleaned}</div></div>'
        )
    list_html = re.sub(r'\s*style="[^"]*"', "", ul_match.group(1), flags=re.IGNORECASE)
    note_match = re.search(
        r'<p class="takeaways__note"[^>]*>(.*?)</p>',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    review_match = re.search(
        r'<p class="review-note[^"]*"[^>]*>.*?</p>',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    note_html = (
        f'<p class="crypto-story-callout__note">{note_match.group(1)}</p>'
        if note_match
        else ""
    )
    review_html = review_match.group(0) if review_match else ""
    callout = (
        '<aside class="crypto-story-callout" aria-labelledby="key-obs-callout-title">'
        '<p class="crypto-story-callout__title" role="heading" aria-level="3" '
        'id="key-obs-callout-title">Key observations</p>'
        f'<ul class="crypto-story-callout__list">{list_html}</ul>'
        f"{note_html}"
        "</aside>"
    )
    return (
        '<div class="inner-rich-block etp-mock-key-obs-block" id="js-deep-ko-section" '
        'aria-labelledby="js-deep-ko-h">'
        '<h2 class="subsection-head u-vh" id="js-deep-ko-h">Key Observations</h2>'
        f'<div id="js-deep-ko">{callout}{review_html}</div></div>'
    )
