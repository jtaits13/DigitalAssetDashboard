"""FastAPI entrypoint: same data loaders as Streamlit, server-rendered HTML (no static JSON export)."""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import escape
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from crypto_etps.client import sorted_by_assets
from crypto_etps.dataframe_table import build_etp_dataframe, filter_rows_by_fund_name, style_etp_dataframe
from crypto_etps.widgets import (
    ETP_DATA_SOURCE_CAPTION,
    WIDGET_CSS as ETP_WIDGET_CSS,
    etp_table_height,
    get_etp_user_agent_from_secrets,
    load_crypto_etps_cached,
    resolve_etp_user_agent,
)
from home_layout import (
    hub_subsection_heading_html,
    section_label_teal,
    subpage_footer_heading_html,
    subpage_footnote_html,
    subpage_toolbar_note_html,
)
from news_feeds import (
    ALL_ARTICLES_FEEDS,
    ALL_ARTICLES_FEED_DAY_CAP,
    DEFAULT_FEEDS,
    ETF_ETP_NEWS_FEED_DAY_CAP,
    ETP_PULSE_PREVIEW_COUNT,
    build_etp_market_news_box_html,
    build_full_page_market_news_feed_html,
    build_full_page_regulatory_feed_html,
    build_home_news_lane_body_html,
    cap_market_news_per_day,
    dedupe_articles,
    fetch_feed,
    filter_headlines_by_keyword,
    load_all_feeds,
    load_all_etf_etp_news_cached,
    prepare_home_hub_market_news_lane,
)
from price_ticker import fetch_top_crypto_tickers
from regulatory_news.client import REGULATORY_HEADLINES_PER_UTC_DAY, load_regulatory_articles
from regulatory_news.widgets import (
    build_home_regulatory_lane_body_html,
    clear_regulatory_cache,
)
from rwa_league.dataframe_table import build_rwa_dataframe, style_rwa_dataframe
from rwa_league.widgets import (
    GLOBAL_MARKET_RWA_LINK_LABEL,
    GLOBAL_MARKET_RWA_URL,
    RWA_GLOBAL_MARKET_OVERVIEW_HEADING,
    WIDGET_CSS as RWA_WIDGET_CSS,
    clear_rwa_league_cache,
    load_rwa_global_market_cached,
    rwa_table_height,
)

from crypto_etps.widgets import clear_crypto_etp_cache

from webapp.config import STATIC_DIR, TEMPLATES
from webapp.context import html_shell_context
from webapp.formatters import (
    etp_summary_kpi_row_html,
    etp_user_agent,
    plotly_figure_to_div,
    rwa_explore_gateways_html,
    rwa_global_kpi_block_html,
    styled_dataframe_to_html,
)
from webapp.routes_rwa import router as rwa_router

HOME_REGULATORY_PREVIEW = 3
PER_PAGE = 20
ETP_PREVIEW_ROWS = 5
RWA_HOME_PREVIEW = 8

app = FastAPI(title="Digital Assets Dashboard")
app.include_router(rwa_router)
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/favicon.ico")
async def favicon() -> RedirectResponse:
    return RedirectResponse(url="/static/favicon.svg", status_code=302)


