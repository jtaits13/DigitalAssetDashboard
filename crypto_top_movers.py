"""Top 1M movers for the crypto prices page + optional headline context."""

from __future__ import annotations

import re
import statistics
from collections import defaultdict
from html import escape
from typing import Any
from urllib.parse import quote_plus

import feedparser

from crypto_categories import category_takeaway_label, crypto_category

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


def _row_cap_usd(row: dict[str, Any]) -> float:
    try:
        v = float(row.get("market_cap_usd") or 0)
    except (TypeError, ValueError):
        return 0.0
    return v if v > 0 else 0.0


def _delta_pct_from_kpi(block: dict[str, Any] | None) -> float | None:
    if not block:
        return None
    d = block.get("delta") or {}
    p = d.get("pct")
    if p is None:
        return None
    try:
        v = float(p)
    except (TypeError, ValueError):
        return None
    if v != v:
        return None
    return v


def _breadth_takeaway_li(rows: list[dict[str, Any]]) -> str:
    """Up / down / flat counts among non-stable names with a 1M % change."""
    up = down = flat = 0
    for row in rows:
        cat = str(row.get("category") or "").lower()
        if cat in MOVER_EXCLUDE_CATEGORIES:
            continue
        pct = _pct_30d(row)
        if pct is None:
            continue
        if pct > 0.5:
            up += 1
        elif pct < -0.5:
            down += 1
        else:
            flat += 1
    n = up + down + flat
    if n < 5:
        return ""
    tone_label = (
        "Gains broadened among top-50 alts"
        if up > down + 5
        else "Losses broadened among top-50 alts"
        if down > up + 5
        else "Top-50 alts showed mixed 1M moves"
    )
    return (
        f"<li><strong>{tone_label}:</strong> "
        f"{up} names up more than ~0.5%, {down} down more than ~0.5%, and {flat} roughly flat "
        f"out of <strong>{n}</strong> non-stable coins with a valid 1M % (top-50 table).</li>"
    )


def _category_rotation_takeaway_li(rows: list[dict[str, Any]]) -> str:
    """Cap-weighted average 1M % by coarse category (l1, defi, meme, cex, rwa, other)."""
    sums: dict[str, list[tuple[float, float]]] = defaultdict(list)
    symbols_by_cat: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        sym = str(row.get("symbol") or "").strip().upper()
        name = str(row.get("name") or "")
        cat = crypto_category(sym, name)
        if cat in MOVER_EXCLUDE_CATEGORIES:
            continue
        pct = _pct_30d(row)
        if pct is None:
            continue
        cap = _row_cap_usd(row)
        sums[cat].append((pct, cap))
        if sym and sym not in symbols_by_cat[cat]:
            symbols_by_cat[cat].append(sym)

    avgs: dict[str, float] = {}
    for cat, pairs in sums.items():
        tw = sum(c for _, c in pairs)
        if tw > 0:
            avgs[cat] = sum(p * c for p, c in pairs) / tw
        elif pairs:
            avgs[cat] = statistics.mean(p for p, _ in pairs)

    if len(avgs) < 2:
        return ""

    best_cat = max(avgs, key=avgs.get)
    worst_cat = min(avgs, key=avgs.get)
    if best_cat == worst_cat:
        return ""
    b = avgs[best_cat]
    w = avgs[worst_cat]
    if abs(b - w) < 0.35:
        return ""

    bl = escape(
        category_takeaway_label(
            best_cat,
            example_symbols=symbols_by_cat.get(best_cat),
        )
    )
    wl = escape(
        category_takeaway_label(
            worst_cat,
            example_symbols=symbols_by_cat.get(worst_cat),
        )
    )
    return (
        f"<li><strong>{bl} outpaced {wl} over 1M:</strong> "
        f"the stronger group averaged about <strong>{b:+.1f}%</strong> cap-weighted in the top-50, while "
        f"the weaker averaged about <strong>{w:+.1f}%</strong>—the widest gap among category tabs.</li>"
    )


