"""
Resolve the EDGAR filing *index* URL for a fund ticker (ETF-Dashboard / sec_filings method).

Walks data.sec.gov submissions for the registrant CIK, considers S-1 / N-1A / 485BPOS / 485APOS
(and common variants), fetches each filing index + primary/supporting docs, parses tickers, and
returns the ``-index.htm`` URL when the row ticker matches.
"""

from __future__ import annotations

import logging
import re
import time
import requests

from crypto_etps.edgar_parsers import (
    extract_series_entries,
    extract_supporting_document_urls,
    extract_ticker,
    sanitize_ticker,
)

logger = logging.getLogger(__name__)

INDEX_PAGE_MAX_CHARS = 60_000
PRIMARY_MAX_CHARS = 300_000
SUPPORTING_XML_MAX = 120_000
MAX_FILINGS_TO_SCAN = 28
MAX_SUPPORTING_DOCS = 4
REQUEST_DELAY_SEC = 0.32

# Base forms (SEC also emits S-1/A, etc.)
_BASE_FORMS = frozenset({"S-1", "N-1A", "485BPOS", "485APOS"})


def _form_allowed(form: str) -> bool:
    if not form:
        return False
    if form in _BASE_FORMS:
        return True
    u = form.upper().strip()
    for b in _BASE_FORMS:
        if u.startswith(b + "/"):
            return True
        if u.startswith(b) and len(u) <= len(b) + 4:
            return True
    if u.startswith("S-1") or u.startswith("N-1A"):
        return True
    if u.startswith("485B") or u.startswith("485A"):
        return True
    return False


def _fetch_text(url: str, max_chars: int, user_agent: str) -> str:
    headers = {"User-Agent": user_agent.strip(), "Accept": "text/html,application/xml,*/*"}
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=35)
            r.raise_for_status()
            return r.text[:max_chars]
        except requests.RequestException as e:
            logger.debug("fetch %s: %s", url[:80], e)
            if attempt == 2:
                return ""
            time.sleep(0.8 + attempt * 0.4)
    return ""


def _ticker_matches_target(parsed: str, target: str) -> bool:
    if not parsed:
        return False
    return sanitize_ticker(parsed) == sanitize_ticker(target)


def _collect_tickers_for_filing(
    index_text: str,
    primary_document_url: str,
    user_agent: str,
) -> set[str]:
    tickers: set[str] = set()

    if primary_document_url:
        max_chars = SUPPORTING_XML_MAX if primary_document_url.lower().endswith("_htm.xml") else PRIMARY_MAX_CHARS
        primary_text = _fetch_text(primary_document_url, max_chars, user_agent)
        time.sleep(REQUEST_DELAY_SEC)
        pt = extract_ticker(primary_text)
        if pt:
            tickers.add(pt)

    series = extract_series_entries(index_text)
    for e in series:
        if e.get("ticker"):
            tickers.add(sanitize_ticker(e["ticker"]))

    if not tickers or any(not e.get("ticker") for e in series):
        for url in extract_supporting_document_urls(index_text)[:MAX_SUPPORTING_DOCS]:
            max_chars = SUPPORTING_XML_MAX if url.lower().endswith("_htm.xml") else PRIMARY_MAX_CHARS
            st = _fetch_text(url, max_chars, user_agent)
            time.sleep(REQUEST_DELAY_SEC)
            t = extract_ticker(st)
            if t:
                tickers.add(t)

    return tickers


def find_fund_filing_index_url(symbol: str, user_agent: str) -> str | None:
    """
    Return the SEC filing index URL (``...-index.htm``) for the most recent relevant filing
    whose parsed documents reference ``symbol``, or None.
    """
    from crypto_etps.sec_prospectus import load_sec_submissions, load_sec_ticker_to_cik

    ua = user_agent.strip()
    sym = re.sub(r"\s+", "", symbol).upper()
    if not sym:
        return None

    try:
        tmap = load_sec_ticker_to_cik(ua)
    except (requests.RequestException, ValueError, TypeError, KeyError) as e:
        logger.debug("ticker map: %s", e)
        return None

    cik = tmap.get(sym)
    if not cik:
        return None

    sub = load_sec_submissions(cik, ua)
    if not sub:
        return None

    recent = sub.get("filings", {}).get("recent", {})
    forms = recent.get("form") or []
    accession_numbers = recent.get("accessionNumber") or []
    primary_documents = recent.get("primaryDocument") or []

    scanned = 0
    for index, form in enumerate(forms):
        if scanned >= MAX_FILINGS_TO_SCAN:
            break
        if not _form_allowed(form):
            continue
        if index >= len(accession_numbers):
            continue

        scanned += 1
        accession_number = accession_numbers[index]
        accession_clean = accession_number.replace("-", "")
        filing_url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{accession_clean}/{accession_number}-index.htm"
        )

        primary_document = primary_documents[index] if index < len(primary_documents) else ""
        primary_document_url = ""
        if primary_document:
            primary_document_url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                f"{accession_clean}/{primary_document}"
            )

        index_text = _fetch_text(filing_url, INDEX_PAGE_MAX_CHARS, ua)
        time.sleep(REQUEST_DELAY_SEC)
        if not index_text:
            continue

        tickers = _collect_tickers_for_filing(index_text, primary_document_url, ua)
        for t in tickers:
            if _ticker_matches_target(t, sym):
                return filing_url

    return None
