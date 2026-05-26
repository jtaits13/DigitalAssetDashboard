"""Top 1M movers for the crypto prices page + optional headline context."""

from __future__ import annotations

import re
from html import escape
from typing import Any
from urllib.parse import quote_plus

import feedparser

MOVER_EXCLUDE_CATEGORIES: frozenset[str] = frozenset({"stablecoin"})

# Prefer CoinDesk / Decrypt / The Block when matching the shared news pool.
_PREFERRED_SOURCES = (
    "coindesk",
    "decrypt",
    "the block",
    "cointelegraph",
    "blockworks",
)


def _pct_30d(row: dict[str, Any]) -> float | None:
    raw = row.get("pct_30d")
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if v != v:  # NaN
        return None
    return v


def pick_top_movers(
    rows: list[dict[str, Any]],
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Largest absolute 1M % moves in the top-50 table (stablecoins excluded)."""
    candidates: list[dict[str, Any]] = []
    for row in rows:
        cat = str(row.get("category") or "").lower()
        if cat in MOVER_EXCLUDE_CATEGORIES:
            continue
        pct = _pct_30d(row)
        if pct is None:
            continue
        sym = str(row.get("symbol") or "").strip().upper()
        name = str(row.get("name") or sym or "—").strip()
        candidates.append(
            {
                "symbol": sym,
                "name": name,
                "pct_30d": round(pct, 4),
                "category": cat,
                "category_label": row.get("category_label") or "",
                "detail_url": row.get("detail_url") or "",
            }
        )
    candidates.sort(key=lambda x: abs(float(x["pct_30d"])), reverse=True)
    return candidates[: max(1, limit)]


def _name_tokens(name: str) -> list[str]:
    stop = frozenset({"the", "and", "network", "protocol", "token", "coin"})
    parts = re.findall(r"[a-z0-9]{3,}", name.lower())
    return [p for p in parts if p not in stop]


def _article_matches_mover(article: dict[str, Any], symbol: str, name: str) -> bool:
    sym = symbol.strip().upper()
    if not sym:
        return False
    title = str(article.get("title") or "")
    summary = str(article.get("summary") or "")
    blob = f"{title} {summary}".lower()
    if re.search(rf"\b{re.escape(sym.lower())}\b", blob):
        return True
    if sym == "BTC" and "bitcoin" in blob:
        return True
    if sym == "ETH" and "ethereum" in blob:
        return True
    name_l = name.strip().lower()
    if len(name_l) >= 4 and name_l in blob:
        return True
    for tok in _name_tokens(name):
        if len(tok) >= 5 and tok in blob:
            return True
    return False


def _article_sort_key(article: dict[str, Any]) -> tuple[int, float]:
    src = str(article.get("source") or "").lower()
    pref = 0
    for i, needle in enumerate(_PREFERRED_SOURCES):
        if needle in src:
            pref = len(_PREFERRED_SOURCES) - i
            break
    pub = article.get("published")
    ts = 0.0
    if hasattr(pub, "timestamp"):
        ts = pub.timestamp()
    return (pref, ts)


def match_headline_from_articles(
    articles: list[dict[str, Any]],
    *,
    symbol: str,
    name: str,
) -> dict[str, str] | None:
    hits = [a for a in articles if _article_matches_mover(a, symbol, name)]
    if not hits:
        return None
    hits.sort(key=_article_sort_key, reverse=True)
    top = hits[0]
    title = str(top.get("title") or "").strip()
    link = str(top.get("link") or "").strip()
    if not title:
        return None
    out: dict[str, str] = {
        "title": title,
        "source": str(top.get("source") or "").strip(),
    }
    if link:
        out["link"] = link
    return out


def _google_news_rss_url(query: str) -> str:
    return (
        "https://news.google.com/rss/search?q="
        + quote_plus(query)
        + "&hl=en-US&gl=US&ceid=US:en"
    )


def fetch_headline_from_google_news(
    *,
    symbol: str,
    name: str,
    direction: str,
) -> dict[str, str] | None:
    """One recent headline from Google News when the shared pool has no match."""
    move = "rally" if direction == "up" else "selloff"
    queries = (
        f"{name} crypto {move}",
        f"{symbol} cryptocurrency price",
        f"{name} price",
    )
    for q in queries:
        try:
            feed = feedparser.parse(_google_news_rss_url(q))
        except Exception:
            continue
        for entry in getattr(feed, "entries", [])[:6]:
            title = str(getattr(entry, "title", "") or "").strip()
            link = str(getattr(entry, "link", "") or "").strip()
            if not title:
                continue
            out: dict[str, str] = {"title": title, "source": "Google News"}
            if link:
                out["link"] = link
            return out
    return None


def enrich_movers_with_context(
    movers: list[dict[str, Any]],
    articles: list[dict[str, Any]] | None,
    *,
    use_google_fallback: bool = True,
) -> list[dict[str, Any]]:
    pool = list(articles or [])
    enriched: list[dict[str, Any]] = []
    for m in movers:
        pct = float(m["pct_30d"])
        direction = "up" if pct >= 0 else "down"
        sym = str(m.get("symbol") or "")
        name = str(m.get("name") or sym)
        ctx = match_headline_from_articles(pool, symbol=sym, name=name)
        if not ctx and use_google_fallback:
            ctx = fetch_headline_from_google_news(
                symbol=sym, name=name, direction=direction
            )
        item = dict(m)
        item["direction"] = direction
        if ctx:
            item["context"] = ctx
        else:
            item["context"] = {
                "title": (
                    "No recent headline matched in the dashboard news pool; "
                    "check major crypto outlets for catalysts."
                ),
                "source": "",
            }
        enriched.append(item)
    return enriched


def top_movers_callout_payload(
    rows: list[dict[str, Any]],
    articles: list[dict[str, Any]] | None = None,
    *,
    limit: int = 3,
) -> dict[str, object]:
    movers = pick_top_movers(rows, limit=limit)
    if not movers:
        return {"title": "Top movers (1M)", "movers": []}
    movers = enrich_movers_with_context(movers, articles)
    return {
        "title": "Top movers (1M)",
        "footnote": (
            "Largest 1-month % moves in the top-50 table (stablecoins excluded). "
            "Context lines match recent headlines from dashboard news feeds, with Google News as fallback."
        ),
        "movers": movers,
    }


def _fmt_signed_pct(pct: float | None) -> str:
    if pct is None:
        return "—"
    try:
        n = float(pct)
    except (TypeError, ValueError):
        return "—"
    if n != n:
        return "—"
    return f"{n:+.2f}%"


def _kpi_line(label: str, value: str, pct: float | None, *, window: str = "1M") -> str:
    delta = _fmt_signed_pct(pct)
    if delta == "—":
        return f"<strong>{escape(label)}:</strong> {escape(value)}."
    return (
        f"<strong>{escape(label)}:</strong> {escape(value)} "
        f"({delta} over {escape(window)})."
    )


def _mover_takeaway_li(mover: dict[str, Any]) -> str:
    sym = escape(str(mover.get("symbol") or ""))
    name = escape(str(mover.get("name") or sym))
    pct = float(mover.get("pct_30d") or 0)
    direction = "gained" if pct >= 0 else "lost"
    ctx = mover.get("context") or {}
    headline = str(ctx.get("title") or "").strip()
    link = str(ctx.get("link") or "").strip()
    lead = (
        f"<strong>{sym}</strong> ({name}) {direction} about <strong>{abs(pct):.1f}%</strong> "
        f"over one month—the largest move in the top-50 table (stablecoins excluded)."
    )
    if headline and "no recent headline matched" not in headline.lower():
        if link:
            lead += (
                f' Recent coverage: <a href="{escape(link, quote=True)}" '
                f'target="_blank" rel="noopener noreferrer">{escape(headline)}</a>.'
            )
        else:
            lead += f" Recent coverage: {escape(headline)}."
    return f"<li>{lead}</li>"


def crypto_key_takeaways_html(
    rows: list[dict[str, Any]],
    kpis: dict[str, Any],
    articles: list[dict[str, Any]] | None = None,
    *,
    mover_limit: int = 3,
) -> str:
    """HTML ``ul`` block for static Key observations (ETP / RWA callout pattern)."""
    bullets: list[str] = []

    primary = kpis.get("primary") or {}
    if primary.get("value_display"):
        delta = (primary.get("delta") or {}).get("pct")
        bullets.append(
            "<li>"
            + _kpi_line(
                str(primary.get("label") or "Total market cap"),
                str(primary.get("value_display") or "—"),
                delta,
            )
            + "</li>"
        )

    btc_dom = kpis.get("btc_dominance") or {}
    stable = kpis.get("stablecoin_share") or {}
    if btc_dom.get("value_display") and stable.get("value_display"):
        dom_pct = (btc_dom.get("delta") or {}).get("pct")
        st_pct = (stable.get("delta") or {}).get("pct")
        bullets.append(
            "<li>"
            + _kpi_line("BTC dominance", str(btc_dom.get("value_display")), dom_pct)
            + " "
            + _kpi_line("stablecoin share of the top-50 list", str(stable.get("value_display")), st_pct)
            + "</li>"
        )

    btc = kpis.get("btc") or {}
    eth = kpis.get("eth") or {}
    if btc.get("value_display") and eth.get("value_display"):
        bullets.append(
            "<li>"
            + _kpi_line("BTC", str(btc.get("value_display")), (btc.get("delta") or {}).get("pct"))
            + " "
            + _kpi_line("ETH", str(eth.get("value_display")), (eth.get("delta") or {}).get("pct"))
            + " Spot prices are from the top-50 table (CoinGecko with CoinCap fallback).</li>"
        )

    movers = enrich_movers_with_context(
        pick_top_movers(rows, limit=mover_limit),
        articles,
    )
    bullets.extend(_mover_takeaway_li(m) for m in movers)

    if not bullets:
        return ""

    note = (
        '<p class="takeaways__note">Context only—not investment advice. KPIs use CoinPaprika and the top-50 '
        "list; headline links are matched from dashboard news feeds (Google News fallback).</p>"
    )
    return (
        '<div class="takeaways">'
        '<ul class="crypto-story-callout__list">'
        + "".join(bullets)
        + "</ul>"
        + note
        + "</div>"
    )
