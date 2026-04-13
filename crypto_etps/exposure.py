"""Infer spot vs. futures exposure from issuer, fund name, and ticker rules."""

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
    return bool(re.search(r"(?:U|D|X|S|I|2X|-2X)$", t))


def infer_spot_futures_exposure(symbol: str, name: str, issuer: str) -> str:
    """Return ``Spot`` or ``Futures`` using issuer/name/ticker rules."""
    sym = (symbol or "").strip().upper()
    nm = name or ""
    iss = _norm(issuer)

    if sym == "EETH":
        return "Futures"
    if any(x in iss for x in _FUTURES_ISSUERS):
        return "Futures"
    if _name_has_futures_term(nm):
        return "Futures"
    if _ticker_looks_futures(sym):
        return "Futures"
    if sym in _SPOT_TICKERS:
        return "Spot"
    if any(x in iss for x in _SPOT_ISSUERS):
        return "Spot"
    return "Futures"
