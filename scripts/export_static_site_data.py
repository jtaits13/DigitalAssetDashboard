"""
Build JSON payloads under static_home/data/ for the GitHub Pages mirror.

Run locally:  python scripts/export_static_site_data.py
Run in CI:    before upload-pages-artifact (see .github/workflows).

Uses the same RSS / StockAnalysis / yfinance / RWA.xyz logic as the Streamlit app (no Streamlit UI).

Optional env ``STATIC_WEBAPP_BASE``: absolute origin for FastAPI-only links (e.g. ``/rwa/explore/...``) embedded in JSON when the static hub is on GitHub Pages but the API lives elsewhere. The full RWA Global overview is served as ``static_home/rwa-global.html`` (not ``/rwa/global``).
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
APP_RWA_NETWORKS_URL = "https://app.rwa.xyz/networks"

DEFAULT_UA = os.environ.get(
    "STOCKANALYSIS_USER_AGENT",
    "JPM-Digital/1.0 (static site export; contact per StockAnalysis terms)",
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

    explore_at = _webapp_href("/rwa/explore/asset-type")
    explore_mp = _webapp_href("/rwa/explore/participant")

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
        "page_title": "RWA Global Market Overview",
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

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        f"Wrote static data to {OUT} ({len(rows_payload)} ETPs, {len(etf_items)} ETF headlines, "
        f"{len(rwa_rows)} RWA networks; rwa_global_market.json + rwa_onchain_home.json)."
    )


if __name__ == "__main__":
    main()
