"""
Resolve fund prospectus links via SEC EDGAR (public data.sec.gov + company_tickers).

Requires a descriptive User-Agent with contact info per https://www.sec.gov/os/accessing-edgar-data
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

import requests
import streamlit as st

logger = logging.getLogger(__name__)

SEC_TICKERS_JSON = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_TMPL = "https://data.sec.gov/submissions/CIK{cik10}.json"

# Newest filing wins within each form type (outer order = preference).
_PROSPECTUS_FORMS: tuple[str, ...] = (
    "424B3",
    "424B2",
    "424I",
    "N-1A",
    "N-2",
    "S-1",
    "N-8B-2",
    "485BPOS",
    "485APOS",
    "497",
)


def _edgar_search_url(symbol: str) -> str:
    sym = re.sub(r"\s+", "", symbol).upper()
    return f"https://www.sec.gov/edgar/search/#/q={quote(sym, safe='')}"


def edgar_search_fallback_url(symbol: str) -> str:
    """SEC EDGAR search URL for a ticker (when no direct filing link)."""
    return _edgar_search_url(symbol)


def _build_archive_url(cik: int, accession: str, primary: str) -> str:
    acc = accession.replace("-", "")
    doc = quote(primary, safe="/")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"


def _pick_prospectus_filing(submissions: dict, cik: int) -> str | None:
    rec = submissions.get("filings", {}).get("recent", {})
    forms = rec.get("form") or []
    accs = rec.get("accessionNumber") or []
    docs = rec.get("primaryDocument") or []
    if not forms or not accs:
        return None
    n = min(len(forms), len(accs), len(docs))
    for form_wanted in _PROSPECTUS_FORMS:
        for i in range(n):
            if forms[i] == form_wanted and docs[i]:
                return _build_archive_url(cik, accs[i], docs[i])
    return None


@st.cache_data(ttl=86400, show_spinner=False)
def load_sec_ticker_to_cik(user_agent: str) -> dict[str, int]:
    """Uppercase ticker -> integer CIK (SEC company_tickers.json)."""
    ua = user_agent.strip()
    headers = {"User-Agent": ua, "Accept": "application/json"}
    r = requests.get(SEC_TICKERS_JSON, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()
    out: dict[str, int] = {}
    for _k, v in data.items():
        if isinstance(v, dict) and v.get("ticker"):
            out[str(v["ticker"]).upper()] = int(v["cik_str"])
    return out


@st.cache_data(ttl=3600, show_spinner=False)
def load_sec_submissions(cik: int, user_agent: str) -> dict | None:
    """Cached submissions JSON for one CIK."""
    ua = user_agent.strip()
    cik10 = str(cik).zfill(10)
    url = SEC_SUBMISSIONS_TMPL.format(cik10=cik10)
    headers = {"User-Agent": ua, "Accept": "application/json"}
    try:
        r = requests.get(url, headers=headers, timeout=35)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError) as e:
        logger.debug("SEC submissions %s: %s", cik, e)
        return None


def resolve_fund_prospectus_url(symbol: str, user_agent: str) -> str:
    """
    Prefer a direct EDGAR document link (latest matching prospectus-related form);
    fall back to EDGAR full-text search for the ticker.
    """
    ua = user_agent.strip()
    sym = re.sub(r"\s+", "", symbol).upper()
    if not sym:
        return _edgar_search_url(symbol)
    try:
        tmap = load_sec_ticker_to_cik(ua)
    except (requests.RequestException, ValueError, TypeError, KeyError) as e:
        logger.debug("SEC ticker map: %s", e)
        return _edgar_search_url(symbol)
    cik = tmap.get(sym)
    if not cik:
        return _edgar_search_url(symbol)
    sub = load_sec_submissions(cik, ua)
    if not sub:
        return _edgar_search_url(symbol)
    url = _pick_prospectus_filing(sub, cik)
    return url if url else _edgar_search_url(symbol)


def clear_sec_prospectus_caches() -> None:
    load_sec_ticker_to_cik.clear()
    load_sec_submissions.clear()
