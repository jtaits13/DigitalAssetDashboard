"""
Build JSON payloads under static_home/data/ for the GitHub Pages mirror.

Run locally:  python scripts/export_static_site_data.py
Run in CI:    before upload-pages-artifact (see .github/workflows).

Uses the same RSS / StockAnalysis / yfinance / RWA.xyz logic as the Streamlit app (no Streamlit UI), plus ``price_ticker.fetch_top_crypto_tickers`` for ``crypto_ticker.json`` (GitHub Pages marquee).

Optional env ``STATIC_WEBAPP_BASE``: absolute origin for FastAPI-only routes when needed. Served as HTML in ``static_home/``: Global overview ``rwa-global.html``, Explore by Asset Type ``rwa-explore-asset-type.html``, Explore by Market Participant ``rwa-explore-market-participant.html``, participant deep pages ``rwa-participants-*.html``, Stablecoins ``rwa-stablecoins.html``, US Treasuries ``rwa-us-treasuries.html``, Tokenized Stocks ``rwa-tokenized-stocks.html``.
"""

from __future__ import annotations

import json
import os
import re
import sys
from html import escape as html_escape
from typing import Any
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from crypto_etps.client import (
    CryptoEtpRow,
    fetch_crypto_etps_enriched,
    format_usd_compact,
    has_listed_aum_usd,
    sorted_by_assets,
    total_aum_usd,
)
from crypto_etps.custodian import resolve_custodian
from crypto_etps.aum_history import (
    aggregate_aum_pct_from_history,
    build_aggregate_aum_history_12m,
    etp_rows_to_fund_pairs,
    etp_symbol_price_change_cached,
)
from news_feeds import (
    ETP_PULSE_PREVIEW_COUNT,
    dedupe_articles,
    load_all_etf_etp_news_cached,
    load_all_feeds,
)
from news_feeds import DEFAULT_FEEDS  # noqa: E402
from regulatory_news.client import load_regulatory_articles

OUT = _REPO / "static_home" / "data"
HOME_NEWS_N = 3
REG_N = 3
HOME_RWA_PREVIEW_ROWS = 8
EXPLORE_ASSET_PREVIEW_ROWS = 8
STATIC_RWA_EXPLORE_ASSET_TYPE_PAGE = "rwa-explore-asset-type.html"
STATIC_RWA_EXPLORE_MARKET_PARTICIPANT_PAGE = "rwa-explore-market-participant.html"
STATIC_RWA_PARTICIPANTS_NETWORKS_PAGE = "rwa-participants-networks.html"
STATIC_RWA_PARTICIPANTS_PLATFORMS_PAGE = "rwa-participants-platforms.html"
STATIC_RWA_PARTICIPANTS_ASSET_MANAGERS_PAGE = "rwa-participants-asset-managers.html"
STATIC_RWA_STABLECOINS_PAGE = "rwa-stablecoins.html"
STATIC_RWA_US_TREASURIES_PAGE = "rwa-us-treasuries.html"
STATIC_RWA_TOKENIZED_STOCKS_PAGE = "rwa-tokenized-stocks.html"
APP_RWA_NETWORKS_URL = "https://app.rwa.xyz/networks"

_CAPTION_INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

DEFAULT_UA = os.environ.get(
    "STOCKANALYSIS_USER_AGENT",
    "Digital-Assets-Dashboard/1.0 (static site export; contact per StockAnalysis terms)",
).strip()


def _row_by_symbol(rows: list[CryptoEtpRow], symbol: str) -> CryptoEtpRow | None:
    u = symbol.strip().upper()
    for r in rows:
        if r.symbol.strip().upper() == u:
            return r
    return None


def _serialize_dt(o: object) -> str | None:
    if isinstance(o, datetime):
        return o.isoformat()
    return None


def _article_json(a: dict) -> dict:
    pub = a.get("published")
    return {
        "title": a.get("title") or "",
        "link": a.get("link") or "",
        "source": a.get("source") or "",
        "published": _serialize_dt(pub) if isinstance(pub, datetime) else None,
        "summary": (a.get("summary") or "")[:500],
        "country": a.get("country") or "",
    }


def _etp_row_json(r: CryptoEtpRow) -> dict:
    inc = (r.inception or "").strip()
    filing = (r.fund_filing_url or "").strip()
    assets = float(r.assets_usd) if has_listed_aum_usd(r.assets_usd) else None
    return {
        "symbol": r.symbol,
        "name": r.name,
        "price": r.price,
        "pct_52w": r.pct_52w,
        "assets_usd": assets,
        "issuer": (r.issuer or "").strip(),
        "custodian": resolve_custodian(r.symbol).strip(),
        "inception": inc,
        "fund_filing_url": filing,
    }


def _webapp_href(path: str) -> str:
    """Prefix FastAPI paths when STATIC_WEBAPP_BASE is set (absolute hub links from GitHub Pages)."""
    base = (os.environ.get("STATIC_WEBAPP_BASE") or "").strip().rstrip("/")
    p = path if path.startswith("/") else "/" + path
    return base + p if base else p


def _rwa_explore_gateways_static_html(at_href: str, mp_href: str) -> str:
    """Two Explore cards for static pages (classes align with ``static_home/styles.css``)."""
    ae = html_escape(at_href, quote=True)
    pe = html_escape(mp_href, quote=True)
    return (
        '<section class="rwa-explore-row" aria-label="Explore gateways">'
        '<div class="rwa-explore-card">'
        '<p class="eyebrow">On-chain</p>'
        '<h3>Explore by Asset Type</h3>'
        '<ul class="rwa-explore-list">'
        "<li>Stablecoins</li><li>US Treasuries</li><li>Tokenized Stocks</li>"
        "</ul>"
        '<p class="rwa-explore-tail">Use <strong>Explore</strong> to open the hub and go deeper on the next pages.</p>'
        f'<a class="btn btn-primary" href="{ae}">Explore</a>'
        "</div>"
        '<div class="rwa-explore-card">'
        '<p class="eyebrow">On-chain</p>'
        '<h3>Explore by Market Participant</h3>'
        '<ul class="rwa-explore-list">'
        "<li>Networks</li><li>Platforms</li><li>Asset Managers</li>"
        "</ul>"
        '<p class="rwa-explore-tail">Use <strong>Explore</strong> to open the hub and go deeper on the next pages.</p>'
        f'<a class="btn btn-primary" href="{pe}">Explore</a>'
        "</div>"
        "</section>"
    )


def _rwa_kpi_to_dict(k: object) -> dict[str, object]:
    delta = getattr(k, "delta_30d_pct", None)
    return {
        "label": str(getattr(k, "label", "")),
        "value_display": str(getattr(k, "value_display", "")),
        "delta_30d_pct": float(delta) if delta is not None else None,
    }


def _dataframe_json_records(df: Any) -> tuple[list[dict[str, object]], list[str]]:
    """Serialize RWA preview DataFrame rows for static JSON (no NaN / numpy scalars)."""
    import numpy as np

    if df is None or getattr(df, "empty", True):
        return [], []
    cols = [str(c) for c in df.columns]
    rows_out: list[dict[str, object]] = []
    for rec in df.to_dict(orient="records"):
        row: dict[str, object] = {}
        for key, val in rec.items():
            k = str(key)
            if val is None:
                row[k] = None
                continue
            if isinstance(val, np.integer):
                row[k] = int(val)
            elif isinstance(val, np.floating):
                fv = float(val)
                row[k] = None if np.isnan(fv) or np.isinf(fv) else fv
            elif isinstance(val, float):
                row[k] = None if np.isnan(val) or np.isinf(val) else val
            elif isinstance(val, bool):
                row[k] = val
            elif isinstance(val, int):
                row[k] = val
            else:
                row[k] = val
        rows_out.append(row)
    return rows_out, cols


def _kpi_legend_for_asset(overview_title: str) -> str:
    return (
        "All % changes in this row are 30-day (30D) (RWA.xyz). "
        f"Headline totals from the RWA.xyz {overview_title} Overview."
    )


def _html_escape_segment_with_bold(seg: str) -> str:
    if not seg:
        return ""
    parts = seg.split("**")
    out: list[str] = []
    for i, p in enumerate(parts):
        esc_p = html_escape(p)
        out.append(f"<strong>{esc_p}</strong>" if i % 2 == 1 else esc_p)
    return "".join(out)


