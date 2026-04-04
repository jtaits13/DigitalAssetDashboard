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

# Broad OR query: high recall for crypto / digital assets / blockchain / tokenization.
# Do NOT wrap the whole expression in parentheses — SEC's parser treats a trailing ")" as a
# required match on the character ")", which returns zero results.
DEFAULT_SEARCH_Q = (
    "crypto OR cryptocurrency OR blockchain OR bitcoin OR ethereum OR "
    '"digital asset" OR "digital assets" OR "virtual currency" OR "digital currency" OR '
    "tokenized OR tokenization OR token OR tokens OR "
    "stablecoin OR stablecoins OR USDC OR USDT OR BTC OR ETH OR Ether OR "
    "defi OR web3 OR NFT OR NFTs OR altcoin OR "
    '"distributed ledger" OR DLT OR "smart contract" OR '
    "satoshi OR hashrate OR mining OR validator OR staking OR "
    "RWA OR rwa OR "
    '"real-world asset" OR "real world asset" OR "real-world assets" OR '
    '"tokenized asset" OR "tokenized assets" OR "tokenized security" OR "tokenized securities" OR '
    '"tokenized treasury" OR "tokenized treasuries" OR "tokenized bond" OR "tokenized bonds" OR '
    '"tokenized credit" OR "tokenized real estate" OR '
    '"digital commodity" OR "digital securities" OR "digital shares" OR '
    '"digital asset strategy" OR "blockchain strategy" OR "crypto strategy" OR '
    '"digital asset fund" OR "blockchain fund" OR "crypto fund" OR "tokenized fund" OR '
    '"exposure to crypto" OR "exposure to blockchain" OR "exposure to digital assets" OR '
    '"digital asset custody" OR "crypto custody" OR "custody of digital assets"'
)

# Post-filter: only show traditional registered-fund / investment-company style forms
# (NPORT, N-CEN, 485/497, 40-*, etc.). Excludes 8-K, 10-Q, S-1, and other operating-co filings.
_ALLOWED_FORM_PREFIXES: tuple[str, ...] = (
    "NPORT",
    "N-CEN",
    "N-CSR",
    "N-CSRS",
    "N-1A",
    "N-2",
    "N-14",
    "N-8A",
    "N-8F",
    "N-54A",
    "N-23C",
    "N-5",
    "N-6",
    "N-LIQUID",
    "N-MFP",
    "485",
    "497",
    "40-17",
    "40-APP",
    "40-6C",
    "40-33",
    "40-6B",
    "24F-2",
    "424B",
    "FWP",
    "S-6",  # UIT / unit investment trust registration
)

_EXCLUDED_FORM_PREFIXES: tuple[str, ...] = (
    "8-K",
    "10-K",
    "10-Q",
    "6-K",
    "20-F",
    "S-1",
    "S-3",
    "S-4",
    "S-11",
    "CORRESP",
    "UPLOAD",
    "DRSLTR",
    "DEF 14A",
    "PRE 14A",
    "SC 13D",
    "SC 13G",
)


def _primary_form_fields(src: dict[str, Any]) -> tuple[str, str]:
    """Best-effort form label from SEC hit (form, root_forms[0], or file_type)."""
    form = str(src.get("form") or "").strip().upper()
    if not form:
        rf = src.get("root_forms")
        if isinstance(rf, list) and rf:
            form = str(rf[0]).strip().upper()
    ft = str(src.get("file_type") or "").strip().upper()
    primary = form or ft
    return primary, ft


def _fund_like_display_names(blob: str) -> bool:
    """424B/FWP appear for stocks too; require IC- or ETF-style naming."""
    b = blob.lower()
    return any(
        x in b
        for x in (
            "trust",
            "etf",
            "fund",
            "series",
            "investment company",
            "unit investment",
            "closed-end",
            "advisers act",
            "1940 act",
        )
    )


def _is_traditional_fund_form(primary: str, display_names_blob: str) -> bool:
    if not primary or primary == "—":
        return False
    base = primary.split("/")[0].strip()
    for ex in _EXCLUDED_FORM_PREFIXES:
        if base.startswith(ex) or primary.startswith(ex):
            return False
    # Reject other S-* except S-6 (handled in allowlist)
    if primary.startswith("S-") and not primary.startswith("S-6"):
        return False
    for ap in _ALLOWED_FORM_PREFIXES:
        if not (base.startswith(ap) or primary.startswith(ap)):
            continue
        # Prospectus / FWP: must look like a fund product name, not a corporate equity deal
        if ap in ("424B", "FWP") or base.startswith("424") or primary.startswith("FWP"):
            if not _fund_like_display_names(display_names_blob):
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
    primary, _ft = _primary_form_fields(src)
    names = src.get("display_names")
    if not isinstance(names, list):
        names = []
    str_names = [str(n) for n in names if n]
    display_blob = " ".join(str_names)
    if not _is_traditional_fund_form(primary, display_blob):
        return None
    form = str(src.get("form") or src.get("file_type") or "").strip() or primary or "—"
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
    page_size: int = 100,
    max_pages: int = 8,
    max_list: int = 22,
) -> FundFilingsResult:
    """
    Query EDGAR full-text search, keep only traditional fund/IC form types, dedupe by accession.

    user_agent must identify your app and include contact per https://www.sec.gov/os/accessing-edgar-data
    """
    out = FundFilingsResult()
    q = search_q if (search_q and search_q.strip()) else DEFAULT_SEARCH_Q
    headers = {
        "User-Agent": user_agent.strip(),
        "Accept": "application/json",
    }

    seen: set[str] = set()
    rows: list[FundFilingRow] = []
    total_hits_seen = 0

    try:
        for page in range(max_pages):
            start = page * page_size
            params = {"q": q, "start": str(start), "count": str(page_size)}
            url = f"{EFTS_URL}?{urlencode(params)}"
            r = requests.get(url, headers=headers, timeout=45)
            r.raise_for_status()
            data = r.json()
            hits = data.get("hits", {}).get("hits") if isinstance(data, dict) else None
            if not isinstance(hits, list):
                out.error = "Unexpected SEC response shape."
                return out
            total_hits_seen += len(hits)
            if not hits:
                break
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
            if len(rows) >= max_list or len(hits) < page_size:
                break
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

    out.raw_hits_considered = total_hits_seen
    if total_hits_seen == 0:
        out.error = (
            "SEC search returned no hits for this query. "
            "The index may be busy or the query may need adjustment."
        )
        return out

    rows.sort(key=lambda x: x.file_date or "", reverse=True)
    out.filings = rows[:max_list]
    if not out.filings:
        out.error = (
            "No traditional fund forms (NPORT, N-CEN, 497, 485, etc.) appeared in the search results. "
            "Try again later or broaden keywords in sec_filings/client.py."
        )
    return out
