"""
Build JSON payloads under static_home/data/ for the GitHub Pages mirror.

Run locally:  python scripts/export_static_site_data.py
  Crypto only (rewrites ``crypto_*.json`` with ``about_blurb`` on each row, ~1–3 min):  python scripts/export_static_site_data.py --crypto-only
  ETP only (``etps.json``, ``etp_kpis.json``, ``aum_series.json``; ~2–4 min):  python scripts/export_etp_static_data.py
Run in CI:    every 6 hours via ``.github/workflows/refresh-static-home-data.yml`` (full export + deploy).
  Ad-hoc git pushes only deploy committed ``static_home/`` (see ``deploy-static-home.yml``)—run export locally before committing JSON if you need fresh data on push.

Uses the same RSS / StockAnalysis / yfinance / RWA.xyz logic as the Streamlit app (no Streamlit UI), plus ``price_ticker.fetch_top_crypto_tickers`` for ``crypto_ticker.json`` (GitHub Pages marquee).

Optional env ``COINGECKO_DEMO_API_KEY`` (or ``COINGECKO_API_KEY``): sent as ``x-cg-demo-apikey`` for CoinGecko description calls so CI can fill ``about_blurb`` without hitting public rate limits as often. Optional ``COINGECKO_PRO_API_KEY`` uses the Pro API host. Descriptions are cached in ``static_home/data/crypto_about_blurbs_cache.json`` across exports so scheduled deploys can fill remaining coins without re-fetching every id. When the API still returns nothing, ``coingecko_about`` applies short static fallbacks for major assets (BTC, ETH, …) so the static crypto table always shows hint affordances for top names.

Optional env ``STATIC_WEBAPP_BASE``: absolute origin for FastAPI-only routes when needed. Served as HTML in ``static_home/``: Global overview ``rwa-global.html``, Explore by Asset Type ``rwa-explore-asset-type.html``, Explore by Market Participant ``rwa-explore-market-participant.html``, participant deep pages ``rwa-participants-*.html``, Stablecoins ``rwa-stablecoins.html``, US Treasuries ``rwa-us-treasuries.html``, Tokenized Stocks ``rwa-tokenized-stocks.html``, Tokenized MMF ``rwa-tokenized-mmf.html``.
"""

from __future__ import annotations

import json
import os
import re
import sys
from html import escape as html_escape
from typing import Any
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

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
from crypto_etps.flows import (
    aggregate_flow_for_symbols,
    aggregate_flow_mom_pct,
    format_flow_usd_compact,
    fund_flow_usd,
    load_farside_flow_series_with_source,
)
from news_feeds import (
    ALL_ARTICLES_FEEDS,
    DEFAULT_FEEDS,
    ETP_PULSE_PREVIEW_COUNT,
    dedupe_articles,
    load_all_etf_etp_news_cached,
    load_all_feeds,
)
from custodian_news.client import CUSTODIAN_LOOKBACK_DAYS, detect_article_access, load_custodian_articles
from regulatory_news.client import load_regulatory_articles

OUT = _REPO / "static_home" / "data"
HOME_NEWS_N = 4
REG_N = 3
# Static site only: [The Defiant](https://thedefiant.io/) RSS merged into market, all-articles, regulatory, and ETF pools.
STATIC_THE_DEFIANT_RSS = "https://thedefiant.io/feed/"
STATIC_THE_DEFIANT_FEED: tuple[str, str] = ("The Defiant", STATIC_THE_DEFIANT_RSS)
STATIC_THE_DEFIANT_REG_EXTRA: list[tuple[str, str, str, bool]] = [
    ("The Defiant", STATIC_THE_DEFIANT_RSS, "Global", False),
]
ALL_DIGITAL_NEWS_LOOKBACK_DAYS = 7
CUSTODIAN_ACCESS_FETCH_MAX = 25
HOME_RWA_PREVIEW_ROWS = 8
HOME_CRYPTO_PREVIEW_ROWS = 5
EXPLORE_ASSET_PREVIEW_ROWS = 8




STATIC_RWA_EXPLORE_ASSET_TYPE_PAGE = "rwa-explore-asset-type.html"
STATIC_RWA_EXPLORE_MARKET_PARTICIPANT_PAGE = "rwa-explore-market-participant.html"
STATIC_RWA_PARTICIPANTS_NETWORKS_PAGE = "rwa-participants-networks.html"
STATIC_RWA_PARTICIPANTS_PLATFORMS_PAGE = "rwa-participants-platforms.html"
STATIC_RWA_PARTICIPANTS_ASSET_MANAGERS_PAGE = "rwa-participants-asset-managers.html"
STATIC_RWA_STABLECOINS_PAGE = "rwa-stablecoins.html"
STATIC_RWA_US_TREASURIES_PAGE = "rwa-us-treasuries.html"
STATIC_RWA_TOKENIZED_STOCKS_PAGE = "rwa-tokenized-stocks.html"
STATIC_RWA_TOKENIZED_MMF_PAGE = "rwa-tokenized-mmf.html"
STATIC_HOME_STABLECOINS_SECTION = "index.html"
STATIC_HOME_TMMF_SECTION = "index.html"
APP_RWA_NETWORKS_URL = "https://app.rwa.xyz/networks"
COINPAPRIKA_GLOBAL_URL = "https://api.coinpaprika.com/v1/global"
COINPAPRIKA_MARKET_OVERVIEW_TOTAL_30D_URL = "https://coinpaprika.com/market-overview/data/total/30d/"

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
    out = {
        "title": a.get("title") or "",
        "link": a.get("link") or "",
        "source": a.get("source") or "",
        "published": _serialize_dt(pub) if isinstance(pub, datetime) else None,
        "summary": (a.get("summary") or "")[:500],
        "country": a.get("country") or "",
    }
    access = a.get("access")
    if access:
        out["access"] = str(access)
    category = a.get("category")
    if category:
        out["category"] = str(category)
    return out


def enrich_custodian_access(articles: list[dict[str, Any]]) -> None:
    """Best-effort HTML paywall check for items still marked ``unknown`` (bounded)."""
    n = 0
    for a in articles:
        if n >= CUSTODIAN_ACCESS_FETCH_MAX:
            break
        if (a.get("access") or "unknown") != "unknown":
            continue
        link = (a.get("link") or "").strip()
        if not link:
            continue
        a["access"] = detect_article_access(link, rss_summary=a.get("summary") or "")
        n += 1


