"""Shared Jinja context for HTML pages (matches Streamlit CSS blocks)."""

from __future__ import annotations

from fastapi import Request

from crypto_etps.widgets import WIDGET_CSS as ETP_WIDGET_CSS
from news_feeds import app_shared_layout_css, article_styles_markdown
from price_ticker import TICKER_STYLES_MARKDOWN, fetch_top_crypto_tickers, render_price_ticker_html
from rwa_league.widgets import WIDGET_CSS as RWA_WIDGET_CSS


def html_shell_context(request: Request, *, include_ticker: bool = True, **extra: object) -> dict:
    ctx = {
        "request": request,
        "article_css": article_styles_markdown(),
        "layout_css": app_shared_layout_css(),
        "ticker_css": TICKER_STYLES_MARKDOWN,
        "etp_widget_css": ETP_WIDGET_CSS,
        "rwa_widget_css": RWA_WIDGET_CSS,
    }
    if include_ticker and "ticker_inner" not in extra:
        rows, err, src = fetch_top_crypto_tickers()
        ctx["ticker_inner"] = render_price_ticker_html(rows, err, src)
    ctx.update(extra)
    return ctx