@app.get("/refresh", response_class=HTMLResponse)
async def refresh_all() -> RedirectResponse:
    """Clear Streamlit cache layers used by the Python loaders, then return home."""
    try:
        fetch_feed.clear()
    except Exception:
        pass
    try:
        from news_feeds import load_all_etf_etp_news_cached  # noqa: PLC0415

        load_all_etf_etp_news_cached.clear()
    except Exception:
        pass
    try:
        fetch_top_crypto_tickers.clear()
    except Exception:
        pass
    clear_regulatory_cache()
    clear_crypto_etp_cache()
    clear_rwa_league_cache()
    return RedirectResponse(url="/", status_code=303)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    ua = resolve_etp_user_agent(etp_user_agent() or get_etp_user_agent_from_secrets())
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_news = pool.submit(load_all_feeds, DEFAULT_FEEDS)
        f_reg = pool.submit(load_regulatory_articles)
        f_etp = pool.submit(load_crypto_etps_cached, ua)
        f_rwa = pool.submit(load_rwa_global_market_cached)
        articles, feed_errors = f_news.result()
        regulatory_articles, regulatory_errors = f_reg.result()
        for f in (f_etp, f_rwa):
            try:
                f.result()
            except Exception:
                pass

    etp_data = load_crypto_etps_cached(ua)
    rows_glob, kpis_glob, err_glob = load_rwa_global_market_cached()

    news_lane = ""
    reg_lane = ""
    home_news_capped_total: list = []
    if not articles:
        news_lane = (
            '<section class="jd-hub-news-panel jd-hub-news-panel--empty" aria-labelledby="jd-hub-news-market-h2">'
            "<h2 id=\"jd-hub-news-market-h2\" class=\"jd-hub-panel-title\">Latest Digital Asset News</h2>"
            "<p class=\"jd-hub-news-empty\">Headlines will appear when RSS feeds load successfully.</p></section>"
        )
    else:
        home_news_lane, home_news_capped_total = prepare_home_hub_market_news_lane(articles)
        news_lane = build_home_news_lane_body_html(
            home_news_lane,
            show_footnote=len(home_news_lane) == len(home_news_capped_total),
        )

    reg_lane = build_home_regulatory_lane_body_html(regulatory_articles, max_items=HOME_REGULATORY_PREVIEW)

    need_news = len(home_news_capped_total) > 0
    need_reg = len(regulatory_articles) > HOME_REGULATORY_PREVIEW

    etp_block = ""
    if etp_data.error and not etp_data.rows:
        etp_block = f'<p class="alert warn">{escape(etp_data.error)}</p>'
    else:
        ranked = sorted_by_assets(etp_data.rows)
        display_rows = ranked[:ETP_PREVIEW_ROWS]
        from crypto_etps.flows import load_farside_flow_series_cached

        flow_series = load_farside_flow_series_cached()
        df = build_etp_dataframe(display_rows, flow_series=flow_series)
        etp_block = (
            f"<h2 class=\"home-widget-heading\">U.S. Digital Asset ETPs</h2>"
            f"{etp_summary_kpi_row_html(etp_data.rows, metrics_above_methodology_note=False)}"
            f"{styled_dataframe_to_html(style_etp_dataframe(df))}"
            f"<p class=\"jd-hub-cta-note\"><a class=\"btn primary\" href=\"/etps\">Full ETP list →</a></p>"
        )

    rwa_block_parts: list[str] = []
    h2_cls = "home-widget-heading"
    if err_glob and not rows_glob:
        rwa_block_parts.append(f'<p class="alert warn">{escape(err_glob)}</p>')
        rwa_block_parts.append(
            f'<div class="jd-hub-subsection-head" id="jd-rwa-market">'
            f'<h2 class="{h2_cls}">{escape(RWA_GLOBAL_MARKET_OVERVIEW_HEADING)}</h2></div>'
        )
        rwa_block_parts.append(rwa_global_kpi_block_html(kpis_glob, kpi_legend_name="Global Market"))
        rwa_block_parts.append(
            f'<p><a class="btn" href="{escape(GLOBAL_MARKET_RWA_URL, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(GLOBAL_MARKET_RWA_LINK_LABEL)}</a></p>'
        )
    elif not rows_glob:
        rwa_block_parts.append('<p class="alert info">No network rows returned.</p>')
    else:
        working = list(rows_glob)[: max(1, min(RWA_HOME_PREVIEW, len(rows_glob)))]
        df_r = build_rwa_dataframe(working)
        rwa_block_parts.append(
            f'<div class="jd-hub-subsection-head" id="jd-rwa-market">'
            f'<h2 class="{h2_cls}">{escape(RWA_GLOBAL_MARKET_OVERVIEW_HEADING)}</h2></div>'
        )
        rwa_block_parts.append(rwa_global_kpi_block_html(kpis_glob, kpi_legend_name="Global Market"))
        rwa_block_parts.append(styled_dataframe_to_html(style_rwa_dataframe(df_r)))
        rwa_block_parts.append('<p><a class="btn primary" href="/rwa/global">Open full RWA Market Overview table →</a></p>')
        rwa_block_parts.append(
            f'<p><a class="btn" href="{escape(GLOBAL_MARKET_RWA_URL, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(GLOBAL_MARKET_RWA_LINK_LABEL)}</a></p>'
        )
    rwa_block_parts.append(rwa_explore_gateways_html("home"))
    rwa_block = "".join(rwa_block_parts)

    ctx = html_shell_context(request, page_title="Digital Assets Dashboard")
    ctx.update(
        {
            "feed_errors": feed_errors,
            "regulatory_errors": regulatory_errors,
            "news_section_label": section_label_teal("News & Regulatory", placement="first"),
            "news_lane_html": news_lane,
            "reg_lane_html": reg_lane,
            "need_news_btn": need_news,
            "need_reg_btn": need_reg,
            "etp_section_label": section_label_teal("Markets & Funds", placement="after_divider"),
            "rwa_section_label": section_label_teal("On-chain Data", placement="after_divider"),
            "etp_section_html": etp_block,
            "rwa_section_html": rwa_block,
            "footer_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        }
    )
    return TEMPLATES.TemplateResponse("home.html", ctx)


@app.get("/articles", response_class=HTMLResponse)
async def all_articles(
    request: Request,
    q: str = "",
    page: int = Query(1, ge=1),
) -> HTMLResponse:
    articles, feed_errors = load_all_feeds(ALL_ARTICLES_FEEDS)
    search_q = (q or "").strip()
    unique = dedupe_articles(articles, max_items=None)
    unique = cap_market_news_per_day(unique, max_per_day=ALL_ARTICLES_FEED_DAY_CAP)
    filtered = filter_headlines_by_keyword(unique, search_q)
    n = len(filtered)
    total_pages = max(1, (n + PER_PAGE - 1) // PER_PAGE) if n else 1
    page = min(page, total_pages)
    start = (page - 1) * PER_PAGE
    page_items = filtered[start : start + PER_PAGE]
    cap_parts = (
        [f"Showing {start + 1}–{min(start + PER_PAGE, n)} of {n} articles"]
        if n
        else ["No articles"]
    )
    if search_q and n:
        cap_parts.append(f"(filtered from {len(unique)} total)")
    body = ""
    if n == 0:
        body = (
            '<p class="alert info">No articles match your search.</p>'
            if len(unique)
            else '<p class="alert info">No articles loaded yet.</p>'
        )
    else:
        body = build_full_page_market_news_feed_html(page_items)
    ctx = html_shell_context(request, page_title="All digital asset headlines")
    ctx.update(
        {
            "feed_errors": feed_errors,
            "headline": section_label_teal("All digital asset headlines", placement="first"),
            "subhead": (
                '<p class="jd-hub-dek jd-hub-dek-large">'
                "Same <strong>All articles</strong> bundle as Streamlit and the static export; after deduplication, up to "
                f"<strong>{ALL_ARTICLES_FEED_DAY_CAP}</strong> ranked headlines per UTC calendar day. "
                f"<strong>{PER_PAGE}</strong> per page.</p>"
            ),
            "search_q": search_q,
            "body_html": body,
            "toolbar_note": subpage_toolbar_note_html(" · ".join(cap_parts)),
            "page": page,
            "total_pages": total_pages,
            "has_results": n > 0,
            "footnote": subpage_footnote_html(
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · Page {page} of {total_pages}"
            ),
            "subpage_footer": subpage_footer_heading_html("Pages"),
        }
    )
    return TEMPLATES.TemplateResponse("list_page.html", ctx)


@app.get("/regulatory", response_class=HTMLResponse)
async def all_regulatory(
    request: Request,
    q: str = "",
    page: int = Query(1, ge=1),
) -> HTMLResponse:
    articles, feed_errors = load_regulatory_articles()
    search_q = (q or "").strip()
    filtered = filter_headlines_by_keyword(articles, search_q)
    n = len(filtered)
    total_pages = max(1, (n + PER_PAGE - 1) // PER_PAGE) if n else 1
    page = min(page, total_pages)
    start = (page - 1) * PER_PAGE
    page_items = filtered[start : start + PER_PAGE]
    cap_parts = (
        [f"Showing {start + 1}–{min(start + PER_PAGE, n)} of {n} headlines"]
        if n
        else ["No headlines"]
    )
    if search_q and n:
        cap_parts.append(f"(filtered from {len(articles)} total)")
    body = ""
    if n == 0:
        body = (
            '<p class="alert info">No headlines match your search.</p>'
            if len(articles)
            else '<p class="alert info">No headlines loaded yet.</p>'
        )
    else:
        body = build_full_page_regulatory_feed_html(page_items)
    ctx = html_shell_context(request, page_title="All regulatory headlines")
    ctx.update(
        {
            "feed_errors": feed_errors,
            "headline": section_label_teal("All regulatory headlines", placement="first"),
            "subhead": (
                '<p class="jd-hub-dek jd-hub-dek-large">'
                "Same global regulatory wire pool as the home hub; up to "
                f"<strong>{REGULATORY_HEADLINES_PER_UTC_DAY}</strong> ranked headlines per UTC calendar day. "
                f"<strong>{PER_PAGE}</strong> per page.</p>"
            ),
            "search_q": search_q,
            "body_html": body,
            "toolbar_note": subpage_toolbar_note_html(" · ".join(cap_parts)),
            "page": page,
            "total_pages": total_pages,
            "has_results": n > 0,
            "footnote": subpage_footnote_html(
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · Page {page} of {total_pages}"
            ),
            "subpage_footer": subpage_footer_heading_html("Pages"),
        }
    )
    return TEMPLATES.TemplateResponse("list_page.html", ctx)


@app.get("/etf-news", response_class=HTMLResponse)
async def etf_news(
    request: Request,
    q: str = "",
    page: int = Query(1, ge=1),
) -> HTMLResponse:
    articles, feed_errors = load_all_etf_etp_news_cached()
    search_q = (q or "").strip()
    filtered = filter_headlines_by_keyword(articles, search_q)
    n = len(filtered)
    total_pages = max(1, (n + PER_PAGE - 1) // PER_PAGE) if n else 1
    page = min(page, total_pages)
    start = (page - 1) * PER_PAGE
    page_items = filtered[start : start + PER_PAGE]
    cap_parts = (
        [f"Showing {start + 1}–{min(start + PER_PAGE, n)} of {n} articles"]
        if n
        else ["No articles"]
    )
    if search_q and n:
        cap_parts.append(f"(filtered from {len(articles)} ETF-related headlines)")
    body = ""
    if n == 0:
        body = (
            '<p class="alert info">No articles match your search.</p>'
            if len(articles)
            else '<p class="alert info">No ETF headlines loaded yet.</p>'
        )
    else:
        body = build_full_page_market_news_feed_html(page_items)
    ctx = html_shell_context(request, page_title="ETF & ETP Market News")
    ctx.update(
        {
            "feed_errors": feed_errors,
            "headline": section_label_teal("ETF & ETP Market News", placement="first"),
            "subhead": (
                '<p class="jd-hub-dek jd-hub-dek-large">'
                "Digital-asset ETF and ETP headlines from the expanded pool—up to "
                f"<strong>{ETF_ETP_NEWS_FEED_DAY_CAP}</strong> ranked stories per UTC calendar day "
                "(same pipeline as Streamlit).</p>"
            ),
            "search_q": search_q,
            "body_html": body,
            "toolbar_note": subpage_toolbar_note_html(" · ".join(cap_parts)),
            "page": page,
            "total_pages": total_pages,
            "has_results": n > 0,
            "footnote": subpage_footnote_html(
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · Page {page} of {total_pages}"
            ),
            "subpage_footer": subpage_footer_heading_html("Pages"),
        }
    )
    return TEMPLATES.TemplateResponse("list_page.html", ctx)


@app.get("/etps", response_class=HTMLResponse)
async def us_crypto_etps(request: Request, q: str = "") -> HTMLResponse:
    from crypto_etps.aum_history import (  # noqa: PLC0415
        build_aggregate_aum_plotly_figure,
        etp_rows_to_fund_pairs,
        load_aggregate_aum_history_cached,
    )

    ua = resolve_etp_user_agent(etp_user_agent() or get_etp_user_agent_from_secrets())
    etp_res = load_crypto_etps_cached(ua)
    etp_all_news, etp_feed_errors = load_all_etf_etp_news_cached()
    search_q = (q or "").strip()
    body_parts: list[str] = []
    if etp_res.error and not etp_res.rows:
        body_parts.append(f'<p class="alert warn">{escape(etp_res.error)}</p>')
    else:
        from pages.US_Crypto_ETPs import _etp_key_observations_html  # noqa: PLC0415

        rows = etp_res.rows
        etp_pulse = etp_all_news[:ETP_PULSE_PREVIEW_COUNT]
        body_parts.append(
            hub_subsection_heading_html("Top-Line Market Snapshot", element_id="jd-etp-summary")
        )
        body_parts.append(etp_summary_kpi_row_html(rows, metrics_above_methodology_note=True))
        body_parts.append(hub_subsection_heading_html("Key Observations"))
        body_parts.append(_etp_key_observations_html(rows, etp_news=etp_all_news))
        body_parts.append('<div class="split-etp">')
        body_parts.append("<div>")
        body_parts.append(
            hub_subsection_heading_html("Aggregate AUM trend (12 months)", element_id="jd-etp-aggregate-aum")
        )
        pairs = etp_rows_to_fund_pairs(rows)
        chart_df, chart_err = load_aggregate_aum_history_cached(pairs)
        if chart_df is not None and not chart_df.empty:
            plot_df = chart_df.copy()
            plot_df["aum_billions_usd"] = plot_df["total_aum_usd"] / 1e9
            fig = build_aggregate_aum_plotly_figure(plot_df, height=420)
            body_parts.append(plotly_figure_to_div(fig))
        elif chart_err:
            body_parts.append(f'<p class="alert info">{escape(chart_err)}</p>')
        body_parts.append("</div><div>")
        body_parts.append(build_etp_market_news_box_html(etp_pulse))
        if len(etp_all_news) > ETP_PULSE_PREVIEW_COUNT:
            body_parts.append('<p class="jd-hub-cta-note"><a class="btn primary" href="/etf-news">Explore all ETF news →</a></p>')
        body_parts.append("</div></div>")
        body_parts.append("<hr class=\"jd-divider\" />")
        filtered = filter_rows_by_fund_name(rows, search_q)
        sorted_rows = sorted_by_assets(filtered)
        from crypto_etps.flows import load_farside_flow_series_cached

        flow_series = load_farside_flow_series_cached()
        df = build_etp_dataframe(sorted_rows, flow_series=flow_series)
        if not df.empty and "Assets (B)" in df.columns:
            has_assets = df["Assets (B)"].notna() & (df["Assets (B)"] > 0)
            df = (
                df.assign(_has_assets=has_assets)
                .sort_values(
                    by=["_has_assets", "Assets (B)"],
                    ascending=[False, False],
                    na_position="last",
                )
                .drop(columns=["_has_assets"])
                .reset_index(drop=True)
            )
        if search_q:
            body_parts.append(
                subpage_toolbar_note_html(
                    f"Showing {len(sorted_rows)} of {len(rows)} funds matching “{search_q}”."
                )
            )
        else:
            body_parts.append(subpage_toolbar_note_html(f"Showing all {len(sorted_rows)} funds."))
        body_parts.append(
            subpage_toolbar_note_html(
                "Sorted by listed assets (USD), largest to smallest; funds with no AUM shown (—) are listed last."
            )
        )
        body_parts.append(
            styled_dataframe_to_html(
                style_etp_dataframe(df),
                table_id="etp-full",
            )
        )
        body_parts.append(f'<p class="caption">{ETP_DATA_SOURCE_CAPTION}</p>')
    ctx = html_shell_context(request, page_title="U.S. Digital Asset ETPs")
    ctx.update(
        {
            "etp_feed_errors": etp_feed_errors,
            "search_q": search_q,
            "head_block": section_label_teal("U.S. Digital Asset ETPs — Full List", placement="first")
            + '<p class="jd-hub-dek jd-hub-dek-large">U.S. crypto-related exchange-traded products: KPIs, aggregate AUM trend, fund table, ETF headline teaser.</p><hr class="jd-divider" />',
            "body_html": "".join(body_parts),
            "footnote": subpage_footnote_html(
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · StockAnalysis snapshot"
            ),
        }
    )
    return TEMPLATES.TemplateResponse("etps.html", ctx)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("webapp.main:app", host="0.0.0.0", port=8000, reload=True)