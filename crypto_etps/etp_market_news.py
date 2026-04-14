"""ETF/ETP RSS pulse — re-exports from ``news_feeds`` (single module for RSS + ETP headlines)."""

from __future__ import annotations

from news_feeds import build_etp_market_news_box_html, load_etp_market_news_cached

__all__ = ["build_etp_market_news_box_html", "load_etp_market_news_cached"]
