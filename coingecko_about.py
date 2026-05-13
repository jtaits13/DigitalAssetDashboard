"""Summarize CoinGecko coin ``description.en`` for short UI blurbs (tooltips)."""

from __future__ import annotations

import html as html_module
import os
import re
import time
from typing import Any

import requests

# CoinGecko id for a ticker when markets rows omit ``coin_id`` (e.g. CoinCap fallback) or for robustness.
SYMBOL_TO_COINGECKO_ID: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "BNB": "binancecoin",
    "SOL": "solana",
    "USDC": "usd-coin",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "ADA": "cardano",
    "TRX": "tron",
    "AVAX": "avalanche-2",
    "SHIB": "shiba-inu",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "POL": "polygon-ecosystem-token",
    "TON": "toncoin",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "NEAR": "near",
    "APT": "aptos",
    "UNI": "uniswap",
    "ICP": "internet-computer",
    "ATOM": "cosmos",
    "FIL": "filecoin",
    "ETC": "ethereum-classic",
    "XLM": "stellar",
    "XMR": "monero",
    "OKB": "okb",
    "HBAR": "hedera-hashgraph",
    "VET": "vechain",
    "CRO": "crypto-com-chain",
    "AAVE": "aave",
    "RENDER": "render-token",
    "MNT": "mantle",
    "ALGO": "algorand",
    "QNT": "quant-network",
    "ARB": "arbitrum",
    "OP": "optimism",
    "STX": "blockstack",
    "IMX": "immutable-x",
    "INJ": "injective-protocol",
    "MKR": "maker",
    "GRT": "the-graph",
    "SUI": "sui",
    "PEPE": "pepe",
    "FET": "fetch-ai",
    "RNDR": "render-token",
    "THETA": "theta-token",
    "FTM": "fantom",
    "EOS": "eos",
    "XTZ": "tezos",
    "FLOW": "flow",
    "SAND": "the-sandbox",
    "MANA": "decentraland",
    "AXS": "axie-infinity",
    "CHZ": "chiliz",
    "BEAM": "beam-2",
    "LDO": "lido-dao",
    "TIA": "celestia",
    "SEI": "sei-network",
    "WLD": "worldcoin-wld",
}

# Used when CoinGecko description API fails (rate limits in CI) so the static site still shows tooltips.
STATIC_ABOUT_BLURBS: dict[str, str] = {
    "bitcoin": (
        "Bitcoin is a decentralized digital currency and payment network, launched in 2009, "
        "often used as a store-of-value and settlement asset. Spot Bitcoin ETFs and corporate treasuries "
        "have broadened traditional access and adoption."
    ),
    "ethereum": (
        "Ethereum is a programmable blockchain for smart contracts and decentralized applications. "
        "Ether (ETH) pays transaction fees, secures the network via staking, and is widely used in DeFi and digital assets."
    ),
    "tether": (
        "Tether (USDT) is a widely used stablecoin designed to track the U.S. dollar, commonly used for trading "
        "liquidity and value transfer across crypto markets."
    ),
    "binancecoin": (
        "BNB is the native asset of the BNB Chain ecosystem, used for network fees and participation across "
        "applications built on BNB-compatible chains."
    ),
    "solana": (
        "Solana is a high-throughput blockchain aimed at fast, low-cost applications. SOL is used for fees, "
        "staking, and native programs on the network."
    ),
    "usd-coin": (
        "USD Coin (USDC) is a dollar-pegged stablecoin issued by regulated entities, widely used for payments, "
        "treasury, and trading pairs across crypto markets."
    ),
    "ripple": (
        "XRP is the native digital asset of the XRP Ledger, used for fast cross-border payments and liquidity "
        "in some institutional and payment-focused workflows."
    ),
    "dogecoin": (
        "Dogecoin began as a meme coin and peer-to-peer cryptocurrency; it remains a widely recognized asset "
        "with an active community and exchange liquidity."
    ),
    "cardano": (
        "Cardano is a proof-of-stake blockchain focused on formal methods and upgrades via its research-driven roadmap. "
        "ADA is used for staking and network fees."
    ),
    "tron": (
        "TRON is a blockchain platform emphasizing content and payments use cases. TRX is used for energy, bandwidth, "
        "and fees on the network."
    ),
}

_COINGECKO_DETAIL_RE = re.compile(
    r"^https://www\.coingecko\.com/en/coins/(?P<id>[^/?#]+)/?",
    re.I,
)


