"""Classify top crypto tickers for table categories and market-structure KPIs."""

from __future__ import annotations

from typing import Any

# Slug stored in JSON; ``label`` is display text for tabs and table badges.
CATEGORY_LABELS: dict[str, str] = {
    "l1": "Layer 1",
    "stablecoin": "Stablecoin",
    "cex": "CEX",
    "defi": "DeFi",
    "meme": "Meme",
    "rwa": "RWA / Tokenized",
    "other": "Other",
}

CATEGORY_TAB_ORDER: tuple[str, ...] = (
    "all",
    "l1",
    "stablecoin",
    "cex",
    "defi",
    "meme",
    "rwa",
    "other",
)

STABLECOIN_SYMBOLS: frozenset[str] = frozenset(
    {
        "USDT",
        "USDC",
        "USDS",
        "DAI",
        "USDE",
        "PYUSD",
        "USDG",
        "USD1",
        "USDF",
        "USDY",
        "USYC",
        "TUSD",
        "FRAX",
        "LUSD",
        "GUSD",
        "FDUSD",
        "EURC",
    }
)

_SYMBOL_CATEGORY: dict[str, str] = {
    "BTC": "l1",
    "ETH": "l1",
    "SOL": "l1",
    "ADA": "l1",
    "TRX": "l1",
    "BCH": "l1",
    "TON": "l1",
    "XLM": "l1",
    "SUI": "l1",
    "LTC": "l1",
    "AVAX": "l1",
    "HBAR": "l1",
    "NEAR": "l1",
    "DOT": "l1",
    "XMR": "l1",
    "ZEC": "l1",
    "TAO": "l1",
    "CC": "l1",
    "ATOM": "l1",
    "ICP": "l1",
    "APT": "l1",
    "FIL": "l1",
    "ETC": "l1",
    "STX": "l1",
    "INJ": "l1",
    "SEI": "l1",
    "TIA": "l1",
    "BNB": "cex",
    "OKB": "cex",
    "CRO": "cex",
    "LEO": "cex",
    "WBT": "cex",
    "KCS": "cex",
    "GT": "cex",
    "DOGE": "meme",
    "SHIB": "meme",
    "PEPE": "meme",
    "PI": "meme",
    "M": "meme",
    "RAIN": "meme",
    "BONK": "meme",
    "FLOKI": "meme",
    "WIF": "meme",
    "LINK": "defi",
    "UNI": "defi",
    "AAVE": "defi",
    "MKR": "defi",
    "LDO": "defi",
    "CRV": "defi",
    "ONDO": "rwa",
    "BUIDL": "rwa",
    "USDY": "rwa",
    "USYC": "rwa",
    "XAUT": "rwa",
    "PAXG": "rwa",
    "FIGR_HELOC": "rwa",
    "USDT": "stablecoin",
    "USDC": "stablecoin",
    "USDS": "stablecoin",
    "DAI": "stablecoin",
    "USDE": "stablecoin",
    "PYUSD": "stablecoin",
    "USDG": "stablecoin",
    "USD1": "stablecoin",
    "USDF": "stablecoin",
    "HYPE": "other",
    "WLFI": "other",
    "XRP": "l1",
}


def crypto_category(symbol: str, name: str = "") -> str:
    sym = (symbol or "").strip().upper()
    if sym in _SYMBOL_CATEGORY:
        return _SYMBOL_CATEGORY[sym]
    if sym in STABLECOIN_SYMBOLS:
        return "stablecoin"
    low_name = (name or "").lower()
    if "stablecoin" in low_name or sym.startswith("USD") and len(sym) <= 6:
        return "stablecoin"
    if "meme" in low_name or sym in ("MEME",):
        return "meme"
    return "other"


def category_label(slug: str) -> str:
    return CATEGORY_LABELS.get((slug or "").strip(), CATEGORY_LABELS["other"])


def _cap(row: dict[str, Any]) -> float:
    try:
        v = float(row.get("market_cap_usd") or 0)
    except (TypeError, ValueError):
        return 0.0
    return v if v > 0 else 0.0


def compute_market_structure(
    rows: list[dict[str, Any]],
    *,
    total_market_cap_usd: float | None,
) -> dict[str, Any]:
    """
    BTC dominance vs CoinPaprika total; stablecoin share vs sum of top-list market caps.
    """
    top50_cap = sum(_cap(r) for r in rows)
    btc_cap = _cap(next((r for r in rows if str(r.get("symbol", "")).upper() == "BTC"), {}))
    stable_cap = sum(
        _cap(r) for r in rows if crypto_category(str(r.get("symbol") or ""), str(r.get("name") or "")) == "stablecoin"
    )

    btc_dom_pct: float | None = None
    if total_market_cap_usd and total_market_cap_usd > 0 and btc_cap > 0:
        btc_dom_pct = (btc_cap / total_market_cap_usd) * 100.0

    stable_top50_pct: float | None = None
    if top50_cap > 0 and stable_cap > 0:
        stable_top50_pct = (stable_cap / top50_cap) * 100.0

    return {
        "btc_dominance_pct": round(btc_dom_pct, 2) if btc_dom_pct is not None else None,
        "stablecoin_share_top50_pct": round(stable_top50_pct, 2) if stable_top50_pct is not None else None,
        "top50_market_cap_usd": top50_cap,
        "stablecoin_market_cap_usd": stable_cap,
        "btc_market_cap_usd": btc_cap,
    }


