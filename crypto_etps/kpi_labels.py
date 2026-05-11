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


def etp_kpi_methodology_footnote_html() -> str:
    """Sources and lookback (below the KPI row)."""
    return (
        '<p class="jd-kpi-window-note">'
        "The <strong>% figures</strong> are typically about <strong>one-month</strong> changes (~30 calendar days). "
        "Each tile repeats the exact window in parentheses next to the percent (<strong>1 mo</strong>, <strong>1 yr</strong>, or <strong>52W</strong>) "
        "when the standard month window is unavailable. "
        "<strong>Total</strong>: percent change on estimated aggregate AUM (weekly series). "
        "<strong>IBIT / ETHA</strong>: Yahoo adjusted closes when available; otherwise StockAnalysis "
        "<strong>52W %</strong> from the ETF detail page. "
        "Dollar amounts are latest listed assets from <strong>StockAnalysis</strong> "
        "(crypto ETF list and detail pages; scraped; not affiliated)."
        "</p>"
    )
