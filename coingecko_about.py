"""Summarize CoinGecko coin ``description.en`` for short UI blurbs (tooltips)."""

from __future__ import annotations

import html as html_module
import re
import time
from typing import Any

import requests

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
    h = headers or {
        "User-Agent": "Mozilla/5.0 (compatible; Digital-Assets-Dashboard/1.0)",
        "Accept": "application/json",
    }
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
    for raw_id in coin_ids:
        cid = str(raw_id or "").strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        try:
            raw = fetch_coin_description_en(cid, headers=headers)
            out[cid] = build_about_blurb_from_description(raw) if raw else ""
        except (requests.RequestException, ValueError, TypeError, KeyError):
            out[cid] = ""
        if delay_s > 0:
            time.sleep(delay_s)
    return out