def _structure_takeaway_li(_rows: list[dict[str, Any]], kpis: dict[str, Any]) -> str:
    """Interpretation: majors vs alts, dominance vs flat total, or stablecoin share shift."""
    btc_d = _delta_pct_from_kpi(kpis.get("btc"))
    eth_d = _delta_pct_from_kpi(kpis.get("eth"))
    primary_d = _delta_pct_from_kpi(kpis.get("primary"))
    dom_d = _delta_pct_from_kpi(kpis.get("btc_dominance"))
    st_d = _delta_pct_from_kpi(kpis.get("stablecoin_share"))

    if btc_d is not None and eth_d is not None:
        spread = btc_d - eth_d
        if abs(spread) >= 0.75:
            if spread > 0:
                return (
                    "<li><strong>BTC outpaced ETH over 1M:</strong> "
                    f"about <strong>{spread:.1f}pp</strong> on spot from the top-50 table.</li>"
                )
            return (
                "<li><strong>ETH outpaced BTC over 1M:</strong> "
                f"about <strong>{abs(spread):.1f}pp</strong> on spot from the top-50 table.</li>"
            )

    if primary_d is not None and dom_d is not None and abs(primary_d) < 2.0 and abs(dom_d) >= 0.12:
        return (
            "<li><strong>Bitcoin drove moves in a flat market:</strong> "
            f"aggregate market cap moved about <strong>{primary_d:+.1f}%</strong> over 1M while "
            f"<strong>BTC dominance</strong> shifted about <strong>{dom_d:+.2f}pp</strong>.</li>"
        )

    if st_d is not None and dom_d is not None and abs(st_d) >= 0.08:
        return (
            "<li><strong>Stablecoin share moved with BTC dominance:</strong> "
            f"stablecoin share of the top-50 list shifted about <strong>{st_d:+.2f}pp</strong> over 1M "
            f"alongside a <strong>BTC dominance</strong> change of about <strong>{dom_d:+.2f}pp</strong>.</li>"
        )

    dom_v = (kpis.get("btc_dominance") or {}).get("value_display")
    st_v = (kpis.get("stablecoin_share") or {}).get("value_display")
    if dom_v and st_v:
        return (
            "<li><strong>Dominance and stablecoin share diverged this month:</strong> "
            f"<strong>BTC dominance</strong> is {escape(str(dom_v))} and "
            f"<strong>stablecoin share of the top-50</strong> is {escape(str(st_v))}—compare whether "
            "liquidity and beta leaned the same direction.</li>"
        )

    return ""


def _li_to_candidate(
    bullet_id: str,
    li_html: str,
    score: float,
    themes: tuple[str, ...],
) -> ObservationCandidate | None:
    import re

    from key_observations.models import ObservationCandidate

    m = re.match(
        r"<li><strong>(.*?)</strong>\s*(.*)</li>\s*$",
        li_html.strip(),
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not m:
        return None
    lead = m.group(1).strip()
    if not lead.endswith(":"):
        lead = f"{lead}:"
    return ObservationCandidate(
        id=bullet_id,
        lead=lead,
        body=m.group(2).strip(),
        score=score,
        themes=themes,
        source="data",
    )


def crypto_key_takeaways_html(
    rows: list[dict[str, Any]],
    kpis: dict[str, Any],
    articles: list[dict[str, Any]] | None = None,
    *,
    mover_limit: int = 3,
) -> str:
    """HTML for static Key observations: table-derived signals ranked with industry headlines."""
    del mover_limit
    from key_observations import build_key_observations_html

    candidates: list[ObservationCandidate] = []
    b1 = _breadth_takeaway_li(rows)
    if b1:
        c = _li_to_candidate("crypto_breadth", b1, 72.0, ("market_structure",))
        if c:
            candidates.append(c)
    b2 = _category_rotation_takeaway_li(rows)
    if b2:
        c = _li_to_candidate("crypto_rotation", b2, 68.0, ("market_structure",))
        if c:
            candidates.append(c)
    b3 = _structure_takeaway_li(rows, kpis)
    if b3:
        themes: tuple[str, ...] = ("etf_flows", "market_structure")
        if "stablecoin" in b3.lower():
            themes = ("market_structure", "etf_flows")
        c = _li_to_candidate("crypto_structure", b3, 66.0, themes)
        if c:
            candidates.append(c)

    if not candidates and not articles:
        return ""

    return build_key_observations_html(
        "crypto",
        candidates,
        articles,
        context_note=(
            "Context only—not investment advice. Observations rank the top-50 table and KPI math on this page "
            "against recent crypto and ETF headlines."
        ),
        min_bullets=2,
        max_bullets=4,
        variant="crypto",
    )
