"""
Render Streamlit home as static GitHub Pages HTML (tables, KPIs, zones).

Avoids st.dataframe / default Streamlit chrome inside home zones.
"""

from __future__ import annotations

import math
from html import escape
from typing import Any, Sequence

import streamlit as st
import streamlit.components.v1 as components

from crypto_categories import (
    btc_dominance_change_pct_1m,
    category_label,
    compute_market_structure,
    crypto_category,
    stablecoin_share_change_pct_1m,
    structure_kpi_dicts,
)
from crypto_etps.client import (
    CryptoEtpRow,
    format_usd_compact,
    has_listed_aum_usd,
    total_aum_usd,
)
from crypto_etps.aum_history import (
    aggregate_aum_pct_from_history,
    etp_rows_to_fund_pairs,
    etp_symbol_price_change_cached,
    load_aggregate_aum_history_cached,
)
from crypto_etps.dataframe_table import build_etp_dataframe
from crypto_etps.flows import (
    aggregate_flow_for_symbols,
    aggregate_flow_mom_pct,
    format_flow_usd_compact,
    load_farside_flow_series_cached,
)
from crypto_etps.widgets import _row_by_symbol
from rwa_league.client import RwaGlobalKpi
from rwa_league.dataframe_table import (
    build_rwa_dataframe,
    build_stablecoin_network_dataframe,
    build_us_treasury_network_dataframe,
)
from rwa_league.mmf import asset_distributed_value_usd, build_curated_mmf_dashboard_data

HOME_PREVIEW = 5

_NUM_COLS = frozenset(
    {
        "Price",
        "1Y %",
        "1Y Flow",
        "Assets (B)",
        "Total Value",
        "Market Cap",
        "1M %",
        "Market Share",
        "30D Δ share",
        "7D Δ value",
        "Rank",
        "RWA Count",
        "Stablecoins",
    }
)

# Home preview column sets (match static_home/index.html + home-rwa-asset-zones.js)
TMMF_HOME_COLS = ("Fund Name", "Ticker", "Platform", "Total Value", "7D Δ value")
STABLE_HOME_COLS = ("Network", "Stablecoins", "Total Value", "Market Share", "30D Δ share")
RWA_HOME_COLS = ("Network", "RWA Count", "Total Value", "Market Share")
ETP_HOME_COLS = ("Symbol", "Fund Name", "Price", "1Y %", "1Y Flow", "Assets (B)")
CRYPTO_HOME_COLS = ("Rank", "Ticker", "Coin", "Category", "Price", "1M %", "Market Cap")


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


def _delta30_html(frac: float | None) -> str:
    if frac is None or (isinstance(frac, float) and math.isnan(frac)):
        return '<span class="rwa-kpi-delta rwa-kpi-delta--placeholder" aria-hidden="true">&nbsp;</span>'
    pct = float(frac) * 100.0
    cls = "up" if pct > 0 else "down" if pct < 0 else "neutral"
    sign = "+" if pct > 0 else ""
    return f'<span class="rwa-kpi-delta {cls}">{sign}{pct:.2f}%</span>'


def _snapshot_pct_html(pct: float | None) -> str:
    if pct is None or (isinstance(pct, float) and math.isnan(pct)):
        return '<span class="rwa-kpi-delta neutral">—</span>'
    n = float(pct)
    cls = "up" if n > 0 else "down" if n < 0 else "neutral"
    sign = "+" if n > 0 else ""
    return f'<span class="rwa-kpi-delta {cls}">{sign}{n:.2f}%</span>'


