"""Summarize CoinGecko coin ``description.en`` for short UI blurbs (tooltips)."""

from __future__ import annotations

import html as html_module
import json
import os
import re
import time
from pathlib import Path
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
    "dogecoin": (
        "Dogecoin began as a meme coin and peer-to-peer cryptocurrency; it remains a widely recognized asset "
        "with an active community and exchange liquidity."
    ),
    "cardano": (
        "Cardano is a proof-of-stake blockchain focused on formal methods and upgrades via its research-driven roadmap. "
        "ADA is used for staking and network fees."
    ),
    "avalanche-2": (
        "Avalanche is a proof-of-stake platform for decentralized apps and custom subnets. AVAX secures the network "
        "and pays transaction fees."
    ),
    "chainlink": (
        "Chainlink provides decentralized oracle infrastructure that connects smart contracts to real-world data "
        "and off-chain systems."
    ),
    "polkadot": (
        "Polkadot is a multi-chain network designed to connect specialized blockchains (parachains) with shared security."
    ),
    "shiba-inu": (
        "Shiba Inu (SHIB) is an Ethereum-based token associated with the Shiba ecosystem and community-driven projects."
    ),
    "litecoin": (
        "Litecoin is a peer-to-peer cryptocurrency derived from Bitcoin's codebase, often used for faster confirmation "
        "times and payments."
    ),
    "bitcoin-cash": (
        "Bitcoin Cash (BCH) is a Bitcoin fork focused on on-chain payments with larger block capacity."
    ),
    "stellar": (
        "Stellar (XLM) is a network for cross-border payments and tokenized assets, emphasizing low-cost transfers."
    ),
    "near": (
        "NEAR Protocol is a sharded proof-of-stake blockchain aimed at developer-friendly Web3 applications."
    ),
    "sui": (
        "Sui is a Layer 1 blockchain using the Move language, designed for high-throughput apps and digital assets."
    ),
    "uniswap": (
        "Uniswap is a decentralized exchange protocol on Ethereum; UNI is the governance token for the Uniswap ecosystem."
    ),
    "hedera-hashgraph": (
        "Hedera (HBAR) is a public network using hashgraph consensus for enterprise and payment use cases."
    ),
}

_COINGECKO_DETAIL_RE = re.compile(
    r"^https://www\.coingecko\.com/en/coins/(?P<id>[^/?#]+)/?",
    re.I,
)