def _cap_then_from_row(row: dict[str, Any]) -> float:
    """Rough 30d-ago market cap from current cap and CoinGecko 30d % (supply held ~constant)."""
    cap = _cap(row)
    if cap <= 0:
        return 0.0
    pct = row.get("pct_30d")
    if pct is None:
        return cap
    try:
        p = float(pct)
    except (TypeError, ValueError):
        return cap
    if p <= -99.9:
        return cap
    return cap / (1.0 + p / 100.0)


def btc_dominance_change_pct_1m(
    rows: list[dict[str, Any]],
    *,
    total_market_cap_now: float | None,
    total_market_cap_then: float | None,
) -> float | None:
    """
    Approximate 1M % change in BTC dominance (ratio of BTC cap to CoinPaprika total).
    Uses CoinPaprika total cap series endpoints for total_then/total_now and BTC row 30d % for BTC cap then.
    """
    if (
        not total_market_cap_now
        or total_market_cap_now <= 0
        or not total_market_cap_then
        or total_market_cap_then <= 0
    ):
        return None
    btc_row = next((r for r in rows if str(r.get("symbol", "")).upper() == "BTC"), None)
    if not btc_row:
        return None
    cap_now = _cap(btc_row)
    cap_then = _cap_then_from_row(btc_row)
    if cap_now <= 0 or cap_then <= 0:
        return None
    dom_now = (cap_now / total_market_cap_now) * 100.0
    dom_then = (cap_then / total_market_cap_then) * 100.0
    if dom_then <= 0:
        return None
    return ((dom_now / dom_then) - 1.0) * 100.0


def stablecoin_share_change_pct_1m(rows: list[dict[str, Any]]) -> float | None:
    """
    Approximate 1M % change in stablecoin share of top-list market cap, using each row's 30d % on caps.
    """
    top50_now = sum(_cap(r) for r in rows)
    top50_then = sum(_cap_then_from_row(r) for r in rows)
    if top50_now <= 0 or top50_then <= 0:
        return None
    stable_now = sum(
        _cap(r)
        for r in rows
        if crypto_category(str(r.get("symbol") or ""), str(r.get("name") or "")) == "stablecoin"
    )
    stable_then = sum(
        _cap_then_from_row(r)
        for r in rows
        if crypto_category(str(r.get("symbol") or ""), str(r.get("name") or "")) == "stablecoin"
    )
    if stable_now <= 0 or stable_then <= 0:
        return None
    sh_now = (stable_now / top50_now) * 100.0
    sh_then = (stable_then / top50_then) * 100.0
    if sh_then <= 0:
        return None
    return ((sh_now / sh_then) - 1.0) * 100.0


def structure_kpi_dicts(
    structure: dict[str, Any],
    *,
    btc_dom_delta_pct_1m: float | None = None,
    stable_share_delta_pct_1m: float | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    dom = structure.get("btc_dominance_pct")
    stb = structure.get("stablecoin_share_top50_pct")
    btc_dom: dict[str, object] = {
        "label": "BTC dominance",
        "value_display": f"{dom:.1f}%" if dom is not None else "—",
    }
    if btc_dom_delta_pct_1m is not None:
        btc_dom["delta"] = {"pct": round(btc_dom_delta_pct_1m, 4), "window": "1M"}
    stable: dict[str, object] = {
        "label": "Stablecoin share",
        "value_display": f"{stb:.1f}%" if stb is not None else "—",
    }
    if stable_share_delta_pct_1m is not None:
        stable["delta"] = {"pct": round(stable_share_delta_pct_1m, 4), "window": "1M"}
    return btc_dom, stable


def story_callout_payload() -> dict[str, object]:
    return {
        "title": "How to read this snapshot",
        "bullets": [
            "KPI strip: Total market cap and its 1M % come from CoinPaprika. BTC dominance compares Bitcoin’s market cap to that total, with an approximate 1M % using the same total-cap window and BTC’s 30d cap change from this list. Stablecoin share is stablecoin cap vs this top-50 list, with an approximate 1M % from row-level 30d cap changes.",
            "Chart: TradingView TOTAL tracks a broad crypto market-cap index (about the top 125 coins). Use it for trend context; its level can differ from the KPI total because sources and universes differ.",
            "Table: Spot prices, 1M % changes, and categories use the top-50 CoinGecko list (CoinCap fallback when 30-day change is missing). Hover tickers for short About summaries.",
        ],
    }
