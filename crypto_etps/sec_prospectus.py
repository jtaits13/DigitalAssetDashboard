"""
Resolve S-1 filing links via SEC EDGAR (data.sec.gov submissions + company_tickers).

Direct link: newest S-1 / S-1/A (etc.) primary document in recent filings when present.
Fallback: EDGAR browse for type=S-1 for that CIK, then EDGAR search (ticker + S-1 hint).

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

# S-1, S-1/A, S-1M, etc. — not S-11, S-12, …
_S1_FORM_RE = re.compile(r"^S-1(?:/[A-Z0-9]+)?$", re.IGNORECASE)


def _is_s1_form(form: str) -> bool:
    return bool(form and _S1_FORM_RE.match(form.strip()))


def _edgar_search_ticker_only(symbol: str) -> str:
    sym = re.sub(r"\s+", "", symbol).upper()
    return f"https://www.sec.gov/edgar/search/#/q={quote(sym, safe='')}"


def _edgar_search_s1_hint(symbol: str) -> str:
    """When CIK is unknown: search pre-filled with ticker and S-1."""
    sym = re.sub(r"\s+", "", symbol).upper()
    q = quote(f"{sym} S-1", safe="")
    return f"https://www.sec.gov/edgar/search/#/q={q}"


def edgar_s1_fallback_url(symbol: str) -> str:
    """Fallback when row has no resolved URL (should be rare)."""
    return _edgar_search_s1_hint(symbol)


def _build_archive_url(cik: int, accession: str, primary: str) -> str:
    acc = accession.replace("-", "")
    doc = quote(primary, safe="/")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"


def _browse_s1_url(cik: int) -> str:
    """List of S-1 filings for this registrant (newest at top in SEC UI)."""
    return (
        "https://www.sec.gov/cgi-bin/browse-edgar"
        f"?action=getcompany&CIK={cik}&type=S-1&owner=exclude&count=40"
    )


def _pick_s1_document_url(submissions: dict, cik: int) -> str | None:
    """Newest S-1 family filing in `filings.recent` with a primary document."""
    rec = submissions.get("filings", {}).get("recent", {})
    forms = rec.get("form") or []
    accs = rec.get("accessionNumber") or []
    docs = rec.get("primaryDocument") or []
    if not forms or not accs:
        return None
    n = min(len(forms), len(accs), len(docs))
    for i in range(n):
        if _is_s1_form(forms[i]) and docs[i]:
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


def resolve_s1_filing_url(symbol: str, user_agent: str) -> str:
    """
    Prefer the primary document URL for the newest S-1 / S-1/A filing in recent history.

    If none appear in the submissions `recent` slice, link to EDGAR browse filtered to S-1
    for that CIK. If CIK is unknown, link to EDGAR search (ticker + S-1).
    """
    ua = user_agent.strip()
    sym = re.sub(r"\s+", "", symbol).upper()
    if not sym:
        return _edgar_search_s1_hint(symbol)
    try:
        tmap = load_sec_ticker_to_cik(ua)
    except (requests.RequestException, ValueError, TypeError, KeyError) as e:
        logger.debug("SEC ticker map: %s", e)
        return _edgar_search_s1_hint(symbol)
    cik = tmap.get(sym)
    if not cik:
        return _edgar_search_s1_hint(symbol)
    sub = load_sec_submissions(cik, ua)
    if not sub:
        return _browse_s1_url(cik)
    direct = _pick_s1_document_url(sub, cik)
    if direct:
        return direct
    return _browse_s1_url(cik)


def clear_sec_prospectus_caches() -> None:
    load_sec_ticker_to_cik.clear()
    load_sec_submissions.clear()