def rwa_snapshot_kpi_html(kpis: list[RwaGlobalKpi], *, legend: str = "") -> str:
    if not kpis:
        return ""
    cells: list[str] = []
    for k in kpis:
        cells.append(
            "<div class='rwa-kpi-cell'>"
            f"<span class='rwa-kpi-label'>{escape(k.label)}</span>"
            f"<span class='rwa-kpi-val'>{escape(k.value_display)}</span>"
            f"{_delta30_html(k.delta_30d_pct)}"
            "</div>"
        )
    legend_html = (
        f'<p class="jd-kpi-window-note rwa-onchain-kpi-legend">{escape(legend)}</p>' if legend else ""
    )
    return (
        '<div class="rwa-kpi-panel-static">'
        f"{legend_html}"
        f"<div class=\"rwa-kpi-row rwa-kpi-row--home-grid\">{''.join(cells)}</div>"
        "</div>"
    )


def etp_snapshot_kpi_html(rows: list[CryptoEtpRow]) -> str:
    total = total_aum_usd(rows)
    aum_s = format_usd_compact(total) if total > 0 else "—"
    pairs = etp_rows_to_fund_pairs(rows)
    hist_df, _ = load_aggregate_aum_history_cached(pairs)
    agg_pct, _ = aggregate_aum_pct_from_history(hist_df)
    ibit = _row_by_symbol(rows, "IBIT")
    etha = _row_by_symbol(rows, "ETHA")
    flow_series = load_farside_flow_series_cached()
    syms = [r.symbol for r in rows if (r.symbol or "").strip()]
    net_flow, _ = aggregate_flow_for_symbols(syms, flow_series, days=30)
    net_flow_pct, _ = aggregate_flow_mom_pct(syms, flow_series, days=30)

    def _aum(r: CryptoEtpRow | None) -> str:
        if r and has_listed_aum_usd(r.assets_usd):
            return format_usd_compact(r.assets_usd)
        return "—"

    def _pct(sym: str, r: CryptoEtpRow | None) -> float | None:
        p, _ = etp_symbol_price_change_cached(sym)
        if p is not None:
            return float(p)
        if r and r.pct_52w is not None:
            return float(r.pct_52w)
        return None

    cells = [
        ("Total AUM (listed)", aum_s, agg_pct),
        ("BTC & ETH Fund flows (listed)", format_flow_usd_compact(net_flow), net_flow_pct),
        ("IBIT · AUM", _aum(ibit), _pct("IBIT", ibit)),
        ("ETHA · AUM", _aum(etha), _pct("ETHA", etha)),
    ]
    parts = []
    for label, val, delta in cells:
        parts.append(
            "<div class='rwa-kpi-cell'>"
            f"<span class='rwa-kpi-label'>{escape(label)}</span>"
            f"<span class='rwa-kpi-val'>{escape(val)}</span>"
            f"{_snapshot_pct_html(delta)}"
            "</div>"
        )
    return (
        '<div class="rwa-kpi-panel-static">'
        f"<div class=\"rwa-kpi-row rwa-kpi-row--home-grid\">{''.join(parts)}</div>"
        "</div>"
    )


def crypto_snapshot_kpi_html(
    rows: list[dict[str, Any]],
    paprika: dict[str, float],
) -> str:
    total_cap = paprika.get("total_market_cap_usd")
    cap_pct = paprika.get("market_cap_change_pct_1m")
    primary = format_usd_compact(total_cap) if total_cap else "—"

    structure = compute_market_structure(rows, total_market_cap_usd=total_cap)
    dom_delta = btc_dominance_change_pct_1m(
        rows,
        total_market_cap_now=total_cap,
        total_market_cap_then=paprika.get("total_market_cap_usd_30d_ago"),
    )
    st_delta = stablecoin_share_change_pct_1m(rows)
    btc_dom_kpi, stable_kpi = structure_kpi_dicts(
        structure,
        btc_dom_delta_pct_1m=dom_delta,
        stable_share_delta_pct_1m=st_delta,
    )

    parts_payload = [
        {"label": "Total market cap", "value_display": primary, "delta_pct": cap_pct},
        btc_dom_kpi,
        stable_kpi,
    ]
    cells: list[str] = []
    for p in parts_payload:
        if not p:
            continue
        label = str(p.get("label") or "")
        val = str(p.get("value_display") or "—")
        delta = p.get("delta", {})
        dp = delta.get("pct") if isinstance(delta, dict) else p.get("delta_pct")
        cells.append(
            "<div class='rwa-kpi-cell'>"
            f"<span class='rwa-kpi-label'>{escape(label)}</span>"
            f"<span class='rwa-kpi-val'>{escape(val)}</span>"
            f"{_snapshot_pct_html(float(dp) if dp is not None else None)}"
            "</div>"
        )
    return (
        '<div class="rwa-kpi-panel-static rwa-kpi-panel-static--compact">'
        f"<div class=\"rwa-kpi-row rwa-kpi-row--home-grid\">{''.join(cells)}</div>"
        "</div>"
    )


