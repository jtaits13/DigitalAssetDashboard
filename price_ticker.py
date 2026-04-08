"""Shared crypto price ticker (CoinGecko → CoinCap) for all app pages."""

from __future__ import annotations

from html import escape
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components

COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
COINCAP_ASSETS_URL = "https://api.coincap.io/v2/assets"
TICKER_COUNT = 25

TICKER_STYLES_MARKDOWN = """
<style>
.cd-ticker-shell {
    background: linear-gradient(90deg, #ffffff 0%, #f1f5f9 50%, #ffffff 100%);
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 0.45rem 0;
    margin-bottom: 1rem;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}
.cd-ticker-error {
    padding: 0.5rem 1rem;
    font-size: 0.9rem;
    color: #b91c1c;
}
.cd-ticker-label {
    display: inline-block;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #000000;
    font-weight: 700;
    padding: 0 1rem 0.25rem 1rem;
}
.cd-ticker-viewport {
    overflow: hidden;
    width: 100%;
}
.cd-ticker-move {
    display: flex;
    width: max-content;
    animation: cd-marquee 120s linear infinite;
}
.cd-ticker-move:hover {
    animation-play-state: paused;
}
.cd-ticker-track {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    gap: 0.75rem 2.25rem;
    padding: 0.15rem 0.5rem 0.35rem 0.5rem;
    white-space: nowrap;
}
@keyframes cd-marquee {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}
.cd-chip {
    font-size: 0.92rem;
    color: #334155;
}
.cd-chip strong {
    color: #0f172a;
    margin-right: 0.35rem;
}
.cd-usd {
    color: #64748b;
    margin-right: 0.35rem;
}
.cd-pct {
    font-weight: 600;
    font-size: 0.88rem;
}
.cd-pct-up { color: #059669; }
.cd-pct-down { color: #dc2626; }
.cd-pct-na { color: #94a3b8; }
a.cd-chip-link {
    text-decoration: none;
    color: inherit;
    cursor: pointer;
    border-radius: 6px;
    outline-offset: 2px;
}
a.cd-chip-link:hover .cd-chip {
    background: rgba(5, 150, 105, 0.08);
}
a.cd-chip-link .cd-chip {
    padding: 0.15rem 0.35rem;
    margin: 0 -0.15rem;
    border-radius: 6px;
    transition: background 0.15s ease;
}
</style>
"""


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _parse_coingecko_markets(data: Any, limit: int) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for c in data:
        if not isinstance(c, dict):
            continue
        sym = str(c.get("symbol", "?")).strip().upper()[:14]
        price = _to_float(c.get("current_price"))
        pct = _to_float(c.get("price_change_percentage_24h"))
        if price is None:
            continue
        cid = c.get("id")
        detail_url = (
            f"https://www.coingecko.com/en/coins/{cid}"
            if isinstance(cid, str) and cid.strip()
            else None
        )
        out.append(
            {
                "symbol": sym,
                "name": str(c.get("name", sym))[:48],
                "price_usd": price,
                "pct_24h": pct,
                "detail_url": detail_url,
            }
        )
        if len(out) >= limit:
            break
    return out


def _parse_coincap_assets(payload: Any, limit: int) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for c in data:
        if not isinstance(c, dict):
            continue
        sym = str(c.get("symbol", "?")).strip().upper()[:14]
        price = _to_float(c.get("priceUsd"))
        pct = _to_float(c.get("changePercent24Hr"))
        if price is None:
            continue
        aid = c.get("id")
        detail_url = (
            f"https://coincap.io/assets/{aid}"
            if isinstance(aid, str) and aid.strip()
            else None
        )
        out.append(
            {
                "symbol": sym,
                "name": str(c.get("name", sym))[:48],
                "price_usd": price,
                "pct_24h": pct,
                "detail_url": detail_url,
            }
        )
        if len(out) >= limit:
            break
    return out


