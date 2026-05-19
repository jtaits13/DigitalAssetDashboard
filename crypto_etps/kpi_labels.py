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
        "All <strong>% figures</strong> in the KPI row are typically <strong>one-month</strong> changes (~30 calendar days); "
        "IBIT and ETHA may use <strong>52-week</strong> figures when one-month Yahoo data is unavailable. "
        "<strong>Total</strong>: percent change on estimated aggregate AUM (weekly series). "
        "<strong>BTC &amp; ETH Fund flows</strong>: sum of daily net creations/redemptions over ~30 calendar days from "
        '<a href="https://farside.co.uk/" target="_blank" rel="noopener noreferrer">Farside Investors</a> '
        "(listed spot Bitcoin and Ethereum ETFs only). The <strong>%</strong> is month-over-month change in that "
        "30-day total vs the prior 30 days. "
        "<strong>IBIT / ETHA</strong>: Yahoo adjusted closes when available; otherwise StockAnalysis "
        "<strong>52W %</strong> from the ETF detail page. "
        "Table <strong>1Y Flow</strong> uses the same Farside source over ~12 months (see column when present). "
        "Dollar amounts are latest listed assets from <strong>StockAnalysis</strong> "
        "(crypto ETF list and detail pages; scraped; not affiliated)."
        "</p>"
    )
