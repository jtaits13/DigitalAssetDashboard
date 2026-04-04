"""
SEC EDGAR full-text search (public, no API key).

Uses https://efts.sec.gov/LATEST/search-index — same backend as sec.gov/edgar/search.
Per SEC fair-access rules, requests must send a descriptive User-Agent with contact info.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

EFTS_URL = "https://efts.sec.gov/LATEST/search-index"

# Full-text OR query (EDGAR search syntax). Results are post-filtered to fund-style forms.
# Does not include ETF or investment-company phrasing in the search string (per product request).
DEFAULT_SEARCH_Q = (
    "(crypto OR cryptocurrency OR "
    '"digital asset" OR "digital assets" OR '
    "blockchain OR "
    '"distributed ledger" OR DLT OR '
    "token OR tokens OR tokenized OR tokenization OR "
    "Bitcoin OR BTC OR Ethereum OR ETH OR Ether OR "
    "stablecoin OR stablecoins OR USDC OR USDT OR "
    '"tokenized treasury" OR "tokenized treasuries" OR '
    '"digital asset strategy" OR "blockchain strategy" OR "crypto strategy" OR '
    '"digital asset fund" OR "blockchain fund" OR "crypto fund" OR '
    '"tokenized fund" OR "tokenized assets" OR '
    '"digital commodity" OR "digital securities" OR "digital shares" OR '
    '"tokenized real estate" OR "tokenized credit" OR "tokenized bonds" OR "tokenized securities" OR '
    "RWA OR "
    '"real-world asset" OR "real-world assets" OR '
    '"exposure to digital assets" OR "exposure to crypto" OR "exposure to blockchain" OR '
    '"custody of digital assets" OR "digital asset custody" OR "crypto custody"'
    ")"
)

# Form types commonly used by registered funds and similar fund-style registrants.
_FORM_PREFIXES = (
    "NPORT",
    "N-CEN",
    "N-CSR",
    "N-CSRS",
    "N-1A",
    "N-2",
    "N-14",
    "N-8A",
    "N-54A",
    "N-23C",
    "485",
    "497",
    "40-17",
    "40-APP",
    "40-6C",
    "S-1",
    "S-3",
    "S-6",
    "S-11",
    "424B",
    "FWP",
    "NPORT-EX",
)


def _looks_like_fund_filing(form: str, display_names: list[str]) -> bool:
    fu = (form or "").upper().replace(" ", "")
    for p in _FORM_PREFIXES:
        if fu.startswith(p.replace(" ", "")) or p.replace(" ", "") in fu:
            return True
    blob = " ".join(display_names or []).lower()
    if any(
        w in blob
        for w in (
            " etf",
            "etf ",
            "trust",
            "fund",
            "series",
            "investment company",
            "unit investment",
            "closed-end",
        )
    ):
        # Exclude obvious non-fund junk unless name ties to funds/ETFs
        if fu in ("CORRESP", "UPLOAD", "DRSLTR"):
            return any(x in blob for x in ("etf", "trust", "fund", "crypto", "bitcoin", "index"))
        if fu in ("8-K", "10-K", "10-Q", "6-K") and not any(
            x in blob for x in ("etf", "trust", "fund", "series trust", "index fund")
        ):
            return False
        return True
    return False


@dataclass
class FundFilingRow:
    title: str
    form: str
    file_date: str
    accession: str
    cik: str
    detail_url: str


@dataclass
class FundFilingsResult:
    filings: list[FundFilingRow] = field(default_factory=list)
    error: str | None = None
    raw_hits_considered: int = 0


def _viewer_url(cik: str, accession: str) -> str:
    cik10 = re.sub(r"\D", "", str(cik))[:10].zfill(10)
    ad = str(accession).strip()
    return (
        f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik10}"
        f"&accession_number={ad}&xbrl_type=v"
    )


def _parse_hit(hit: dict[str, Any]) -> FundFilingRow | None:
    src = hit.get("_source") if isinstance(hit, dict) else None
    if not isinstance(src, dict):
        return None
    form = str(src.get("form") or src.get("file_type") or "").strip()
    names = src.get("display_names")
    if not isinstance(names, list):
        names = []
    str_names = [str(n) for n in names if n]
    if not _looks_like_fund_filing(form, str_names):
        return None
    adsh = str(src.get("adsh") or "").strip()
    if not adsh:
        return None
    ciks = src.get("ciks")
    cik = "0000000000"
    if isinstance(ciks, list) and ciks:
        cik = str(ciks[0])
    file_date = str(src.get("file_date") or "")[:10]
    title = str_names[0] if str_names else "Filing"
    desc = src.get("file_description")
    if isinstance(desc, str) and desc.strip():
        title = f"{title} — {desc.strip()}"[:200]
    return FundFilingRow(
        title=title[:220],
        form=form[:32],
        file_date=file_date,
        accession=adsh,
        cik=cik,
        detail_url=_viewer_url(cik, adsh),
    )


def fetch_crypto_fund_filings(
    user_agent: str,
    *,
    search_q: str | None = None,
    max_fetch: int = 100,
    max_list: int = 18,
) -> FundFilingsResult:
    """
    Query EDGAR full-text search and return fund-related rows (deduped by accession).

    user_agent must identify your app and include contact per https://www.sec.gov/os/accessing-edgar-data
    """
    out = FundFilingsResult()
    q = search_q if (search_q and search_q.strip()) else DEFAULT_SEARCH_Q
    params = {"q": q, "start": 0, "count": str(max_fetch)}
    url = f"{EFTS_URL}?{urlencode(params)}"
    headers = {
        "User-Agent": user_agent.strip(),
        "Accept": "application/json",
    }
    try:
        r = requests.get(url, headers=headers, timeout=45)
        r.raise_for_status()
        data = r.json()
    except requests.HTTPError as e:
        out.error = f"SEC search HTTP {e.response.status_code if e.response else 'error'}"
        logger.warning("EFTS HTTP: %s", e)
        return out
    except requests.RequestException as e:
        out.error = f"Network error: {e!s}"
        return out
    except ValueError as e:
        out.error = f"Invalid JSON: {e!s}"
        return out

    hits = data.get("hits", {}).get("hits") if isinstance(data, dict) else None
    if not isinstance(hits, list):
        out.error = "Unexpected SEC response shape."
        return out

    out.raw_hits_considered = len(hits)
    seen: set[str] = set()
    rows: list[FundFilingRow] = []
    for h in hits:
        row = _parse_hit(h)
        if row is None:
            continue
        if row.accession in seen:
            continue
        seen.add(row.accession)
        rows.append(row)
        if len(rows) >= max_list:
            break

    rows.sort(key=lambda x: x.file_date or "", reverse=True)
    out.filings = rows
    if not rows:
        out.error = (
            "No fund-style filings matched the filters in this batch. "
            "Try again later or adjust search keywords in sec_filings/client.py."
        )
    return out
