"""Infer exposure from issuer, fund name, and ticker rules (spot vs futures vs options vs basket)."""

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
    "franklin templeton",
    "wisdomtree",
    "coinshares",
    "volatility shares",
    "canary",
)

_FUTURES_ISSUERS: tuple[str, ...] = ("proshares",)

_FUTURES_NAME_TERMS: tuple[str, ...] = (
    "strategy",
    "futures",
    "ultra",
    "ultrashort",
    "leveraged",
    "short",
    "inverse",
)

# Covered calls, options overlays, etc. — not spot single-asset funds.
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
)

# If the fund name includes any of these (substring), we treat it as naming a specific crypto asset.
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


def _name_has_options_term(name: str) -> bool:
    n = _norm(name)
    if any(p in n for p in _OPTIONS_NAME_PHRASES):
        return True
    # Standalone "options" / "option" as a product type (avoid matching "optional").
    if re.search(r"\boptions\b", n):
        return True
    if re.search(r"\boption\b", n) and "optional" not in n:
        return True
    return False


def _name_has_futures_term(name: str) -> bool:
    n = _norm(name)
    if any(term in n for term in _FUTURES_NAME_TERMS):
        return True
    return bool(re.search(r"(^|\s)(?:2x|-2x)(\s|$)", n))


def _ticker_looks_futures(ticker: str) -> bool:
    t = (ticker or "").strip().upper()
    if not t:
        return False
    if t in _FUTURES_TICKERS:
        return True
    # Avoid single-letter symbols matching the suffix class (e.g. "X").
    if len(t) < 2:
        return False
    return bool(re.search(r"(?:U|D|X|S|I|2X|-2X)$", t))


def _name_mentions_named_crypto(name: str) -> bool:
    """True if the fund name appears to reference a specific digital asset (not generic 'crypto')."""
    n = _norm(name)
    if any(s in n for s in _NAMED_CRYPTO_SUBSTRINGS):
        return True
    # Standalone "ether" (e.g. staked ether) but not "whether" / "ethereum" already covered.
    if re.search(r"\bether\b", n):
        return True
    # Ticker-like token mentions occasionally appear in names.
    if re.search(r"\bxrp\b", n):
        return True
    if re.search(r"\bsol\b", n):
        return True
    return False


def infer_spot_futures_exposure(symbol: str, name: str, issuer: str) -> str:
    """Return ``Spot``, ``Futures``, ``Options``, or ``Basket``."""
    sym = (symbol or "").strip().upper()
    nm = name or ""
    iss = _norm(issuer)
    n = _norm(nm)

    if sym == "EETH":
        return "Futures"
    if any(x in iss for x in _FUTURES_ISSUERS):
        return "Futures"
    if _name_has_options_term(nm):
        return "Options"
    if _name_has_futures_term(nm):
        return "Futures"
    if _ticker_looks_futures(sym):
        return "Futures"
    if sym in _SPOT_TICKERS:
        return "Spot"
    if "basket" in n:
        return "Basket"
    if any(x in iss for x in _SPOT_ISSUERS):
        if not _name_mentions_named_crypto(nm):
            return "Basket"
        return "Spot"
    return "Futures"