def _cell_display(col: str, val: Any) -> tuple[str, str]:
    """Return (html, extra_td_class)."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "—", ""
    if col in ("Total Value", "Market Cap", "Assets (B)", "1Y Flow"):
        if col == "Assets (B)":
            try:
                return f"{float(val):.2f}", " num"
            except (TypeError, ValueError):
                return "—", " num"
        if col == "1Y Flow":
            try:
                n = float(val)
                cls = " num up" if n > 0 else " num down" if n < 0 else " num"
                return escape(format_flow_usd_compact(n)), cls
            except (TypeError, ValueError):
                return "—", " num"
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
    if col == "Price":
        try:
            return escape(f"${float(val):,.2f}" if float(val) < 1000 else f"${float(val):,.0f}"), " num"
        except (TypeError, ValueError):
            return escape(str(val)), " num"
    if col in ("Rank", "RWA Count", "Stablecoins"):
        try:
            return escape(str(int(val))), " num" if col != "Rank" else ""
        except (TypeError, ValueError):
            return escape(str(val)), ""
    return escape(str(val)), ""


def _df_to_row_dicts(df: pd.DataFrame, columns: Sequence[str], *, limit: int = HOME_PREVIEW) -> list[dict[str, Any]]:
    if df.empty:
        return []
    cols = [c for c in columns if c in df.columns]
    out: list[dict[str, Any]] = []
    for _, row in df.head(limit).iterrows():
        out.append({c: row.get(c) for c in cols})
    return out


def _data_table_html(
    columns: Sequence[str],
    rows: list[dict[str, Any]],
    *,
    table_id: str,
    empty_msg: str = "No preview rows available.",
) -> str:
    thead = "".join(
        f'<th scope="col"{" class=\"num\"" if c in _NUM_COLS else ""}>{escape(c)}</th>'
        for c in columns
    )
    if not rows:
        tbody = f'<tr><td colspan="{len(columns)}">{escape(empty_msg)}</td></tr>'
    else:
        body_rows: list[str] = []
        for row in rows:
            tds: list[str] = []
            for c in columns:
                txt, cls = _cell_display(c, row.get(c))
                tds.append(f"<td class=\"{cls.strip()}\">{txt}</td>")
            body_rows.append(f"<tr data-search=\"{escape(' '.join(str(row.get(c) or '') for c in columns).lower(), quote=True)}\">{''.join(tds)}</tr>")
        tbody = "".join(body_rows)
    return (
        f'<div class="table-wrap" data-home-table="{escape(table_id)}">'
        f'<table class="data-table data-table--dense" aria-label="{escape(table_id)}">'
        f"<thead><tr>{thead}</tr></thead>"
        f"<tbody id=\"{escape(table_id)}-tbody\">{tbody}</tbody>"
        "</table></div>"
    )


def _search_field_html(*, field_id: str, label: str, placeholder: str) -> str:
    return (
        f'<label class="search-field home-preview-search-row" for="{escape(field_id)}">'
        f'<span class="search-field__label">{escape(label)}</span>'
        f'<input type="search" class="search-field__input home-preview-filter" '
        f'id="{escape(field_id)}" data-table-target="{escape(field_id)}" '
        f'placeholder="{escape(placeholder)}" autocomplete="off" />'
        "</label>"
        f'<p class="toolbar-note home-preview-toolbar" id="{escape(field_id)}-toolbar" hidden></p>'
    )


def _cta_html(href: str, label: str) -> str:
    return (
        f'<div class="cta-row rwa-table-actions">'
        f'<a class="btn btn-primary" href="{escape(href)}">{escape(label)}</a>'
        "</div>"
    )


def _zone_open(
    *,
    section_id: str,
    badge: str,
    title: str,
    subtitle: str,
    zone_class: str,
    extra_body_top: str = "",
) -> str:
    return (
        f'<div class="hub-section hub-section--panel home-zone {zone_class} home-reveal is-visible site-experience page-home" '
        f'role="region" id="{escape(section_id)}" aria-labelledby="{escape(section_id)}-heading">'
        '<div class="home-zone__stripe" aria-hidden="true"></div>'
        '<div class="home-zone__head">'
        f'<span class="home-zone__badge" aria-hidden="true">{escape(badge)}</span>'
        '<div class="home-zone__titles">'
        f'<h2 class="band-label zone-label" id="{escape(section_id)}-heading">{escape(title)}</h2>'
        f'<p class="section-dek section-dek--wide">{escape(subtitle)}</p>'
        "</div></div>"
        f'<div class="home-zone__body">{extra_body_top}'
    )


def _zone_close(*, explore: bool = False, source_cap: str = "") -> str:
    explore_html = ""
    if explore:
        explore_html = """
    <nav class="home-explore-compact" aria-label="Explore RWA">
      <span class="home-explore-compact__label">Explore</span>
      <a class="home-explore-compact__btn" href="/RWA_Explore_By_Asset_Type">By asset type</a>
      <a class="home-explore-compact__btn" href="/RWA_Explore_By_Market_Participant">By participant</a>
    </nav>"""
    cap = f'<p class="source-cap">{escape(source_cap)}</p>' if source_cap else ""
    return f"{cap}{explore_html}</div></div>"


def _mmf_fund_rows(mmfs: list[dict[str, Any]], *, limit: int = HOME_PREVIEW) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in mmfs[:limit]:
        name = str(asset.get("name") or "—").strip()
        ticker = str(asset.get("ticker") or "—").strip() or "—"
        plat = asset.get("issuer_name") or asset.get("platform_name")
        if not plat:
            pobj = asset.get("platform") or {}
            plat = pobj.get("name") if isinstance(pobj, dict) else "—"
        platform = str(plat or "—").strip()
        total = asset_distributed_value_usd(asset)
        val_obj = asset.get("bridged_token_value_dollar") or {}
        pct7 = val_obj.get("chg_7d_pct") if isinstance(val_obj, dict) else None
        try:
            pct7f = float(pct7) if pct7 is not None else None
        except (TypeError, ValueError):
            pct7f = None
        rows.append(
            {
                "Fund Name": name,
                "Ticker": ticker,
                "Platform": platform,
                "Total Value": total,
                "7D Δ value": pct7f,
            }
        )
    return rows


def _crypto_preview_rows(rows: list[dict[str, Any]], *, limit: int = HOME_PREVIEW) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, r in enumerate(rows[:limit], start=1):
        sym = str(r.get("symbol") or "")
        name = str(r.get("name") or sym)
        cat = crypto_category(sym, name)
        rank = r.get("market_cap_rank")
        try:
            rank_num = int(rank) if rank is not None else i
        except (TypeError, ValueError):
            rank_num = i
        cap = r.get("market_cap_usd")
        pct = r.get("pct_30d")
        out.append(
            {
                "Rank": rank_num,
                "Ticker": sym,
                "Coin": name,
                "Category": category_label(cat),
                "Price": r.get("price_usd"),
                "1M %": float(pct) if pct is not None else None,
                "Market Cap": float(cap) if cap is not None else None,
            }
        )
    return out


def build_home_markets_stack_html(
    *,
    mmf_kpis: list[RwaGlobalKpi],
    mmf_funds: list[dict[str, Any]],
    stable_kpis: list[RwaGlobalKpi],
    stable_df: pd.DataFrame,
    rwa_kpis: list[RwaGlobalKpi],
    rwa_df: pd.DataFrame,
    etp_rows: list[CryptoEtpRow],
    crypto_rows: list[dict[str, Any]],
    crypto_paprika: dict[str, float],
) -> str:
    return "".join(
        iter_home_markets_stack_html(
            mmf_kpis=mmf_kpis,
            mmf_funds=mmf_funds,
            stable_kpis=stable_kpis,
            stable_df=stable_df,
            rwa_kpis=rwa_kpis,
            rwa_df=rwa_df,
            etp_rows=etp_rows,
            crypto_rows=crypto_rows,
            crypto_paprika=crypto_paprika,
        )
    )


def iter_home_markets_stack_html(
    *,
    mmf_kpis: list[RwaGlobalKpi],
    mmf_funds: list[dict[str, Any]],
    stable_kpis: list[RwaGlobalKpi],
    stable_df: pd.DataFrame,
    rwa_kpis: list[RwaGlobalKpi],
    rwa_df: pd.DataFrame,
    etp_rows: list[CryptoEtpRow],
    crypto_rows: list[dict[str, Any]],
    crypto_paprika: dict[str, float],
) -> list[str]:
    """One HTML fragment per zone — Streamlit drops extra blocks in a single markdown blob."""
    parts: list[str] = [
        '<p class="home-kpi-legend-once" id="home-kpi-legend">'
        "<strong>How to read KPIs:</strong> On-chain figures use 30-day (30D) % from RWA.xyz. "
        "U.S. ETP and crypto rows use ~30 calendar days unless noted on the full page."
        "</p>"
    ]

    # TMMF
    tmmf: list[str] = [
        _zone_open(
            section_id="section-tmmf",
            badge="MMF",
            title="Tokenized Money Market Funds",
            subtitle="Curated on-chain fund list — KPIs and searchable preview.",
            zone_class="home-zone--tmmf",
        ),
        rwa_snapshot_kpi_html(mmf_kpis),
        '<p class="home-table-caption">Funds preview</p>',
        _search_field_html(
            field_id="js-home-tmmf-search",
            label="Filter preview by fund or network name",
            placeholder="Filter by fund, platform, or network…",
        ),
        _data_table_html(
            TMMF_HOME_COLS,
            _mmf_fund_rows(mmf_funds),
            table_id="js-home-tmmf",
            empty_msg="TMMF fund preview is unavailable.",
        ),
        _cta_html("/RWA_Tokenized_MMF", "Open full TMMF page"),
        _zone_close(
            source_cap="Curated fund population preview. Population may not include all TMMFs in the market."
        ),
    ]
    parts.append("".join(tmmf))

    # Stablecoins
    stable: list[str] = [
        _zone_open(
            section_id="section-stablecoins",
            badge="SC",
            title="Stablecoins",
            subtitle="Market cap, holders, and network distribution from RWA.xyz.",
            zone_class="home-zone--stable",
        ),
        rwa_snapshot_kpi_html(stable_kpis),
        '<p class="home-table-caption">Networks preview</p>',
        _search_field_html(
            field_id="js-home-stable-search",
            label="Filter preview by network name",
            placeholder="Filter by network…",
        ),
        _data_table_html(
            STABLE_HOME_COLS,
            _df_to_row_dicts(stable_df, STABLE_HOME_COLS),
            table_id="js-home-stable",
            empty_msg="Stablecoin preview is unavailable.",
        ),
        _cta_html("/RWA_Stablecoins", "Open full Stablecoins page"),
        _zone_close(source_cap="RWA.xyz stablecoin networks"),
    ]
    parts.append("".join(stable))

    # RWA
    rwa: list[str] = [
        _zone_open(
            section_id="section-onchain",
            badge="RWA",
            title="On-chain Data",
            subtitle="Global overview KPIs and a networks preview from RWA.xyz.",
            zone_class="home-zone--rwa",
        ),
        rwa_snapshot_kpi_html(rwa_kpis),
        '<p class="home-table-caption">Networks preview</p>',
        _search_field_html(
            field_id="js-home-rwa-search",
            label="Filter preview by network name",
            placeholder="Filter by network…",
        ),
        _data_table_html(
            RWA_HOME_COLS,
            _df_to_row_dicts(rwa_df, RWA_HOME_COLS),
            table_id="js-home-rwa",
            empty_msg="On-chain preview is unavailable.",
        ),
        _cta_html("/RWA_Global_Market_Overview", "Open full RWA Market Overview"),
        _zone_close(explore=True, source_cap="RWA.xyz Global Market Overview · parent networks"),
    ]
    parts.append("".join(rwa))

    # ETP
    flow_series = load_farside_flow_series_cached()
    etp_sorted = sorted(etp_rows, key=lambda r: -(r.assets_usd or 0))
    etp_df = build_etp_dataframe(etp_sorted[:HOME_PREVIEW], flow_series=flow_series)
    etp: list[str] = [
        _zone_open(
            section_id="section-markets",
            badge="ETP",
            title="U.S. ETP Market",
            subtitle="U.S.-listed digital-asset ETP snapshot with fund preview.",
            zone_class="home-zone--etp",
        ),
        etp_snapshot_kpi_html(etp_rows),
        '<p class="home-table-caption">Funds preview</p>',
        _search_field_html(
            field_id="js-home-etp-search",
            label="Filter preview by fund name or ticker",
            placeholder="Filter by name or ticker…",
        ),
        _data_table_html(
            ETP_HOME_COLS,
            _df_to_row_dicts(etp_df, ETP_HOME_COLS),
            table_id="js-home-etp",
            empty_msg="ETP preview is unavailable.",
        ),
        _cta_html("/US_Crypto_ETPs", "Open full U.S. ETP page"),
        _zone_close(),
    ]
    parts.append("".join(etp))

    # Crypto
    crypto: list[str] = [
        _zone_open(
            section_id="section-crypto",
            badge="CRY",
            title="Crypto Prices",
            subtitle="Top-line crypto market snapshot and top-50 price preview.",
            zone_class="home-zone--crypto",
        ),
        crypto_snapshot_kpi_html(crypto_rows, crypto_paprika),
        '<p class="home-table-caption">Top coins preview</p>',
        _search_field_html(
            field_id="js-home-crypto-search",
            label="Filter preview by coin name or ticker",
            placeholder="Filter by name or ticker…",
        ),
        _data_table_html(
            CRYPTO_HOME_COLS,
            _crypto_preview_rows(crypto_rows),
            table_id="js-home-crypto",
            empty_msg="Crypto preview is unavailable.",
        ),
        _cta_html("/Crypto_Prices", "Open full Crypto Prices page"),
        _zone_close(source_cap="Spot rows: CoinGecko with CoinCap fallback · total cap: CoinPaprika"),
    ]
    parts.append("".join(crypto))

    return parts


def build_home_body_iframe_html(*, news_rail: str, **zone_data: Any) -> str:
    """News Hub + markets: news sets row height; markets column scrolls internally."""
    from streamlit_site_parity import _cached_iframe_body_stylesheet

    markets = "".join(iter_home_markets_stack_html(**zone_data))
    css = _cached_iframe_body_stylesheet()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
</head>
<body class="page-home site-experience">
<div class="page-shell">
<div class="home-main-split">
<div class="home-markets-stack">{markets}</div>
{news_rail.strip()}
</div>
</div>
<script>
(function () {{
  function applyFilter(input) {{
    var tid = input.getAttribute("data-table-target") || input.id.replace("-search", "");
    var tbody = document.getElementById(tid + "-tbody");
    var toolbar = document.getElementById(input.id + "-toolbar");
    if (!tbody) return;
    var rows = tbody.querySelectorAll("tr");
    var q = (input.value || "").trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (tr) {{
      var blob = (tr.getAttribute("data-search") || tr.textContent || "").toLowerCase();
      var ok = !q || blob.indexOf(q) !== -1;
      tr.style.display = ok ? "" : "none";
      if (ok) shown++;
    }});
    if (toolbar) {{
      toolbar.hidden = !q;
      toolbar.textContent = q ? ("Showing " + shown + " of " + rows.length + " preview rows.") : "";
    }}
  }}
  function bindFilters() {{
    document.querySelectorAll("input.home-preview-filter").forEach(function (input) {{
      if (input.dataset.stBound) return;
      input.dataset.stBound = "1";
      input.addEventListener("input", function () {{ applyFilter(input); }});
    }});
  }}
  function syncHomeSplitHeights() {{
    var rail = document.querySelector(".home-news-rail");
    var markets = document.querySelector(".home-markets-stack");
    var split = document.querySelector(".home-main-split");
    if (!rail || !markets || !split) return;
    var h = rail.offsetHeight;
    if (h < 200) return;
    markets.style.height = h + "px";
    markets.style.maxHeight = h + "px";
    markets.style.overflowY = "auto";
    split.style.minHeight = h + "px";
    split.style.height = "";
    split.style.maxHeight = "";
    split.style.overflow = "";
    var shell = document.querySelector(".page-shell");
    if (shell) {{
      shell.style.height = "";
      shell.style.maxHeight = "";
      shell.style.overflow = "";
    }}
  }}
  window.syncHomeSplitHeights = syncHomeSplitHeights;
  document.querySelectorAll('a[href^="/"]').forEach(function (a) {{
    a.target = "_top";
  }});
  bindFilters();
  syncHomeSplitHeights();
  window.addEventListener("load", function () {{
    bindFilters();
    syncHomeSplitHeights();
  }});
  if (typeof ResizeObserver !== "undefined") {{
    var rail = document.querySelector(".home-news-rail");
    if (rail) new ResizeObserver(syncHomeSplitHeights).observe(rail);
  }}
  [100, 400, 1000].forEach(function (ms) {{ setTimeout(syncHomeSplitHeights, ms); }});
}})();
</script>
</body>
</html>"""


