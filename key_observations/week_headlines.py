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
    r"\b(etf flow|net flow|inflow|outflow|outflows?|logged \$\d|aum fell|professionals? dumped|"
    r"bleed(?:s|ing)?|flow streak|weekly outflow)\b",
    re.IGNORECASE,
)

_LINK_ANCHOR_RE = re.compile(
    r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)

_NOISE_NOTABLE_RE = re.compile(
    r"\b(golden cross|market down today|canary in the coal mine|price prediction|"
    r"why is (?:the )?crypto market down|liquidation|slides below \$|weekly outflow)\b",
    re.IGNORECASE,
)

_MARKET_SIZING_REJECT_RE = re.compile(
    r"\b(outflow|inflow|bleed|streak|liquidat|exits? entire|positions?|"
    r"arthur hayes|hype|near\b|war and ai)\b",
    re.IGNORECASE,
)

_MARKET_SIZING_ALLOW_RE = re.compile(
    r"\b(estimate|forecast|scenario|market size|billion|analyst|2026|"
    r"assets under management|top \$\d|say analysts|planning range)\b",
    re.IGNORECASE,
)

_LAUNCH_PIPELINE_SIGNAL_RE = re.compile(
    r"\b(filing|filings|s-1|pipeline|etf application|wall of filing|product pipeline|"
    r"crypto etf|spot etf|next wave)\b",
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
        "remain",
        "among",
        "early",
        "shows",
        "still",
        "becoming",
        "largest",
        "several",
        "broadened",
        "roughly",
        "flat",
        "valid",
        "table",
        "names",
        "group",
        "weaker",
        "stronger",
        "crowded",
        "large",
        "still",
        "lane",
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


def executive_news_text_allowed(text: str) -> bool:
    """Whether plain text fits executive newsletter news/headline topics."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text or _EXECUTIVE_HEADLINE_EXCLUDE_RE.search(text):
        return False
    stub: dict[str, Any] = {"title": text, "summary": "", "source": "", "category": ""}
    if _is_price_headline(stub):
        return False
    if _fund_launch_category(stub) is not None:
        return True
    if _EXECUTIVE_STABLECOIN_NEWS_RE.search(text):
        return True
    return bool(
        _EXECUTIVE_REGULATORY_RE.search(text) and _EXECUTIVE_DIGITAL_ASSET_RE.search(text)
    )


def _executive_headline_bucket(
    article: dict[str, Any],
) -> tuple[str, str | None, str] | None:
    """Return (bucket, theme_id, theme_family) for executive headline eligibility."""
    text = _article_text(article)
    if _EXECUTIVE_HEADLINE_EXCLUDE_RE.search(text) or _is_price_headline(article):
        return None

    launch_cat = _fund_launch_category(article)
    if launch_cat:
        theme_id, theme_family = {
            "tmmf": ("institutional_settlement", "tmmf"),
            "stablecoin_reserve": ("stablecoin_policy", "stablecoins"),
            "crypto_etf": ("launch_pipeline", "etp"),
        }[launch_cat]
        return (f"launch:{launch_cat}", theme_id, theme_family)

    if _EXECUTIVE_STABLECOIN_NEWS_RE.search(text):
        return ("stablecoin_news", "stablecoin_policy", "stablecoins")

    if _EXECUTIVE_REGULATORY_RE.search(text) and _EXECUTIVE_DIGITAL_ASSET_RE.search(text):
        return ("regulatory", "regulation", "regulation")

    return None


def pick_executive_week_headlines(
    articles: list[dict[str, Any]] | None,
    *,
    n: int = 3,
    max_age_days: float = 7.0,
) -> list[WeekHeadlinePick]:
    """Top ``n`` headlines scoped to executive brief topics (launches, stablecoins, regulation)."""
    pool = list(articles or [])
    recent: list[dict[str, Any]] = []
    bucket_by_art: dict[int, tuple[str, str | None, str]] = {}

    for art in pool:
        bucket_info = _executive_headline_bucket(art)
        if bucket_info is None:
            continue
        age = _article_age_days(art)
        if age is not None and age > max_age_days:
            continue
        if not str(art.get("title") or "").strip():
            continue
        bucket_by_art[id(art)] = bucket_info
        recent.append(art)

    clusters = _cluster_articles(recent)
    ranked: list[WeekHeadlinePick] = []
    for items in clusters:
        theme_id: str | None = None
        theme_family = "general"
        bucket = ""
        for art in sorted(items, key=_article_sort_key, reverse=True):
            info = bucket_by_art.get(id(art))
            if info:
                bucket, theme_id, theme_family = info
                break
        if theme_family not in _EXECUTIVE_HEADLINE_FAMILIES:
            continue
        score, title, link, source, outlet_count = _score_cluster(items, theme_id=theme_id)
        if bucket.startswith("launch:"):
            score += 8.0
        elif bucket == "regulatory":
            score += 4.0
        if not title:
            continue
        ranked.append(
            WeekHeadlinePick(
                title=title,
                link=link,
                source=source,
                score=score,
                theme_id=theme_id,
                theme_family=theme_family,
                outlet_count=outlet_count,
            )
        )

    ranked.sort(key=lambda c: c.score, reverse=True)

    picked: list[WeekHeadlinePick] = []
    used_families: set[str] = set()
    for cluster in ranked:
        if cluster.theme_family in used_families:
            continue
        picked.append(cluster)
        used_families.add(cluster.theme_family)
        if len(picked) >= n:
            break

    if len(picked) < n:
        for cluster in ranked:
            if cluster in picked:
                continue
            picked.append(cluster)
            if len(picked) >= n:
                break

    return picked[:n]


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


FundLaunchCategory = str  # "tmmf" | "stablecoin_reserve" | "crypto_etf"

_MAJOR_INSTITUTION_RE = re.compile(
    r"\b(state street|blackrock|fidelity|franklin templeton|jpmorgan|jpmorgan chase|jpm\b|"
    r"goldman sachs|morgan stanley|citigroup|citi\b|bank of america|bofa\b|bny mellon|"
    r"vanguard|invesco|wisdomtree|grayscale|schwab|charles schwab|ubs\b|hsbc|dbs\b|"
    r"northern trust|wells fargo|amex|american express)\b",
    re.IGNORECASE,
)
_LAUNCH_VERB_RE = re.compile(
    r"\b(launches?|launched|debuts?|debuted|unveils?|unveiled|introduces?|introduced|"
    r"rolls out|rolled out|files for|filing for|lists? new|newly listed)\b",
    re.IGNORECASE,
)
_POST_LAUNCH_FLOW_RE = re.compile(
    r"\b(since launch|since its launch|draw in.*launch|hits? all[- ]time|aum since)\b",
    re.IGNORECASE,
)
_STABLECOIN_RESERVE_LAUNCH_RE = re.compile(
    r"\b(stablecoin reserves?|reserves? money market|money market fund.{0,40}stablecoin|"
    r"stablecoin.{0,40}money market fund|genius act.{0,40}money market)\b",
    re.IGNORECASE,
)
_TMMF_LAUNCH_RE = re.compile(
    r"\b(tokenized money[- ]market|tokenized mmf|tokenized fund|on[- ]chain money[- ]market|"
    r"tokenized cash fund|buidl)\b",
    re.IGNORECASE,
)
_CRYPTO_ETF_LAUNCH_RE = re.compile(
    r"\b(bitcoin etf|ethereum etf|crypto etf|spot bitcoin etf|covered[- ]call.{0,30}etf|"
    r"premium income etf|income etf.{0,20}bitcoin|ishares bitcoin)\b",
    re.IGNORECASE,
)

# Executive weekly brief: headlines / news bullets must match one of these scopes.
_EXECUTIVE_DIGITAL_ASSET_RE = re.compile(
    r"\b(crypto|cryptocurrency|digital asset|blockchain|tokeniz|tokenization|stablecoin|"
    r"bitcoin|ethereum|defi|web3|on-?chain|\brwa\b)\b",
    re.IGNORECASE,
)
_EXECUTIVE_REGULATORY_RE = re.compile(
    r"\b(sec|cftc|regulat|legislation|enforcement|compliance|genius act|mica|"
    r"bitlicense|licensing|rulemaking|oversight|approved|approval|proposed rule|final rule)\b",
    re.IGNORECASE,
)
_EXECUTIVE_STABLECOIN_NEWS_RE = re.compile(
    r"\b(stablecoin|usdc|usdt|usdp|dai|payment stablecoin|genius act|"
    r"stablecoin reserves?|issuer reserves?|circle\b|tether|bitlicense)\b",
    re.IGNORECASE,
)
_EXECUTIVE_HEADLINE_EXCLUDE_RE = re.compile(
    r"\b(prediction market|kalshi|polymarket|meme coin|nft\b|golden cross|"
    r"price prediction|why is (?:the )?crypto market down)\b",
    re.IGNORECASE,
)
_EXECUTIVE_HEADLINE_FAMILIES = frozenset({"tmmf", "stablecoins", "etp", "regulation"})


@dataclass(frozen=True)
class FundLaunch:
    category: FundLaunchCategory
    title: str
    link: str
    source: str
    summary: str


def _fund_launch_category(art: dict[str, Any]) -> FundLaunchCategory | None:
    text = _article_text(art)
    if _is_price_headline(art):
        return None
    if not _LAUNCH_VERB_RE.search(text):
        return None
    if _POST_LAUNCH_FLOW_RE.search(text) and not _LAUNCH_VERB_RE.search(
        str(art.get("title") or "")
    ):
        return None
    if not _MAJOR_INSTITUTION_RE.search(text):
        return None
    if _STABLECOIN_RESERVE_LAUNCH_RE.search(text):
        return "stablecoin_reserve"
    if _CRYPTO_ETF_LAUNCH_RE.search(text) and re.search(r"\betf\b", text, re.IGNORECASE):
        if re.search(r"tokenized stock|tokenized equit", text, re.IGNORECASE):
            return None
        return "crypto_etf"
    if _TMMF_LAUNCH_RE.search(text):
        if _STABLECOIN_RESERVE_LAUNCH_RE.search(text):
            return "stablecoin_reserve"
        return "tmmf"
    return None


def pick_fund_launch(
    articles: list[dict[str, Any]] | None,
    category: FundLaunchCategory,
    *,
    max_age_days: float = 14.0,
) -> FundLaunch | None:
    pool = list(articles or [])
    best_rank: tuple[Any, ...] | None = None
    best_art: dict[str, Any] | None = None
    for art in pool:
        age = _article_age_days(art)
        if age is not None and age > max_age_days:
            continue
        if _fund_launch_category(art) != category:
            continue
        rank = _article_sort_key(art)
        if best_rank is None or rank > best_rank:
            best_rank = rank
            best_art = art
    if not best_art:
        return None
    return FundLaunch(
        category=category,
        title=str(best_art.get("title") or "").strip(),
        link=str(best_art.get("link") or "").strip(),
        source=str(best_art.get("source") or "Industry").strip(),
        summary=str(best_art.get("summary") or "").strip(),
    )


# Broader than headline "notable launch" gates: section takeaways include non-major issuers.
_TMMF_SECTION_LAUNCH_RE = re.compile(
    r"\b(tokenized money[- ]market|tokenized mmf|tokenized (?:money[- ]market )?fund|"
    r"on[- ]chain money[- ]market|tokenized cash(?: fund)?|buidl|benji|ibenji|"
    r"jltxx|usyc|jtrsy|wtrig|money[- ]market fund)\b",
    re.IGNORECASE,
)
_TMMF_PRODUCT_RE = re.compile(
    r"\b(buidl|benji|ibenji|jltxx|usyc|jtrsy|wtrig)\b",
    re.IGNORECASE,
)
_TMMF_ISSUER_DISPLAY = {
    "state street": "State Street",
    "blackrock": "BlackRock",
    "fidelity": "Fidelity",
    "franklin templeton": "Franklin Templeton",
    "jpmorgan": "JPMorgan",
    "jpmorgan chase": "JPMorgan",
    "jpm": "JPMorgan",
    "goldman sachs": "Goldman Sachs",
    "morgan stanley": "Morgan Stanley",
    "citigroup": "Citi",
    "citi": "Citi",
    "bank of america": "Bank of America",
    "bofa": "Bank of America",
    "bny mellon": "BNY Mellon",
    "vanguard": "Vanguard",
    "invesco": "Invesco",
    "wisdomtree": "WisdomTree",
    "grayscale": "Grayscale",
    "schwab": "Schwab",
    "charles schwab": "Schwab",
    "ubs": "UBS",
    "hsbc": "HSBC",
    "dbs": "DBS",
    "northern trust": "Northern Trust",
    "wells fargo": "Wells Fargo",
    "amex": "American Express",
    "american express": "American Express",
}
_TMMF_TITLE_ISSUER_RE = re.compile(
    r"^([A-Z][\w&.\'-]*(?:[\s-](?:[A-Z][\w&.\'-]+|and|&)){0,4})\s+"
    r"(?:launches|launched|debuts|debuted|unveils|unveiled|introduces|introduced|"
    r"rolls out|rolled out|lists|listed)",
    re.IGNORECASE,
)


def _is_tmmf_section_launch_article(art: dict[str, Any]) -> bool:
    """TMMF launch candidate for section takeaways (major-issuer not required)."""
    text = _article_text(art)
    title = str(art.get("title") or "")
    if _is_price_headline(art):
        return False
    if not _LAUNCH_VERB_RE.search(text):
        return False
    if _POST_LAUNCH_FLOW_RE.search(text) and not _LAUNCH_VERB_RE.search(title):
        return False
    if _STABLECOIN_RESERVE_LAUNCH_RE.search(text):
        return False
    if _CRYPTO_ETF_LAUNCH_RE.search(text) and re.search(r"\betf\b", text, re.IGNORECASE):
        if not _TMMF_LAUNCH_RE.search(text):
            return False
    return bool(_TMMF_SECTION_LAUNCH_RE.search(text) or _TMMF_LAUNCH_RE.search(text))


def pick_tmmf_fund_launch(
    articles: list[dict[str, Any]] | None,
    *,
    max_age_days: float = 7.0,
) -> FundLaunch | None:
    """
    Pick a TMMF fund launch for the newsletter section bullet.

    Major-institution ("notable") hits are ranked first when several match;
    non-major issuer launches still qualify.
    """
    best_rank: tuple[Any, ...] | None = None
    best_art: dict[str, Any] | None = None
    for art in articles or []:
        age = _article_age_days(art)
        if age is not None and age > max_age_days:
            continue
        if not _is_tmmf_section_launch_article(art):
            continue
        text = _article_text(art)
        is_major = 1 if _MAJOR_INSTITUTION_RE.search(text) else 0
        rank = (is_major, _article_sort_key(art))
        if best_rank is None or rank > best_rank:
            best_rank = rank
            best_art = art
    if not best_art:
        return None
    return FundLaunch(
        category="tmmf",
        title=str(best_art.get("title") or "").strip(),
        link=str(best_art.get("link") or "").strip(),
        source=str(best_art.get("source") or "Industry").strip(),
        summary=str(best_art.get("summary") or "").strip(),
    )


def _tmmf_issuer_label(text: str) -> str | None:
    m = _MAJOR_INSTITUTION_RE.search(text or "")
    if m:
        key = m.group(0).lower()
        return _TMMF_ISSUER_DISPLAY.get(key, m.group(0).strip().title())
    tm = _TMMF_TITLE_ISSUER_RE.search((text or "").strip())
    if not tm:
        return None
    name = re.sub(r"\s+", " ", tm.group(1)).strip(" -")
    if len(name) < 2 or len(name) > 48:
        return None
    return name


def _tmmf_product_label(text: str) -> str | None:
    m = _TMMF_PRODUCT_RE.search(text or "")
    return m.group(0).upper() if m else None


def tmmf_launch_takeaway_copy(launch: FundLaunch) -> tuple[str, str]:
    """Lead + market-impact body for the TMMF section launch bullet."""
    blob = f"{launch.title} {launch.summary}".strip()
    issuer = _tmmf_issuer_label(blob)
    product = _tmmf_product_label(blob)

    if issuer and product:
        lead = f"{issuer} launched {product}, a tokenized money-market fund"
        body = (
            f"{issuer}'s {product} adds another on-chain cash wrapper institutions can use "
            "for settlement and treasury, even before aggregate TMMF AUM jumps again."
        )
    elif product:
        lead = f"{product} launched as a tokenized money-market fund"
        body = (
            f"{product} expands the tokenized cash menu institutions can use for "
            "settlement and treasury workflows."
        )
    elif issuer:
        lead = f"{issuer} launched a new tokenized money-market fund"
        body = (
            f"{issuer} is widening who can hold on-chain cash through a new TMMF wrapper—"
            "useful for settlement and treasury even before aggregate AUM jumps."
        )
    else:
        lead = "A new tokenized money-market fund launched"
        body = (
            "New wrappers expand who can hold on-chain cash and use TMMFs in settlement or "
            "treasury workflows, even before aggregate AUM jumps again."
        )
    return lead, body


def detect_fund_launches(
    articles: list[dict[str, Any]] | None,
    *,
    max_age_days: float = 14.0,
) -> dict[FundLaunchCategory, FundLaunch | None]:
    return {
        "tmmf": pick_fund_launch(articles, "tmmf", max_age_days=max_age_days),
        "stablecoin_reserve": pick_fund_launch(
            articles, "stablecoin_reserve", max_age_days=max_age_days
        ),
        "crypto_etf": pick_fund_launch(articles, "crypto_etf", max_age_days=max_age_days),
    }


def fund_launch_headline_pick(launch: FundLaunch) -> WeekHeadlinePick:
    family = {
        "tmmf": "tmmf",
        "stablecoin_reserve": "stablecoins",
        "crypto_etf": "etp",
    }[launch.category]
    theme_id = {
        "tmmf": "institutional_settlement",
        "stablecoin_reserve": "stablecoin_policy",
        "crypto_etf": "launch_pipeline",
    }[launch.category]
    return WeekHeadlinePick(
        title=launch.title,
        link=launch.link,
        source=launch.source,
        score=999.0,
        theme_id=theme_id,
        theme_family=family,
        outlet_count=1,
    )


def pick_week_headlines_with_launches(
    articles: list[dict[str, Any]] | None,
    *,
    n: int = 3,
    max_age_days: float = 7.0,
) -> tuple[list[WeekHeadlinePick], dict[FundLaunchCategory, FundLaunch | None]]:
    """Headlines of the week, prioritizing major fund launches when present."""
    return _merge_headline_picks_with_launches(
        articles,
        n=n,
        max_age_days=max_age_days,
        base_picker=pick_week_headlines,
    )


def pick_executive_week_headlines_with_launches(
    articles: list[dict[str, Any]] | None,
    *,
    n: int = 3,
    max_age_days: float = 7.0,
) -> tuple[list[WeekHeadlinePick], dict[FundLaunchCategory, FundLaunch | None]]:
    """Executive brief headlines: fund launches, stablecoin news, and digital-asset regulation only."""
    return _merge_headline_picks_with_launches(
        articles,
        n=n,
        max_age_days=max_age_days,
        base_picker=pick_executive_week_headlines,
    )


def _merge_headline_picks_with_launches(
    articles: list[dict[str, Any]] | None,
    *,
    n: int,
    max_age_days: float,
    base_picker: Any,
) -> tuple[list[WeekHeadlinePick], dict[FundLaunchCategory, FundLaunch | None]]:
    launches = detect_fund_launches(articles, max_age_days=max(14.0, max_age_days))
    launch_picks: list[WeekHeadlinePick] = []
    seen_links: set[str] = set()
    for cat in ("stablecoin_reserve", "crypto_etf", "tmmf"):
        if launch := launches.get(cat):
            pick = fund_launch_headline_pick(launch)
            if pick.link and pick.link in seen_links:
                continue
            if pick.link:
                seen_links.add(pick.link)
            launch_picks.append(pick)

    base = base_picker(articles, n=n, max_age_days=max_age_days)
    merged: list[WeekHeadlinePick] = []
    for pick in launch_picks + base:
        link = str(pick.link or "").strip()
        if link and link in seen_links and pick not in launch_picks:
            continue
        if link:
            seen_links.add(link)
        merged.append(pick)
        if len(merged) >= n:
            break
    return merged[:n], launches


def plain_language_launch_brief(launch: FundLaunch) -> str:
    """Week-in-brief watch clause hook for a major fund launch."""
    title_l = launch.title.lower()
    summary_l = launch.summary.lower()
    blob = f"{title_l} {summary_l}"
    if launch.category == "stablecoin_reserve":
        if "state street" in blob:
            return (
                "State Street launched a GENIUS Act-aligned money market fund for stablecoin "
                "reserves—major custodians are now productizing reserve infrastructure"
            )
        return (
            "a major institution launched a dedicated stablecoin reserve money market fund—"
            "reserve productization is moving beyond pilot banking relationships"
        )
    if launch.category == "crypto_etf":
        if "blackrock" in blob and ("bita" in blob or "covered-call" in blob or "premium income" in blob):
            return (
                "BlackRock launched BITA, a covered-call Bitcoin ETF aimed at monthly income—"
                "listed crypto access is broadening beyond spot beta"
            )
        return (
            "a major asset manager launched a new crypto-focused ETF—"
            "product innovation is still expanding the listed-access menu"
        )
    if "blackrock" in blob and "buidl" in blob:
        return (
            "BlackRock expanded its BUIDL tokenized cash fund footprint—"
            "on-chain money-market issuance keeps scaling through major issuers"
        )
    if "franklin" in blob and "benji" in blob:
        return (
            "Franklin Templeton extended its BENJI tokenized money-market fund into new "
            "on-chain payment workflows"
        )
    return (
        "a major institution launched a new tokenized money-market product—"
        "issuer-led settlement infrastructure keeps expanding"
    )


def launch_section_copy(launch: FundLaunch) -> tuple[str, str]:
    """Bold lead + body for a highlighted section takeaway."""
    title_l = launch.title.lower()
    summary = re.sub(r"\s+", " ", launch.summary).strip()
    if launch.category == "stablecoin_reserve":
        if "state street" in title_l:
            lead = "State Street launched a stablecoin reserves money market fund."
            body = (
                summary
                or "The fund is framed for stablecoin issuer reserve management under the "
                "GENIUS Act—another step toward dedicated reserve products from major custodians."
            )
        else:
            lead = "A major institution launched a stablecoin reserve money market fund."
            body = summary or (
                "Dedicated reserve funds signal that stablecoin infrastructure is moving from "
                "banking relationships to purpose-built cash products."
            )
    elif launch.category == "crypto_etf":
        if "blackrock" in title_l:
            lead = "BlackRock launched BITA, a covered-call Bitcoin income ETF."
            body = (
                summary
                or "BITA trades partial upside for yield via options overlays—expanding how "
                "allocators access Bitcoin through listed products beyond spot beta."
            )
        else:
            lead = "A major asset manager launched a new crypto-focused ETF."
            body = summary or (
                "New listed products keep broadening institutional access beyond core spot "
                "Bitcoin and Ethereum exposures."
            )
    else:
        if "buidl" in title_l:
            lead = "BlackRock expanded its BUIDL tokenized money-market fund."
            body = summary or (
                "Issuer-led tokenized cash products continue scaling across networks as "
                "settlement and collateral workflows deepen."
            )
        else:
            lead = "A major institution launched a new tokenized money-market fund."
            body = summary or (
                "Tokenized cash launches reinforce that on-chain money-market funds are "
                "infrastructure plays—not retail savings products."
            )
    if len(body) > 320:
        body = body[:317].rsplit(" ", 1)[0] + "…"
    return lead, body


_TMMF_BRIEF_MUST_HAVE_RE = re.compile(
    r"\b(money[- ]market|mmf|tmmf|tokenized fund|buidl|liquidity fund|tokenized cash|"
    r"benji|usyc|jtrsy|ibenji|cash management fund)\b",
    re.IGNORECASE,
)
_TMMF_BRIEF_BOOST_RE = re.compile(
    r"\b(money[- ]market|mmf|tmmf|tokenized fund|buidl|settlement|liquidity fund|"
    r"tokenized cash|benji|usyc|jtrsy|ibenji)\b",
    re.IGNORECASE,
)
_TMMF_BRIEF_ETF_NOISE_RE = re.compile(
    r"\b(bitcoin etf|spot etf|etf market|etf flows?)\b",
    re.IGNORECASE,
)
_TMMF_BRIEF_IPO_NOISE_RE = re.compile(
    r"\b(ipo underwriter|underwriter status|underwriter approval|mega ipo|"
    r"retail allocation|serve as an ipo)\b",
    re.IGNORECASE,
)


def _brief_family_article_score(art: dict[str, Any], family: str) -> tuple[float, Any]:
    rank = _article_sort_key(art)
    bonus = 0.0
    if family == "tmmf":
        text = _article_text(art)
        if not _TMMF_BRIEF_MUST_HAVE_RE.search(text):
            return (-100.0, rank)
        if _TMMF_BRIEF_IPO_NOISE_RE.search(text):
            return (-100.0, rank)
        if _TMMF_BRIEF_BOOST_RE.search(text):
            bonus += 6.0
        if _TMMF_BRIEF_ETF_NOISE_RE.search(text):
            bonus -= 10.0
    return (bonus, rank)


def pick_brief_family_article(
    articles: list[dict[str, Any]] | None,
    family: str,
    *,
    exclude_links: set[str] | None = None,
    max_age_days: float = 7.0,
) -> dict[str, Any] | None:
    """Best recent article for a theme family (Week in brief watch clauses)."""
    pool = list(articles or [])
    if not pool:
        return None
    themes = _all_themes()
    exclude = {u.strip() for u in (exclude_links or set()) if u}
    best_score: tuple[float, Any] | None = None
    best_art: dict[str, Any] | None = None
    for art in pool:
        if _is_price_headline(art):
            continue
        age = _article_age_days(art)
        if age is not None and age > max_age_days:
            continue
        link = str(art.get("link") or "").strip()
        if link in exclude:
            continue
        title = str(art.get("title") or "").strip()
        if not title:
            continue
        theme_id = _theme_for_article(art, themes)
        if _theme_family(theme_id) != family:
            continue
        score = _brief_family_article_score(art, family)
        if score[0] < 0:
            continue
        if best_score is None or score > best_score:
            best_score = score
            best_art = art
    return best_art


def pick_brief_family_headline(
    articles: list[dict[str, Any]] | None,
    family: str,
    *,
    exclude_links: set[str] | None = None,
    max_age_days: float = 7.0,
) -> str | None:
    art = pick_brief_family_article(
        articles,
        family,
        exclude_links=exclude_links,
        max_age_days=max_age_days,
    )
    if not art:
        return None
    return str(art.get("title") or "").strip() or None


_TMMF_PLAIN_HOOK_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"buidl.*avalanche|avalanche.*buidl", re.IGNORECASE),
        "BlackRock routing its BUIDL tokenized cash fund onto Avalanche, "
        "expanding multichain settlement options",
    ),
    (
        re.compile(r"benji.*money|money[- ]market.*benji|benji.*moonpay", re.IGNORECASE),
        "Franklin Templeton linking its BENJI money-market fund into on-chain "
        "payment workflows",
    ),
    (
        re.compile(r"visa.*brale|brale.*visa", re.IGNORECASE),
        "Visa and Brale testing institutional stablecoin settlement on Canton",
    ),
    (
        re.compile(r"\bbuidl\b", re.IGNORECASE),
        "BlackRock expanding its BUIDL tokenized cash fund across on-chain networks",
    ),
    (
        re.compile(r"network share|market share", re.IGNORECASE),
        "issuers shifting tokenized cash fund routing across blockchain networks",
    ),
    (
        re.compile(r"multichain|cross[- ]chain", re.IGNORECASE),
        "multichain expansion of tokenized money-market fund settlement",
    ),
)


def plain_language_tmmf_hook(title: str, *, summary: str = "") -> str:
    """Exec-readable TMMF phrasing for Week in brief — never a raw wire headline."""
    blob = f"{title} {summary}".strip()
    if not blob:
        return "issuers pushing tokenized money-market fund infrastructure forward"
    for pattern, phrase in _TMMF_PLAIN_HOOK_RULES:
        if pattern.search(blob):
            return phrase
    if re.search(
        r"money[- ]market|benji|usyc|jtrsy|ibenji|liquidity fund|tokenized fund",
        blob,
        re.IGNORECASE,
    ):
        return (
            "asset managers extending tokenized money-market funds into on-chain workflows"
        )
    if re.search(r"settlement", blob, re.IGNORECASE):
        return "institutional trials expanding tokenized cash settlement rails"
    return "issuers pushing tokenized money-market fund and settlement infrastructure forward"


def pick_brief_tmmf_article(
    articles: list[dict[str, Any]] | None,
    *,
    exclude_links: set[str] | None = None,
) -> dict[str, Any] | None:
    """On-topic tokenized-fund article for Week in brief; 7-day window, then 14-day."""
    for max_age in (7.0, 14.0):
        if art := pick_brief_family_article(
            articles,
            "tmmf",
            exclude_links=exclude_links,
            max_age_days=max_age,
        ):
            return art
    return None


def pick_brief_tmmf_headline(
    articles: list[dict[str, Any]] | None,
    *,
    exclude_links: set[str] | None = None,
) -> str | None:
    art = pick_brief_tmmf_article(articles, exclude_links=exclude_links)
    if not art:
        return None
    return str(art.get("title") or "").strip() or None


def _bullet_tokens(text: str) -> set[str]:
    return _title_tokens(text)


@dataclass(frozen=True)
class _BulletMatchProfile:
    topic_keys: tuple[str, ...]
    preferred_theme_ids: frozenset[str]
    focus_terms: frozenset[str]
    must_have_terms: frozenset[str] = frozenset()


_MACRO_NOISE_RE = re.compile(
    r"\b(inflation|cpi|energy shock|interest rate|fed\b|macroeconomic|treasury yield curve)\b",
    re.IGNORECASE,
)

_BULLET_PROFILE_RULES: tuple[tuple[re.Pattern[str], _BulletMatchProfile], ...] = (
    (
        re.compile(r"tokenized u\.s\. treasur", re.IGNORECASE),
        _BulletMatchProfile(
            ("us_treasuries", "rwa_global"),
            frozenset({"tokenized_treasuries"}),
            frozenset({"treasury", "treasuries", "t-bill", "buidl", "ondo", "tokenized"}),
            frozenset({"tokenized treasur", "u.s. treasur", "treasuries", "t-bill", "buidl", "ondo"}),
        ),
    ),
    (
        re.compile(r"distribution still drives", re.IGNORECASE),
        _BulletMatchProfile(
            ("us_treasuries", "rwa_global"),
            frozenset({"tokenized_treasuries", "institutional_adoption"}),
            frozenset({"distribution", "treasury", "tokenized", "rwa", "platform"}),
            frozenset({"tokenized treasur", "treasuries", "t-bill", "buidl", "ondo", "rwa"}),
        ),
    ),
    (
        re.compile(r"tokenized stock|market plumbing", re.IGNORECASE),
        _BulletMatchProfile(
            ("tokenized_stocks", "rwa_global"),
            frozenset({"tokenized_equities"}),
            frozenset({"tokenized stock", "tokenized equit", "tokenized share", "securitize", "equity", "xstock"}),
            frozenset({"tokenized stock", "tokenized equit", "tokenized share", "securitize", "xstock", "pre-ipo"}),
        ),
    ),
    (
        re.compile(r"in the news · rwa tokenization|private credit|on-?chain credit", re.IGNORECASE),
        _BulletMatchProfile(
            ("rwa_global",),
            frozenset({"tokenization_growth"}),
            frozenset({"tokeniz", "private credit", "real world", "rwa", "onchain", "on-chain"}),
            frozenset({"tokeniz", "private credit", "real world", "rwa"}),
        ),
    ),
    (
        re.compile(r"flight to efficiency", re.IGNORECASE),
        _BulletMatchProfile(
            ("tokenized_mmf",),
            frozenset({"chain_efficiency", "multichain"}),
            frozenset({"money market", "mmf", "tokenized fund", "network share", "tmmf"}),
            frozenset({"money market", "mmf", "tokenized fund", "liquidity fund", "buidl", "ibenji", "usyc", "jtrsy"}),
        ),
    ),
    (
        re.compile(r"issuer strategy", re.IGNORECASE),
        _BulletMatchProfile(
            ("tokenized_mmf",),
            frozenset({"issuer_models", "institutional_settlement"}),
            frozenset({"money market", "mmf", "tokenized fund", "issuer", "ucits", "institutional"}),
            frozenset({"money market", "mmf", "tokenized fund", "liquidity fund", "buidl", "ucits", "benji"}),
        ),
    ),
    (
        re.compile(r"de facto settlement|settlement layer", re.IGNORECASE),
        _BulletMatchProfile(
            ("tokenized_mmf",),
            frozenset({"institutional_settlement"}),
            frozenset({"money market", "mmf", "tokenized fund", "buidl", "settlement", "collateral", "cash management"}),
            frozenset({"money market", "mmf", "tokenized fund", "liquidity fund", "buidl", "ibenji", "usyc", "jtrsy"}),
        ),
    ),
    (
        re.compile(r"\btmmf", re.IGNORECASE),
        _BulletMatchProfile(
            ("tokenized_mmf",),
            frozenset({"institutional_settlement", "chain_efficiency"}),
            frozenset({"money market", "mmf", "tokenized fund", "buidl", "settlement"}),
            frozenset({"money market", "mmf", "tokenized fund", "liquidity fund", "buidl", "ibenji", "usyc", "jtrsy"}),
        ),
    ),
    (
        re.compile(r"in the news · stablecoin", re.IGNORECASE),
        _BulletMatchProfile(
            ("stablecoins",),
            frozenset({"stablecoin_policy"}),
            frozenset({"stablecoin", "usdc", "usdt", "reserves", "policy", "genius act"}),
            frozenset({"stablecoin", "usdc", "usdt", "dai", "usdp", "reserves"}),
        ),
    ),
    (
        re.compile(r"stablecoin market structure|stablecoin policy", re.IGNORECASE),
        _BulletMatchProfile(
            ("stablecoins",),
            frozenset({"stablecoin_policy"}),
            frozenset({"stablecoin", "usdc", "usdt", "reserves", "issuer"}),
            frozenset({"stablecoin", "usdc", "usdt", "dai", "usdp"}),
        ),
    ),
    (
        re.compile(r"institutional relevance|bank integration|bank-integration", re.IGNORECASE),
        _BulletMatchProfile(
            ("stablecoins",),
            frozenset({"bank_integration"}),
            frozenset({"bank", "payment", "stablecoin", "settlement", "visa", "mastercard"}),
            frozenset({"stablecoin", "bank", "payment", "visa", "mastercard", "stripe"}),
        ),
    ),
    (
        re.compile(r"forward market-size|market-size scenario", re.IGNORECASE),
        _BulletMatchProfile(
            ("etp",),
            frozenset({"market_sizing"}),
            frozenset({"etf", "aum", "market size", "assets under management", "billion"}),
            frozenset({"etf", "etp", "ibit", "spot bitcoin", "spot ether"}),
        ),
    ),
    (
        re.compile(r"launch pipeline", re.IGNORECASE),
        _BulletMatchProfile(
            ("etp",),
            frozenset({"launch_pipeline"}),
            frozenset({"filing", "s-1", "etf application", "crypto etf", "spot etf", "pipeline"}),
            frozenset({"spot bitcoin etf", "spot ether etf", "crypto etf", "bitcoin etf", "crypto etp", "etf filing"}),
        ),
    ),
    (
        re.compile(r"in the news · etf flow|etf flows|inflows", re.IGNORECASE),
        _BulletMatchProfile(
            ("etp",),
            frozenset({"etf_flows"}),
            frozenset({"etf", "inflow", "outflow", "ibit", "spot bitcoin"}),
            frozenset({"etf", "inflow", "outflow", "ibit", "spot bitcoin", "spot ether"}),
        ),
    ),
    (
        re.compile(r"losses broadened", re.IGNORECASE),
        _BulletMatchProfile(
            ("crypto",),
            frozenset(),
            frozenset({"altcoin", "top-50", "top 50", "market breadth", "losers", "gainers", "losses"}),
            frozenset({"altcoin", "altcoins", "top 50", "market cap", "losses", "losers", "defi"}),
        ),
    ),
    (
        re.compile(r"others outpaced", re.IGNORECASE),
        _BulletMatchProfile(
            ("crypto",),
            frozenset(),
            frozenset({"defi", "category", "outpaced", "hype", "layer 1", "meme", "outperform"}),
            frozenset({"outpaced", "defi", "category", "layer", "meme", "hype", "altcoin"}),
        ),
    ),
    (
        re.compile(r"in the news · crypto regulation", re.IGNORECASE),
        _BulletMatchProfile(
            ("crypto",),
            frozenset({"regulation"}),
            frozenset({"sec", "regulation", "cftc", "legislation", "enforcement"}),
            frozenset({"sec", "regulation", "cftc", "legislation", "enforcement"}),
        ),
    ),
)


def _is_news_bullet(lead: str) -> bool:
    return lead.lower().startswith("in the news")


def _strip_inline_tags(html: str) -> str:
    from html import unescape

    text = re.sub(r"<[^>]+>", " ", html or "")
    return unescape(re.sub(r"\s+", " ", text)).strip()


def _normalize_article_url(url: str) -> str:
    from html import unescape
    from urllib.parse import urlparse

    url = unescape(url.strip().replace("&amp;", "&"))
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    return f"{parsed.netloc.lower()}{path}".lower()


def _extract_cited_links(bullet_html: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for match in _LINK_ANCHOR_RE.finditer(bullet_html or ""):
        url = match.group(1).strip()
        title = _strip_inline_tags(match.group(2))
        if url.startswith("http") and title:
            links.append((url, title))
    return links


def _source_from_url(url: str) -> str:
    from urllib.parse import urlparse

    host = urlparse(url).netloc.replace("www.", "")
    if not host:
        return "Web"
    label = host.split(".")[0]
    return label[:1].upper() + label[1:]


def _synthetic_article(url: str, title: str) -> dict[str, Any]:
    return {"title": title, "link": url, "source": _source_from_url(url)}


def _find_article_by_cited_url(
    pool: list[dict[str, Any]],
    url: str,
    *,
    used_links: set[str],
) -> dict[str, Any] | None:
    key = _normalize_article_url(url)
    for art in pool:
        link = str(art.get("link") or "").strip()
        if not link or link in used_links:
            continue
        art_key = _normalize_article_url(link)
        if art_key == key or key in art_key or art_key in key:
            return art
    return None


def _is_noise_notable(title: str) -> bool:
    return bool(_NOISE_NOTABLE_RE.search(title))


def _article_hard_rejected(
    bullet_lead: str,
    profile: _BulletMatchProfile,
    art: dict[str, Any],
) -> bool:
    title = str(art.get("title") or "")
    art_text = _article_text(art)
    combined = f"{title} {art_text}"
    lead = bullet_lead.lower()

    if profile.preferred_theme_ids & frozenset({"market_sizing"}):
        if _MARKET_SIZING_REJECT_RE.search(combined) and not _MARKET_SIZING_ALLOW_RE.search(combined):
            return True
        if _FLOW_ONLY_RE.search(combined) and not _MARKET_SIZING_ALLOW_RE.search(combined):
            return True

    if profile.preferred_theme_ids & frozenset({"launch_pipeline"}):
        if not _LAUNCH_PIPELINE_SIGNAL_RE.search(combined):
            return True
        if _FLOW_ONLY_RE.search(combined) and not _LAUNCH_PIPELINE_SIGNAL_RE.search(title):
            return True

    if profile.preferred_theme_ids & frozenset({"etf_flows"}):
        if not (_FLOW_ONLY_RE.search(combined) or "etf" in title.lower()):
            return True

    if profile.preferred_theme_ids & frozenset({"stablecoin_policy"}) and _is_news_bullet(bullet_lead):
        if _is_noise_notable(title) or _is_price_headline(art):
            return True
        if not _text_has_focus(
            combined,
            frozenset({"stablecoin", "usdc", "usdt", "reserves", "policy", "genius act", "issuer", "bitlicense"}),
        ):
            return True

    if "losses broadened" in lead:
        if _MACRO_NOISE_RE.search(combined) and not _text_has_focus(
            combined, frozenset({"altcoin", "top 50", "market breadth", "losers", "gainers", "losses", "defi"})
        ):
            return True
        if re.search(r"\b(live updates: bitcoin|bitcoin narrows|returns to \$\d{2,})\b", combined, re.I):
            if not _text_has_focus(
                combined, frozenset({"altcoin", "top 50", "losers", "gainers", "market breadth"})
            ):
                return True

    if "others outpaced" in lead:
        if re.search(r"\b(mica|architect says|prioritize tokenization|sec unveils|strategic plan)\b", combined, re.I):
            return True
        if not re.search(r"\b(outpaced|outperform|category|layer 1|meme|hype|defi token|morpho|funding round)\b", combined, re.I):
            if re.search(r"\b(regulation|legislation|enforcement)\b", combined, re.I):
                return True

    if profile.preferred_theme_ids & frozenset({"tokenization_growth"}) and _is_news_bullet(bullet_lead):
        if re.search(r"\bmica\b", combined, re.IGNORECASE) and not re.search(
            r"\b(private credit|tradfi|trad fi|tokenized stock|securitize|broker)\b",
            combined,
            re.IGNORECASE,
        ):
            return True

    if profile.topic_keys == ("tokenized_mmf",) and _is_news_bullet(bullet_lead):
        if not _text_has_focus(
            combined,
            frozenset({"money market", "mmf", "tokenized fund", "issuer", "galaxy", "kaiko", "buidl", "benji"}),
        ):
            return True

    return False


def _resolve_bullet_profile(bullet_text: str, topic_keys: tuple[str, ...]) -> _BulletMatchProfile:
    for pattern, profile in _BULLET_PROFILE_RULES:
        if pattern.search(bullet_text):
            return profile
    return _BulletMatchProfile(topic_keys, frozenset(), frozenset(), frozenset())


def _normalize_match_text(text: str) -> str:
    return re.sub(r"[\s\-–]+", " ", text.lower()).strip()


def _text_has_focus(text: str, focus_terms: frozenset[str]) -> bool:
    low = _normalize_match_text(text)
    for term in focus_terms:
        norm_term = _normalize_match_text(term)
        if not norm_term:
            continue
        pattern = r"\b" + r"\s+".join(re.escape(part) for part in norm_term.split()) + r"\b"
        if re.search(pattern, low):
            return True
    return False


def _strip_source_suffix(headline: str) -> str:
    headline = re.sub(r"\s*\((?:CoinDesk|CoinTelegraph|The Block|Google News|AMBCrypto|The Defiant|FinTech Weekly)\)\s*$", "", headline, flags=re.I)
    headline = re.sub(r"\s[\-–]\s(?:CoinDesk|CoinTelegraph|The Block|Google News|AMBCrypto|The Defiant|FinTech Weekly)\s*$", "", headline, flags=re.I)
    return headline.strip()


def _clean_notable_part(part: str) -> str:
    part = re.sub(r"\s*Related:.*$", "", part, flags=re.IGNORECASE).strip()
    part = _strip_source_suffix(part)
    m = re.match(
        r"^(.+?\((?:CoinDesk|CoinTelegraph|The Block|Google News|AMBCrypto|The Defiant|FinTech Weekly)\))",
        part,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    m = re.match(
        r"^(.+?\s[\-–]\s(?:CoinDesk|CoinTelegraph|The Block|Google News|AMBCrypto|The Defiant|FinTech Weekly))",
        part,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    if "." in part:
        return part.split(".", 1)[0].strip()
    return part.strip()


def _extract_industry_headline_titles(bullet_text: str) -> list[str]:
    m = re.search(r"Recent coverage includes\s*(.+)", bullet_text, re.IGNORECASE)
    if m:
        body = m.group(1).strip()
        body = re.split(
            r"\.\s+(?:Reserve|Coverage|Flow|Enforcement|Tokenization|Issuer|Increased|Spot|Industry|Network|platform|issuer)",
            body,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        parts = [p.strip() for p in body.split(";") if p.strip()]
    else:
        # Declarative news bodies append linked titles after the insight.
        parts = [
            re.sub(r"<[^>]+>", "", t).strip()
            for t in re.findall(r"<a\b[^>]*>(.*?)</a>", bullet_text or "", flags=re.I | re.S)
        ]
        parts = [p for p in parts if len(p) >= 12]
        if not parts:
            return []
    titles: list[str] = []
    for part in parts:
        if re.match(r"\+\d+\s+more", part, re.I):
            continue
        clean = _clean_notable_part(part)
        if len(clean) >= 12:
            titles.append(clean)
    return titles


def _extract_notable_titles(bullet_text: str) -> list[str]:
    m = re.search(r"Notable:\s*(.+)", bullet_text, re.IGNORECASE)
    if not m:
        return _extract_industry_headline_titles(bullet_text)
    body = m.group(1).strip()
    body = re.split(
        r"\.\s+(?:Reserve|Coverage|Flow|Enforcement|Tokenization|Issuer|Increased|Spot|Industry|Network|platform|issuer)",
        body,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    body = re.split(r"\s*Related:", body, maxsplit=1, flags=re.IGNORECASE)[0]
    parts = [p.strip() for p in body.split(";") if p.strip()]
    titles: list[str] = []
    for part in parts:
        if re.match(r"\+\d+\s+more", part, re.I):
            continue
        clean = _clean_notable_part(part)
        if len(clean) >= 12:
            titles.append(clean)
    return titles


def _title_matches_notable(title: str, notable: str) -> bool:
    title_low = title.lower()
    notable_low = notable.lower()
    if notable_low in title_low or title_low in notable_low:
        return True
    a = _title_tokens(title)
    b = _title_tokens(notable)
    return _similar_token_sets(a, b)


def _news_topic_theme_ids(bullet_text: str) -> frozenset[str]:
    m = re.search(r"in the news · ([^.]+)", bullet_text, re.IGNORECASE)
    if not m:
        return frozenset()
    topic = m.group(1).strip().lower()
    hits: set[str] = set()
    for themes in TOPIC_THEMES.values():
        for theme in themes:
            label = theme.label.lower()
            if topic in label or label in topic:
                hits.add(theme.id)
                continue
            for kw in theme.keywords:
                if len(kw) >= 5 and kw in topic:
                    hits.add(theme.id)
    return frozenset(hits)


def _themes_for_topic_keys(topic_keys: tuple[str, ...]) -> list[TopicTheme]:
    themes: list[TopicTheme] = []
    for key in topic_keys:
        themes.extend(TOPIC_THEMES.get(key, ()))
    return [t for t in themes if t.id not in _EXCLUDED_THEME_IDS]


def _lead_article_overlap(lead_toks: set[str], title: str) -> int:
    if not lead_toks:
        return 0
    return len(lead_toks & _bullet_tokens(title))


def _score_article_for_takeaway(
    art: dict[str, Any],
    *,
    bullet_text: str,
    profile: _BulletMatchProfile,
    section_themes: list[TopicTheme],
    news_hints: frozenset[str],
    lead_toks: set[str],
    bullet_toks: set[str],
    notable_titles: list[str],
    penalize_macro_noise: bool,
    penalize_flow_only: bool,
    penalize_missing_must_have: bool,
) -> float:
    title = str(art.get("title") or "").strip()
    art_text = _article_text(art)
    age = _article_age_days(art)

    score = _source_weight(art)
    if age is not None:
        score += max(0.0, 3.5 - age * 0.45)

    art_toks = _bullet_tokens(title)
    lead_overlap = len(lead_toks & art_toks)
    score += min(14.0, lead_overlap * 3.5)
    body_overlap = len((bullet_toks - lead_toks) & art_toks)
    score += min(4.0, body_overlap * 0.75)

    if profile.must_have_terms:
        if _text_has_focus(art_text, profile.must_have_terms):
            score += 6.0
        elif penalize_missing_must_have:
            score -= 18.0

    matched_ids: set[str] = set()
    for theme in section_themes:
        if _matches_theme(art, theme):
            matched_ids.add(theme.id)

    for tid in matched_ids & profile.preferred_theme_ids:
        score += 7.0
    for tid in matched_ids & set(news_hints):
        score += 4.0
    for tid in matched_ids - profile.preferred_theme_ids - set(news_hints):
        score += 0.75

    if profile.focus_terms:
        focus_hits = sum(
            1 for term in profile.focus_terms if _text_has_focus(art_text, frozenset({term}))
        )
        score += focus_hits * 3.5

    for notable in notable_titles:
        if _title_matches_notable(title, notable):
            score += 22.0
            break

    if penalize_macro_noise and _MACRO_NOISE_RE.search(art_text) and not (
        profile.preferred_theme_ids & frozenset({"macro_rates", "rates_yields"})
        or "macro" in bullet_text.lower()
    ):
        score -= 12.0

    if _STRUCTURAL_BOOST_RE.search(art_text):
        score += 2.0
    if (
        penalize_flow_only
        and _FLOW_ONLY_RE.search(art_text)
        and not _STRUCTURAL_BOOST_RE.search(art_text)
        and profile.preferred_theme_ids != frozenset({"etf_flows"})
    ):
        score -= 8.0

    if profile.preferred_theme_ids and matched_ids:
        if not (matched_ids & profile.preferred_theme_ids):
            score -= 14.0
        elif profile.preferred_theme_ids & frozenset({"launch_pipeline", "market_sizing"}):
            if _FLOW_ONLY_RE.search(art_text) and not _STRUCTURAL_BOOST_RE.search(art_text):
                score -= 16.0

    return score


def _pick_takeaway_article(
    pool: list[dict[str, Any]],
    *,
    bullet_text: str,
    bullet_lead: str,
    profile: _BulletMatchProfile,
    section_themes: list[TopicTheme],
    news_hints: frozenset[str],
    lead_toks: set[str],
    bullet_toks: set[str],
    notable_titles: list[str],
    used_links: set[str],
    max_age_days: float,
    require_must_have: bool,
    require_focus: bool,
    require_preferred_theme: bool,
    require_section_theme: bool,
    require_stablecoin_title: bool,
    require_lead_overlap: int,
    require_must_have_or_focus: bool,
    min_score: float,
    penalize_macro_noise: bool,
    penalize_flow_only: bool,
    penalize_missing_must_have: bool,
) -> dict[str, Any] | None:
    best_score = -1.0
    best_art: dict[str, Any] | None = None

    for art in pool:
        link = str(art.get("link") or "").strip()
        title = str(art.get("title") or "").strip()
        if not title or not link or link in used_links:
            continue
        age = _article_age_days(art)
        if age is not None and age > max_age_days:
            continue
        if _is_price_headline(art):
            continue
        if _article_hard_rejected(bullet_lead, profile, art):
            continue

        art_text = _article_text(art)
        if require_must_have and profile.must_have_terms:
            if not _text_has_focus(art_text, profile.must_have_terms):
                continue
        if (
            require_stablecoin_title
            and profile.preferred_theme_ids == frozenset({"stablecoin_policy"})
            and "market structure" in bullet_text.lower()
            and not _text_has_focus(title, frozenset({"stablecoin", "usdc", "usdt", "dai", "usdp"}))
        ):
            continue

        matched_ids: set[str] = set()
        for theme in section_themes:
            if _matches_theme(art, theme):
                matched_ids.add(theme.id)

        if require_preferred_theme and profile.preferred_theme_ids:
            if not (matched_ids & profile.preferred_theme_ids):
                continue

        if require_section_theme and section_themes:
            if not matched_ids:
                continue

        if require_focus and profile.focus_terms:
            has_focus = _text_has_focus(art_text, profile.focus_terms)
            has_preferred = bool(profile.preferred_theme_ids and matched_ids & profile.preferred_theme_ids)
            if not has_focus and not has_preferred:
                continue

        if require_lead_overlap > 0 and _lead_article_overlap(lead_toks, title) < require_lead_overlap:
            continue

        if require_must_have_or_focus and (profile.must_have_terms or profile.focus_terms):
            has_must = (
                _text_has_focus(art_text, profile.must_have_terms) if profile.must_have_terms else False
            )
            has_focus = (
                _text_has_focus(art_text, profile.focus_terms) if profile.focus_terms else False
            )
            has_lead = _lead_article_overlap(lead_toks, title) >= 2
            if not (has_must or has_focus or has_lead):
                continue

        if profile.preferred_theme_ids & frozenset({"launch_pipeline", "market_sizing"}):
            if (
                _FLOW_ONLY_RE.search(art_text)
                and not _STRUCTURAL_BOOST_RE.search(art_text)
                and not _text_has_focus(art_text, profile.must_have_terms | profile.focus_terms)
            ):
                continue

        if profile.preferred_theme_ids & frozenset({"launch_pipeline"}):
            if not _text_has_focus(art_text, profile.must_have_terms | profile.focus_terms):
                continue

        if profile.preferred_theme_ids & frozenset({"market_sizing"}):
            if not (
                _text_has_focus(art_text, profile.must_have_terms)
                or _text_has_focus(title, frozenset({"etf", "etp", "aum", "billion"}))
            ):
                continue

        if (
            profile.must_have_terms
            and bullet_lead.lower().startswith("losses broadened")
            and min_score >= 0
        ):
            if not _text_has_focus(art_text, profile.must_have_terms):
                continue

        if "launch pipeline" in bullet_lead.lower():
            if not _text_has_focus(
                art_text,
                frozenset(
                    {"etf", "spot etf", "crypto etf", "bitcoin etf", "crypto etp", "filing", "s-1", "pipeline", "launch"}
                ),
            ):
                continue
            if (
                _FLOW_ONLY_RE.search(art_text)
                and not _text_has_focus(art_text, frozenset({"filing", "s-1", "pipeline", "launch", "application"}))
            ):
                continue

        if "forward market-size" in bullet_lead.lower() or "market-size scenario" in bullet_lead.lower():
            if not (
                _text_has_focus(art_text, profile.must_have_terms)
                or _text_has_focus(title, frozenset({"etf", "etp", "aum", "billion", "market size"}))
            ):
                continue
            if _is_price_headline(art) or re.search(
                r"\b(reclaim|liquidat|slides below|rally|surge|tumble)\b", title, re.IGNORECASE
            ):
                continue
            if (
                _FLOW_ONLY_RE.search(art_text)
                and not _text_has_focus(
                    art_text, frozenset({"market size", "aum", "billion", "forecast", "scenario", "assets under management"})
                )
            ):
                continue

        if "in the news · etf flow" in bullet_lead.lower() or "etf flows" in bullet_lead.lower():
            if not _FLOW_ONLY_RE.search(art_text) and "etf" not in title.lower():
                continue

        score = _score_article_for_takeaway(
            art,
            bullet_text=bullet_text,
            profile=profile,
            section_themes=section_themes,
            news_hints=news_hints,
            lead_toks=lead_toks,
            bullet_toks=bullet_toks,
            notable_titles=notable_titles,
            penalize_macro_noise=penalize_macro_noise,
            penalize_flow_only=penalize_flow_only,
            penalize_missing_must_have=penalize_missing_must_have,
        )

        if score > best_score:
            best_score = score
            best_art = art

    if best_art is None or best_score < min_score:
        return None
    return best_art


def match_article_for_takeaway(
    bullet_text: str,
    *,
    bullet_lead: str | None = None,
    bullet_html: str | None = None,
    topic_keys: tuple[str, ...],
    articles: list[dict[str, Any]] | None,
    used_links: set[str],
    max_age_days: float = 14.0,
    strict: bool = False,
) -> dict[str, Any] | None:
    """Best weekly article for a takeaway bullet.

    When ``strict`` is True, only higher-confidence passes run (optional Related
    links on data takeaways — skip weak force-matches).
    """
    pool = list(articles or [])
    if not pool and not bullet_html:
        return None

    lead = (bullet_lead or bullet_text).strip()
    profile = _resolve_bullet_profile(lead, topic_keys)
    profile_themes = _themes_for_topic_keys(profile.topic_keys)
    section_themes = _themes_for_topic_keys(topic_keys)
    news_hints = _news_topic_theme_ids(bullet_text) | profile.preferred_theme_ids
    lead_toks = _bullet_tokens(lead)
    bullet_toks = _bullet_tokens(bullet_text) | lead_toks
    notable_titles = [
        title for title in _extract_notable_titles(bullet_text) if not _is_noise_notable(title)
    ]

    cited_html = bullet_html or bullet_text
    for url, title in _extract_cited_links(cited_html):
        if _is_noise_notable(title):
            continue
        art = _find_article_by_cited_url(pool, url, used_links=used_links) if pool else None
        if art is not None:
            link = str(art.get("link") or "").strip()
            if link and not _article_hard_rejected(lead, profile, art):
                used_links.add(link)
                return art
        if url not in used_links:
            used_links.add(url)
            return _synthetic_article(url, title)

    if _is_news_bullet(lead):
        for notable in notable_titles:
            for art in pool:
                link = str(art.get("link") or "").strip()
                title = str(art.get("title") or "").strip()
                if not title or not link or link in used_links:
                    continue
                if _is_price_headline(art):
                    continue
                if _article_hard_rejected(lead, profile, art):
                    continue
                if not _title_matches_notable(title, notable):
                    continue
                used_links.add(link)
                return art

    passes: list[dict[str, Any]] = [
        {
            "themes": profile_themes,
            "max_age_days": max_age_days,
            "require_must_have": True,
            "require_focus": True,
            "require_preferred_theme": False,
            "require_section_theme": False,
            "require_stablecoin_title": True,
            "require_lead_overlap": 0,
            "require_must_have_or_focus": False,
            "min_score": 4.0,
            "penalize_macro_noise": True,
            "penalize_flow_only": True,
            "penalize_missing_must_have": True,
        },
        {
            "themes": profile_themes,
            "max_age_days": max_age_days,
            "require_must_have": False,
            "require_focus": False,
            "require_preferred_theme": True,
            "require_section_theme": False,
            "require_stablecoin_title": False,
            "require_lead_overlap": 1,
            "require_must_have_or_focus": True,
            "min_score": 3.0,
            "penalize_macro_noise": True,
            "penalize_flow_only": True,
            "penalize_missing_must_have": True,
        },
        {
            "themes": profile_themes,
            "max_age_days": max_age_days,
            "require_must_have": False,
            "require_focus": False,
            "require_preferred_theme": False,
            "require_section_theme": True,
            "require_stablecoin_title": False,
            "require_lead_overlap": 1,
            "require_must_have_or_focus": True,
            "min_score": 2.5,
            "penalize_macro_noise": True,
            "penalize_flow_only": False,
            "penalize_missing_must_have": True,
        },
        {
            "themes": profile_themes,
            "max_age_days": max(max_age_days, 21.0),
            "require_must_have": False,
            "require_focus": False,
            "require_preferred_theme": False,
            "require_section_theme": False,
            "require_stablecoin_title": False,
            "require_lead_overlap": 2,
            "require_must_have_or_focus": True,
            "min_score": 2.0,
            "penalize_macro_noise": False,
            "penalize_flow_only": False,
            "penalize_missing_must_have": True,
        },
        {
            "themes": section_themes,
            "max_age_days": max(max_age_days, 21.0),
            "require_must_have": False,
            "require_focus": False,
            "require_preferred_theme": False,
            "require_section_theme": True,
            "require_stablecoin_title": False,
            "require_lead_overlap": 2,
            "require_must_have_or_focus": True,
            "min_score": 1.5,
            "penalize_macro_noise": False,
            "penalize_flow_only": False,
            "penalize_missing_must_have": False,
        },
        {
            "themes": section_themes,
            "max_age_days": max(max_age_days, 21.0),
            "require_must_have": False,
            "require_focus": False,
            "require_preferred_theme": False,
            "require_section_theme": False,
            "require_stablecoin_title": False,
            "require_lead_overlap": 1,
            "require_must_have_or_focus": True,
            "min_score": 0.5,
            "penalize_macro_noise": False,
            "penalize_flow_only": False,
            "penalize_missing_must_have": False,
        },
        {
            "themes": profile_themes or section_themes,
            "max_age_days": max(max_age_days, 21.0),
            "require_must_have": False,
            "require_focus": False,
            "require_preferred_theme": False,
            "require_section_theme": False,
            "require_stablecoin_title": False,
            "require_lead_overlap": 0,
            "require_must_have_or_focus": True,
            "min_score": -50.0,
            "penalize_macro_noise": False,
            "penalize_flow_only": False,
            "penalize_missing_must_have": True,
        },
    ]

    for pass_cfg in passes:
        if strict and float(pass_cfg.get("min_score") or 0) < 4.0:
            continue
        picked = _pick_takeaway_article(
            pool,
            bullet_text=bullet_text,
            bullet_lead=lead,
            profile=profile,
            section_themes=pass_cfg["themes"],
            news_hints=news_hints,
            lead_toks=lead_toks,
            bullet_toks=bullet_toks,
            notable_titles=notable_titles,
            used_links=used_links,
            max_age_days=pass_cfg["max_age_days"],
            require_must_have=pass_cfg["require_must_have"],
            require_focus=pass_cfg["require_focus"],
            require_preferred_theme=pass_cfg["require_preferred_theme"],
            require_section_theme=pass_cfg["require_section_theme"],
            require_stablecoin_title=pass_cfg["require_stablecoin_title"],
            require_lead_overlap=pass_cfg["require_lead_overlap"],
            require_must_have_or_focus=pass_cfg["require_must_have_or_focus"],
            min_score=pass_cfg["min_score"],
            penalize_macro_noise=pass_cfg["penalize_macro_noise"],
            penalize_flow_only=pass_cfg["penalize_flow_only"],
            penalize_missing_must_have=pass_cfg["penalize_missing_must_have"],
        )
        if picked is not None:
            used_links.add(str(picked.get("link") or "").strip())
            return picked

    return None
