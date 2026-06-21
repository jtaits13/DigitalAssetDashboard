"""Crypto price snapshot widgets aligned with static_home crypto zones."""

from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd
import requests
import streamlit as st

from crypto_categories import category_label, crypto_category
from crypto_etps.client import format_usd_compact
from home_layout import KPI_WINDOW_NOTE_CSS, STREAMLIT_TABLE_UNIFY_CSS
from price_ticker import TICKER_COUNT, fetch_top_crypto_tickers

COINPAPRIKA_GLOBAL_URL = "https://api.coinpaprika.com/v1/global"
COINPAPRIKA_MARKET_OVERVIEW_TOTAL_30D_URL = "https://coinpaprika.com/market-overview/data/total/30d/"

WIDGET_CSS = """
<style>
.crypto-kpi-wrap {
    background: #ffffff;
    border: 1px solid #C7D8E8;
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    padding: 0.65rem 0.9rem 0.55rem;
    margin: 0.45rem 0 0.9rem 0;
}
.crypto-kpi-row { display: flex; flex-wrap: wrap; gap: 0.75rem 1.25rem; }
.crypto-kpi-cell { min-width: 7rem; }
.crypto-kpi-label {
    display: block;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #64748b;
    font-weight: 600;
}
.crypto-kpi-val {
    display: block;
    font-size: 1.05rem;
    font-weight: 700;
    color: #1a3d5c;
}
.crypto-kpi-delta { font-size: 0.82rem; font-weight: 650; margin-left: 0.15rem; }
.crypto-kpi-delta--up { color: #28794E; }
.crypto-kpi-delta--down { color: #dc2626; }
.crypto-kpi-delta--na { color: #94a3b8; }
</style>
"""


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


def _find_row(rows: list[dict[str, Any]], symbol: str) -> dict[str, Any] | None:
    target = symbol.strip().upper()
    for row in rows:
        if str(row.get("symbol", "")).strip().upper() == target:
            return row
    return None


def _delta_html(pct: object, window: str = "1M") -> str:
    try:
        num = float(pct) if pct is not None else None
    except (TypeError, ValueError):
        num = None
    if num is None:
        return "<span class='crypto-kpi-delta crypto-kpi-delta--na'>—</span>"
    sign = "+" if num >= 0 else ""
    cls = "crypto-kpi-delta--up" if num >= 0 else "crypto-kpi-delta--down"
    win = f" {escape(window)}" if window else ""
    return (
        f"<span class='crypto-kpi-delta {cls}'>{sign}{num:.2f}%{win}</span>"
    )


def _fetch_coinpaprika_total_snapshot() -> tuple[dict[str, float], str | None]:
    headers = {"Accept": "application/json", "User-Agent": "DigitalAssetsDashboard/1.0"}
    out: dict[str, float] = {}
    errs: list[str] = []

    try:
        resp = requests.get(COINPAPRIKA_GLOBAL_URL, headers=headers, timeout=25)
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, dict):
            market_cap_usd = payload.get("market_cap_usd")
            if market_cap_usd is not None:
                out["total_market_cap_usd"] = float(market_cap_usd)
    except (requests.RequestException, ValueError, TypeError) as exc:
        errs.append(f"CoinPaprika global: {type(exc).__name__}")

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
                        values.append(float(point[1]))
                    except (TypeError, ValueError):
                        continue

        if len(values) >= 2:
            first_val = values[0]
            last_val = values[-1]
            out["total_market_cap_usd_30d_ago"] = first_val
            out.setdefault("total_market_cap_usd", last_val)
            if first_val > 0:
                out["market_cap_change_pct_1m"] = ((last_val - first_val) / first_val) * 100.0
        else:
            errs.append("CoinPaprika 30d series unavailable.")
    except (requests.RequestException, ValueError, TypeError) as exc:
        errs.append(f"CoinPaprika overview: {type(exc).__name__}")

    return out, "; ".join(errs) if errs else None


@st.cache_data(ttl=300, show_spinner=False)
def load_crypto_snapshot_cached(_schema: int = 2) -> tuple[list[dict[str, Any]], dict[str, float], str | None, str | None]:
    rows, err, src = fetch_top_crypto_tickers(TICKER_COUNT)
    row_dicts = [dict(r) for r in rows]
    paprika, paprika_err = _fetch_coinpaprika_total_snapshot()
    return row_dicts, paprika, err, paprika_err or src


def clear_crypto_snapshot_cache() -> None:
    load_crypto_snapshot_cached.clear()


