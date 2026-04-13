"""Infer exposure from issuer, fund name, and ticker rules (Spot vs Futures for the table)."""

from __future__ import annotations

import re

_SPOT_ISSUERS: tuple[str, ...] = (
    "blackrock",
    "ishares",
    "fidelity",
    "grayscale",
    "bitwise",
    "ark",
    "21shares",
    "vaneck",
    "invesco galaxy",
    "invesco",
    "franklin templeton",
    "franklin",
    "wisdomtree",
    "coinshares",
    "volatility shares",
    "canary",
)

_FUTURES_ISSUERS: tuple[str, ...] = ("proshares",)

# Leveraged / inverse / futures-structure (avoid bare "strategy" — too many false positives).
_FUTURES_NAME_TERMS: tuple[str, ...] = (
    "futures",
    "ultra",
    "ultrashort",
    "leveraged",
    "inverse",
)

# Covered calls, options overlays, premium — not single-asset spot.
_OPTIONS_NAME_PHRASES: tuple[str, ...] = (
    "covered call",
    "covered calls",
    "buy-write",
    "buy write",
    "put write",
    "call write",
    "options income",
    "option income",
    "options strategy",
    "option strategy",
    "call option",
    "put option",
    "collar fund",
    "collar strategy",
    "put spread",
    "call spread",
    "synthetic",
    "premium income",
    "yield enhancement",
    "write strategy",
)

# Multi-asset / broad index — not a single-coin spot product (name-only; works if issuer is missing).
_BASKET_INDEX_PHRASES: tuple[str, ...] = (
    "basket",
    "crypto index",
    "digital asset index",
    "digital assets index",
    "multi-asset",
    "multi asset",
    "multi-crypto",
    "multi crypto",
    "fund of funds",
    "top 10",
    "top 5",
    "broad crypto",
    "broad digital",
)

_NAMED_CRYPTO_SUBSTRINGS: tuple[str, ...] = (
    "bitcoin",
    "btc",
    "ethereum",
    "solana",
    "xrp",
    "ripple",
    "chainlink",
    "dogecoin",
    "doge",
    "avalanche",
    "litecoin",
    "stellar",
    "cardano",
    "polygon",
    "polkadot",
    "cosmos",
    "shiba",
    "uniswap",
    "aave",
    "staked ethereum",
    "staked ether",
    "staked eth",
)

_SPOT_TICKERS: set[str] = {
    "BTC", "IBIT", "FBTC", "BITB", "ARKB", "HODL", "BTCO", "BRRR", "EZBC", "BTCW",
    "ETHA", "ETH", "ETHE", "FETH", "ETHV", "QETH", "EZET", "ETHB", "TETH",
    "BSOL", "GSOL", "FSOL", "VSOL", "SOEZ", "SOLC", "TSOL",
    "XRP", "XRPC", "XRPZ", "XRPI", "TOXR", "XRPR",
    "GLNK", "CLNK",
    "GSUI", "TSUI",
    "GAVA",
    "GDOG", "TDOG", "BWOW",
}

_FUTURES_TICKERS: set[str] = {"BITO", "BITX", "BITI", "SBIT", "ETHU", "ETHT", "ETHD", "EETH"}


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def _name_implies_basket_or_broad_index(name: str) -> bool:
    """Multi-coin / index / basket products (issuer-independent)."""
    n = _norm(name)
    if any(p in n for p in _BASKET_INDEX_PHRASES):
        return True
    # e.g. "Bitwise 10 Crypto Index ETF"
    if re.search(r"\b\d{1,2}\s+crypto\b", n):
        return True
    # "Franklin Crypto Index" / "… Crypto Index …"
    if "crypto" in n and "index" in n:
        return True
    return False


def _name_has_options_term(name: str) -> bool:
    n = _norm(name)
    if any(p in n for p in _OPTIONS_NAME_PHRASES):
        return True
    # Typo-tolerant covered call
    if re.search(r"cover[ea]?d\s+calls?", n):
        return True
    if re.search(r"\boptions\b", n):
        return True
    if re.search(r"\boption\b", n) and "optional" not in n:
        return True
    return False


def _name_has_futures_or_leverage_term(name: str) -> bool:
    n = _norm(name)
    if any(term in n for term in _FUTURES_NAME_TERMS):
        return True
    if re.search(r"(^|\s)(?:2x|-2x)(\s|$)", n):
        return True
    if re.search(r"\bshort\s+bitcoin\b", n) or re.search(r"\bshort\s+ether", n):
        return True
    if re.search(r"\bshort\s+btc\b", n):
        return True
    # "Inverse Bitcoin", etc.
    if re.search(r"\binverse\s+(bitcoin|btc|ether|ethereum|crypto)\b", n):
        return True
    return False


def _ticker_looks_futures(ticker: str) -> bool:
    t = (ticker or "").strip().upper()
    if not t:
        return False
    if t in _FUTURES_TICKERS:
        return True
    if len(t) < 2:
        return False
    return bool(re.search(r"(?:U|D|X|S|I|2X|-2X)$", t))


def _name_mentions_named_crypto(name: str) -> bool:
    """True if the fund name references a specific digital asset (not generic 'crypto')."""
    n = _norm(name)
    if any(s in n for s in _NAMED_CRYPTO_SUBSTRINGS):
        return True
    if re.search(r"\bether\b", n):
        return True
    if re.search(r"\bxrp\b", n):
        return True
    if re.search(r"\bsol\b", n):
        return True
    return False


def infer_spot_futures_exposure(symbol: str, name: str, issuer: str) -> str:
    """Return ``Spot`` or ``Futures`` only (table column).

    Multi-asset index, basket, and options-overlay names are **Futures**, not Spot.
    """
    sym = (symbol or "").strip().upper()
    nm = name or ""
    iss = _norm(issuer)
    n = _norm(nm)

    if sym == "EETH":
        return "Futures"
    if any(x in iss for x in _FUTURES_ISSUERS):
        return "Futures"
    # Broad index / basket — not single-asset spot; show as Futures in Exposure.
    if _name_implies_basket_or_broad_index(nm):
        return "Futures"
    if _name_has_options_term(nm):
        return "Futures"
    if _name_has_futures_or_leverage_term(nm):
        return "Futures"
    if _ticker_looks_futures(sym):
        return "Futures"
    if sym in _SPOT_TICKERS:
        return "Spot"
    if any(x in iss for x in _SPOT_ISSUERS):
        if not _name_mentions_named_crypto(nm):
            return "Futures"
        return "Spot"
    return "Futures"
