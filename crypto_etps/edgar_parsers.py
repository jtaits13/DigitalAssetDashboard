"""
HTML/text helpers for EDGAR filing bodies (aligned with ETF-Dashboard sec_parsers.py).
"""

from __future__ import annotations

import html
import re

INVALID_TICKERS = frozenset({"CIK", "ETF", "FUND"})


def clean_html_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    decoded = html.unescape(without_tags)
    decoded = re.sub(r"[\u2000-\u200f\u2028-\u202f\u205f\u2060\ufeff]", " ", decoded)
    return " ".join(decoded.split())


def extract_ticker(text: str) -> str:
    bracketed_pipe_match = re.search(
        r"\[\s*([A-Z]{1,8})\s*\]\s*\|\s*([A-Za-z0-9&.\-\s]{3,120}?(?:ETF|Fund))",
        clean_html_text(text),
        re.IGNORECASE,
    )
    if bracketed_pipe_match:
        ticker = bracketed_pipe_match.group(1).upper()
        if ticker not in INVALID_TICKERS:
            return ticker

    contract_row_match = re.search(
        r'<tr[^>]*class="contractRow"[^>]*>(.*?)</tr>',
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if contract_row_match:
        td_matches = re.findall(
            r"<td[^>]*>(.*?)</td>",
            contract_row_match.group(1),
            re.IGNORECASE | re.DOTALL,
        )
        if td_matches:
            ticker_candidate = clean_html_text(td_matches[-1]).upper()
            if re.fullmatch(r"[A-Z]{1,8}", ticker_candidate) and ticker_candidate not in INVALID_TICKERS:
                return ticker_candidate

    raw_label_match = re.search(r"Ticker Symbol", text, re.IGNORECASE)
    if raw_label_match:
        start = raw_label_match.start()
        ticker_snippet = clean_html_text(text[start : start + 2000])
        ticker_label_match = re.search(
            r"Ticker Symbol\s*:?\s*([A-Z]{2,8})\b",
            ticker_snippet,
            re.IGNORECASE,
        )
        if ticker_label_match:
            ticker = ticker_label_match.group(1).upper()
            if ticker not in INVALID_TICKERS:
                return ticker

    cleaned_text = clean_html_text(text)

    prospectus_table_match = re.search(
        r"Fund\s+Ticker\s+Principal U\.S\. Listing Exchange.*?(?:ETF|Fund)\s+([A-Z]{1,8})\b",
        cleaned_text,
        re.IGNORECASE,
    )
    if prospectus_table_match:
        ticker = prospectus_table_match.group(1).upper()
        if ticker not in INVALID_TICKERS:
            return ticker

    pipe_match = re.search(
        r"([A-Z]{2,6})\s*\|\s*([A-Za-z0-9&.\-\s]{3,120}?(?:ETF|Fund))",
        cleaned_text,
        re.IGNORECASE,
    )
    if pipe_match:
        ticker = pipe_match.group(1).upper()
        if ticker not in INVALID_TICKERS:
            return ticker

    ticker_cell_match = re.search(
        r"Ticker Symbol\s+([A-Z]{1,8})",
        cleaned_text,
        re.IGNORECASE,
    )
    if ticker_cell_match:
        ticker = ticker_cell_match.group(1).upper()
        if ticker not in INVALID_TICKERS:
            return ticker

    return ""


def sanitize_ticker(value: object) -> str:
    ticker = str(value or "").strip().upper()
    if re.fullmatch(r"[A-Z]{1,8}", ticker) and ticker not in INVALID_TICKERS:
        return ticker
    return "Not Listed"


def extract_series_entries(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    contract_rows = re.findall(
        r'<tr[^>]*class="contractRow"[^>]*>.*?<td[^>]*>.*?</td>\s*<td[^>]*>.*?</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>',
        text,
        re.IGNORECASE | re.DOTALL,
    )
    for name_html, ticker_html in contract_rows:
        name = clean_html_text(name_html)
        ticker = clean_html_text(ticker_html).upper()
        if not name:
            continue
        if ticker and not re.fullmatch(r"[A-Z]{1,8}", ticker):
            ticker = ""
        if ticker in INVALID_TICKERS:
            ticker = ""
        entries.append({"etf_name": name, "ticker": ticker})
    return entries


def build_sec_url(path_or_url: str) -> str:
    if path_or_url.startswith("http"):
        return path_or_url
    return f"https://www.sec.gov{path_or_url}"


def extract_supporting_document_urls(index_text: str) -> list[str]:
    prioritized_paths: list[str] = []
    groups = [
        re.findall(
            r'href="/ix\?doc=(/Archives/edgar/data/[^"]+\.(?:htm|html))"',
            index_text,
            re.IGNORECASE,
        ),
        re.findall(
            r'<tr[^>]*>\s*<td[^>]*>\s*1\s*</td>.*?href="(/Archives/edgar/data/[^"]+\.(?:htm|html))"',
            index_text,
            re.IGNORECASE | re.DOTALL,
        ),
        re.findall(r'href="(/Archives/edgar/data/[^"]+_htm\.xml)"', index_text, re.IGNORECASE),
        re.findall(r'href="(/Archives/edgar/data/[^"]+\.txt)"', index_text, re.IGNORECASE),
        re.findall(r'href="(/Archives/edgar/data/[^"]+\.(?:htm|html))"', index_text, re.IGNORECASE),
    ]
    for group in groups:
        for path in group:
            filename = path.rsplit("/", 1)[-1].lower()
            if filename in {"index.htm", "index.html"}:
                continue
            if path not in prioritized_paths:
                prioritized_paths.append(path)
    return [build_sec_url(p) for p in prioritized_paths]