def render_crypto_kpi_row(
    rows: list[dict[str, Any]],
    paprika: dict[str, float],
    *,
    include_styles: bool = True,
) -> None:
    if include_styles:
        st.markdown(WIDGET_CSS + KPI_WINDOW_NOTE_CSS, unsafe_allow_html=True)

    total_cap = paprika.get("total_market_cap_usd")
    cap_pct = paprika.get("market_cap_change_pct_1m")
    cap_display = format_usd_compact(total_cap) if total_cap else "—"

    btc = _find_row(rows, "BTC")
    eth = _find_row(rows, "ETH")

    cells = [
        ("Total market cap", cap_display, _delta_html(cap_pct, "1M")),
        ("BTC price", _fmt_crypto_price(btc.get("price_usd") if btc else None), _delta_html(btc.get("pct_30d") if btc else None, "1M")),
        ("ETH price", _fmt_crypto_price(eth.get("price_usd") if eth else None), _delta_html(eth.get("pct_30d") if eth else None, "1M")),
    ]
    parts: list[str] = []
    for label, val, delta in cells:
        val_html = val if isinstance(val, str) and val.startswith("<") else escape(str(val))
        parts.append(
            "<div class='crypto-kpi-cell'>"
            f"<span class='crypto-kpi-label'>{escape(label)}</span>"
            f"<span class='crypto-kpi-val'>{val_html}</span>"
            f"{delta}"
            "</div>"
        )
    st.html(f"<div class='crypto-kpi-wrap'><div class='crypto-kpi-row'>{''.join(parts)}</div></div>")


def _build_preview_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    out_rows: list[dict[str, str]] = []
    for i, r in enumerate(rows, start=1):
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
        out_rows.append(
            {
                "Rank": rank_num,
                "Ticker": sym,
                "Coin": name,
                "Category": category_label(cat),
                "Price": _fmt_crypto_price(r.get("price_usd")),
                "1M %": f"{float(pct):+.2f}%" if pct is not None else "—",
                "Market Cap": format_usd_compact(float(cap)) if cap is not None else "—",
            }
        )
    return pd.DataFrame(out_rows)


def _filter_rows(rows: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    tokens = [t.lower() for t in query.split() if t.strip()]
    if not tokens:
        return list(rows)
    out: list[dict[str, Any]] = []
    for r in rows:
        blob = " ".join(
            str(r.get(k) or "")
            for k in ("symbol", "name")
        ).lower()
        cat = category_label(crypto_category(str(r.get("symbol") or ""), str(r.get("name") or ""))).lower()
        blob = f"{blob} {cat}"
        if all(tok in blob for tok in tokens):
            out.append(r)
    return out


def show_crypto_home_zone(
    *,
    zone_layout: bool = False,
    preview_rows: int = 5,
) -> None:
    """Home crypto zone: KPI strip + searchable preview table."""
    if not zone_layout:
        st.markdown(WIDGET_CSS + KPI_WINDOW_NOTE_CSS + STREAMLIT_TABLE_UNIFY_CSS, unsafe_allow_html=True)

    with st.spinner("Loading crypto prices…"):
        rows, paprika, err, src_note = load_crypto_snapshot_cached()

    if err and not rows:
        st.warning(err)
        return

    render_crypto_kpi_row(rows, paprika, include_styles=zone_layout)

    st.markdown('<p class="home-table-caption">Top coins preview</p>', unsafe_allow_html=True)
    q = st.text_input(
        "Filter preview by coin name or ticker",
        "",
        key="crypto_home_search",
        placeholder="Filter by name or ticker…",
        label_visibility="collapsed",
    )
    filtered = _filter_rows(rows, q.strip())
    if q.strip():
        st.caption(f"Showing {min(preview_rows, len(filtered))} of {len(filtered)} matches (top {preview_rows} preview).")
    display = filtered[:preview_rows]
    df = _build_preview_dataframe(display)
    st.dataframe(df, use_container_width=True, hide_index=True, height=min(320, 44 + len(df) * 35))

    if st.button(
        "Open full Crypto Prices page",
        key="see_full_crypto_prices",
        use_container_width=True,
        type="primary",
    ):
        st.switch_page("pages/Crypto_Prices.py")

    if src_note:
        st.caption(f"Spot rows: {src_note}")


def show_crypto_prices_page(*, zone_layout: bool = False) -> None:
    """Full crypto prices page body (top 50 table + KPI strip)."""
    if not zone_layout:
        st.markdown(WIDGET_CSS + KPI_WINDOW_NOTE_CSS + STREAMLIT_TABLE_UNIFY_CSS, unsafe_allow_html=True)

    with st.spinner("Loading crypto prices…"):
        rows, paprika, err, src_note = load_crypto_snapshot_cached()

    if err and not rows:
        st.warning(err)
        return

    render_crypto_kpi_row(rows, paprika, include_styles=False)

    q = st.text_input(
        "Search coins",
        "",
        key="crypto_full_search",
        placeholder="Filter by name, ticker, or category…",
    )
    filtered = _filter_rows(rows, q.strip())
    if q.strip():
        st.caption(f"Showing {len(filtered)} of {len(rows)} coins.")
    else:
        st.caption(f"Top {len(filtered)} cryptocurrencies by market cap.")

    df = _build_preview_dataframe(filtered)
    st.dataframe(df, use_container_width=True, hide_index=True, height=min(900, 44 + len(df) * 35))

    if src_note:
        st.caption(
            "Total market cap and 1M change from CoinPaprika; spot prices from CoinGecko with CoinCap fallback. "
            f"({src_note})"
        )