def _caption_markdownish_to_html(text: str) -> str:
    """Turn ``**bold**`` and ``[lab](url)`` (no nested links) into safe HTML for static captions."""
    if not text:
        return ""
    chunks: list[str] = []
    i = 0
    for m in _CAPTION_INLINE_LINK_RE.finditer(text):
        chunks.append(_html_escape_segment_with_bold(text[i : m.start()]))
        chunks.append(
            f'<a href="{html_escape(m.group(2).strip(), quote=True)}" target="_blank" rel="noopener noreferrer">'
            f"{html_escape(m.group(1))}</a>"
        )
        i = m.end()
    chunks.append(_html_escape_segment_with_bold(text[i:]))
    return "".join(chunks)


def _league_split_payload(
    rows: list[Any],
    *,
    build_df: Any,
    block_heading: str,
    table_heading: str,
    chart_heading: str,
    name_column: str,
    value_column: str,
    chart_max_bars: int,
    caption_md: str | None,
    search_entity: str,
    section_intro_md: str | None = None,
    chart_note_below_split: bool = False,
    filter_note_suffix_all: str | None = None,
    filter_note_entity_plural: str | None = None,
    search_label: str | None = None,
    search_placeholder: str | None = None,
    chart_entity_plural: str | None = None,
) -> dict[str, Any] | None:
    """Serialize one Networks or Platforms league block for deep static pages."""
    from rwa_league.widgets import rwa_table_height

    if not rows:
        return None
    df = build_df(rows)
    rj, cj = _dataframe_json_records(df)
    ent = search_entity.strip().lower()
    if chart_entity_plural:
        plural = chart_entity_plural
    elif ent == "network":
        plural = "networks"
    elif ent == "platform":
        plural = "platforms"
    else:
        plural = "rows"
    n_sync = min(chart_max_bars, len(rows)) if rows else 1
    split_h = rwa_table_height(max(1, n_sync), max_h=560)
    chart_note = (
        f"The chart lists the top <strong>{chart_max_bars}</strong> {plural} "
        "by total value (labels include market share). Scroll the table for the full filtered list."
    )
    chart_note_inner = ""
    chart_note_wide = ""
    if chart_note_below_split:
        chart_note_wide = chart_note
    else:
        chart_note_inner = chart_note

    if search_label and search_placeholder:
        label, ph = search_label, search_placeholder
    elif ent == "network":
        label, ph = "Search network table", "Filter by network name…"
    elif ent == "platform":
        label, ph = "Search platform table", "Filter by platform name…"
    else:
        label, ph = "Search table", "Filter…"

    cap_html = _caption_markdownish_to_html(caption_md) if caption_md else ""
    section_intro_html = _caption_markdownish_to_html(section_intro_md) if section_intro_md else ""

    out: dict[str, Any] = {
        "block_heading": block_heading,
        "table_heading": table_heading,
        "chart_heading": chart_heading,
        "search_label": label,
        "search_placeholder": ph,
        "name_column": name_column,
        "value_column": value_column,
        "columns": cj,
        "rows_full": rj,
        "caption_html": cap_html,
        "chart_note_html": chart_note_inner,
        "wide_chart_note_html": chart_note_wide,
        "split_body_height_px": int(split_h),
        "chart_empty_filtered_entity_plural": plural,
    }
    if section_intro_html:
        out["section_intro_html"] = section_intro_html
    if filter_note_suffix_all:
        out["filter_note_suffix_all"] = filter_note_suffix_all
    if filter_note_entity_plural:
        out["filter_note_entity_plural"] = filter_note_entity_plural
    return out