@st.cache_data(ttl=120, show_spinner=False)
def fetch_top_crypto_tickers(limit: int = TICKER_COUNT) -> tuple[list[dict[str, Any]], str | None, str]:
    """Top ~25 by market cap: CoinGecko, then CoinCap."""
    lim = max(min(limit, 250), 1)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; JPM-Digital-News/1.0)",
        "Accept": "application/json",
    }
    cg_err: str | None = None
    try:
        r = requests.get(
            COINGECKO_MARKETS_URL,
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": lim,
                "page": 1,
                "sparkline": "false",
            },
            headers=headers,
            timeout=25,
        )
        r.raise_for_status()
        rows = _parse_coingecko_markets(r.json(), limit)
        if rows:
            return rows[:limit], None, "CoinGecko"
    except (requests.RequestException, ValueError, TypeError) as e:
        cg_err = f"{type(e).__name__}: {e}"

    cc_err: str | None = None
    try:
        r = requests.get(COINCAP_ASSETS_URL, params={"limit": lim}, headers=headers, timeout=25)
        r.raise_for_status()
        rows = _parse_coincap_assets(r.json(), limit)
        if rows:
            return rows[:limit], None, "CoinCap"
    except (requests.RequestException, ValueError, TypeError) as e:
        cc_err = f"{type(e).__name__}: {e}"

    parts = []
    if cg_err:
        parts.append(f"CoinGecko ({cg_err})")
    if cc_err:
        parts.append(f"CoinCap ({cc_err})")
    msg = " · ".join(parts) if parts else "No price data returned."
    return [], msg, ""


def _format_usd(price: float) -> str:
    if price >= 1:
        return f"${price:,.2f}"
    if price >= 0.01:
        return f"${price:.4f}"
    return f"${price:.6g}"


def render_price_ticker_html(
    rows: list[dict[str, Any]],
    error: str | None,
    source_label: str = "",
) -> str:
    label = escape(source_label) if source_label else "Live"
    if error:
        esc = escape(error)
        return (
            f'<div class="cd-ticker-shell cd-ticker-error">'
            f'<span class="cd-ticker-label">{label}</span> {esc}</div>'
        )
    if not rows:
        return (
            f'<div class="cd-ticker-shell cd-ticker-error">'
            f'<span class="cd-ticker-label">{label}</span> No price data.</div>'
        )

    def one_item(r: dict[str, Any]) -> str:
        sym = escape(str(r["symbol"]))
        price_s = escape(_format_usd(float(r["price_usd"])))
        pct = r.get("pct_24h")
        if pct is None:
            pct_html = '<span class="cd-pct cd-pct-na">—</span>'
        else:
            p = float(pct)
            arrow = "▲" if p >= 0 else "▼"
            cls = "cd-pct-up" if p >= 0 else "cd-pct-down"
            sign = "+" if p > 0 else ""
            pct_html = f'<span class="cd-pct {cls}">{arrow} {sign}{p:.2f}%</span>'
        inner = (
            f'<span class="cd-chip"><strong>{sym}</strong> '
            f'<span class="cd-usd">{price_s}</span> {pct_html}</span>'
        )
        href = r.get("detail_url")
        if isinstance(href, str) and href.startswith(("https://www.coingecko.com/", "https://coincap.io/")):
            h = escape(href, quote=True)
            return (
                f'<a class="cd-chip cd-chip-link" href="{h}" target="_blank" rel="noopener noreferrer">{inner}</a>'
            )
        return inner

    parts = [one_item(r) for r in rows]
    joined = "".join(parts)
    inner = f'<div class="cd-ticker-track">{joined}</div><div class="cd-ticker-track" aria-hidden="true">{joined}</div>'
    src = escape(source_label) if source_label else "Live"
    return (
        f'<div class="cd-ticker-shell">'
        f'<span class="cd-ticker-label">{src} · Top {len(rows)}</span>'
        f'<div class="cd-ticker-viewport"><div class="cd-ticker-move">{inner}</div></div></div>'
    )


NAV_TICKER_ALIGN_SCRIPT = """
<script>
(function () {
  const p = window.parent;
  const doc = p.document;
  function align() {
    const ticker = doc.querySelector(".cd-ticker-shell");
    const nav = doc.querySelector(".jd-site-nav-fixed-wrap");
    if (!ticker || !nav) return;
    const r = ticker.getBoundingClientRect();
    if (r.width < 4) return;
    nav.style.paddingLeft = Math.max(0, Math.round(r.left)) + "px";
    nav.style.paddingRight = Math.max(0, Math.round(p.innerWidth - r.right)) + "px";
  }
  align();
  p.addEventListener("resize", align);
  p.setTimeout(align, 100);
  p.setTimeout(align, 400);
})();
</script>
"""


def show_price_ticker() -> None:
    """Inject ticker CSS and HTML. Call once per page that should show the ticker."""
    st.markdown(TICKER_STYLES_MARKDOWN, unsafe_allow_html=True)
    rows, err, src = fetch_top_crypto_tickers(TICKER_COUNT)
    st.markdown(render_price_ticker_html(rows, err, src), unsafe_allow_html=True)
    components.html(NAV_TICKER_ALIGN_SCRIPT, height=0, width=0)