def default_coingecko_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Headers for CoinGecko; set ``COINGECKO_DEMO_API_KEY`` for higher public-demo rate limits."""
    h: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (compatible; Digital-Assets-Dashboard/1.0)",
        "Accept": "application/json",
    }
    if extra:
        h.update(extra)
    key = (os.environ.get("COINGECKO_DEMO_API_KEY") or os.environ.get("COINGECKO_API_KEY") or "").strip()
    if key:
        h["x-cg-demo-apikey"] = key
    return h


def resolve_coingecko_id_for_blurb(row: dict[str, Any]) -> str:
    """
    Best CoinGecko ``id`` for fetching ``/coins/{id}`` About text, given a ticker row from markets or fallback feeds.
    """
    cid = str(row.get("coin_id") or "").strip()
    if cid:
        return cid
    url = str(row.get("detail_url") or "").strip()
    m = _COINGECKO_DETAIL_RE.match(url)
    if m:
        return (m.group("id") or "").strip()
    sym = str(row.get("symbol") or "").strip().upper()
    return (SYMBOL_TO_COINGECKO_ID.get(sym) or "").strip()


def blurb_with_static_fallback(coin_id: str, api_blurb: str) -> str:
    """Prefer API-derived blurb; otherwise a short static line for major assets (static hub tooltips)."""
    t = (api_blurb or "").strip()
    if t:
        return t
    return (STATIC_ABOUT_BLURBS.get((coin_id or "").strip()) or "").strip()


COINGECKO_COIN_URL = "https://api.coingecko.com/api/v3/coins/{coin_id}"
_COIN_MIN_PARAMS: dict[str, str] = {
    "localization": "false",
    "tickers": "false",
    "market_data": "false",
    "community_data": "false",
    "developer_data": "false",
    "sparkline": "false",
}

_MAINSTREAM_RX = re.compile(
    r"mainstream\s+adoption|institutional\s+adoption|achieved\s+mainstream|significant\s+.{0,40}?\badoption\b|"
    r"increasingly\s+adopted|adoption\s+ranging\s+from|spot\s+.{0,20}?\betfs?\b.*\bapprov",
    re.I,
)
_USES_RX = re.compile(
    r"what\s+can\s+.{0,80}?be\s+used\s+for|"
    r"\bbe\s+used\s+for\b|"
    r"serves\s+multiple\s+functions|"
    r"\bserves\s+as\b|"
    r"primary\s+(currency|use)|"
    r"native\s+token\b",
    re.I,
)


def _strip_htmlish(raw: str) -> str:
    if not raw:
        return ""
    text = html_module.unescape(raw)
    if "<" in text and ">" in text:
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        text = re.sub(r"</(p|div|section|h[1-6])\s*>", "\n\n", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def _paragraphs(raw: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n+", _strip_htmlish(raw)) if p.strip()]


def _truncate_smart(s: str, max_chars: int) -> str:
    s = s.strip()
    if len(s) <= max_chars:
        return s
    cut = s[: max_chars + 1]
    sp = cut.rfind(". ")
    if sp >= max_chars // 3:
        return cut[: sp + 1].strip()
    sp = cut.rfind(" ")
    if sp > max_chars // 2:
        return cut[:sp].rstrip(".,; ") + "…"
    return s[:max_chars].rstrip(".,; ") + "…"


def build_about_blurb_from_description(raw_description: str, *, max_chars: int = 720) -> str:
    """
    Build a short blurb: brief lead from the first paragraph, then (when present) paragraphs
    touching mainstream/institutional adoption and practical uses, matching CoinGecko's About copy.
    """
    paras = _paragraphs(raw_description or "")
    if not paras:
        return ""
    pieces: list[str] = []
    intro = _truncate_smart(paras[0], 170)
    pieces.append(intro)
    blob = intro.lower()

    main_p = next((p for p in paras[1:] if _MAINSTREAM_RX.search(p)), None)
    use_p = next((p for p in paras[1:] if _USES_RX.search(p)), None)

    if main_p and use_p and main_p.strip() == use_p.strip():
        frag = _truncate_smart(main_p, min(580, max_chars + 100))
        if frag.lower() not in blob and frag:
            pieces.append(frag)
    else:
        if main_p:
            frag = _truncate_smart(main_p, 220)
            if frag.lower() not in blob and frag:
                pieces.append(frag)
                blob += " " + frag.lower()
        if use_p:
            frag = _truncate_smart(use_p, 220)
            low = frag.lower()
            if low not in blob and frag:
                pieces.append(frag)

    out = " ".join(x for x in pieces if x).strip()
    return _truncate_smart(out, max_chars)


def fetch_coin_description_en(
    coin_id: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 25.0,
) -> str:
    """Return raw ``description.en`` from CoinGecko (may include HTML)."""
    cid = (coin_id or "").strip()
    if not cid:
        return ""
    base = default_coingecko_headers()
    if headers:
        base = {**base, **headers}
    h = base
    url = COINGECKO_COIN_URL.format(coin_id=cid)
    r = requests.get(url, params=_COIN_MIN_PARAMS, headers=h, timeout=timeout)
    if r.status_code == 429:
        time.sleep(2.5)
        r = requests.get(url, params=_COIN_MIN_PARAMS, headers=h, timeout=timeout)
    r.raise_for_status()
    data: Any = r.json()
    if not isinstance(data, dict):
        return ""
    desc = data.get("description")
    if isinstance(desc, dict):
        return str(desc.get("en") or "").strip()
    return ""


def fetch_blurbs_for_coin_ids(
    coin_ids: list[str],
    *,
    headers: dict[str, str] | None = None,
    delay_s: float = 0.1,
) -> dict[str, str]:
    """
    Fetch summarized blurbs for unique CoinGecko ids (sequential, small delay to reduce 429s).
    """
    out: dict[str, str] = {}
    seen: set[str] = set()
    merged = default_coingecko_headers()
    if headers:
        merged = {**merged, **headers}
    for raw_id in coin_ids:
        cid = str(raw_id or "").strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        try:
            raw = fetch_coin_description_en(cid, headers=merged)
            out[cid] = build_about_blurb_from_description(raw) if raw else ""
        except (requests.RequestException, ValueError, TypeError, KeyError):
            out[cid] = ""
        if delay_s > 0:
            time.sleep(delay_s)
    return out
