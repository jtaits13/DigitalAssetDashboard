"""
JPM Digital — crypto & digital asset news (RSS aggregation).
Deploy on Streamlit Community Cloud with this file as the main entrypoint.
"""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape
from typing import Any

import feedparser
import requests
import streamlit as st

# Price ticker: CoinGecko first, then CoinCap (both public, no API key for this usage).
COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
COINCAP_ASSETS_URL = "https://api.coincap.io/v2/assets"
TICKER_COUNT = 25

# Public RSS feeds (no API keys). Replace or extend as needed.
DEFAULT_FEEDS: list[tuple[str, str]] = [
    ("CoinTelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("The Block", "https://www.theblockcrypto.com/rss.xml"),
]


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
    """Top ~25 by market cap: CoinGecko, then CoinCap. Returns (rows, error, attribution label)."""
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
    # Duplicate for seamless marquee loop
    inner = f'<div class="cd-ticker-track">{joined}</div><div class="cd-ticker-track" aria-hidden="true">{joined}</div>'
    src = escape(source_label) if source_label else "Live"
    return (
        f'<div class="cd-ticker-shell">'
        f'<span class="cd-ticker-label">{src} · Top {len(rows)}</span>'
        f'<div class="cd-ticker-viewport"><div class="cd-ticker-move">{inner}</div></div></div>'
    )


def _parse_entry_date(entry: Any) -> datetime | None:
    if getattr(entry, "published_parsed", None):
        t = entry.published_parsed
        try:
            return datetime(*t[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    if getattr(entry, "updated_parsed", None):
        t = entry.updated_parsed
        try:
            return datetime(*t[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (TypeError, ValueError):
            pass
    return None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_feed(source_name: str, url: str) -> list[dict[str, Any]]:
    parsed = feedparser.parse(url)
    out: list[dict[str, Any]] = []
    for entry in getattr(parsed, "entries", []) or []:
        link = getattr(entry, "link", "") or ""
        title = (getattr(entry, "title", "") or "Untitled").strip()
        if not link and not title:
            continue
        out.append(
            {
                "title": title,
                "link": link,
                "source": source_name,
                "published": _parse_entry_date(entry),
            }
        )
    return out


def load_all_feeds(feeds: list[tuple[str, str]]) -> tuple[list[dict[str, Any]], list[str]]:
    combined: list[dict[str, Any]] = []
    errors: list[str] = []
    for name, url in feeds:
        try:
            combined.extend(fetch_feed(name, url))
        except Exception as e:  # noqa: BLE001 — show feed errors in UI
            errors.append(f"{name}: {e!s}")
    combined.sort(key=lambda x: x["published"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return combined, errors


def main() -> None:
    st.set_page_config(
        page_title="JPM Digital — Crypto News",
        page_icon="◆",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlock"] > div:has(div.news-card) {
            gap: 0.75rem;
        }
        .news-card {
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 1rem 1.1rem;
            background: #ffffff;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
        }
        .news-meta {
            font-size: 0.85rem;
            color: #64748b;
            margin-bottom: 0.35rem;
        }
        .news-title a {
            color: #0f172a;
            text-decoration: none;
            font-weight: 600;
            font-size: 1.05rem;
        }
        .news-title a:hover {
            color: #059669;
        }
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
            color: #059669;
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
        """,
        unsafe_allow_html=True,
    )

    price_rows, price_err, price_src = fetch_top_crypto_tickers(TICKER_COUNT)
    st.markdown(render_price_ticker_html(price_rows, price_err, price_src), unsafe_allow_html=True)

    with st.sidebar:
        st.header("Sources")
        st.caption("RSS feeds aggregated on refresh. Add your own in the repo.")
        max_items = st.slider("Articles to show", min_value=10, max_value=80, value=30, step=5)
        refresh = st.button("Refresh feeds", use_container_width=True)

    if refresh:
        fetch_feed.clear()
        fetch_top_crypto_tickers.clear()
        st.rerun()

    col_title, col_tag = st.columns([3, 1])
    with col_title:
        st.title("Digital asset & crypto news")
    with col_tag:
        st.caption("Aggregated headlines · RSS")

    articles, feed_errors = load_all_feeds(DEFAULT_FEEDS)

    if feed_errors:
        with st.expander("Some feeds could not be loaded", expanded=False):
            for err in feed_errors:
                st.warning(err)

    if not articles:
        st.info("No articles loaded. Check your network or RSS URLs in `streamlit_app.py`.")
        st.caption(
            f"Last built at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
            "Prices: CoinGecko or CoinCap · Headlines: original publishers."
        )
        return

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for a in articles:
        key = a["link"] or a["title"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(a)
        if len(unique) >= max_items:
            break

    n_cols = 2
    rows = [unique[i : i + n_cols] for i in range(0, len(unique), n_cols)]
    for row in rows:
        cols = st.columns(n_cols)
        for col, item in zip(cols, row):
            with col:
                pub = item["published"]
                pub_s = pub.strftime("%b %d, %Y · %H:%M UTC") if pub else "Date unknown"
                title_esc = (
                    item["title"]
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                link = item["link"] or "#"
                st.markdown(
                    f"""
                    <div class="news-card">
                      <div class="news-meta">{item["source"]} · {pub_s}</div>
                      <div class="news-title"><a href="{link}" target="_blank" rel="noopener noreferrer">{title_esc}</a></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.divider()
    st.caption(
        f"Last built at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "Prices & 24h % from CoinGecko (fallback: CoinCap) · Headlines link to original publishers."
    )


if __name__ == "__main__":
    main()
