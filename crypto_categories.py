"""Classify top crypto tickers for table categories and market-structure KPIs."""

from __future__ import annotations

from typing import Any

# Slug stored in JSON; ``label`` is display text for tabs and table badges.
CATEGORY_LABELS: dict[str, str] = {
    "l1": "Layer 1",
    "stablecoin": "Stablecoin",
    "exchange": "Exchange",
    "defi": "DeFi",
    "meme": "Meme",
    "rwa": "RWA / Tokenized",
    "other": "Other",
}

CATEGORY_TAB_ORDER: tuple[str, ...] = (
    "all",
    "l1",
    "stablecoin",
    "exchange",
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
    "BNB": "exchange",
    "OKB": "exchange",
    "CRO": "exchange",
    "LEO": "exchange",
    "WBT": "exchange",
    "KCS": "exchange",
    "GT": "exchange",
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


def structure_kpi_dicts(structure: dict[str, Any]) -> tuple[dict[str, object], dict[str, object]]:
    dom = structure.get("btc_dominance_pct")
    stb = structure.get("stablecoin_share_top50_pct")
    btc_dom: dict[str, object] = {
        "label": "BTC dominance",
        "value_display": f"{dom:.1f}%" if dom is not None else "—",
        "subnote": "BTC market cap ÷ CoinPaprika total market cap",
    }
    stable: dict[str, object] = {
        "label": "Stablecoin share",
        "value_display": f"{stb:.1f}%" if stb is not None else "—",
        "subnote": "Stablecoin market cap ÷ top-50 list market cap",
    }
    return btc_dom, stable


def story_callout_payload() -> dict[str, object]:
    return {
        "title": "How to read this snapshot",
        "bullets": [
            "KPI strip: Total market cap and its 1M % come from CoinPaprika. BTC and ETH prices and 1M % come from CoinGecko spot data. BTC dominance compares Bitcoin’s market cap to the CoinPaprika total; stablecoin share is the portion of this page’s top-50 list held by stablecoins.",
            "Chart: TradingView TOTAL tracks a broad crypto market-cap index (about the top 125 coins). Use it for trend context; its level can differ from the KPI total because sources and universes differ.",
            "Table: Spot prices, 1M % changes, and categories use the top-50 CoinGecko list (CoinCap fallback when 30-day change is missing). Hover tickers for short About summaries.",
        ],
    }