def _build_rwa_stablecoins_deep_payload(sc_pack: tuple[Any, Any, Any, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    from home_layout import rwa_xyz_mirror_footer_text
    from rwa_league.client import APP_STABLECOINS
    from rwa_league.dataframe_table import (
        build_stablecoin_network_dataframe,
        build_stablecoin_platform_dataframe,
    )
    from rwa_league.widgets import (
        RWA_STABLECOINS_CHART_MAX_BARS,
        STABLECOIN_NETWORK_CAPTION,
        STABLECOIN_PLATFORM_CAPTION,
        STABLECOINS_RWA_LINK_LABEL,
    )

    rows_net: list[Any] = list(sc_pack[0])
    rows_plat: list[Any] = list(sc_pack[1])
    kpis: list[Any] = list(sc_pack[2])
    err_any = sc_pack[3]
    err_s = "" if err_any is None else str(err_any)

    def _seed() -> dict[str, Any]:
        return {
            "page_title": "Stablecoins — Digital Assets Dashboard",
            "band_label": "Stablecoins",
            "page_subtitle_html": (
                "This page mirrors the "
                f'<a href="{html_escape(APP_STABLECOINS, quote=True)}">RWA.xyz Stablecoins</a> view, including '
                "headline <strong>30-day (30D)</strong> % changes plus <strong>Networks</strong> and "
                "<strong>Platforms</strong> tables (aggregate stablecoin market cap by chain and by issuer). "
                "Level columns are market-cap amounts."
            ),
            "kpi_window_note": _kpi_legend_for_asset("Stablecoins"),
            "kpis": [_rwa_kpi_to_dict(k) for k in kpis],
            "chart_max_bars": RWA_STABLECOINS_CHART_MAX_BARS,
            "back_href": STATIC_RWA_EXPLORE_ASSET_TYPE_PAGE,
            "footer_note": re.sub(r"\*\*", "", rwa_xyz_mirror_footer_text()),
            "bottom_cta": {"href": APP_STABLECOINS, "label": STABLECOINS_RWA_LINK_LABEL},
        }

    if err_s.strip() and not rows_net and not rows_plat:
        b = _seed()
        b["error_mode"] = "warn_total"
        b["error_detail"] = err_s
        b["key_observations_html"] = ""
        b["networks"] = None
        b["platforms"] = None
        return b
    if not rows_net and not rows_plat:
        b = _seed()
        b["error_mode"] = "empty_total"
        b["empty_message"] = "No Stablecoins league rows returned."
        b["key_observations_html"] = ""
        b["networks"] = None
        b["platforms"] = None
        return b

    try:
        from pages.RWA_Stablecoins import _stablecoins_takeaway_html as _ko_sc

        ko_html = _ko_sc()
    except Exception as exc:  # pragma: no cover - export-only
        manifest["errors"].append(f"Stablecoins takeaway HTML export: {exc}")
        ko_html = ""

    b = _seed()
    b["error_mode"] = ""
    b["key_observations_html"] = ko_html
    b["between_ko_and_leagues_html"] = ""
    if not rows_net and rows_plat:
        b["between_ko_and_leagues_html"] = (
            '<p class="alert info">The <strong>Networks</strong> league was not present in the Stablecoins embed; '
            "the <strong>Platforms</strong> section below may still load.</p>"
        )
    b["after_network_block_html"] = ""
    if rows_net and not rows_plat:
        b["after_network_block_html"] = (
            '<p class="alert info">No <strong>Platforms</strong> league rows were returned for Stablecoins in this '
            "embed.</p>"
        )

    b["networks"] = (
        _league_split_payload(
            rows_net,
            build_df=build_stablecoin_network_dataframe,
            block_heading="By network (Stablecoins · Networks)",
            table_heading="Networks table",
            chart_heading="Top networks by value",
            name_column="Network",
            value_column="Total Value",
            chart_max_bars=RWA_STABLECOINS_CHART_MAX_BARS,
            caption_md=STABLECOIN_NETWORK_CAPTION,
            search_entity="network",
            section_intro_md=(
                "**Networks** league — aggregate stablecoin market cap by chain. "
                "**7-day** % change follows the numeric field from **RWA.xyz** (see table column help)."
            ),
            chart_note_below_split=True,
            filter_note_suffix_all="networks (Stablecoins · Networks).",
            filter_note_entity_plural="networks",
        )
        if rows_net
        else None
    )
    b["platforms"] = (
        _league_split_payload(
            rows_plat,
            build_df=build_stablecoin_platform_dataframe,
            block_heading="By platform (Stablecoins · Platforms)",
            table_heading="Platforms table",
            chart_heading="Top platforms by value",
            name_column="Platform",
            value_column="Total Value",
            chart_max_bars=RWA_STABLECOINS_CHART_MAX_BARS,
            caption_md=STABLECOIN_PLATFORM_CAPTION,
            search_entity="platform",
            section_intro_md=(
                "**Platforms** league — issuer-level aggregate stablecoin market cap from **RWA.xyz** "
                "(same **7-day** / **market share** fields as Networks)."
            ),
            chart_note_below_split=True,
            filter_note_suffix_all="platforms (Stablecoins · Platforms tab).",
            filter_note_entity_plural="platforms",
        )
        if rows_plat
        else None
    )
    return b


def _build_rwa_us_treasuries_deep_payload(tr_pack: tuple[Any, Any, Any, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    from home_layout import rwa_xyz_mirror_footer_text
    from rwa_league.client import APP_TREASURIES
    from rwa_league.dataframe_table import (
        build_us_treasury_network_dataframe,
        build_us_treasury_platform_dataframe,
    )
    from rwa_league.widgets import (
        RWA_TREASURIES_CHART_MAX_BARS,
        TREASURIES_RWA_LINK_LABEL,
        TREASURY_PLATFORM_CAPTION,
        TREASURY_RWA_CAPTION,
    )

    rows_net: list[Any] = list(tr_pack[0])
    rows_plat: list[Any] = list(tr_pack[1])
    kpis: list[Any] = list(tr_pack[2])
    err_any = tr_pack[3]
    err_s = "" if err_any is None else str(err_any)

    def _seed() -> dict[str, Any]:
        return {
            "page_title": "US Treasuries — Digital Assets Dashboard",
            "band_label": "US Treasuries",
            "page_subtitle_html": (
                f'Mirrors <a href="{html_escape(APP_TREASURIES, quote=True)}">'
                "RWA.xyz US Treasuries</a> — Distributed Networks and Platforms."
            ),
            "kpi_window_note": _kpi_legend_for_asset("US Treasuries"),
            "kpis": [_rwa_kpi_to_dict(k) for k in kpis],
            "chart_max_bars": RWA_TREASURIES_CHART_MAX_BARS,
            "back_href": STATIC_RWA_EXPLORE_ASSET_TYPE_PAGE,
            "footer_note": re.sub(r"\*\*", "", rwa_xyz_mirror_footer_text()),
            "bottom_cta": {"href": APP_TREASURIES, "label": TREASURIES_RWA_LINK_LABEL},
        }

    if err_s.strip() and not rows_net and not rows_plat:
        b = _seed()
        b["error_mode"] = "warn_total"
        b["error_detail"] = err_s
        b["key_observations_html"] = ""
        b["networks"] = None
        b["platforms"] = None
        return b
    if not rows_net and not rows_plat:
        b = _seed()
        b["error_mode"] = "empty_total"
        b["empty_message"] = "No US Treasuries league rows returned."
        b["key_observations_html"] = ""
        b["networks"] = None
        b["platforms"] = None
        return b

    try:
        from pages.RWA_US_Treasuries import _treasuries_takeaway_html as _ko_tr

        ko_html = _ko_tr()
    except Exception as exc:
        manifest["errors"].append(f"US Treasuries takeaway HTML export: {exc}")
        ko_html = ""

    b = _seed()
    b["error_mode"] = ""
    b["key_observations_html"] = ko_html
    b["networks"] = _league_split_payload(
        rows_net,
        build_df=build_us_treasury_network_dataframe,
        block_heading="By network (Distributed · Networks)",
        table_heading="Networks table",
        chart_heading="Top networks by value",
        name_column="Network",
        value_column="Distributed Value",
        chart_max_bars=RWA_TREASURIES_CHART_MAX_BARS,
        caption_md=TREASURY_RWA_CAPTION,
        search_entity="network",
    )
    b["platforms"] = _league_split_payload(
        rows_plat,
        build_df=build_us_treasury_platform_dataframe,
        block_heading="By platform (Distributed · Platforms)",
        table_heading="Platforms table",
        chart_heading="Top platforms by value",
        name_column="Platform",
        value_column="Total Value",
        chart_max_bars=RWA_TREASURIES_CHART_MAX_BARS,
        caption_md=TREASURY_PLATFORM_CAPTION,
        search_entity="platform",
    )
    return b


def _build_rwa_tokenized_stocks_deep_payload(st_pack: tuple[Any, Any, Any, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    from home_layout import rwa_xyz_mirror_footer_text
    from rwa_league.client import APP_STOCKS
    from rwa_league.dataframe_table import (
        build_tokenized_stock_network_dataframe,
        build_tokenized_stock_platform_dataframe,
    )
    from rwa_league.widgets import (
        RWA_TOKENIZED_STOCKS_CHART_MAX_BARS,
        TOKENIZED_STOCKS_RWA_CAPTION,
        TOKENIZED_STOCKS_RWA_LINK_LABEL,
    )

    rows_net_raw: list[Any] = list(st_pack[0])
    rows_plat: list[Any] = list(st_pack[1])
    kpis: list[Any] = list(st_pack[2])
    err_any = st_pack[3]
    err_s = "" if err_any is None else str(err_any)

    rows_net_sorted = sorted(rows_net_raw, key=lambda r: int(getattr(r, "rank", 0) or 0))

    def _seed() -> dict[str, Any]:
        return {
            "page_title": "Tokenized Stocks — Digital Assets Dashboard",
            "band_label": "Tokenized Stocks",
            "page_subtitle_html": (
                f'Mirrors <a href="{html_escape(APP_STOCKS, quote=True)}">RWA.xyz Tokenized Stocks</a>'
                " — Networks and Platforms."
            ),
            "kpi_window_note": _kpi_legend_for_asset("Tokenized Stocks"),
            "kpis": [_rwa_kpi_to_dict(k) for k in kpis],
            "chart_max_bars": RWA_TOKENIZED_STOCKS_CHART_MAX_BARS,
            "back_href": STATIC_RWA_EXPLORE_ASSET_TYPE_PAGE,
            "footer_note": re.sub(r"\*\*", "", rwa_xyz_mirror_footer_text()),
            "bottom_cta": {"href": APP_STOCKS, "label": TOKENIZED_STOCKS_RWA_LINK_LABEL},
        }

    if err_s.strip() and not rows_net_raw and not rows_plat:
        b = _seed()
        b["error_mode"] = "warn_total"
        b["error_detail"] = err_s
        b["key_observations_html"] = ""
        b["networks"] = None
        b["platforms"] = None
        return b
    if not rows_net_raw and not rows_plat:
        b = _seed()
        b["error_mode"] = "empty_total"
        b["empty_message"] = "No Tokenized Stocks league rows returned."
        b["key_observations_html"] = ""
        b["networks"] = None
        b["platforms"] = None
        return b

    try:
        from pages.RWA_Tokenized_Stocks import _tokenized_stocks_takeaway_html as _ko_st

        ko_html = _ko_st()
    except Exception as exc:
        manifest["errors"].append(f"Tokenized Stocks takeaway HTML export: {exc}")
        ko_html = ""

    b = _seed()
    b["error_mode"] = ""
    b["key_observations_html"] = ko_html
    b["networks"] = _league_split_payload(
        rows_net_sorted,
        build_df=build_tokenized_stock_network_dataframe,
        block_heading="By Network (Distributed · Networks)",
        table_heading="Networks table",
        chart_heading="Top networks by value",
        name_column="Network",
        value_column="Distributed Value",
        chart_max_bars=RWA_TOKENIZED_STOCKS_CHART_MAX_BARS,
        caption_md=None,
        search_entity="network",
    )
    b["platforms"] = _league_split_payload(
        rows_plat,
        build_df=build_tokenized_stock_platform_dataframe,
        block_heading="By Platform (Distributed · Platforms)",
        table_heading="Platforms table",
        chart_heading="Top platforms by value",
        name_column="Platform",
        value_column="Distributed Value",
        chart_max_bars=RWA_TOKENIZED_STOCKS_CHART_MAX_BARS,
        caption_md=TOKENIZED_STOCKS_RWA_CAPTION,
        search_entity="platform",
    )
    return b


def _build_rwa_explore_asset_type_payload(
    manifest: dict,
    sc_pack: tuple[Any, Any, Any, Any],
    tr_pack: tuple[Any, Any, Any, Any],
    st_pack: tuple[Any, Any, Any, Any],
) -> dict[str, Any]:
    """Preview sections aligned with Streamlit ``show_rwa_explore_by_asset_type_widget`` (+ FastAPI hub index)."""
    from home_layout import rwa_xyz_mirror_footer_text
    from rwa_league.client import APP_STABLECOINS, APP_STOCKS, APP_TREASURIES
    from rwa_league.dataframe_table import (
        build_stablecoin_network_dataframe,
        build_stablecoin_platform_dataframe,
        build_tokenized_stock_network_dataframe,
        build_tokenized_stock_platform_dataframe,
        build_us_treasury_network_dataframe,
    )
    from rwa_league.widgets import (
        STABLECOINS_RWA_LINK_LABEL,
        TREASURIES_RWA_LINK_LABEL,
        TOKENIZED_STOCKS_RWA_LINK_LABEL,
    )

    sections: list[dict[str, Any]] = []

    sc_net, sc_plat, sc_kpis, sc_err = sc_pack

    sec_sc: dict[str, Any] = {
        "id": "stablecoins",
        "title": "Stablecoins",
        "anchor_id": "jd-rwa-stablecoins",
        "kpi_window_note": _kpi_legend_for_asset("Stablecoins"),
        "kpis": [_rwa_kpi_to_dict(k) for k in sc_kpis],
        "table_subheading": None,
        "columns": [],
        "rows": [],
        "preview_note": "",
        "info_html": "",
        "warn_html": "",
        "cta": [
            {
                "href": STATIC_RWA_STABLECOINS_PAGE,
                "label": "Open full Stablecoins table",
                "variant": "primary",
                "internal": True,
            },
            {"href": APP_STABLECOINS, "label": STABLECOINS_RWA_LINK_LABEL, "variant": "secondary"},
        ],
    }
    if sc_err and not sc_net and not sc_plat:
        sec_sc["warn_html"] = f'<p class="alert warn">{html_escape(str(sc_err))}</p>'
    elif not sc_net and not sc_plat:
        sec_sc["info_html"] = '<p class="alert info">No Stablecoins league rows returned.</p>'
    elif sc_net:
        prev = list(sc_net)[:EXPLORE_ASSET_PREVIEW_ROWS]
        df_sc = build_stablecoin_network_dataframe(prev)
        rj, cj = _dataframe_json_records(df_sc)
        sec_sc["columns"], sec_sc["rows"] = cj, rj
        sec_sc["table_subheading"] = "By network (Stablecoins · Networks)"
        sec_sc["preview_note"] = (
            f"Preview: first {len(prev)} of {len(sc_net)} networks (Stablecoins · Networks)."
        )
    elif sc_plat:
        prev = list(sc_plat)[:EXPLORE_ASSET_PREVIEW_ROWS]
        df_sc = build_stablecoin_platform_dataframe(prev)
        rj, cj = _dataframe_json_records(df_sc)
        sec_sc["columns"], sec_sc["rows"] = cj, rj
        sec_sc["preview_note"] = (
            f"Preview: first {len(prev)} of {len(sc_plat)} platforms (Stablecoins · Platforms)."
        )
    else:
        sec_sc["info_html"] = '<p class="muted"><em>No stablecoin league rows.</em></p>'
    sections.append(sec_sc)

    tr_rows, tr_plat, tr_kpis, tr_err = tr_pack

    sec_tr: dict[str, Any] = {
        "id": "treasuries",
        "title": "US Treasuries",
        "anchor_id": "jd-rwa-treasuries",
        "kpi_window_note": _kpi_legend_for_asset("US Treasuries"),
        "kpis": [_rwa_kpi_to_dict(k) for k in tr_kpis],
        "table_subheading": "By network (Distributed · Networks)",
        "columns": [],
        "rows": [],
        "preview_note": "",
        "info_html": "",
        "warn_html": "",
        "cta": [
            {
                "href": STATIC_RWA_US_TREASURIES_PAGE,
                "label": "Open full US Treasuries table",
                "variant": "primary",
                "internal": True,
            },
            {"href": APP_TREASURIES, "label": TREASURIES_RWA_LINK_LABEL, "variant": "secondary"},
        ],
    }
    if tr_err and not tr_rows and not tr_plat:
        sec_tr["warn_html"] = f'<p class="alert warn">{html_escape(str(tr_err))}</p>'
    elif not tr_rows and not tr_plat:
        sec_tr["info_html"] = '<p class="alert info">No US Treasuries league rows returned.</p>'
    elif tr_rows:
        prev = list(tr_rows)[:EXPLORE_ASSET_PREVIEW_ROWS]
        df_tr = build_us_treasury_network_dataframe(prev)
        rj, cj = _dataframe_json_records(df_tr)
        sec_tr["columns"], sec_tr["rows"] = cj, rj
        sec_tr["preview_note"] = (
            f"Preview: first {len(prev)} of {len(tr_rows)} networks (US Treasuries · Distributed · Networks)."
        )
    else:
        sec_tr["info_html"] = '<p class="muted"><em>No treasury network rows.</em></p>'
    sections.append(sec_tr)

    st_net, st_plat, st_kpis, st_err = st_pack

    sec_st: dict[str, Any] = {
        "id": "tokenized_stocks",
        "title": "Tokenized Stocks",
        "anchor_id": "jd-rwa-tokenized-stocks",
        "kpi_window_note": _kpi_legend_for_asset("Tokenized Stocks"),
        "kpis": [_rwa_kpi_to_dict(k) for k in st_kpis],
        "table_subheading": None,
        "columns": [],
        "rows": [],
        "preview_note": "",
        "info_html": "",
        "warn_html": "",
        "cta": [
            {
                "href": STATIC_RWA_TOKENIZED_STOCKS_PAGE,
                "label": "Open full Tokenized Stocks table",
                "variant": "primary",
                "internal": True,
            },
            {"href": APP_STOCKS, "label": TOKENIZED_STOCKS_RWA_LINK_LABEL, "variant": "secondary"},
        ],
    }
    if st_err and not st_net and not st_plat:
        sec_st["warn_html"] = f'<p class="alert warn">{html_escape(str(st_err))}</p>'
    elif not st_net and not st_plat:
        sec_st["info_html"] = '<p class="alert info">No Tokenized Stocks league rows returned.</p>'
    elif st_net:
        ordered_n = sorted(st_net, key=lambda r: int(r.rank))
        prev = ordered_n[:EXPLORE_ASSET_PREVIEW_ROWS]
        df_st = build_tokenized_stock_network_dataframe(prev)
        rj, cj = _dataframe_json_records(df_st)
        sec_st["columns"], sec_st["rows"] = cj, rj
        sec_st["table_subheading"] = "By Network (Distributed · Networks)"
        sec_st["preview_note"] = (
            f"Preview: first {len(prev)} of {len(st_net)} networks "
            "(Tokenized Stocks · Distributed · Networks), sorted by #."
        )
    elif st_plat:
        prev = list(st_plat)[:EXPLORE_ASSET_PREVIEW_ROWS]
        df_st = build_tokenized_stock_platform_dataframe(prev)
        rj, cj = _dataframe_json_records(df_st)
        sec_st["columns"], sec_st["rows"] = cj, rj
        sec_st["preview_note"] = (
            f"Preview: first {len(prev)} of {len(st_plat)} platforms "
            "(Tokenized Stocks · Distributed · Platforms)."
        )
    else:
        sec_st["info_html"] = '<p class="alert info">No Tokenized Stocks network or platform rows returned.</p>'
    sections.append(sec_st)

    intro_html = (
        "<p><strong>On-chain RWA</strong> by asset—short previews for "
        "<strong>Stablecoins</strong>, <strong>US Treasuries</strong>, and <strong>Tokenized Stocks</strong> "
        "(<strong>RWA.xyz</strong>). Use <strong>Open full … table</strong> for search, charts, and full leagues; "
        "use the second button to open the live app.</p>"
    )

    return {
        "page_title": "Explore by Asset Type — Digital Assets Dashboard",
        "page_subtitle_html": (
            f"Network or platform previews (first {EXPLORE_ASSET_PREVIEW_ROWS} rows each)—aligned with Streamlit "
            "<strong>Explore by Asset Type</strong>."
        ),
        "intro_html": intro_html,
        "sections": sections,
        "footer_note": re.sub(r"\*\*", "", rwa_xyz_mirror_footer_text()),
        "links": {
            "rwa_global": "rwa-global.html",
            "hub_home": "index.html",
        },
    }


def _build_rwa_explore_market_participant_payload(
    manifest: dict,
    net_pack: tuple[list[Any], list[Any], Any],
    plat_pack: tuple[list[Any], list[Any], Any],
    am_pack: tuple[list[Any], list[Any], Any],
) -> dict[str, Any]:
    """Preview sections aligned with Streamlit ``show_rwa_explore_by_market_participant_widget``."""
    from home_layout import rwa_xyz_mirror_footer_text
    from rwa_league.client import APP_ASSET_MANAGERS, APP_NETWORKS, APP_PLATFORMS
    from rwa_league.dataframe_table import (
        build_rwa_asset_managers_page_dataframe,
        build_rwa_networks_page_dataframe,
        build_rwa_platforms_page_dataframe,
    )
    from rwa_league.widgets import (
        ASSET_MANAGERS_RWA_LINK_LABEL,
        ASSET_MANAGERS_RWA_URL,
        GLOBAL_MARKET_RWA_LINK_LABEL,
        GLOBAL_MARKET_RWA_URL,
        PLATFORMS_RWA_LINK_LABEL,
        PLATFORMS_RWA_URL,
    )

    sections: list[dict[str, Any]] = []

    pnet_rows, pnet_kpis, pnet_err = net_pack
    sec_net: dict[str, Any] = {
        "id": "participant_networks",
        "title": "Networks",
        "anchor_id": "jd-rwa-participants-networks",
        "kpi_window_note": _kpi_legend_for_asset("Networks"),
        "kpis": [_rwa_kpi_to_dict(k) for k in pnet_kpis],
        "table_subheading": None,
        "info_html_preview": "",
        "columns": [],
        "rows": [],
        "preview_note": "",
        "info_html": "",
        "warn_html": "",
        "cta": [
            {
                "href": STATIC_RWA_PARTICIPANTS_NETWORKS_PAGE,
                "label": "Open full Participants — Networks page",
                "variant": "primary",
                "internal": True,
            },
            {"href": GLOBAL_MARKET_RWA_URL, "label": GLOBAL_MARKET_RWA_LINK_LABEL, "variant": "secondary"},
        ],
    }
    if pnet_err and not pnet_rows:
        sec_net["warn_html"] = f'<p class="alert warn">{html_escape(str(pnet_err))}</p>'
    elif not pnet_rows:
        sec_net["info_html"] = '<p class="alert info">No Networks league rows returned.</p>'
    else:
        sec_net["info_html_preview"] = (
            '<p class="muted">Preview of the <strong>Networks</strong> table from '
            f'<a href="{html_escape(APP_NETWORKS, quote=True)}" target="_blank" rel="noopener noreferrer">RWA.xyz Networks</a> '
            "(same KPI totals formatted under <strong>Participants — Networks</strong>).</p>"
        )
        prev = list(pnet_rows)[:EXPLORE_ASSET_PREVIEW_ROWS]
        df_n = build_rwa_networks_page_dataframe(prev)
        rj, cj = _dataframe_json_records(df_n)
        sec_net["columns"], sec_net["rows"] = cj, rj
        sec_net["preview_note"] = (
            f"Preview: first {len(prev)} of {len(pnet_rows)} networks (Distributed · Networks)."
        )
    sections.append(sec_net)

    pplat_rows, pplat_kpis, pplat_err = plat_pack
    sec_plat: dict[str, Any] = {
        "id": "participant_platforms",
        "title": "Platforms",
        "anchor_id": "jd-rwa-participants-platforms",
        "kpi_window_note": _kpi_legend_for_asset("Platforms"),
        "kpis": [_rwa_kpi_to_dict(k) for k in pplat_kpis],
        "table_subheading": None,
        "info_html_preview": "",
        "columns": [],
        "rows": [],
        "preview_note": "",
        "info_html": "",
        "warn_html": "",
        "cta": [
            {
                "href": STATIC_RWA_PARTICIPANTS_PLATFORMS_PAGE,
                "label": "Open full Participants — Platforms page",
                "variant": "primary",
                "internal": True,
            },
            {"href": PLATFORMS_RWA_URL, "label": PLATFORMS_RWA_LINK_LABEL, "variant": "secondary"},
        ],
    }
    if pplat_err and not pplat_rows:
        sec_plat["warn_html"] = f'<p class="alert warn">{html_escape(str(pplat_err))}</p>'
    elif not pplat_rows:
        sec_plat["info_html"] = '<p class="alert info">No Platforms league rows returned.</p>'
    else:
        sec_plat[
            "info_html_preview"
        ] = f'<p class="muted">Preview of the <strong>Distributed</strong> Platforms issuer table from <a href="{html_escape(APP_PLATFORMS, quote=True)}" target="_blank" rel="noopener noreferrer">RWA.xyz Platforms</a>.</p>'
        prev = list(pplat_rows)[:EXPLORE_ASSET_PREVIEW_ROWS]
        df_p = build_rwa_platforms_page_dataframe(prev)
        rj, cj = _dataframe_json_records(df_p)
        sec_plat["columns"], sec_plat["rows"] = cj, rj
        sec_plat["preview_note"] = (
            f"Preview: first {len(prev)} of {len(pplat_rows)} platforms (Distributed · Platforms)."
        )
    sections.append(sec_plat)

    pam_rows, pam_kpis, pam_err = am_pack
    sec_am: dict[str, Any] = {
        "id": "participant_asset_managers",
        "title": "Asset Managers",
        "anchor_id": "jd-rwa-participants-asset-managers",
        "kpi_window_note": _kpi_legend_for_asset("Asset Managers"),
        "kpis": [_rwa_kpi_to_dict(k) for k in pam_kpis],
        "table_subheading": None,
        "info_html_preview": "",
        "columns": [],
        "rows": [],
        "preview_note": "",
        "info_html": "",
        "warn_html": "",
        "cta": [
            {
                "href": STATIC_RWA_PARTICIPANTS_ASSET_MANAGERS_PAGE,
                "label": "Open full Participants — Asset Managers page",
                "variant": "primary",
                "internal": True,
            },
            {"href": ASSET_MANAGERS_RWA_URL, "label": ASSET_MANAGERS_RWA_LINK_LABEL, "variant": "secondary"},
        ],
    }
    if pam_err and not pam_rows:
        sec_am["warn_html"] = f'<p class="alert warn">{html_escape(str(pam_err))}</p>'
    elif not pam_rows:
        sec_am["info_html"] = '<p class="alert info">No Asset Managers league rows returned.</p>'
    else:
        sec_am[
            "info_html_preview"
        ] = f'<p class="muted">Preview of the <strong>Distributed</strong> Asset Managers table from <a href="{html_escape(APP_ASSET_MANAGERS, quote=True)}" target="_blank" rel="noopener noreferrer">RWA.xyz Asset Managers</a>.</p>'
        prev = list(pam_rows)[:EXPLORE_ASSET_PREVIEW_ROWS]
        df_a = build_rwa_asset_managers_page_dataframe(prev)
        rj, cj = _dataframe_json_records(df_a)
        sec_am["columns"], sec_am["rows"] = cj, rj
        sec_am["preview_note"] = (
            f"Preview: first {len(prev)} of {len(pam_rows)} asset managers (Distributed · Asset Managers)."
        )
    sections.append(sec_am)

    intro_html = (
        "<p><strong>RWA market participants</strong>—previews for "
        "<strong>Networks</strong>, <strong>Platforms</strong> (issuers), and <strong>Asset Managers</strong> "
        "(<strong>RWA.xyz</strong>). Use <strong>Open full … page</strong> for search, charts, and full tables; "
        "use the second button for the live app.</p>"
    )

    return {
        "page_title": "Explore by Market Participant — Digital Assets Dashboard",
        "page_subtitle_html": (
            f"First {EXPLORE_ASSET_PREVIEW_ROWS} rows per preview—aligned with Streamlit "
            "<strong>Explore by Market Participant</strong>."
        ),
        "intro_html": intro_html,
        "sections": sections,
        "footer_note": re.sub(r"\*\*", "", rwa_xyz_mirror_footer_text()),
        "links": {
            "rwa_global": "rwa-global.html",
            "hub_home": "index.html",
            "explore_asset_type": STATIC_RWA_EXPLORE_ASSET_TYPE_PAGE,
        },
    }


def _build_rwa_participants_networks_deep_payload(
    pack: tuple[list[Any], list[Any], Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    from home_layout import rwa_xyz_mirror_footer_text
    from rwa_league.client import APP_NETWORKS
    from rwa_league.dataframe_table import build_rwa_networks_page_dataframe
    from rwa_league.widgets import (
        GLOBAL_MARKET_RWA_LINK_LABEL,
        GLOBAL_MARKET_RWA_URL,
        RWA_DATA_SOURCE_CAPTION,
        RWA_PARTICIPANTS_CHART_MAX_BARS,
    )

    rows: list[Any] = list(pack[0])
    kpis: list[Any] = list(pack[1])
    err_any = pack[2]
    err_s = "" if err_any is None else str(err_any)

    def _seed() -> dict[str, Any]:
        return {
            "page_title": "Participants — Networks — Digital Assets Dashboard",
            "band_label": "Participants — Networks",
            "page_subtitle_html": (
                f'Mirrors <a href="{html_escape(APP_NETWORKS, quote=True)}">RWA.xyz Networks</a> '
                "— Distributed Networks league."
            ),
            "kpi_window_note": _kpi_legend_for_asset("Networks"),
            "kpis": [_rwa_kpi_to_dict(k) for k in kpis],
            "chart_max_bars": RWA_PARTICIPANTS_CHART_MAX_BARS,
            "back_href": STATIC_RWA_EXPLORE_MARKET_PARTICIPANT_PAGE,
            "footer_note": re.sub(r"\*\*", "", rwa_xyz_mirror_footer_text()),
            "bottom_cta": {"href": GLOBAL_MARKET_RWA_URL, "label": GLOBAL_MARKET_RWA_LINK_LABEL},
        }

    if err_s.strip() and not rows:
        b = _seed()
        b["error_mode"] = "warn_total"
        b["error_detail"] = err_s
        b["key_observations_html"] = ""
        b["networks"] = None
        b["platforms"] = None
        return b
    if not rows:
        b = _seed()
        b["error_mode"] = "empty_total"
        b["empty_message"] = "No network rows returned."
        b["key_observations_html"] = ""
        b["networks"] = None
        b["platforms"] = None
        return b

    try:
        from pages.RWA_Participants_Networks import (
            _participants_networks_takeaway_html as _ko,
        )

        ko_html = _ko()
    except Exception as exc:
        manifest["errors"].append(f"Participants Networks takeaway HTML export: {exc}")
        ko_html = ""

    b = _seed()
    b["error_mode"] = ""
    b["key_observations_html"] = ko_html
    b["networks"] = _league_split_payload(
        sorted(rows, key=lambda r: int(getattr(r, "rank", 0) or 0)),
        build_df=build_rwa_networks_page_dataframe,
        block_heading="By network (Distributed · Networks)",
        table_heading="Networks table",
        chart_heading="Top networks by distributed value",
        name_column="Network",
        value_column="RWA value (distributed)",
        chart_max_bars=RWA_PARTICIPANTS_CHART_MAX_BARS,
        caption_md=RWA_DATA_SOURCE_CAPTION,
        search_entity="network",
    )
    b["platforms"] = None
    return b


def _build_rwa_participants_platforms_deep_payload(
    pack: tuple[list[Any], list[Any], Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    from home_layout import rwa_xyz_mirror_footer_text
    from rwa_league.client import APP_PLATFORMS
    from rwa_league.dataframe_table import build_rwa_platforms_page_dataframe
    from rwa_league.widgets import (
        PLATFORMS_RWA_LINK_LABEL,
        PLATFORMS_RWA_URL,
        RWA_PARTICIPANTS_CHART_MAX_BARS,
        RWA_PLATFORMS_DATA_SOURCE_CAPTION,
    )

    rows_l: list[Any] = list(pack[0])
    kpis: list[Any] = list(pack[1])
    err_any = pack[2]
    err_s = "" if err_any is None else str(err_any)

    def _seed() -> dict[str, Any]:
        return {
            "page_title": "Participants — Platforms — Digital Assets Dashboard",
            "band_label": "Participants — Platforms",
            "page_subtitle_html": (
                f'Mirrors <a href="{html_escape(APP_PLATFORMS, quote=True)}">RWA.xyz Platforms</a> '
                "— Distributed Platforms league."
            ),
            "kpi_window_note": _kpi_legend_for_asset("Platforms"),
            "kpis": [_rwa_kpi_to_dict(k) for k in kpis],
            "chart_max_bars": RWA_PARTICIPANTS_CHART_MAX_BARS,
            "back_href": STATIC_RWA_EXPLORE_MARKET_PARTICIPANT_PAGE,
            "footer_note": re.sub(r"\*\*", "", rwa_xyz_mirror_footer_text()),
            "bottom_cta": {"href": PLATFORMS_RWA_URL, "label": PLATFORMS_RWA_LINK_LABEL},
        }

    if err_s.strip() and not rows_l:
        b = _seed()
        b["error_mode"] = "warn_total"
        b["error_detail"] = err_s
        b["key_observations_html"] = ""
        b["networks"] = None
        b["platforms"] = None
        return b
    if not rows_l:
        b = _seed()
        b["error_mode"] = "empty_total"
        b["empty_message"] = "No platform rows returned."
        b["key_observations_html"] = ""
        b["networks"] = None
        b["platforms"] = None
        return b

    try:
        from pages.RWA_Participants_Platforms import (
            _participants_platforms_takeaway_html as _ko,
        )

        ko_html = _ko()
    except Exception as exc:
        manifest["errors"].append(f"Participants Platforms takeaway HTML export: {exc}")
        ko_html = ""

    b = _seed()
    b["error_mode"] = ""
    b["key_observations_html"] = ko_html
    b["networks"] = _league_split_payload(
        list(rows_l),
        build_df=build_rwa_platforms_page_dataframe,
        block_heading="By platform (Distributed · Platforms)",
        table_heading="Platforms table",
        chart_heading="Top platforms by value",
        name_column="Platform",
        value_column="RWA value (distributed)",
        chart_max_bars=RWA_PARTICIPANTS_CHART_MAX_BARS,
        caption_md=RWA_PLATFORMS_DATA_SOURCE_CAPTION,
        search_entity="platform",
    )
    b["platforms"] = None
    return b


def _build_rwa_participants_asset_managers_deep_payload(
    pack: tuple[list[Any], list[Any], Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    from home_layout import rwa_xyz_mirror_footer_text
    from rwa_league.client import APP_ASSET_MANAGERS
    from rwa_league.dataframe_table import build_rwa_asset_managers_page_dataframe
    from rwa_league.widgets import (
        ASSET_MANAGERS_RWA_LINK_LABEL,
        ASSET_MANAGERS_RWA_URL,
        RWA_ASSET_MANAGERS_DATA_SOURCE_CAPTION,
        RWA_PARTICIPANTS_CHART_MAX_BARS,
    )

    rows_l: list[Any] = list(pack[0])
    kpis: list[Any] = list(pack[1])
    err_any = pack[2]
    err_s = "" if err_any is None else str(err_any)

    def _seed() -> dict[str, Any]:
        return {
            "page_title": "Participants — Asset Managers — Digital Assets Dashboard",
            "band_label": "Participants — Asset Managers",
            "page_subtitle_html": (
                f'Mirrors <a href="{html_escape(APP_ASSET_MANAGERS, quote=True)}">RWA.xyz Asset Managers</a>.'
            ),
            "kpi_window_note": _kpi_legend_for_asset("Asset Managers"),
            "kpis": [_rwa_kpi_to_dict(k) for k in kpis],
            "chart_max_bars": RWA_PARTICIPANTS_CHART_MAX_BARS,
            "back_href": STATIC_RWA_EXPLORE_MARKET_PARTICIPANT_PAGE,
            "footer_note": re.sub(r"\*\*", "", rwa_xyz_mirror_footer_text()),
            "bottom_cta": {"href": ASSET_MANAGERS_RWA_URL, "label": ASSET_MANAGERS_RWA_LINK_LABEL},
        }

    if err_s.strip() and not rows_l:
        b = _seed()
        b["error_mode"] = "warn_total"
        b["error_detail"] = err_s
        b["key_observations_html"] = ""
        b["networks"] = None
        b["platforms"] = None
        return b
    if not rows_l:
        b = _seed()
        b["error_mode"] = "empty_total"
        b["empty_message"] = "No asset manager rows returned."
        b["key_observations_html"] = ""
        b["networks"] = None
        b["platforms"] = None
        return b

    try:
        from pages.RWA_Participants_Asset_Managers import (
            _participants_asset_managers_takeaway_html as _ko,
        )

        ko_html = _ko()
    except Exception as exc:
        manifest["errors"].append(f"Participants Asset Managers takeaway HTML export: {exc}")
        ko_html = ""

    b = _seed()
    b["error_mode"] = ""
    b["key_observations_html"] = ko_html
    b["networks"] = _league_split_payload(
        list(rows_l),
        build_df=build_rwa_asset_managers_page_dataframe,
        block_heading="By asset manager (Distributed · Asset Managers)",
        table_heading="Asset Managers table",
        chart_heading="Top asset managers by value",
        name_column="Asset manager",
        value_column="RWA value (distributed)",
        chart_max_bars=RWA_PARTICIPANTS_CHART_MAX_BARS,
        caption_md=RWA_ASSET_MANAGERS_DATA_SOURCE_CAPTION,
        search_entity="platform",
        search_label="Search asset managers table",
        search_placeholder="Filter by asset manager name…",
        chart_entity_plural="asset managers",
    )
    b["platforms"] = None
    return b


def _kpi_delta(symbol: str, row: CryptoEtpRow | None) -> dict:
    p, lbl = etp_symbol_price_change_cached(symbol)
    if p is not None:
        return {"pct": round(float(p), 4), "window": lbl or ""}
    if row is not None and row.pct_52w is not None:
        return {"pct": round(float(row.pct_52w), 4), "window": "52W"}
    return {"pct": None, "window": ""}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"generated_at": datetime.now(timezone.utc).isoformat(), "errors": []}

    # --- ETP list + AUM + KPIs (StockAnalysis + Yahoo; same as app) ---
    etp_result = fetch_crypto_etps_enriched(DEFAULT_UA)
    if etp_result.error:
        manifest["errors"].append(f"ETP scrape: {etp_result.error}")
    rows = sorted_by_assets(etp_result.rows)
    rows_payload = [_etp_row_json(r) for r in rows]

    pairs = etp_rows_to_fund_pairs(rows)
    chart_df, chart_err = build_aggregate_aum_history_12m(list(pairs))
    if chart_err:
        manifest["errors"].append(f"AUM chart: {chart_err}")

    series: list[dict] = []
    if chart_df is not None and not chart_df.empty:
        for _, r in chart_df.iterrows():
            d = r["date"]
            if hasattr(d, "isoformat"):
                ds = d.isoformat()
            else:
                ds = str(d)
            series.append(
                {
                    "date": ds,
                    "aum_billions": float(r["total_aum_usd"]) / 1e9,
                }
            )

    agg_pct, agg_lbl = aggregate_aum_pct_from_history(chart_df)
    total = total_aum_usd(rows)
    aum_s = format_usd_compact(total) if total > 0 else "—"

    ibit_r = _row_by_symbol(rows, "IBIT")
    etha_r = _row_by_symbol(rows, "ETHA")
    ibit_aum = (
        format_usd_compact(ibit_r.assets_usd)
        if ibit_r and has_listed_aum_usd(ibit_r.assets_usd)
        else "—"
    )
    etha_aum = (
        format_usd_compact(etha_r.assets_usd)
        if etha_r and has_listed_aum_usd(etha_r.assets_usd)
        else "—"
    )

    kpis = {
        "total_aum_display": aum_s,
        "aggregate_pct": round(float(agg_pct), 4) if agg_pct is not None else None,
        "aggregate_window": agg_lbl or "",
        "ibit": {"aum_display": ibit_aum, "delta": _kpi_delta("IBIT", ibit_r)},
        "etha": {"aum_display": etha_aum, "delta": _kpi_delta("ETHA", etha_r)},
    }

    (OUT / "etps.json").write_text(
        json.dumps({"rows": rows_payload}, indent=2),
        encoding="utf-8",
    )
    (OUT / "aum_series.json").write_text(json.dumps({"series": series}, indent=2), encoding="utf-8")
    (OUT / "etp_kpis.json").write_text(json.dumps(kpis, indent=2), encoding="utf-8")

    # --- Crypto price ticker marquee (same CoinGecko→CoinCap pipeline as ``price_ticker`` / Streamlit) ---
    try:
        from price_ticker import TICKER_COUNT, fetch_top_crypto_tickers, hub_ticker_static_json_payload

        t_rows, t_err, t_src = fetch_top_crypto_tickers(TICKER_COUNT)
        crypto_payload = hub_ticker_static_json_payload(t_rows, t_err, t_src)
        crypto_payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        manifest["errors"].append(f"Crypto ticker export: {exc}")
        crypto_payload = {
            "banner_title": "Top 25 Cryptocurrencies",
            "chips_inner_html": f'<span class="ticker-chip ticker-chip--error">{html_escape(str(exc))}</span>',
            "source": "",
            "error": str(exc),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    (OUT / "crypto_ticker.json").write_text(
        json.dumps(crypto_payload, indent=2),
        encoding="utf-8",
    )

    # --- Home RSS lanes ---
    articles, feed_errs = load_all_feeds(DEFAULT_FEEDS)
    for e in feed_errs:
        manifest["errors"].append(f"news RSS: {e}")
    unique = dedupe_articles(articles, max_items=None)
    home_top = unique[:HOME_NEWS_N]

    reg_articles, reg_errs = load_regulatory_articles()
    for e in reg_errs:
        manifest["errors"].append(f"reg RSS: {e}")
    reg_top = reg_articles[:REG_N]

    (OUT / "home_news.json").write_text(
        json.dumps({"items": [_article_json(a) for a in home_top]}, indent=2),
        encoding="utf-8",
    )
    (OUT / "regulatory.json").write_text(
        json.dumps({"items": [_article_json(a) for a in reg_top]}, indent=2),
        encoding="utf-8",
    )
    # Full lists for static GitHub Pages (search + pagination); same pools as Streamlit All articles / Regulatory.
    (OUT / "all_articles.json").write_text(
        json.dumps({"items": [_article_json(a) for a in unique]}, indent=2),
        encoding="utf-8",
    )
    (OUT / "all_regulatory.json").write_text(
        json.dumps({"items": [_article_json(a) for a in reg_articles]}, indent=2),
        encoding="utf-8",
    )

    # --- ETF / ETP headline pool (same filter + 3-month window as app) ---
    etf_all, etf_feed_errs = load_all_etf_etp_news_cached()
    for e in etf_feed_errs:
        manifest["errors"].append(f"ETF news RSS: {e}")

    etf_items = [_article_json(a) for a in etf_all]
    (OUT / "etf_news.json").write_text(
        json.dumps({"items": etf_items}, indent=2),
        encoding="utf-8",
    )
    pulse = etf_items[:ETP_PULSE_PREVIEW_COUNT]
    (OUT / "etf_pulse.json").write_text(json.dumps({"items": pulse}, indent=2), encoding="utf-8")

    # --- On-chain hub (Streamlit home): RWA Global Market KPIs + Networks preview + explore hrefs ---
    import pandas as pd
    from rwa_league.client import fetch_rwa_home_data
    from rwa_league.dataframe_table import build_rwa_dataframe

    try:
        rwa_rows, rwa_kpis, rwa_err = fetch_rwa_home_data()
    except Exception as exc:
        rwa_rows, rwa_kpis, rwa_err = [], [], str(exc)

    if rwa_err:
        manifest["errors"].append(f"RWA home overview: {rwa_err}")

    rwa_preview = list(rwa_rows)[:HOME_RWA_PREVIEW_ROWS]
    rwa_df = build_rwa_dataframe(rwa_preview) if rwa_preview else pd.DataFrame()
    rwa_table_rows, rwa_columns = _dataframe_json_records(rwa_df)

    explore_at = STATIC_RWA_EXPLORE_ASSET_TYPE_PAGE
    explore_mp = STATIC_RWA_EXPLORE_MARKET_PARTICIPANT_PAGE

    rwa_onchain_payload = {
        "heading": "RWA Global Market Overview",
        "error": rwa_err,
        "kpis": [_rwa_kpi_to_dict(k) for k in rwa_kpis],
        "kpi_window_note": (
            "All % changes in this row are 30-day (30D) (RWA.xyz). "
            "Headline totals from the RWA.xyz Global Market Overview."
        ),
        "columns": rwa_columns,
        "rows": rwa_table_rows,
        "preview_count": len(rwa_table_rows),
        "total_networks": len(rwa_rows),
        "caption": (
            "Source: RWA.xyz homepage (https://app.rwa.xyz/)—the same Global Market Overview headline figures and "
            "Networks league (Distributed / parent networks) shown on the live site."
        ),
        "links": {
            # Static full overview (GitHub Pages has no ``/rwa/global`` route).
            "open_full_overview": "rwa-global.html",
            "see_networks_on_rwa_xyz": APP_RWA_NETWORKS_URL,
            "explore_asset_type": explore_at,
            "explore_market_participant": explore_mp,
        },
    }

    (OUT / "rwa_onchain_home.json").write_text(
        json.dumps(rwa_onchain_payload, indent=2),
        encoding="utf-8",
    )

    # --- Full static RWA Global Market Overview (mirrors Streamlit / FastAPI ``/rwa/global``) ---
    from home_layout import monthly_review_note_html, rwa_xyz_mirror_footer_text
    from rwa_league.widgets import (
        GLOBAL_MARKET_RWA_LINK_LABEL,
        GLOBAL_MARKET_RWA_URL,
        RWA_GLOBAL_MARKET_DATA_SOURCE_CAPTION_HTML,
        RWA_GMO_CHART_MAX_BARS,
        rwa_table_height,
    )

    try:
        from pages.RWA_Global_Market_Overview import RWA_GLOBAL_MARKET_MACRO_CONTEXT_HTML
    except Exception:
        RWA_GLOBAL_MARKET_MACRO_CONTEXT_HTML = ""

    macro_html = (RWA_GLOBAL_MARKET_MACRO_CONTEXT_HTML or "") + monthly_review_note_html()

    rwa_full_df = build_rwa_dataframe(list(rwa_rows)) if rwa_rows else pd.DataFrame()
    rwa_full_rows, rwa_full_cols = _dataframe_json_records(rwa_full_df)

    n_sync = min(RWA_GMO_CHART_MAX_BARS, len(rwa_rows)) if rwa_rows else 1
    chart_h = rwa_table_height(max(1, n_sync), max_h=560)

    chart_note_html = (
        f"The chart lists the top <strong>{RWA_GMO_CHART_MAX_BARS}</strong> networks "
        "by total value (labels include market share). Scroll the table for the full filtered list."
    )

    rwa_global_payload: dict[str, Any] = {
        "page_title": "RWA Global Market Overview — Digital Assets Dashboard",
        "page_subtitle_html": (
            "RWA <strong>Global Market Overview</strong>: the same <strong>headline metrics</strong> and "
            '<strong>Networks</strong> table as the <a href="https://app.rwa.xyz/">RWA.xyz</a> '
            "<strong>Market Overview</strong> tab on the live site. Top-line <strong>30D</strong> % changes and "
            "table values are read from that page so they stay in sync with what visitors see."
        ),
        "error": rwa_err,
        "kpis": [_rwa_kpi_to_dict(k) for k in rwa_kpis],
        "kpi_window_note": rwa_onchain_payload["kpi_window_note"],
        "columns": rwa_full_cols,
        "rows": rwa_full_rows,
        "total_networks": len(rwa_rows),
        "macro_observations_html": "",
        "explore_gateways_html": "",
        "caption_html": "",
        "chart_max_bars": RWA_GMO_CHART_MAX_BARS,
        "chart_height_px": int(chart_h),
        "chart_note_html": chart_note_html,
        "links": {
            "home": "index.html",
            "see_networks_on_rwa_xyz": APP_RWA_NETWORKS_URL,
            "global_market_on_rwa_xyz": GLOBAL_MARKET_RWA_URL,
            "global_market_link_label": GLOBAL_MARKET_RWA_LINK_LABEL,
            "explore_asset_type": explore_at,
            "explore_market_participant": explore_mp,
        },
        "footer_note": re.sub(r"\*\*", "", rwa_xyz_mirror_footer_text()),
    }

    if rwa_err and not rwa_rows:
        pass
    elif not rwa_rows:
        rwa_global_payload["empty_message"] = "No network rows returned."
    else:
        rwa_global_payload["macro_observations_html"] = macro_html
        rwa_global_payload["explore_gateways_html"] = _rwa_explore_gateways_static_html(explore_at, explore_mp)
        rwa_global_payload["caption_html"] = RWA_GLOBAL_MARKET_DATA_SOURCE_CAPTION_HTML

    (OUT / "rwa_global_market.json").write_text(
        json.dumps(rwa_global_payload, indent=2),
        encoding="utf-8",
    )

    from rwa_league.client import (
        fetch_rwa_asset_managers_page_data,
        fetch_rwa_networks_page_data,
        fetch_rwa_platforms_page_data,
        fetch_rwa_stablecoins_data,
        fetch_rwa_treasuries_data,
        fetch_rwa_tokenized_stocks_data,
    )

    try:
        sc_pack = fetch_rwa_stablecoins_data()
    except Exception as exc:
        manifest["errors"].append(f"RWA Stablecoins snapshot (Explore + asset pages): {exc}")
        sc_pack = ([], [], [], str(exc))

    try:
        tr_pack = fetch_rwa_treasuries_data()
    except Exception as exc:
        manifest["errors"].append(f"RWA US Treasuries snapshot (Explore + asset pages): {exc}")
        tr_pack = ([], [], [], str(exc))

    try:
        st_pack = fetch_rwa_tokenized_stocks_data()
    except Exception as exc:
        manifest["errors"].append(f"RWA Tokenized Stocks snapshot (Explore + asset pages): {exc}")
        st_pack = ([], [], [], str(exc))

    try:
        p_net_pack = fetch_rwa_networks_page_data()
    except Exception as exc:
        manifest["errors"].append(f"RWA Participants Networks snapshot: {exc}")
        p_net_pack = ([], [], str(exc))

    try:
        p_plat_pack = fetch_rwa_platforms_page_data()
    except Exception as exc:
        manifest["errors"].append(f"RWA Participants Platforms snapshot: {exc}")
        p_plat_pack = ([], [], str(exc))

    try:
        p_am_pack = fetch_rwa_asset_managers_page_data()
    except Exception as exc:
        manifest["errors"].append(f"RWA Participants Asset Managers snapshot: {exc}")
        p_am_pack = ([], [], str(exc))

    explore_at_payload = _build_rwa_explore_asset_type_payload(manifest, sc_pack, tr_pack, st_pack)
    (OUT / "rwa_explore_asset_type.json").write_text(
        json.dumps(explore_at_payload, indent=2),
        encoding="utf-8",
    )

    explore_mp_payload = _build_rwa_explore_market_participant_payload(manifest, p_net_pack, p_plat_pack, p_am_pack)
    (OUT / "rwa_explore_market_participant.json").write_text(
        json.dumps(explore_mp_payload, indent=2),
        encoding="utf-8",
    )

    (OUT / "rwa_participants_networks.json").write_text(
        json.dumps(_build_rwa_participants_networks_deep_payload(p_net_pack, manifest), indent=2),
        encoding="utf-8",
    )
    (OUT / "rwa_participants_platforms.json").write_text(
        json.dumps(_build_rwa_participants_platforms_deep_payload(p_plat_pack, manifest), indent=2),
        encoding="utf-8",
    )
    (OUT / "rwa_participants_asset_managers.json").write_text(
        json.dumps(_build_rwa_participants_asset_managers_deep_payload(p_am_pack, manifest), indent=2),
        encoding="utf-8",
    )

    (OUT / "rwa_stablecoins.json").write_text(
        json.dumps(_build_rwa_stablecoins_deep_payload(sc_pack, manifest), indent=2),
        encoding="utf-8",
    )
    (OUT / "rwa_us_treasuries.json").write_text(
        json.dumps(_build_rwa_us_treasuries_deep_payload(tr_pack, manifest), indent=2),
        encoding="utf-8",
    )
    (OUT / "rwa_tokenized_stocks.json").write_text(
        json.dumps(_build_rwa_tokenized_stocks_deep_payload(st_pack, manifest), indent=2),
        encoding="utf-8",
    )

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        f"Wrote static data to {OUT} ({len(rows_payload)} ETPs, {len(etf_items)} ETF headlines, "
        f"{len(rwa_rows)} RWA networks; crypto_ticker.json, rwa_global_market.json, rwa_explore_asset_type.json, "
        "rwa_explore_market_participant.json, rwa_participants_networks.json, rwa_participants_platforms.json, "
        "rwa_participants_asset_managers.json, rwa_stablecoins.json, rwa_us_treasuries.json, "
        "rwa_tokenized_stocks.json, rwa_onchain_home.json)."
    )


if __name__ == "__main__":
    main()
