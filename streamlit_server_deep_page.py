"""Server-rendered deep RWA pages for Streamlit (no iframe hydration)."""

from __future__ import annotations

import math
from html import escape
from typing import Any, Sequence

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
_LINK_NAME_COLS = frozenset({"Fund Name", "Network", "Platform"})


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
        '<section class="etp-mock-snapshot" aria-labelledby="deep-snap-h">'
        '<h2 class="subsection-head u-vh" id="deep-snap-h">Top-line snapshot</h2>'
        '<div class="rwa-kpi-panel-static">'
        f"{legend}"
        f"<div class=\"rwa-kpi-row rwa-kpi-row--home-grid\">{''.join(cells)}</div>"
        "</div></section>"
    )


def _deep_cell_html(col: str, val: Any, row: dict[str, Any]) -> tuple[str, str]:
    if col in _HTML_COLS and val is not None and "<" in str(val):
        return str(val), ""
    if col in _LINK_NAME_COLS:
        label = str(val or "—")
        link = str(row.get("Link") or row.get("Fund Link") or row.get("Platform Link") or "").strip()
        if link.startswith("http"):
            return f'<a href="{escape(link)}" target="_blank" rel="noopener noreferrer">{escape(label)}</a>', ""
        return escape(label), ""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "—", ""
    if col in ("Total Value", "Distributed Value", "Market Cap", "Assets (B)"):
        try:
            return escape(format_usd_compact(float(val))), " num"
        except (TypeError, ValueError):
            return escape(str(val)), " num"
    if "Δ" in col or col.endswith(" %") or col in ("Market Share", "1M %", "1Y %", "30D Δ share"):
        try:
            n = float(val)
            cls = " num up" if n > 0 else " num down" if n < 0 else " num"
            sign = "+" if n > 0 else ""
            return f"{sign}{n:.2f}%", cls
        except (TypeError, ValueError):
            return "—", " num"
    if col in _NUM_COLS:
        try:
            if col == "#":
                return escape(str(int(val))), ""
            return escape(str(int(val) if float(val).is_integer() else val)), " num"
        except (TypeError, ValueError):
            return escape(str(val)), " num"
    return escape(str(val)), ""


def league_table_html(
    league: dict[str, Any] | None,
    *,
    table_id: str,
    default_heading: str,
) -> str:
    if not league or not league.get("columns"):
        return ""
    columns = [str(c) for c in league["columns"]]
    rows = league.get("rows_full") or []
    heading = str(league.get("block_heading") or default_heading)
    intro = str(league.get("section_intro_html") or "").strip()
    caption = str(league.get("caption_html") or "").strip()
    thead = "".join(
        f'<th scope="col"{" class=\"num\"" if c in _NUM_COLS else ""}>{escape(c)}</th>'
        for c in columns
    )
    body_rows: list[str] = []
    for row in rows:
        tds: list[str] = []
        for c in columns:
            txt, cls = _deep_cell_html(c, row.get(c), row)
            tds.append(f'<td class="{cls.strip()}">{txt}</td>')
        body_rows.append(f"<tr>{''.join(tds)}</tr>")
    tbody = "".join(body_rows) if body_rows else (
        f'<tr><td colspan="{len(columns)}">No rows available.</td></tr>'
    )
    intro_html = f'<p class="rwa-deep-section-intro">{intro}</p>' if intro else ""
    cap_html = f'<p class="source-cap">{caption}</p>' if caption else ""
    return (
        f'<section class="rwa-deep-league-panel etp-mock-table-block" id="{escape(table_id)}">'
        f'<h2 class="subsection-head">{escape(heading)}</h2>'
        f"{intro_html}"
        '<div class="table-wrap table-wrap--scroll rwa-split-table-scroll">'
        f'<table class="data-table data-table--dense" aria-label="{escape(heading)}">'
        f"<thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table></div>"
        f"{cap_html}</section>"
    )


def funds_table_html(funds: dict[str, Any] | None) -> str:
    if not funds or not funds.get("columns"):
        return ""
    columns = [str(c) for c in funds["columns"]]
    rows = funds.get("rows_full") or []
    heading = str(funds.get("table_heading") or "Tokenized money market fund population")
    intro = (
        "Curated fund population (fixed list aligned to RWA.xyz). "
        "Population may not include all TMMFs in the market."
    )
    thead = "".join(
        f'<th scope="col"{" class=\"num\"" if c in _NUM_COLS else ""}>{escape(c)}</th>'
        for c in columns
    )
    body_rows: list[str] = []
    for row in rows:
        tds: list[str] = []
        for c in columns:
            txt, cls = _deep_cell_html(c, row.get(c), row)
            tds.append(f'<td class="{cls.strip()}">{txt}</td>')
        body_rows.append(f"<tr>{''.join(tds)}</tr>")
    tbody = "".join(body_rows) if body_rows else (
        f'<tr><td colspan="{len(columns)}">No funds available.</td></tr>'
    )
    return (
        '<section class="etp-mock-table-block etp-mock-table-block--funds" aria-labelledby="funds-heading">'
        f'<h2 class="subsection-head" id="funds-heading">{escape(heading)}</h2>'
        f'<p class="rwa-deep-section-intro">{escape(intro)}</p>'
        '<div class="table-wrap table-wrap--scroll tmmf-funds-table-wrap">'
        f'<table class="data-table data-table--dense" aria-label="{escape(heading)}">'
        f"<thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table></div>"
        "</section>"
    )


def key_observations_html(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    return (
        '<div class="inner-rich-block etp-mock-key-obs-block" aria-labelledby="deep-ko-h">'
        '<h2 class="subsection-head" id="deep-ko-h">Key observations</h2>'
        f"{raw}</div>"
    )
