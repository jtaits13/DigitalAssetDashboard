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

# CoinDesk production API (powers coindesk.com/price). No API key for public list usage.
COINDESK_CURRENCIES_URL = "https://production.api.coindesk.com/v2/currencies"
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


def _metrics_dict(coin: dict[str, Any]) -> dict[str, Any]:
    m = coin.get("metrics")
    if isinstance(m, dict):
        return m
    inner = coin.get("currency")
    if isinstance(inner, dict):
        im = inner.get("metrics")
        if isinstance(im, dict):
            return im
    return coin


def _parse_price_usd(metrics: dict[str, Any]) -> float | None:
    for key in ("last_price_usd", "price_usd", "last", "PRICE", "price", "usd_price"):
        p = _to_float(metrics.get(key))
        if p is not None:
            return p
    usd = metrics.get("usd")
    if isinstance(usd, dict):
        p = _to_float(usd.get("price") or usd.get("last"))
        if p is not None:
            return p
    return None


def _parse_pct_24h(metrics: dict[str, Any]) -> float | None:
    for key in (
        "percent_change_usd_last_24_hours",
        "percent_change_24h",
        "price_change_percentage_24h",
        "change_percent_24h",
        "CHANGEPCT24HOUR",
    ):
        p = _to_float(metrics.get(key))
        if p is not None:
            return p
    usd = metrics.get("usd")
    if isinstance(usd, dict):
        p = _to_float(usd.get("percent_change_24h") or usd.get("change_percent_24h"))
        if p is not None:
            return p
    return None


def _symbol_from_coin(coin: dict[str, Any]) -> str:
    s = coin.get("symbol") or coin.get("ticker") or coin.get("base_symbol") or coin.get("code")
    if s is None and isinstance(coin.get("currency"), dict):
        s = coin["currency"].get("symbol")
    return str(s or "?").strip().upper()[:14]


def _extract_currency_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "currencies", "items", "Data", "result"):
        block = payload.get(key)
        if isinstance(block, list):
            return [x for x in block if isinstance(x, dict)]
        if isinstance(block, dict):
            inner = block.get("currencies") or block.get("items") or block.get("data")
            if isinstance(inner, list):
                return [x for x in inner if isinstance(x, dict)]
    return []


@st.cache_data(ttl=120, show_spinner=False)
def fetch_coindesk_top_tickers(limit: int = TICKER_COUNT) -> tuple[list[dict[str, Any]], str | None]:
    """Top cryptocurrencies by market cap from CoinDesk; includes ~24h % change when present."""
    params: dict[str, str | int] = {
        "limit": max(limit, 5),
        "sort_by": "MARKET_CAP",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; JPM-Digital-News/1.0; +https://www.coindesk.com/price)",
        "Accept": "application/json",
    }
    payloads: list[Any] = []
    try:
        r = requests.get(COINDESK_CURRENCIES_URL, params=params, headers=headers, timeout=25)
        r.raise_for_status()
        payloads.append(r.json())
    except (requests.RequestException, ValueError) as e:
        return [], f"CoinDesk request failed: {e!s}"

    def build_rows(p: Any) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for coin in _extract_currency_list(p):
            metrics = _metrics_dict(coin)
            sym = _symbol_from_coin(coin)
            price = _parse_price_usd(metrics)
            pct = _parse_pct_24h(metrics)
            if price is None:
                continue
            name = str(coin.get("name") or coin.get("long_name") or sym)[:48]
            out.append(
                {
                    "symbol": sym,
                    "name": name,
                    "price_usd": price,
                    "pct_24h": pct,
                }
            )
            if len(out) >= limit:
                break
        return out

    rows = build_rows(payloads[0])
    if not rows:
        try:
            r2 = requests.get(
                COINDESK_CURRENCIES_URL,
                params={"limit": max(limit, 5)},
                headers=headers,
                timeout=25,
            )
            r2.raise_for_status()
            rows = build_rows(r2.json())
        except (requests.RequestException, ValueError):
            pass

    if not rows:
        return [], "CoinDesk returned no parseable tickers (response shape may have changed)."
    return rows[:limit], None


def _format_usd(price: float) -> str:
    if price >= 1:
        return f"${price:,.2f}"
    if price >= 0.01:
        return f"${price:.4f}"
    return f"${price:.6g}"


def render_price_ticker_html(rows: list[dict[str, Any]], error: str | None) -> str:
    if error:
        esc = escape(error)
        return (
            f'<div class="cd-ticker-shell cd-ticker-error">'
            f'<span class="cd-ticker-label">CoinDesk</span> {esc}</div>'
        )
    if not rows:
        return (
            '<div class="cd-ticker-shell cd-ticker-error">'
            '<span class="cd-ticker-label">CoinDesk</span> No price data.</div>'
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
        return (
            f'<span class="cd-chip"><strong>{sym}</strong> '
            f'<span class="cd-usd">{price_s}</span> {pct_html}</span>'
        )

    parts = [one_item(r) for r in rows]
    joined = "".join(parts)
    # Duplicate for seamless marquee loop
    inner = f'<div class="cd-ticker-track">{joined}</div><div class="cd-ticker-track" aria-hidden="true">{joined}</div>'
    return (
        f'<div class="cd-ticker-shell">'
        f'<span class="cd-ticker-label">CoinDesk · Top {len(rows)}</span>'
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
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            padding: 1rem 1.1rem;
            background: rgba(255,255,255,0.03);
        }
        .news-meta {
            font-size: 0.85rem;
            opacity: 0.75;
            margin-bottom: 0.35rem;
        }
        .news-title a {
            color: #e8eef4;
            text-decoration: none;
            font-weight: 600;
            font-size: 1.05rem;
        }
        .news-title a:hover {
            color: #22c55e;
        }
        .cd-ticker-shell {
            background: linear-gradient(90deg, #121a24 0%, #1a2332 50%, #121a24 100%);
            border: 1px solid rgba(34, 197, 94, 0.2);
            border-radius: 8px;
            padding: 0.45rem 0;
            margin-bottom: 1rem;
            overflow: hidden;
        }
        .cd-ticker-error {
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
            color: #fca5a5;
        }
        .cd-ticker-label {
            display: inline-block;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #22c55e;
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
            animation: cd-marquee 55s linear infinite;
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
            color: #e8eef4;
        }
        .cd-chip strong {
            color: #fff;
            margin-right: 0.35rem;
        }
        .cd-usd {
            color: #cbd5e1;
            margin-right: 0.35rem;
        }
        .cd-pct {
            font-weight: 600;
            font-size: 0.88rem;
        }
        .cd-pct-up { color: #22c55e; }
        .cd-pct-down { color: #f87171; }
        .cd-pct-na { color: #94a3b8; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    price_rows, price_err = fetch_coindesk_top_tickers(TICKER_COUNT)
    st.markdown(render_price_ticker_html(price_rows, price_err), unsafe_allow_html=True)

    with st.sidebar:
        st.header("Sources")
        st.caption("RSS feeds aggregated on refresh. Add your own in the repo.")
        max_items = st.slider("Articles to show", min_value=10, max_value=80, value=30, step=5)
        refresh = st.button("Refresh feeds", use_container_width=True)

    if refresh:
        fetch_feed.clear()
        fetch_coindesk_top_tickers.clear()
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
            "Prices: CoinDesk · Headlines: original publishers."
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
        "Prices & 24h % from CoinDesk · Headlines link to original publishers."
    )


if __name__ == "__main__":
    main()
