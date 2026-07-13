"""Live JSON payloads for full news-feed Streamlit/static pages."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from scripts.export_static_site_data import (
    ALL_DIGITAL_NEWS_LOOKBACK_DAYS,
    STATIC_THE_DEFIANT_FEED,
    STATIC_THE_DEFIANT_REG_EXTRA,
    _article_json,
    articles_published_within_utc_days,
    enrich_custodian_access,
)


def build_all_articles_page_payload() -> dict[str, Any]:
    from news_feeds import (
        ALL_ARTICLES_FEEDS,
        load_all_feeds,
        prepare_all_digital_asset_articles,
    )

    feed_errors: list[str] = []
    articles, errs = load_all_feeds(list(ALL_ARTICLES_FEEDS))
    feed_errors.extend(errs)
    prepared = prepare_all_digital_asset_articles(articles)
    windowed = articles_published_within_utc_days(prepared, ALL_DIGITAL_NEWS_LOOKBACK_DAYS)
    windowed.sort(
        key=lambda x: x["published"]
        if isinstance(x.get("published"), datetime)
        else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    ts = datetime.now(timezone.utc).isoformat()
    return {
        "payloads": {
            "all_articles.json": {
                "generated_at": ts,
                "items": [_article_json(a) for a in windowed],
            },
        },
        "feed_errors": feed_errors,
    }


def build_regulatory_page_payload() -> dict[str, Any]:
    from regulatory_news.client import load_regulatory_articles

    feed_errors: list[str] = []
    articles, errs = load_regulatory_articles(extra_feeds=STATIC_THE_DEFIANT_REG_EXTRA)
    feed_errors.extend(errs)
    ts = datetime.now(timezone.utc).isoformat()
    return {
        "payloads": {
            "all_regulatory.json": {
                "generated_at": ts,
                "items": [_article_json(a) for a in articles],
            },
        },
        "feed_errors": feed_errors,
    }


def build_custodian_page_payload() -> dict[str, Any]:
    from custodian_news.client import CUSTODIAN_LOOKBACK_DAYS, load_custodian_articles

    feed_errors: list[str] = []
    raw, errs = load_custodian_articles(per_day_cap=0)
    feed_errors.extend(errs)
    articles = articles_published_within_utc_days(raw, CUSTODIAN_LOOKBACK_DAYS)
    enrich_custodian_access(articles)
    articles.sort(
        key=lambda x: x["published"]
        if isinstance(x.get("published"), datetime)
        else datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    ts = datetime.now(timezone.utc).isoformat()
    return {
        "payloads": {
            "all_custodian_news.json": {
                "generated_at": ts,
                "items": [_article_json(a) for a in articles],
            },
        },
        "feed_errors": feed_errors,
    }


def build_etf_news_page_payload() -> dict[str, Any]:
    from news_feeds import load_all_etf_etp_news_cached

    feed_errors: list[str] = []
    articles, errs = load_all_etf_etp_news_cached(extra_feeds=[STATIC_THE_DEFIANT_FEED])
    feed_errors.extend(errs)
    ts = datetime.now(timezone.utc).isoformat()
    return {
        "payloads": {
            "etf_news.json": {
                "generated_at": ts,
                "items": [_article_json(a) for a in articles],
            },
        },
        "feed_errors": feed_errors,
    }


NEWS_FEED_BUILDERS = {
    "all_articles": build_all_articles_page_payload,
    "regulatory": build_regulatory_page_payload,
    "custodian": build_custodian_page_payload,
    "etf_news": build_etf_news_page_payload,
}

NEWS_FEED_JSON_KEYS = {
    "all_articles": "all_articles.json",
    "regulatory": "all_regulatory.json",
    "custodian": "all_custodian_news.json",
    "etf_news": "etf_news.json",
}