def _headline_norm_key(title: str) -> str:
    t = (title or "").lower()
    t = re.sub(r"[^\w\s]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:280]


def dedupe_repetitive_headlines(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """After URL/title dedupe: drop later rows whose normalized title repeats (syndicated near-duplicates)."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for a in articles:
        raw_title = str(a.get("title") or "")
        k = _headline_norm_key(raw_title)
        if not k:
            k = f"link:{(a.get('link') or '').strip()}"
        if k in seen:
            continue
        seen.add(k)
        out.append(a)
    return out


def articles_published_within_utc_days(articles: list[dict[str, Any]], days: int) -> list[dict[str, Any]]:
    """Keep only items with ``published`` in the last ``days`` full UTC-relative window (rolling)."""
    if days < 1:
        return []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    out: list[dict[str, Any]] = []
    for a in articles:
        pub = a.get("published")
        if isinstance(pub, datetime) and pub.astimezone(timezone.utc) >= cutoff:
            out.append(a)
    return out


def _etp_row_json(
    r: CryptoEtpRow,
    *,
    flow_1y_usd: float | None = None,
    flow_1y_window: str = "",
) -> dict:
    inc = (r.inception or "").strip()
    filing = (r.fund_filing_url or "").strip()
    assets = float(r.assets_usd) if has_listed_aum_usd(r.assets_usd) else None
    return {
        "symbol": r.symbol,
        "name": r.name,
        "price": r.price,
        "pct_52w": r.pct_52w,
        "assets_usd": assets,
        "flow_1y_usd": round(float(flow_1y_usd), 2) if flow_1y_usd is not None else None,
        "flow_1y_window": (flow_1y_window or "").strip(),
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
    """Compact Explore nav for static pages (matches home ``home-explore-compact``)."""
    ae = html_escape(at_href, quote=True)
    pe = html_escape(mp_href, quote=True)
    return (
        '<nav class="home-explore-compact" aria-label="Explore RWA">'
        '<span class="home-explore-compact__label">Explore</span>'
        f'<a class="home-explore-compact__btn" href="{ae}">By asset type</a>'
        f'<a class="home-explore-compact__btn" href="{pe}">By participant</a>'
        "</nav>"
    )


PARTICIPANT_KPI_MAX = 5
KPI_LABEL_STABLECOIN_HOLDERS = "Total Stablecoin Holders"


def _rwa_kpi_to_dict(k: object) -> dict[str, object]:
    delta = getattr(k, "delta_30d_pct", None)
    return {
        "label": str(getattr(k, "label", "")),
        "value_display": str(getattr(k, "value_display", "")),
        "delta_30d_pct": float(delta) if delta is not None else None,
    }


def _participant_kpis_for_export(
    kpis: list[Any],
    *,
    drop_stablecoin_holders: bool = False,
) -> list[dict[str, object]]:
    """At most five participant headline KPIs; optionally drop stablecoin holders on Networks/Platforms."""
    out: list[dict[str, object]] = []
    for k in kpis:
        row = _rwa_kpi_to_dict(k)
        if drop_stablecoin_holders and row.get("label") == KPI_LABEL_STABLECOIN_HOLDERS:
            continue
        out.append(row)
        if len(out) >= PARTICIPANT_KPI_MAX:
            break
    return out


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


def _static_rwa_footer_text() -> str:
    return f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · Source: RWA.xyz"


def _kpi_legend_for_asset(overview_title: str) -> str:
    return (
        "All % changes in this row are 30-day (30D) (RWA.xyz). "
        f"Headline totals from the RWA.xyz {overview_title} Overview."
    )


CRYPTO_KPI_WINDOW_NOTE = (
    "All % changes in this row are approximately one-month (~30 calendar days). "
    "Total market cap from CoinPaprika; BTC dominance and stablecoin share from the top-50 list "
    "(CoinGecko, CoinCap fallback)."
)

ETP_KPI_WINDOW_NOTE = (
    "All % changes in this row are typically one-month (~30 calendar days); "
    "IBIT and ETHA may use one-year figures when one-month Yahoo data is unavailable. "
    "Aggregate AUM % uses estimated weekly series. "
    "Fund-flow % compares 30-day Farside spot BTC/ETH ETF totals vs the prior 30 days. "
    "Dollar totals from StockAnalysis."
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


def _build_rwa_stablecoins_deep_payload(
    sc_pack: tuple[Any, Any, Any, Any],
    manifest: dict[str, Any],
    articles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
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
            "back_href": STATIC_HOME_STABLECOINS_SECTION,
            "footer_note": _static_rwa_footer_text(),
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
        from key_observations.page_ko import build_legacy_page_ko

        ko_html = build_legacy_page_ko("stablecoins", articles)
    except Exception as exc:  # pragma: no cover - export-only
        manifest["errors"].append(f"Stablecoins takeaway HTML export: {exc}")
        ko_html = ""

    b = _seed()
    b["error_mode"] = ""
    b["key_observations_html"] = ko_html
    b["between_ko_and_leagues_html"] = ""
    b["funds_table"] = None
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


def _build_rwa_us_treasuries_deep_payload(
    tr_pack: tuple[Any, Any, Any, Any],
    manifest: dict[str, Any],
    articles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
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
                f'U.S. Treasuries data from <a href="{html_escape(APP_TREASURIES, quote=True)}">'
                "RWA.xyz US Treasuries</a>, with Distributed Networks and Platforms views."
            ),
            "kpi_window_note": _kpi_legend_for_asset("US Treasuries"),
            "kpis": [_rwa_kpi_to_dict(k) for k in kpis],
            "chart_max_bars": RWA_TREASURIES_CHART_MAX_BARS,
            "back_href": STATIC_RWA_EXPLORE_ASSET_TYPE_PAGE,
            "footer_note": _static_rwa_footer_text(),
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
        from key_observations.page_ko import build_legacy_page_ko

        ko_html = build_legacy_page_ko("us_treasuries", articles)
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


def _build_rwa_tokenized_stocks_deep_payload(
    st_pack: tuple[Any, Any, Any, Any],
    manifest: dict[str, Any],
    articles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
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
                f'Tokenized stock data from <a href="{html_escape(APP_STOCKS, quote=True)}">RWA.xyz Tokenized Stocks</a>,'
                " with Networks and Platforms views."
            ),
            "kpi_window_note": _kpi_legend_for_asset("Tokenized Stocks"),
            "kpis": [_rwa_kpi_to_dict(k) for k in kpis],
            "chart_max_bars": RWA_TOKENIZED_STOCKS_CHART_MAX_BARS,
            "back_href": STATIC_RWA_EXPLORE_ASSET_TYPE_PAGE,
            "footer_note": _static_rwa_footer_text(),
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
        from key_observations.page_ko import build_legacy_page_ko

        ko_html = build_legacy_page_ko("tokenized_stocks", articles)
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


def _kpi_legend_for_mmf() -> str:
    return (
        "Distributed value uses a 30-day (30D) % change vs summed token values 30 days ago. "
        "Top network share is the largest network by distributed value; the 30D figure is the change in "
        "market-share percentage points (pp), not a percent of total. "
        "Fund universe: fixed curated TMMF population on RWA.xyz US Treasuries and Non-U.S. Government Debt; "
        "KPIs, charts, and league tables use the same fund set."
    )


def _build_rwa_tokenized_mmf_deep_payload(
    mmf_pack: tuple[Any, Any, Any, Any],
    manifest: dict[str, Any],
    articles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from rwa_league.client import APP_GOVERNMENT_BONDS, APP_TREASURIES
    from rwa_league.mmf import (
        TMMF_INNER_PAGE_SUBTITLE_HTML,
        asset_distributed_value_usd,
        build_curated_mmf_dashboard_data,
    )
    from rwa_league.dataframe_table import (
        build_us_treasury_network_dataframe,
        build_us_treasury_platform_dataframe,
    )
    from rwa_league.widgets import (
        MMF_NETWORK_CAPTION,
        MMF_PLATFORM_CAPTION,
        MMF_RWA_LINK_LABEL,
        RWA_MMF_CHART_MAX_BARS,
    )

    fund_assets, rows_net, rows_plat, kpis, collect_err = build_curated_mmf_dashboard_data()
    err_any = collect_err or mmf_pack[3]
    if not fund_assets and mmf_pack[0]:
        rows_net = list(mmf_pack[0])
        rows_plat = list(mmf_pack[1])
        kpis = list(mmf_pack[2])
    err_s = "" if err_any is None else str(err_any)
    export_ts = datetime.now(timezone.utc).isoformat()

    sources = (
        f'<a href="{html_escape(APP_TREASURIES, quote=True)}">RWA.xyz US Treasuries</a> and '
        f'<a href="{html_escape(APP_GOVERNMENT_BONDS, quote=True)}">Non-U.S. Government Debt</a>'
    )

    def _seed() -> dict[str, Any]:
        return {
            "generated_at": export_ts,
            "page_title": "Tokenized Money Market Funds — Digital Assets Dashboard",
            "band_label": "Tokenized Money Market Funds",
            "page_subtitle_html": TMMF_INNER_PAGE_SUBTITLE_HTML,
            "kpi_window_note": _kpi_legend_for_mmf(),
            "kpis": [_rwa_kpi_to_dict(k) for k in kpis],
            "chart_max_bars": RWA_MMF_CHART_MAX_BARS,
            "back_href": STATIC_HOME_TMMF_SECTION,
            "footer_note": _static_rwa_footer_text(),
            "bottom_cta": {"href": APP_TREASURIES, "label": MMF_RWA_LINK_LABEL},
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
        b["empty_message"] = "No tokenized money market fund rows returned."
        b["key_observations_html"] = ""
        b["networks"] = None
        b["platforms"] = None
        return b

    ko_html = ""

    b = _seed()
    b["error_mode"] = ""
    b["key_observations_html"] = ko_html
    b["between_ko_and_leagues_html"] = ""

    def _safe_text(v: Any) -> str:
        s = str(v or "").strip()
        return html_escape(s) if s else "—"

    def _network_logo_stack(asset: dict[str, Any]) -> str:
        seen: set[str] = set()
        chips: list[str] = []
        labels: list[str] = []
        for tok in asset.get("tokens") or []:
            if not isinstance(tok, dict):
                continue
            n = tok.get("network") or {}
            if not isinstance(n, dict):
                continue
            slug = str(n.get("slug") or n.get("name") or "").strip()
            if not slug or slug in seen:
                continue
            seen.add(slug)
            n_name = str(n.get("name") or slug).strip() or "—"
            labels.append(n_name)
            icon = str(n.get("icon_url") or "").strip()
            if icon:
                chips.append(
                    '<img class="tmmf-net-avatar" src="'
                    + html_escape(icon, quote=True)
                    + '" alt="'
                    + html_escape(n_name, quote=True)
                    + '" title="'
                    + html_escape(n_name, quote=True)
                    + '" loading="lazy" />'
                )
            else:
                chips.append(
                    '<span class="tmmf-net-avatar tmmf-net-avatar--text" title="'
                    + html_escape(n_name, quote=True)
                    + '">'
                    + html_escape(n_name[:1].upper())
                    + "</span>"
                )
        if not chips:
            return "—"
        return (
            '<div class="tmmf-net-stack" aria-label="'
            + html_escape(", ".join(labels), quote=True)
            + '">'
            + "".join(chips)
            + "</div>"
        )

    def _term_link(asset: dict[str, Any]) -> str:
        for key, label in (
            ("legal_structure__document_url", "Legal document"),
            ("transparency_url", "Terms / transparency"),
            ("website", "Website"),
        ):
            href = str(asset.get(key) or "").strip()
            if href:
                return (
                    '<a href="'
                    + html_escape(href, quote=True)
                    + '" target="_blank" rel="noopener noreferrer">'
                    + html_escape(label)
                    + "</a>"
                )
        return "—"

    def _platform_info(asset: dict[str, Any]) -> tuple[str, str]:
        by_slug: dict[str, dict[str, Any]] = {}
        for tok in asset.get("tokens") or []:
            if not isinstance(tok, dict):
                continue
            p = tok.get("platform") or {}
            if not isinstance(p, dict):
                continue
            slug = str(p.get("slug") or "").strip()
            name = str(p.get("name") or tok.get("platform_name") or "").strip()
            if not slug and not name:
                continue
            key = slug or name.lower().replace(" ", "-")
            if key not in by_slug:
                by_slug[key] = {"slug": slug, "name": name or "—", "value": 0.0}
            b = tok.get("bridged_token_value_dollar") or {}
            v = float(b.get("val")) if isinstance(b, dict) and isinstance(b.get("val"), (int, float)) else 0.0
            by_slug[key]["value"] = float(by_slug[key]["value"]) + float(v)
        if not by_slug:
            fallback = str(asset.get("issuer_name") or "—").strip() or "—"
            return fallback, ""
        best = max(by_slug.values(), key=lambda x: float(x.get("value", 0.0)))
        name = str(best.get("name") or "—").strip() or "—"
        slug = str(best.get("slug") or "").strip()
        href = f"https://app.rwa.xyz/platforms/{slug}" if slug else ""
        return name, href

    fund_err = collect_err
    if fund_err:
        manifest["errors"].append(f"Tokenized MMF funds table export: {fund_err}")
    if fund_assets:
        try:
            from rwa_league.mmf_takeaways import build_mmf_key_observations_html

            b["key_observations_html"] = build_mmf_key_observations_html(
                fund_assets, list(rows_net), articles
            )
        except Exception as exc:
            manifest["errors"].append(f"Tokenized MMF takeaway HTML export: {exc}")
        fund_rows: list[dict[str, Any]] = []
        for asset in fund_assets:
            name_raw = str(asset.get("name") or "").strip() or "—"
            slug_raw = str(asset.get("slug") or "").strip()
            ticker = str(asset.get("ticker") or "").strip() or "—"
            platform, platform_href = _platform_info(asset)
            total_value_num = asset_distributed_value_usd(asset)
            investors_raw = asset.get("primary_market__investor_types")
            investors = (
                ", ".join(str(x).strip() for x in investors_raw if str(x).strip())
                if isinstance(investors_raw, list)
                else str(investors_raw or "").strip()
            )
            holders_raw = asset.get("holding_addresses_count") or {}
            holders = holders_raw.get("val") if isinstance(holders_raw, dict) else None
            val_obj = asset.get("bridged_token_value_dollar") or {}
            pct7 = val_obj.get("chg_7d_pct") if isinstance(val_obj, dict) else None
            domicile = _safe_text(
                asset.get("jurisdiction_country_name")
                or asset.get("legal_structure__country_name")
                or asset.get("dispute_resolution_country_name")
            )
            reg_fw = _safe_text(asset.get("regulatory_framework"))
            cust = asset.get("traditional_custodian") or asset.get("crypto_custodian") or {}
            cust_name = cust.get("name") if isinstance(cust, dict) else None
            custodian = _safe_text(cust_name)
            fund_rows.append(
                {
                    "Fund Name": name_raw,
                    "Link": f"https://app.rwa.xyz/assets/{slug_raw}" if slug_raw else "https://app.rwa.xyz/treasuries",
                    "Fund Link": f"https://app.rwa.xyz/assets/{slug_raw}" if slug_raw else "https://app.rwa.xyz/treasuries",
                    "Ticker": ticker,
                    "Platform": platform,
                    "Platform Link": platform_href,
                    "Networks": _network_logo_stack(asset),
                    "Total Value": float(total_value_num),
                    "7D Δ value": float(pct7) if isinstance(pct7, (int, float)) else None,
                    "Eligible Investors": str(investors or "—"),
                    "Holders": int(holders) if isinstance(holders, (int, float)) else None,
                    "Domicile": str(domicile or "—"),
                    "Regulatory Framework": str(reg_fw or "—"),
                    "Custodian": str(custodian or "—"),
                    "Terms": _term_link(asset),
                }
            )

        fund_rows.sort(key=lambda r: -(float(r.get("Total Value") or 0)))
        for i, row in enumerate(fund_rows, 1):
            row["#"] = i

        b["between_ko_and_leagues_html"] = (
            '<section class="hub-section tmmf-funds-list" id="tmmf-funds-wrap" aria-labelledby="tmmf-funds-h">'
            '<h2 class="subsection-head" id="tmmf-funds-h">Tokenized Money Market Fund Population</h2>'
            '<p class="rwa-deep-section-intro">Curated fund population (fixed list aligned to RWA.xyz). '
            "Population may not include all TMMFs in the market."
            "</p>"
            "</section>"
        )
        b["funds_table"] = {
            "columns": [
                "#",
                "Fund Name",
                "Ticker",
                "Platform",
                "Networks",
                "Total Value",
                "7D Δ value",
                "Eligible Investors",
                "Holders",
                "Domicile",
                "Regulatory Framework",
                "Custodian",
                "Terms",
            ],
            "rows_full": fund_rows,
            "name_column": "Fund Name",
            "search_label": "Search funds table",
            "search_placeholder": "Filter by fund name, ticker, platform, network, domicile…",
            "filter_note_suffix_all": "funds.",
            "filter_note_entity_plural": "funds",
        }

    b["networks"] = _league_split_payload(
        rows_net,
        build_df=build_us_treasury_network_dataframe,
        block_heading="By network (Tokenized MMFs)",
        table_heading="Networks table",
        chart_heading="Top networks by value",
        name_column="Network",
        value_column="Distributed Value",
        chart_max_bars=RWA_MMF_CHART_MAX_BARS,
        caption_md=MMF_NETWORK_CAPTION,
        search_entity="network",
        section_intro_md=(
            "**Networks** — aggregate distributed value of the **curated TMMF population** by chain, "
            "summed from each fund's token deployments."
        ),
        filter_note_suffix_all="networks (Tokenized MMFs).",
        filter_note_entity_plural="networks",
    )
    b["platforms"] = _league_split_payload(
        rows_plat,
        build_df=build_us_treasury_platform_dataframe,
        block_heading="By platform (Tokenized MMFs · Asset managers)",
        table_heading="Platforms table",
        chart_heading="Top platforms by value",
        name_column="Platform",
        value_column="Total Value",
        chart_max_bars=RWA_MMF_CHART_MAX_BARS,
        caption_md=MMF_PLATFORM_CAPTION,
        search_entity="platform",
        section_intro_md=(
            "**Platforms** — issuer / asset-manager aggregates for the **same curated TMMF population** "
            "(same measures as Networks)."
        ),
        filter_note_suffix_all="platforms (Tokenized MMFs).",
        filter_note_entity_plural="platforms",
    )
    return b


def _build_rwa_participants_networks_deep_payload(
    pack: tuple[list[Any], list[Any], Any],
    manifest: dict[str, Any],
    articles: list[dict[str, Any]] | None = None,
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
                f'Network data from <a href="{html_escape(APP_NETWORKS, quote=True)}">RWA.xyz Networks</a>, '
                "focused on the Distributed Networks league."
            ),
            "kpi_window_note": _kpi_legend_for_asset("Networks"),
            "kpis": _participant_kpis_for_export(kpis, drop_stablecoin_holders=True),
            "chart_max_bars": RWA_PARTICIPANTS_CHART_MAX_BARS,
            "back_href": STATIC_RWA_EXPLORE_MARKET_PARTICIPANT_PAGE,
            "footer_note": _static_rwa_footer_text(),
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
        from key_observations.page_ko import build_legacy_page_ko

        ko_html = build_legacy_page_ko("participants_networks", articles)
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
    articles: list[dict[str, Any]] | None = None,
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
                f'Platform data from <a href="{html_escape(APP_PLATFORMS, quote=True)}">RWA.xyz Platforms</a>, '
                "focused on the Distributed Platforms league."
            ),
            "kpi_window_note": _kpi_legend_for_asset("Platforms"),
            "kpis": _participant_kpis_for_export(kpis, drop_stablecoin_holders=True),
            "chart_max_bars": RWA_PARTICIPANTS_CHART_MAX_BARS,
            "back_href": STATIC_RWA_EXPLORE_MARKET_PARTICIPANT_PAGE,
            "footer_note": _static_rwa_footer_text(),
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
        from key_observations.page_ko import build_legacy_page_ko

        ko_html = build_legacy_page_ko("participants_platforms", articles)
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
    articles: list[dict[str, Any]] | None = None,
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
                f'Asset-manager data from <a href="{html_escape(APP_ASSET_MANAGERS, quote=True)}">RWA.xyz Asset Managers</a>.'
            ),
            "kpi_window_note": _kpi_legend_for_asset("Asset Managers"),
            "kpis": _participant_kpis_for_export(kpis),
            "chart_max_bars": RWA_PARTICIPANTS_CHART_MAX_BARS,
            "back_href": STATIC_RWA_EXPLORE_MARKET_PARTICIPANT_PAGE,
            "footer_note": _static_rwa_footer_text(),
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
        from key_observations.page_ko import build_legacy_page_ko

        ko_html = build_legacy_page_ko("participants_asset_managers", articles)
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
        return {"pct": round(float(row.pct_52w), 4), "window": "1Y"}
    return {"pct": None, "window": ""}


def _fmt_crypto_price(v: object) -> str:
    try:
        price = float(v)
    except (TypeError, ValueError):
        return "—"
    if price >= 1000:
        return f"${price:,.0f}"
    if price >= 1:
        return f"${price:,.2f}"
    if price >= 0.01:
        return f"${price:,.4f}"
    return f"${price:.6g}"


def _find_crypto_row(rows: list[dict[str, object]], symbol: str) -> dict[str, object] | None:
    target = symbol.strip().upper()
    for row in rows:
        if str(row.get("symbol", "")).strip().upper() == target:
            return row
    return None


def _crypto_row_json(r: dict[str, object], fallback_rank: int) -> dict[str, object]:
    from crypto_categories import category_label, crypto_category

    rank = r.get("market_cap_rank")
    try:
        rank_num = int(rank) if rank is not None else fallback_rank
    except (TypeError, ValueError):
        rank_num = fallback_rank
    price = r.get("price_usd")
    market_cap = r.get("market_cap_usd")
    pct_30d = r.get("pct_30d")
    sym = str(r.get("symbol") or "")
    name = str(r.get("name") or "")
    cat = crypto_category(sym, name)
    return {
        "rank": rank_num,
        "symbol": sym,
        "name": name,
        "category": cat,
        "category_label": category_label(cat),
        "price_usd": float(price) if price is not None else None,
        "pct_30d": float(pct_30d) if pct_30d is not None else None,
        "market_cap_usd": float(market_cap) if market_cap is not None else None,
        "detail_url": str(r.get("detail_url") or ""),
        "about_blurb": str(r.get("about_blurb") or ""),
    }


def _crypto_delta_dict(pct: object, window: str = "24H") -> dict[str, object]:
    try:
        num = float(pct) if pct is not None else None
    except (TypeError, ValueError):
        num = None
    return {"pct": round(num, 4) if num is not None else None, "window": window}


def _fetch_coinpaprika_total_snapshot(headers: dict[str, str]) -> tuple[dict[str, float], str | None]:
    out: dict[str, float] = {}
    errs: list[str] = []

    try:
        resp = requests.get(COINPAPRIKA_GLOBAL_URL, headers=headers, timeout=25)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, dict):
            errs.append("Unexpected CoinPaprika global payload.")
        else:
            market_cap_usd = payload.get("market_cap_usd")
            try:
                if market_cap_usd is not None:
                    out["total_market_cap_usd"] = float(market_cap_usd)
            except (TypeError, ValueError):
                errs.append("CoinPaprika global market cap was not numeric.")
    except (requests.RequestException, ValueError, TypeError) as exc:
        errs.append(f"CoinPaprika global: {type(exc).__name__}: {exc}")

    try:
        resp = requests.get(COINPAPRIKA_MARKET_OVERVIEW_TOTAL_30D_URL, headers=headers, timeout=25)
        resp.raise_for_status()
        payload = resp.json()
        series = None
        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict):
                series = first.get("usd")
        elif isinstance(payload, dict):
            series = payload.get("usd")

        values: list[float] = []
        if isinstance(series, list):
            for point in series:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    try:
                        val = float(point[1])
                    except (TypeError, ValueError):
                        continue
                    values.append(val)

        if len(values) >= 2:
            first_val = values[0]
            last_val = values[-1]
            out["total_market_cap_usd_30d_ago"] = first_val
            if "total_market_cap_usd" not in out:
                out["total_market_cap_usd"] = last_val
            if first_val > 0:
                out["market_cap_change_pct_1m"] = ((last_val - first_val) / first_val) * 100.0
        else:
            errs.append("CoinPaprika 30d market-cap series was not found.")
    except (requests.RequestException, ValueError, TypeError) as exc:
        errs.append(f"CoinPaprika market overview: {type(exc).__name__}: {exc}")

    return out, "; ".join(errs) if errs else None


def _build_crypto_kpis_from_rows(
    t_rows: list[dict[str, object]],
    *,
    coinpaprika_total: dict[str, float],
    coinpaprika_err: str | None,
    t_src: str,
    t_err: str,
    crypto_generated_at: str,
    news_articles: list[dict[str, Any]] | None,
) -> dict[str, object]:
    from crypto_categories import (
        btc_dominance_change_pct_1m,
        compute_market_structure,
        stablecoin_share_change_pct_1m,
        story_callout_payload,
        structure_kpi_dicts,
    )
    from crypto_top_movers import crypto_key_takeaways_html, top_movers_callout_payload

    total_market_cap_usd = coinpaprika_total.get("total_market_cap_usd")
    total_market_cap_usd_30d_ago = coinpaprika_total.get("total_market_cap_usd_30d_ago")
    total_market_cap_pct_1m = coinpaprika_total.get("market_cap_change_pct_1m")
    primary_label = "Total market cap"
    primary_value = format_usd_compact(total_market_cap_usd) if total_market_cap_usd else "—"

    btc_row = _find_crypto_row(t_rows, "BTC")
    eth_row = _find_crypto_row(t_rows, "ETH")
    structure = compute_market_structure(t_rows, total_market_cap_usd=total_market_cap_usd)
    dom_delta = btc_dominance_change_pct_1m(
        t_rows,
        total_market_cap_now=total_market_cap_usd,
        total_market_cap_then=total_market_cap_usd_30d_ago,
    )
    st_delta = stablecoin_share_change_pct_1m(t_rows)
    btc_dom_kpi, stable_kpi = structure_kpi_dicts(
        structure,
        btc_dom_delta_pct_1m=dom_delta,
        stable_share_delta_pct_1m=st_delta,
    )
    crypto_kpis_payload: dict[str, object] = {
        "generated_at": crypto_generated_at,
        "source": "CoinPaprika + CoinGecko" if (total_market_cap_usd or total_market_cap_pct_1m is not None) else (t_src or ""),
        "error": t_err or "",
        "primary": {
            "label": primary_label,
            "value_display": primary_value,
            "delta": _crypto_delta_dict(total_market_cap_pct_1m, "1M"),
        },
        "btc": {
            "label": "BTC price",
            "value_display": _fmt_crypto_price(btc_row.get("price_usd")) if btc_row else "—",
            "delta": _crypto_delta_dict(btc_row.get("pct_30d") if btc_row else None, "1M"),
        },
        "eth": {
            "label": "ETH price",
            "value_display": _fmt_crypto_price(eth_row.get("price_usd")) if eth_row else "—",
            "delta": _crypto_delta_dict(eth_row.get("pct_30d") if eth_row else None, "1M"),
        },
        "btc_dominance": btc_dom_kpi,
        "stablecoin_share": stable_kpi,
        "market_structure": structure,
        "kpi_window_note": CRYPTO_KPI_WINDOW_NOTE,
        "story_callout": story_callout_payload(),
        "top_movers": top_movers_callout_payload(t_rows, news_articles),
        "source_note": (
            "Total market cap and its 1M change come from CoinPaprika global market data and 30-day market-overview history. "
            "BTC dominance uses Bitcoin’s market cap vs that CoinPaprika total; its 1M % approximates how that ratio moved using the same total-cap window and BTC’s 30d change from this list. "
            "Stablecoin share is stablecoin market cap vs the sum of this top-50 list; its 1M % uses row-level 30d cap changes (approximate). "
            "Coin price changes use CoinGecko spot data with CoinCap fallback for rows that do not include a 30-day change."
            if total_market_cap_usd is not None and total_market_cap_pct_1m is not None
            else (
                "Total market cap comes from CoinPaprika global market data. The 1M total-market-cap change is unavailable right now. "
                "BTC dominance and stablecoin share are computed from the top-50 table when cap data is available. "
                "Coin price changes use CoinGecko spot data with CoinCap fallback for rows that do not include a 30-day change."
                if total_market_cap_usd is not None
                else "Total crypto market-cap data is unavailable right now. Coin price changes use CoinGecko spot data with CoinCap fallback for rows that do not include a 30-day change."
            )
        ),
    }
    if coinpaprika_err and total_market_cap_usd is None and total_market_cap_pct_1m is None:
        crypto_kpis_payload["error"] = coinpaprika_err
    try:
        crypto_kpis_payload["key_observations_html"] = crypto_key_takeaways_html(
            t_rows,
            crypto_kpis_payload,
            news_articles,
        )
    except Exception:
        crypto_kpis_payload["key_observations_html"] = ""
    return crypto_kpis_payload


def build_crypto_prices_page_payloads(
    *,
    news_articles: list[dict[str, Any]] | None = None,
    blurb_cache_path: Path | None = None,
    manifest_errors: list[str] | None = None,
    skip_about_blurbs: bool = False,
    live_cache_path: Path | None = None,
) -> dict[str, Any]:
    """Build crypto page JSON payloads (kpis, prices, chart, ticker)."""
    errors = manifest_errors if manifest_errors is not None else []
    crypto_generated_at = datetime.now(timezone.utc).isoformat()
    crypto_prices_payload: dict[str, object] = {
        "generated_at": crypto_generated_at,
        "source": "",
        "error": "",
        "rows": [],
    }
    crypto_kpis_payload: dict[str, object] = {
        "generated_at": crypto_generated_at,
        "source": "",
        "error": "",
        "primary": {"label": "Total market cap", "value_display": "—", "delta": {"pct": None, "window": ""}},
        "btc": {"label": "BTC price", "value_display": "—", "delta": {"pct": None, "window": "1M"}},
        "eth": {"label": "ETH price", "value_display": "—", "delta": {"pct": None, "window": "1M"}},
        "source_note": "Crypto market data is unavailable right now.",
    }
    crypto_chart_payload: dict[str, object] = {
        "generated_at": crypto_generated_at,
        "source": "TradingView TOTAL",
        "error": "",
        "title": "Crypto total market cap",
        "provider_url": "https://www.tradingview.com/symbols/TOTAL/",
        "symbol": "CRYPTOCAP:TOTAL",
        "caption": "TradingView TOTAL represents crypto market capitalization using the top 125 coins.",
        "method_note": "The interactive market-cap chart is rendered client-side from TradingView so the export does not depend on rate-limited historical API calls.",
        "supported_timeframes": ["1M", "6M", "1Y", "5Y"],
    }
    crypto_banner_title = "Top 50 Cryptocurrencies"
    coinpaprika_total: dict[str, float] = {}
    coinpaprika_err: str | None = None
    t_src = ""
    t_err = ""
    t_rows: list[dict[str, object]] = []
    crypto_payload: dict[str, object] = {
        "banner_title": crypto_banner_title,
        "chips_inner_html": "",
        "source": "",
        "error": "",
        "generated_at": crypto_generated_at,
    }
    try:
        from price_ticker import PRICE_TICKER_BANNER_TITLE, TICKER_COUNT, fetch_top_crypto_tickers, hub_ticker_static_json_payload

        crypto_banner_title = PRICE_TICKER_BANNER_TITLE

        t_rows, t_err, t_src = fetch_top_crypto_tickers(TICKER_COUNT)
        t_rows = [dict(r) for r in t_rows]
        from coingecko_about import (
            attach_about_blurbs_to_rows,
            collect_coingecko_ids_for_rows,
            default_coingecko_headers,
            fetch_blurbs_with_cache,
        )

        crypto_headers = default_coingecko_headers()
        crypto_headers["User-Agent"] = DEFAULT_UA

        blurb_cache_path = blurb_cache_path or (OUT / "crypto_about_blurbs_cache.json")
        if not skip_about_blurbs:
            _blurbs_ids = collect_coingecko_ids_for_rows(t_rows)
            _blurbs_map = (
                fetch_blurbs_with_cache(_blurbs_ids, blurb_cache_path, headers=crypto_headers)
                if _blurbs_ids
                else {}
            )
            attach_about_blurbs_to_rows(
                t_rows,
                headers=crypto_headers,
                prefetched=_blurbs_map,
                refetch_missing=False,
            )

        crypto_payload = hub_ticker_static_json_payload(t_rows, t_err, t_src)
        crypto_payload["generated_at"] = crypto_generated_at

        coinpaprika_total, coinpaprika_err = _fetch_coinpaprika_total_snapshot(crypto_headers)

        crypto_rows_payload = [_crypto_row_json(r, i + 1) for i, r in enumerate(t_rows)]
        crypto_prices_payload = {
            "generated_at": crypto_generated_at,
            "source": t_src or "",
            "error": t_err or "",
            "rows": crypto_rows_payload,
        }

        crypto_kpis_payload = _build_crypto_kpis_from_rows(
            t_rows,
            coinpaprika_total=coinpaprika_total,
            coinpaprika_err=coinpaprika_err,
            t_src=t_src or "",
            t_err=t_err or "",
            crypto_generated_at=crypto_generated_at,
            news_articles=news_articles,
        )

        crypto_chart_payload["generated_at"] = crypto_generated_at
    except Exception as exc:
        errors.append(f"Crypto export: {exc}")
        crypto_payload = {
            "banner_title": crypto_banner_title,
            "chips_inner_html": f'<span class="ticker-chip ticker-chip--error">{html_escape(str(exc))}</span>',
            "source": "",
            "error": str(exc),
            "generated_at": crypto_generated_at,
        }
        crypto_prices_payload["error"] = str(exc)
        crypto_kpis_payload["error"] = str(exc)
        crypto_chart_payload["error"] = str(exc)

    from crypto_live_cache import (
        apply_crypto_live_cache_fallback,
        load_crypto_live_cache,
        save_crypto_live_cache,
    )

    cache_path = live_cache_path or (OUT / "crypto_live_cache.json")
    cached = load_crypto_live_cache(cache_path, static_dir=OUT)

    def _rebuild_kpis(
        rows: list[dict[str, object]],
        paprika: dict[str, float],
        prices_error: str,
    ) -> dict[str, object]:
        return _build_crypto_kpis_from_rows(
            rows,
            coinpaprika_total=paprika,
            coinpaprika_err=coinpaprika_err,
            t_src=t_src or "",
            t_err=prices_error,
            crypto_generated_at=crypto_generated_at,
            news_articles=news_articles,
        )

    pack = {
        "generated_at": crypto_generated_at,
        "kpis": crypto_kpis_payload,
        "prices": crypto_prices_payload,
        "chart": crypto_chart_payload,
        "ticker": crypto_payload,
    }
    merged = apply_crypto_live_cache_fallback(
        pack,
        cache=cached,
        coinpaprika_total=coinpaprika_total,
        rebuild_kpis=_rebuild_kpis,
    )
    if merged["prices"].get("rows") and not merged.get("_used_cached_rows"):
        save_crypto_live_cache(
            cache_path,
            {
                "generated_at": merged["generated_at"],
                "kpis": merged["kpis"],
                "prices": merged["prices"],
                "chart": merged["chart"],
                "coinpaprika_total": merged.get("coinpaprika_total") or coinpaprika_total,
            },
        )

    return {
        "generated_at": merged["generated_at"],
        "kpis": merged["kpis"],
        "prices": merged["prices"],
        "chart": merged["chart"],
        "ticker": merged.get("ticker") or crypto_payload,
    }


def export_crypto_json_bundle(
    manifest: dict[str, Any],
    *,
    news_articles: list[dict[str, Any]] | None = None,
) -> None:
    """Write ``crypto_ticker.json``, ``crypto_prices.json``, ``crypto_kpis.json``, ``crypto_market_cap_series.json``."""
    manifest.setdefault("errors", [])
    pack = build_crypto_prices_page_payloads(
        news_articles=news_articles,
        blurb_cache_path=OUT / "crypto_about_blurbs_cache.json",
        manifest_errors=manifest["errors"],
        live_cache_path=OUT / "crypto_live_cache.json",
    )
    (OUT / "crypto_ticker.json").write_text(json.dumps(pack["ticker"], indent=2), encoding="utf-8")
    (OUT / "crypto_prices.json").write_text(json.dumps(pack["prices"], indent=2), encoding="utf-8")
    (OUT / "crypto_kpis.json").write_text(json.dumps(pack["kpis"], indent=2), encoding="utf-8")
    (OUT / "crypto_market_cap_series.json").write_text(
        json.dumps(pack["chart"], indent=2),
        encoding="utf-8",
    )
    manifest["crypto_refreshed_at"] = pack["generated_at"]


_ETP_MANIFEST_ERROR_PREFIXES = ("ETP scrape:", "ETP flows:", "AUM chart:")


def build_etp_page_payloads(
    *,
    user_agent: str | None = None,
    errors_out: list[str] | None = None,
    live_cache_path: Path | None = None,
    for_streamlit: bool = False,
) -> dict[str, Any]:
    """Build U.S. ETP page JSON payloads (etps, kpis, aum series, pulse, manifest)."""
    ua = user_agent or DEFAULT_UA
    etp_errors: list[str] = errors_out if errors_out is not None else []

    if for_streamlit:
        from crypto_etps.client import fetch_crypto_etps_list

        etp_result = fetch_crypto_etps_list(ua)
    else:
        etp_result = fetch_crypto_etps_enriched(ua)
    if etp_result.error:
        etp_errors.append(f"ETP scrape: {etp_result.error}")
    rows = sorted_by_assets(etp_result.rows)
    flow_series, flow_src = load_farside_flow_series_with_source()
    if flow_src == "none":
        etp_errors.append(
            "ETP flows: could not load Farside BTC/ETH flow tables (live fetch failed and no cache file)."
        )

    rows_payload = []
    for r in rows:
        fy, fy_lbl = fund_flow_usd(r.symbol, flow_series, days=365)
        rows_payload.append(_etp_row_json(r, flow_1y_usd=fy, flow_1y_window=fy_lbl))

    pairs = etp_rows_to_fund_pairs(rows)
    chart_df, chart_err = build_aggregate_aum_history_12m(list(pairs))
    if chart_err:
        etp_errors.append(f"AUM chart: {chart_err}")

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

    listed_syms = [r.symbol for r in rows if (r.symbol or "").strip()]
    net_flow_1m, net_flow_1m_lbl = aggregate_flow_for_symbols(
        listed_syms, flow_series, days=30
    )
    net_flow_1m_pct, net_flow_pct_lbl = aggregate_flow_mom_pct(
        listed_syms, flow_series, days=30
    )

    refreshed_at = datetime.now(timezone.utc).isoformat()

    kpis = {
        "generated_at": refreshed_at,
        "kpi_window_note": ETP_KPI_WINDOW_NOTE,
        "total_aum_display": aum_s,
        "aggregate_pct": round(float(agg_pct), 4) if agg_pct is not None else None,
        "aggregate_window": agg_lbl or "",
        "net_flow_1m_usd": round(float(net_flow_1m), 2) if net_flow_1m is not None else None,
        "net_flow_1m_display": format_flow_usd_compact(net_flow_1m),
        "net_flow_1m_pct": round(float(net_flow_1m_pct), 4) if net_flow_1m_pct is not None else None,
        "net_flow_pct_window": net_flow_pct_lbl or net_flow_1m_lbl or "",
        "ibit": {"aum_display": ibit_aum, "delta": _kpi_delta("IBIT", ibit_r)},
        "etha": {"aum_display": etha_aum, "delta": _kpi_delta("ETHA", etha_r)},
    }

    etf_articles: list[dict[str, Any]] = []
    if for_streamlit:
        kpis["key_observations_html"] = ""
    else:
        try:
            from crypto_etps.etp_takeaways import build_etp_key_observations_html

            etf_articles, etf_feed_errs = load_all_etf_etp_news_cached(extra_feeds=[STATIC_THE_DEFIANT_FEED])
            for e in etf_feed_errs:
                etp_errors.append(f"ETF news RSS: {e}")
            kpis["key_observations_html"] = build_etp_key_observations_html(
                rows,
                net_flow_1m_display=kpis["net_flow_1m_display"],
                net_flow_1m_pct=net_flow_1m_pct,
                articles=etf_articles,
            )
        except Exception as exc:
            kpis["key_observations_html"] = ""
            etp_errors.append(f"ETP key observations HTML: {exc}")

    pulse_items = [_article_json(a) for a in etf_articles[:ETP_PULSE_PREVIEW_COUNT]]
    payloads: dict[str, Any] = {
        "etps.json": {"generated_at": refreshed_at, "rows": rows_payload, "error": etp_result.error or ""},
        "etp_kpis.json": kpis,
        "aum_series.json": {"generated_at": refreshed_at, "series": series},
        "etf_pulse.json": {"generated_at": refreshed_at, "items": pulse_items},
        "manifest.json": {"errors": etp_errors, "etp_refreshed_at": refreshed_at},
    }

    from etp_live_cache import apply_etp_live_cache_fallback, load_etp_live_cache, save_etp_live_cache

    cache_path = live_cache_path or (OUT / "etp_live_cache.json")
    cached = load_etp_live_cache(cache_path, static_dir=OUT)
    merged_payloads = apply_etp_live_cache_fallback(payloads, cache=cached)
    used_cached_rows = not rows_payload and bool((merged_payloads.get("etps.json") or {}).get("rows"))

    if rows_payload and not used_cached_rows:
        save_etp_live_cache(
            cache_path,
            {
                "generated_at": refreshed_at,
                "payloads": merged_payloads,
            },
        )

    return {
        "generated_at": refreshed_at,
        "payloads": merged_payloads,
        "errors": etp_errors,
        "etp_count": len((merged_payloads.get("etps.json") or {}).get("rows") or []),
        "aum_points": len((merged_payloads.get("aum_series.json") or {}).get("series") or []),
    }


def export_etp_json_bundle(
    out: Path | None = None,
    *,
    errors_out: list[str] | None = None,
) -> dict[str, Any]:
    """
    Refresh U.S. ETP JSON only (fund list, KPI strip, aggregate AUM chart series).

    Writes ``etps.json``, ``etp_kpis.json``, and ``aum_series.json`` under ``static_home/data/``.
    Does not touch crypto, RWA, news, or other payloads.
    """
    out_dir = out or OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = build_etp_page_payloads(
        errors_out=errors_out,
        live_cache_path=out_dir / "etp_live_cache.json",
    )
    payloads = summary["payloads"]
    (out_dir / "etps.json").write_text(json.dumps(payloads["etps.json"], indent=2), encoding="utf-8")
    (out_dir / "aum_series.json").write_text(
        json.dumps(payloads["aum_series.json"], indent=2),
        encoding="utf-8",
    )
    (out_dir / "etp_kpis.json").write_text(json.dumps(payloads["etp_kpis.json"], indent=2), encoding="utf-8")
    (out_dir / "etf_pulse.json").write_text(
        json.dumps(payloads["etf_pulse.json"], indent=2),
        encoding="utf-8",
    )
    return {
        "etp_refreshed_at": summary["generated_at"],
        "errors": summary["errors"],
        "etp_count": summary["etp_count"],
        "aum_points": summary["aum_points"],
    }


def merge_etp_refresh_into_manifest(summary: dict[str, Any], manifest_path: Path | None = None) -> None:
    """Patch ``manifest.json``: ETP timestamp + replace ETP-scoped errors only."""
    path = manifest_path or (OUT / "manifest.json")
    if path.exists():
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            manifest = {}
    else:
        manifest = {}
    if not isinstance(manifest.get("errors"), list):
        manifest["errors"] = []
    kept = [
        e
        for e in manifest["errors"]
        if not any(str(e).startswith(p) for p in _ETP_MANIFEST_ERROR_PREFIXES)
    ]
    manifest["errors"] = kept + list(summary.get("errors") or [])
    manifest["etp_refreshed_at"] = summary.get("etp_refreshed_at")
    if not manifest.get("generated_at"):
        manifest["generated_at"] = summary.get("etp_refreshed_at")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"generated_at": datetime.now(timezone.utc).isoformat(), "errors": []}

    etp_summary = export_etp_json_bundle(errors_out=manifest["errors"])
    manifest["etp_refreshed_at"] = etp_summary["etp_refreshed_at"]

    # --- Home RSS lane (also used for crypto Top Movers headline context).
    articles_home, feed_errs_home = load_all_feeds(list(DEFAULT_FEEDS) + [STATIC_THE_DEFIANT_FEED])
    for e in feed_errs_home:
        manifest["errors"].append(f"news RSS (home): {e}")
    home_unique = dedupe_articles(articles_home, max_items=None)
    home_news_items = home_unique[:HOME_NEWS_N]

    export_crypto_json_bundle(manifest, news_articles=home_unique)

    # --- All digital asset headlines: core + supplement + The Defiant; dedupe; last rolling week only (no per-day cap).
    articles_all, feed_errs_all = load_all_feeds(list(ALL_ARTICLES_FEEDS) + [STATIC_THE_DEFIANT_FEED])
    for e in feed_errs_all:
        manifest["errors"].append(f"news RSS (all articles): {e}")
    all_unique = dedupe_articles(articles_all, max_items=None)
    all_unique = dedupe_repetitive_headlines(all_unique)
    articles_for_all_json = articles_published_within_utc_days(all_unique, ALL_DIGITAL_NEWS_LOOKBACK_DAYS)
    articles_for_all_json.sort(
        key=lambda x: x["published"] if isinstance(x.get("published"), datetime) else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    reg_articles, reg_errs = load_regulatory_articles(extra_feeds=STATIC_THE_DEFIANT_REG_EXTRA)
    for e in reg_errs:
        manifest["errors"].append(f"reg RSS: {e}")
    reg_top = reg_articles[:REG_N]

    news_ts = datetime.now(timezone.utc).isoformat()
    (OUT / "home_news.json").write_text(
        json.dumps(
            {"generated_at": news_ts, "items": [_article_json(a) for a in home_news_items]},
            indent=2,
        ),
        encoding="utf-8",
    )
    (OUT / "regulatory.json").write_text(
        json.dumps(
            {"generated_at": news_ts, "items": [_article_json(a) for a in reg_top]},
            indent=2,
        ),
        encoding="utf-8",
    )
    # Full list for static GitHub Pages (search + pagination).
    (OUT / "all_articles.json").write_text(
        json.dumps({"items": [_article_json(a) for a in articles_for_all_json]}, indent=2),
        encoding="utf-8",
    )
    (OUT / "all_regulatory.json").write_text(
        json.dumps({"items": [_article_json(a) for a in reg_articles]}, indent=2),
        encoding="utf-8",
    )

    cust_raw, cust_errs = load_custodian_articles(per_day_cap=0)
    for e in cust_errs:
        manifest["errors"].append(f"custodian RSS: {e}")
    cust_articles = articles_published_within_utc_days(cust_raw, CUSTODIAN_LOOKBACK_DAYS)
    enrich_custodian_access(cust_articles)
    cust_articles.sort(
        key=lambda x: x["published"]
        if isinstance(x.get("published"), datetime)
        else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    (OUT / "all_custodian_news.json").write_text(
        json.dumps({"items": [_article_json(a) for a in cust_articles]}, indent=2),
        encoding="utf-8",
    )

    # --- ETF / ETP headline pool (same filter + ranked daily cap as Streamlit / FastAPI) ---
    etf_all, etf_feed_errs = load_all_etf_etp_news_cached(extra_feeds=[STATIC_THE_DEFIANT_FEED])
    for e in etf_feed_errs:
        manifest["errors"].append(f"ETF news RSS: {e}")

    etf_items = [_article_json(a) for a in etf_all]
    (OUT / "etf_news.json").write_text(
        json.dumps({"items": etf_items}, indent=2),
        encoding="utf-8",
    )
    pulse = etf_items[:ETP_PULSE_PREVIEW_COUNT]
    (OUT / "etf_pulse.json").write_text(
        json.dumps({"generated_at": news_ts, "items": pulse}, indent=2),
        encoding="utf-8",
    )

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

    rwa_df = build_rwa_dataframe(list(rwa_rows)) if rwa_rows else pd.DataFrame()
    rwa_table_rows, rwa_columns = _dataframe_json_records(rwa_df)

    explore_at = STATIC_RWA_EXPLORE_ASSET_TYPE_PAGE
    explore_mp = STATIC_RWA_EXPLORE_MARKET_PARTICIPANT_PAGE

    rwa_ts = datetime.now(timezone.utc).isoformat()
    rwa_onchain_payload = {
        "generated_at": rwa_ts,
        "heading": "RWA Global Market Overview",
        "error": rwa_err,
        "kpis": [_rwa_kpi_to_dict(k) for k in rwa_kpis],
        "kpi_window_note": (
            "All % changes in this row are 30-day (30D) (RWA.xyz). "
            "Headline totals from the RWA.xyz Global Market Overview."
        ),
        "columns": rwa_columns,
        "rows": rwa_table_rows,
        "preview_count": min(HOME_RWA_PREVIEW_ROWS, len(rwa_table_rows)),
        "total_networks": len(rwa_rows),
        "caption": (
            "Source: RWA.xyz homepage (https://app.rwa.xyz/)—Global Market Overview headline figures and the "
            "Networks league (Distributed / parent networks)."
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
    from rwa_global_page_payloads import build_rwa_global_page_payload

    rwa_global_payload = build_rwa_global_page_payload(
        rwa_rows=rwa_rows,
        rwa_kpis=rwa_kpis,
        rwa_err=rwa_err,
    )

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
        fetch_rwa_tokenized_mmf_data,
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
        mmf_pack = fetch_rwa_tokenized_mmf_data()
    except Exception as exc:
        manifest["errors"].append(f"RWA Tokenized MMF snapshot (Explore + asset pages): {exc}")
        mmf_pack = ([], [], [], str(exc))

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

    from key_observations.feeds import merge_takeaway_pools

    takeaway_pool = merge_takeaway_pools(home_unique, all_unique, reg_top)

    from rwa_explore_page_payloads import (
        build_rwa_explore_asset_type_page_payload,
        build_rwa_explore_market_participant_page_payload,
    )

    explore_at_payload = build_rwa_explore_asset_type_page_payload(
        sc_pack=sc_pack, tr_pack=tr_pack, st_pack=st_pack, mmf_pack=mmf_pack
    )
    (OUT / "rwa_explore_asset_type.json").write_text(
        json.dumps(explore_at_payload, indent=2),
        encoding="utf-8",
    )

    explore_mp_payload = build_rwa_explore_market_participant_page_payload(
        net_pack=p_net_pack, plat_pack=p_plat_pack, am_pack=p_am_pack
    )
    (OUT / "rwa_explore_market_participant.json").write_text(
        json.dumps(explore_mp_payload, indent=2),
        encoding="utf-8",
    )

    (OUT / "rwa_participants_networks.json").write_text(
        json.dumps(
            _build_rwa_participants_networks_deep_payload(p_net_pack, manifest, takeaway_pool),
            indent=2,
        ),
        encoding="utf-8",
    )
    (OUT / "rwa_participants_platforms.json").write_text(
        json.dumps(
            _build_rwa_participants_platforms_deep_payload(p_plat_pack, manifest, takeaway_pool),
            indent=2,
        ),
        encoding="utf-8",
    )
    (OUT / "rwa_participants_asset_managers.json").write_text(
        json.dumps(
            _build_rwa_participants_asset_managers_deep_payload(p_am_pack, manifest, takeaway_pool),
            indent=2,
        ),
        encoding="utf-8",
    )

    (OUT / "rwa_stablecoins.json").write_text(
        json.dumps(_build_rwa_stablecoins_deep_payload(sc_pack, manifest, takeaway_pool), indent=2),
        encoding="utf-8",
    )
    (OUT / "rwa_us_treasuries.json").write_text(
        json.dumps(_build_rwa_us_treasuries_deep_payload(tr_pack, manifest, takeaway_pool), indent=2),
        encoding="utf-8",
    )
    (OUT / "rwa_tokenized_stocks.json").write_text(
        json.dumps(_build_rwa_tokenized_stocks_deep_payload(st_pack, manifest, takeaway_pool), indent=2),
        encoding="utf-8",
    )
    (OUT / "rwa_tokenized_mmf.json").write_text(
        json.dumps(_build_rwa_tokenized_mmf_deep_payload(mmf_pack, manifest, takeaway_pool), indent=2),
        encoding="utf-8",
    )

    manifest["sections"] = {
        "news": news_ts,
        "regulatory": news_ts,
        "etp": manifest.get("etp_refreshed_at") or manifest["generated_at"],
        "rwa": rwa_ts,
        "crypto": manifest.get("crypto_refreshed_at") or manifest["generated_at"],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        f"Wrote static data to {OUT} ({etp_summary.get('etp_count', 0)} ETPs, {len(etf_items)} ETF headlines, "
        f"{len(rwa_rows)} RWA networks; crypto_ticker.json, rwa_global_market.json, rwa_explore_asset_type.json, "
        "rwa_explore_market_participant.json, rwa_participants_networks.json, rwa_participants_platforms.json, "
        "rwa_participants_asset_managers.json, rwa_stablecoins.json, rwa_us_treasuries.json, "
        "rwa_tokenized_stocks.json, rwa_tokenized_mmf.json, rwa_onchain_home.json)."
    )


if __name__ == "__main__":
    if any(a in ("--etp-only", "--etp") for a in sys.argv[1:]):
        summary = export_etp_json_bundle()
        merge_etp_refresh_into_manifest(summary)
        print(
            f"Wrote ETP JSON to {OUT} ({summary['etp_count']} funds, "
            f"{summary['aum_points']} chart points). "
            f"Other static_home/data/*.json unchanged."
        )
        if summary["errors"]:
            print("Warnings:", summary["errors"])
        raise SystemExit(0)
    if any(a in ("--crypto-only", "--crypto") for a in sys.argv[1:]):
        OUT.mkdir(parents=True, exist_ok=True)
        manifest_only: dict[str, Any] = {"generated_at": datetime.now(timezone.utc).isoformat(), "errors": []}
        export_crypto_json_bundle(manifest_only)
        sample_path = OUT / "crypto_prices.json"
        sample_keys: list[str] = []
        try:
            loaded = json.loads(sample_path.read_text(encoding="utf-8"))
            rows0 = (loaded.get("rows") or [{}])[0]
            sample_keys = sorted(rows0.keys())
        except (OSError, ValueError, TypeError):
            pass
        print(f"Wrote crypto JSON under {sample_path.parent}. First row keys: {sample_keys}")
        if manifest_only["errors"]:
            print("Warnings:", manifest_only["errors"])
        raise SystemExit(0)
    main()
