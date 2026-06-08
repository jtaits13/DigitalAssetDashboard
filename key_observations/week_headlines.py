"""Pick top structural headlines for the weekly newsletter (cluster + score, Option B)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from key_observations.models import TopicTheme
from key_observations.news import _article_age_days, _article_sort_key, _article_text, _matches_theme
from key_observations.topics import TOPIC_THEMES

_PREFERRED_SOURCES = (
    "coindesk",
    "cointelegraph",
    "the block",
    "bloomberg",
    "reuters",
    "financial times",
    "wsj",
    "sec.gov",
    "blackrock",
)

_EXCLUDED_THEME_IDS = frozenset({"market_structure"})

_PRICE_EXCLUDE_RES = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"why is (the )?crypto market down",
        r"\b(bitcoin|btc|ether|eth|crypto|zcash|solana|doge) (rally|tumble|crash|surge|slips|jumps|falls|rises|drops|soars|bounces)\b",
        r"\bbounces? \d",
        r"\b(rally|surge|slips?|jumps?|falls?|rises?|drops?|soars?|bounces?) \d+(\.\d+)?%?",
        r"\b\d+(\.\d+)?% (gain|loss|rise|fall|bounce|rally|drop|surge)\b",
        r"\bmarket (down|up) today\b",
        r"\bmarket cap\b",
        r"\bliquidation",
        r"\b(selloff|sell-off)\b",
        r"\bcorrection\b",
        r"\bprice prediction\b",
        r"\bcrypto market down\b",
        r"\bweekly outflows?\b",
        r"\betfs? log \$\d",
        r"\bdumped \d+k btc\b",
        r"\bmultibillion outflow\b",
        r"\blargest .{0,24}(outflow|inflow) (streak|since)\b",
        r"\b(blame|tumble).{0,20}(bitcoin|btc|inflation)\b",
        r"\b(buys?|sells?) [\d,]+ (bitcoin|btc)\b",
        r"\b(buys?|sells?) \d[\d,]* (bitcoin|btc)\b",
        r"\bstrategy buys\b",
        r"\b(boosts?|adds?|treasury).{0,30}\b(eth|bitcoin|btc)\b",
        r"\bselling \$\d+(\.\d+)? million of coins\b",
        r"\bcalming investors\b",
        r"\bbitcoin giant\b",
        r"\bpresidential pardon\b",
        r"\bofficially asks trump\b",
        r"\bfor bitcoin bulls?\b",
        r"\bmoving average\b",
        r"\b(slips?|rallies?|drops?|surges?) below\b",
        r"\bgold (slips?|rallies?|drops?|surges?)\b",
    )
)

_STRUCTURAL_BOOST_RE = re.compile(
    r"\b(sec|approval|approved|nyse|tokeniz|regulation|legislation|genius act|blackrock|securitize|"
    r"custody|stablecoin|reserves?|imf|ucits|listing|filing|launch|acquires|acquisition|bank|payments)\b",
    re.IGNORECASE,
)

_FLOW_ONLY_RE = re.compile(
    r"\b(etf flow|net flow|inflow|outflow|logged \$\d|aum fell|professionals? dumped)\b",
    re.IGNORECASE,
)

_TRADING_NOISE_RE = re.compile(
    r"\b(dumps?|dumped|pumps?|pumped|yolo|whale sold|whale bought)\b",
    re.IGNORECASE,
)

_STOPWORDS = frozenset(
    {
        "that",
        "this",
        "with",
        "from",
        "into",
        "over",
        "after",
        "about",
        "what",
        "when",
        "where",
        "which",
        "while",
        "have",
        "been",
        "will",
        "your",
        "their",
        "they",
        "them",
        "than",
        "then",
        "just",
        "more",
        "most",
        "some",
        "such",
        "only",
        "also",
        "here",
        "there",
        "could",
        "would",
        "should",
        "says",
        "said",
        "week",
        "ahead",
        "today",
        "news",
        "google",
    }
)

_THEME_FAMILY: dict[str, str] = {
    "regulation": "regulation",
    "stablecoin_policy": "stablecoins",
    "bank_integration": "stablecoins",
    "tokenization_growth": "tokenization",
    "tokenized_treasuries": "tokenization",
    "tokenized_equities": "tokenization",
    "institutional_adoption": "tokenization",
    "macro_rates": "macro",
    "institutional_settlement": "tmmf",
    "issuer_models": "tmmf",
    "chain_efficiency": "infrastructure",
    "multichain": "infrastructure",
    "rates_yields": "macro",
    "etf_flows": "etp_flows",
    "market_sizing": "etp",
    "launch_pipeline": "etp",
    "concentration": "etp",
    "infrastructure": "infrastructure",
}


@dataclass(frozen=True)
class WeekHeadlinePick:
    title: str
    link: str
    source: str
    score: float
    theme_id: str | None
    theme_family: str
    outlet_count: int


def _all_themes() -> list[TopicTheme]:
    out: list[TopicTheme] = []
    for themes in TOPIC_THEMES.values():
        for theme in themes:
            if theme.id not in _EXCLUDED_THEME_IDS:
                out.append(theme)
    return out


def _source_weight(article: dict[str, Any]) -> float:
    src = str(article.get("source") or "").lower()
    for i, needle in enumerate(_PREFERRED_SOURCES):
        if needle in src:
            return 2.0 + (len(_PREFERRED_SOURCES) - i) * 0.15
    return 1.0


def _is_price_headline(article: dict[str, Any]) -> bool:
    text = _article_text(article)
    if any(pat.search(text) for pat in _PRICE_EXCLUDE_RES):
        return True
    if _TRADING_NOISE_RE.search(text) and not _STRUCTURAL_BOOST_RE.search(text):
        return True
    return False


def _title_tokens(title: str) -> set[str]:
    words = re.findall(r"[a-z0-9]{4,}", title.lower())
    return {w for w in words if w not in _STOPWORDS}


def _similar_token_sets(a: set[str], b: set[str]) -> bool:
    if not a or not b:
        return False
    inter = len(a & b)
    if inter >= 3:
        return True
    union = len(a | b)
    return union > 0 and (inter / union) >= 0.42


def _theme_for_article(article: dict[str, Any], themes: list[TopicTheme]) -> str | None:
    for theme in themes:
        if _matches_theme(article, theme):
            return theme.id
    return None


def _theme_family(theme_id: str | None) -> str:
    if not theme_id:
        return "general"
    return _THEME_FAMILY.get(theme_id, theme_id)


def _cluster_articles(articles: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    clusters: list[list[dict[str, Any]]] = []
    cluster_tokens: list[set[str]] = []
    for art in articles:
        title = str(art.get("title") or "").strip()
        if not title:
            continue
        tokens = _title_tokens(title)
        placed = False
        for idx, existing in enumerate(cluster_tokens):
            if _similar_token_sets(tokens, existing):
                clusters[idx].append(art)
                existing |= tokens
                placed = True
                break
        if not placed:
            clusters.append([art])
            cluster_tokens.append(set(tokens))
    return clusters


def _score_cluster(
    items: list[dict[str, Any]],
    *,
    theme_id: str | None,
) -> tuple[float, str, str, str, int]:
    sources: set[str] = set()
    score = 0.0
    best_title = ""
    best_link = ""
    best_source = ""
    best_rank = (-1, -1.0, -1.0)
    youngest_age = 999.0

    for art in items:
        src = str(art.get("source") or "").strip()
        if src:
            sources.add(src.lower())
        score += _source_weight(art)
        age = _article_age_days(art)
        if age is not None:
            youngest_age = min(youngest_age, age)
        rank = _article_sort_key(art)
        if rank > best_rank:
            best_rank = rank
            best_title = str(art.get("title") or "").strip()
            best_link = str(art.get("link") or "").strip()
            best_source = src or "Industry"

    outlet_count = len(sources)
    if outlet_count > 1:
        score += 3.0 * (outlet_count - 1)

    if youngest_age <= 2:
        score += 4.0
    elif youngest_age <= 5:
        score += 2.0
    elif youngest_age <= 7:
        score += 1.0

    text = _article_text({"title": best_title, "summary": "", "source": best_source, "category": ""})
    if _STRUCTURAL_BOOST_RE.search(text):
        score += 5.0
    if _FLOW_ONLY_RE.search(text) and not _STRUCTURAL_BOOST_RE.search(text):
        score -= 10.0

    if theme_id in {"regulation", "tokenization_growth", "stablecoin_policy", "launch_pipeline", "institutional_adoption"}:
        score += 3.0
    if theme_id == "etf_flows":
        score -= 4.0

    return score, best_title, best_link, best_source, outlet_count


def pick_week_headlines(
    articles: list[dict[str, Any]] | None,
    *,
    n: int = 3,
    max_age_days: float = 7.0,
) -> list[WeekHeadlinePick]:
    """Return top ``n`` non-price structural stories from the last week."""
    pool = list(articles or [])
    themes = _all_themes()

    recent: list[dict[str, Any]] = []
    for art in pool:
        if _is_price_headline(art):
            continue
        age = _article_age_days(art)
        if age is not None and age > max_age_days:
            continue
        if str(art.get("title") or "").strip():
            recent.append(art)

    clusters = _cluster_articles(recent)
    ranked: list[WeekHeadlinePick] = []
    for items in clusters:
        theme_id = None
        for art in sorted(items, key=_article_sort_key, reverse=True):
            theme_id = _theme_for_article(art, themes)
            if theme_id:
                break
        score, title, link, source, outlet_count = _score_cluster(items, theme_id=theme_id)
        if not title:
            continue
        ranked.append(
            WeekHeadlinePick(
                title=title,
                link=link,
                source=source,
                score=score,
                theme_id=theme_id,
                theme_family=_theme_family(theme_id),
                outlet_count=outlet_count,
            )
        )

    ranked.sort(key=lambda c: c.score, reverse=True)

    picked: list[WeekHeadlinePick] = []
    used_families: set[str] = set()
    for cluster in ranked:
        if cluster.theme_family in used_families:
            continue
        if cluster.theme_family == "etp_flows":
            continue
        picked.append(cluster)
        used_families.add(cluster.theme_family)
        if len(picked) >= n:
            break

    if len(picked) < n:
        for cluster in ranked:
            if cluster in picked:
                continue
            if cluster.theme_family == "etp_flows":
                continue
            picked.append(cluster)
            if len(picked) >= n:
                break

    return picked[:n]