def default_coingecko_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Headers for CoinGecko; demo or pro API keys raise rate limits."""
    h: dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (compatible; Digital-Assets-Dashboard/1.0)",
        "Accept": "application/json",
    }
    if extra:
        h.update(extra)
    pro = (os.environ.get("COINGECKO_PRO_API_KEY") or "").strip()
    if pro:
        h["x-cg-pro-apikey"] = pro
        return h
    key = (os.environ.get("COINGECKO_DEMO_API_KEY") or os.environ.get("COINGECKO_API_KEY") or "").strip()
    if key:
        h["x-cg-demo-apikey"] = key
    return h


def coingecko_has_api_key() -> bool:
    return bool(
        (os.environ.get("COINGECKO_PRO_API_KEY") or "").strip()
        or (os.environ.get("COINGECKO_DEMO_API_KEY") or os.environ.get("COINGECKO_API_KEY") or "").strip()
    )


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


def coingecko_api_base() -> str:
    """Public/demo API by default; use Pro host when ``COINGECKO_PRO_API_KEY`` is set."""
    pro = (os.environ.get("COINGECKO_PRO_API_KEY") or "").strip()
    if pro:
        return "https://pro-api.coingecko.com/api/v3"
    return "https://api.coingecko.com/api/v3"


def coingecko_coin_detail_url(coin_id: str) -> str:
    return f"{coingecko_api_base()}/coins/{coin_id}"


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
    max_attempts: int = 3,
) -> str:
    """Return raw ``description.en`` from CoinGecko (may include HTML)."""
    cid = (coin_id or "").strip()
    if not cid:
        return ""
    base = default_coingecko_headers()
    if headers:
        base = {**base, **headers}
    url = coingecko_coin_detail_url(cid)
    wait_s = 2.0
    last_exc: BaseException | None = None
    for attempt in range(max(1, max_attempts)):
        try:
            r = requests.get(url, params=_COIN_MIN_PARAMS, headers=base, timeout=timeout)
            if r.status_code == 429:
                if attempt + 1 >= max_attempts:
                    return ""
                retry_after = r.headers.get("Retry-After")
                pause = float(retry_after) if retry_after and str(retry_after).isdigit() else wait_s
                time.sleep(min(max(pause, 1.5), 20.0))
                wait_s = min(wait_s * 1.5, 20.0)
                continue
            if r.status_code in (502, 503, 504) and attempt + 1 < max_attempts:
                time.sleep(wait_s)
                wait_s = min(wait_s * 1.4, 15.0)
                continue
            r.raise_for_status()
            data: Any = r.json()
            if not isinstance(data, dict):
                return ""
            desc = data.get("description")
            if isinstance(desc, dict):
                return str(desc.get("en") or "").strip()
            return ""
        except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
            last_exc = exc
            if attempt + 1 >= max_attempts:
                break
            time.sleep(wait_s)
            wait_s = min(wait_s * 1.4, 15.0)
    if last_exc:
        raise last_exc
    return ""


def default_blurb_fetch_delay_s() -> float:
    """Pacing between per-coin description calls (slower without an API key)."""
    return 0.35 if coingecko_has_api_key() else 0.85


def collect_coingecko_ids_for_rows(rows: list[dict[str, Any]]) -> list[str]:
    """Unique CoinGecko ids for About blurbs, in stable order."""
    out: list[str] = []
    seen: set[str] = set()
    for row in rows:
        cid = resolve_coingecko_id_for_blurb(row)
        if cid and cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def fetch_blurbs_for_coin_ids(
    coin_ids: list[str],
    *,
    headers: dict[str, str] | None = None,
    delay_s: float | None = None,
) -> dict[str, str]:
    """
    Fetch summarized blurbs for unique CoinGecko ids (sequential, paced to reduce 429s).
    Failed ids are retried once after a longer pause.
    """
    out: dict[str, str] = {}
    seen: set[str] = set()
    merged = default_coingecko_headers()
    if headers:
        merged = {**merged, **headers}
    pace = default_blurb_fetch_delay_s() if delay_s is None else delay_s
    ordered: list[str] = []
    for raw_id in coin_ids:
        cid = str(raw_id or "").strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        ordered.append(cid)

    failed: list[str] = []

    def one(cid: str) -> None:
        try:
            raw = fetch_coin_description_en(cid, headers=merged)
            out[cid] = build_about_blurb_from_description(raw) if raw else ""
        except (requests.RequestException, ValueError, TypeError, KeyError):
            out[cid] = ""
            failed.append(cid)

    for cid in ordered:
        one(cid)
        if pace > 0:
            time.sleep(pace)

    if failed:
        time.sleep(min(12.0, max(4.0, pace * 5)))
        retry_pace = max(pace * 1.5, 0.75)
        for cid in failed[:12]:
            if (out.get(cid) or "").strip():
                continue
            try:
                raw = fetch_coin_description_en(cid, headers=merged, max_attempts=4)
                blurb = build_about_blurb_from_description(raw) if raw else ""
                if blurb:
                    out[cid] = blurb
            except (requests.RequestException, ValueError, TypeError, KeyError):
                pass
            if retry_pace > 0:
                time.sleep(retry_pace)

    return out


def attach_about_blurbs_to_rows(
    rows: list[dict[str, Any]],
    *,
    headers: dict[str, str] | None = None,
    delay_s: float | None = None,
    prefetched: dict[str, str] | None = None,
) -> None:
    """Mutate ticker/price rows with ``about_blurb`` (CoinGecko About, then static fallback)."""
    ids = collect_coingecko_ids_for_rows(rows)
    blurbs = dict(prefetched or {})
    missing = [cid for cid in ids if not (blurbs.get(cid) or "").strip()]
    if missing:
        fetched = fetch_blurbs_for_coin_ids(missing, headers=headers, delay_s=delay_s)
        blurbs.update(fetched)
    for row in rows:
        cid = resolve_coingecko_id_for_blurb(row)
        if cid:
            raw = (blurbs.get(cid) or "").strip()
            row["about_blurb"] = blurb_with_static_fallback(cid, raw)
        else:
            row["about_blurb"] = ""


_BLURB_CACHE_VERSION = 1


def load_blurb_cache(path: Path) -> dict[str, str]:
    """Return coin_id → blurb from a JSON cache file (empty if missing or invalid)."""
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    entries = data.get("blurbs")
    if not isinstance(entries, dict):
        return {}
    out: dict[str, str] = {}
    for key, val in entries.items():
        cid = str(key or "").strip()
        if not cid:
            continue
        if isinstance(val, str):
            text = val.strip()
        elif isinstance(val, dict):
            text = str(val.get("blurb") or "").strip()
        else:
            continue
        if text:
            out[cid] = text
    return out


def save_blurb_cache(path: Path, blurbs: dict[str, str]) -> None:
    """Persist non-empty blurbs for reuse across exports (avoids re-hitting rate limits)."""
    cleaned = {cid: text.strip() for cid, text in blurbs.items() if cid and (text or "").strip()}
    payload = {
        "version": _BLURB_CACHE_VERSION,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "blurbs": cleaned,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def fetch_blurbs_with_cache(
    coin_ids: list[str],
    cache_path: Path,
    *,
    headers: dict[str, str] | None = None,
    delay_s: float | None = None,
) -> dict[str, str]:
    """Merge disk cache with fresh CoinGecko fetches for ids not yet cached."""
    cached = load_blurb_cache(cache_path)
    need = [cid for cid in coin_ids if cid and not (cached.get(cid) or "").strip()]
    if need:
        fresh = fetch_blurbs_for_coin_ids(need, headers=headers, delay_s=delay_s)
        for cid, blurb in fresh.items():
            if (blurb or "").strip():
                cached[cid] = blurb.strip()
        save_blurb_cache(cache_path, cached)
    return {cid: cached[cid] for cid in coin_ids if cid in cached and cached[cid]}