def render_home_body_iframe(*, news_rail: str, **zone_data: Any) -> None:
    """
    Render news + markets in one iframe sized to the News Hub height.

    The markets column matches that height and scrolls internally.
    """
    st.markdown(
        '<span class="home-body-iframe-marker" hidden aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    components.html(
        build_home_body_iframe_html(news_rail=news_rail, **zone_data),
        height=640,
        scrolling=False,
    )


def build_home_markets_iframe_html(**zone_data: Any) -> str:
    """Self-contained markets stack for ``components.html`` (CSS + table filters in iframe)."""
    from streamlit_site_parity import _cached_iframe_home_stylesheet, iframe_auto_height_script

    stack = "".join(iter_home_markets_stack_html(**zone_data))
    css = _cached_iframe_home_stylesheet()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
</head>
<body class="page-home site-experience">
<div class="page-shell home-markets-stack">{stack}</div>
<script>
(function () {{
  function applyFilter(input) {{
    var tid = input.getAttribute("data-table-target") || input.id.replace("-search", "");
    var tbody = document.getElementById(tid + "-tbody");
    var toolbar = document.getElementById(input.id + "-toolbar");
    if (!tbody) return;
    var rows = tbody.querySelectorAll("tr");
    var q = (input.value || "").trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (tr) {{
      var blob = (tr.getAttribute("data-search") || tr.textContent || "").toLowerCase();
      var ok = !q || blob.indexOf(q) !== -1;
      tr.style.display = ok ? "" : "none";
      if (ok) shown++;
    }});
    if (toolbar) {{
      toolbar.hidden = !q;
      toolbar.textContent = q ? ("Showing " + shown + " of " + rows.length + " preview rows.") : "";
    }}
  }}
  function bindFilters() {{
    document.querySelectorAll("input.home-preview-filter").forEach(function (input) {{
      if (input.dataset.stBound) return;
      input.dataset.stBound = "1";
      input.addEventListener("input", function () {{ applyFilter(input); }});
    }});
  }}
  bindFilters();
  window.addEventListener("load", bindFilters);
}})();
</script>
{iframe_auto_height_script(root_selector=".home-markets-stack")}
</body>
</html>"""


def render_home_markets_stack(target: Any, **zone_data: Any) -> None:
    """
    Render the markets column as one auto-height iframe.

    Streamlit Cloud often fails to style sibling ``st.html`` / markdown blocks with the
    parent stylesheet; a self-contained iframe matches the static GitHub Pages DOM.
    """
    marker = getattr(target, "markdown", None)
    if marker:
        marker(
            '<span class="home-markets-iframe" hidden aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
    components.html(
        build_home_markets_iframe_html(**zone_data),
        height=3200,
        scrolling=False,
    )


HOME_PREVIEW_FILTER_JS = """
<script>
(function () {
  var doc = window.parent && window.parent.document ? window.parent.document : document;
  function applyFilter(input) {
    var tid = input.getAttribute("data-table-target") || input.id.replace("-search", "");
    var tbody = doc.getElementById(tid + "-tbody");
    var toolbar = doc.getElementById(input.id + "-toolbar");
    if (!tbody) return;
    var rows = tbody.querySelectorAll("tr");
    var q = (input.value || "").trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (tr) {
      var blob = (tr.getAttribute("data-search") || tr.textContent || "").toLowerCase();
      var ok = !q || blob.indexOf(q) !== -1;
      tr.style.display = ok ? "" : "none";
      if (ok) shown++;
    });
    if (toolbar) {
      toolbar.hidden = !q;
      toolbar.textContent = q ? ("Showing " + shown + " of " + rows.length + " preview rows.") : "";
    }
  }
  function bind() {
    doc.querySelectorAll("input.home-preview-filter").forEach(function (input) {
      if (input.dataset.stBound) return;
      input.dataset.stBound = "1";
      input.addEventListener("input", function () { applyFilter(input); });
    });
  }
  bind();
  setTimeout(bind, 400);
})();
</script>
"""


def load_home_zone_data(etp_ua: str) -> dict[str, Any]:
    """Fetch all datasets needed for the static home HTML stack."""
    from crypto_etps.widgets import load_crypto_etps_cached
    from crypto_prices.widgets import load_crypto_snapshot_cached
    from rwa_league.widgets import load_rwa_global_market_cached, load_rwa_stablecoins_cached

    mmfs, net_m, plat_m, kpis_m, err_m = build_curated_mmf_dashboard_data()
    rows_sc, plat_sc, kpis_sc, err_sc = load_rwa_stablecoins_cached()
    rows_rwa, kpis_rwa, err_rwa = load_rwa_global_market_cached()
    etp_data = load_crypto_etps_cached(etp_ua)
    crypto_rows, paprika, _, _ = load_crypto_snapshot_cached()

    stable_df = build_stablecoin_network_dataframe(list(rows_sc)) if rows_sc else pd.DataFrame()
    rwa_df = build_rwa_dataframe(list(rows_rwa)) if rows_rwa else pd.DataFrame()

    return {
        "mmf_kpis": kpis_m,
        "mmf_funds": mmfs,
        "mmf_err": err_m,
        "stable_kpis": kpis_sc,
        "stable_df": stable_df,
        "stable_err": err_sc,
        "rwa_kpis": kpis_rwa,
        "rwa_df": rwa_df,
        "rwa_err": err_rwa,
        "etp_rows": etp_data.rows,
        "etp_err": etp_data.error,
        "crypto_rows": crypto_rows,
        "crypto_paprika": paprika,
    }
