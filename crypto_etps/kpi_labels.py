"""Human-readable labels and copy for the ETP top-line KPI snapshot (% lookbacks)."""

from __future__ import annotations


def etp_delta_window_caption(yahoo_or_agg_lbl: str) -> str:
    """Short tag shown in parentheses next to each KPI % change."""
    if not yahoo_or_agg_lbl:
        return ""
    u = yahoo_or_agg_lbl.strip().upper()
    if u == "1M":
        return "1 mo"
    if u == "1Y":
        return "1 yr"
    if u == "1Y*":
        return "1 yr*"
    if u == "52W":
        return "52W"
    return yahoo_or_agg_lbl.strip()


def etp_kpi_pct_legend_html() -> str:
    """One-line explainer directly above the KPI figures (Streamlit + FastAPI)."""
    return (
        '<p class="jd-etp-snapshot-pct-legend">'
        "Every <strong>% change</strong> is versus the start of the lookback tagged in parentheses next to it "
        "(normally <strong>~1 month</strong> / ~30 days when Yahoo daily prices or weekly AUM history allow). "
        "When that window is unavailable, the tag shows <strong>1 yr</strong> or <strong>52W</strong> instead."
        "</p>"
    )


def etp_kpi_methodology_footnote_html() -> str:
    """Sources and reconstruction detail (below the KPI row)."""
    return (
        '<p class="jd-kpi-window-note">'
        "<strong>Total</strong> row: % change from estimated aggregate AUM (weekly series). "
        "<strong>IBIT / ETHA</strong>: % change from Yahoo adjusted closes when available; otherwise StockAnalysis "
        "<strong>52W %</strong> narrative on the ETF detail page. "
        "Dollar amounts are latest listed assets from <strong>StockAnalysis</strong> "
        "(crypto ETF list and detail pages; scraped; not affiliated)."
        "</p>"
    )
