"""
Fetch crypto ETF list from stockanalysis.com/list/crypto-etfs/, then enrich each
ETF with Profile fields from its detail page (issuer, inception, past-year return
as a proxy for 52-week performance).

No API key; HTML parsing only. Respect site terms of use and rate limits.
"""

from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

LIST_URL = "https://stockanalysis.com/list/crypto-etfs/"
ETF_PAGE_TMPL = "https://stockanalysis.com/etf/{symbol}/"

DEFAULT_USER_AGENT = (
    "JPM-Digital/1.0 (U.S. crypto ETP widget; contact per site terms; "
    "set a custom User-Agent in app secrets if needed)"
)

# Narrative on ETF detail pages (verified across multiple symbols).
_PAST_YEAR_RETURN_RE = re.compile(
    r"had a total return of ([+-]?[0-9.]+)% in the past year",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CryptoEtpRow:
    symbol: str
    name: str
    price: str
    pct_change: str  # daily % from list page (reference)
    assets_display: str
    assets_usd: float | None
    issuer: str
    inception: str
    pct_52w: float | None  # from "past year" narrative on detail page


@dataclass
class CryptoEtpsResult:
    rows: list[CryptoEtpRow]
    error: str | None = None


def _parse_assets_usd(raw: str) -> float | None:
    s = raw.strip().replace(",", "").replace("$", "")
    if not s or s in ("-", "—"):
        return None
    s = s.upper()
    mult = 1.0
    if s and s[-1] in "KMBT":
        suffix = s[-1]
        s = s[:-1]
        mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[suffix]
    try:
        return float(s) * mult
    except ValueError:
        return None


def _parse_past_year_return(html: str) -> float | None:
    m = _PAST_YEAR_RETURN_RE.search(html)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _parse_issuer_inception(soup: BeautifulSoup) -> tuple[str, str]:
    issuer = ""
    for span in soup.find_all("span"):
        t = span.get_text(strip=True)
        if t == "ETF Provider":
            parent = span.parent
            if parent:
                a = parent.find("a")
                if a:
                    issuer = a.get_text(strip=True)
            break
    inception = ""
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) == 2 and tds[0].get_text(strip=True) == "Inception Date":
            inception = tds[1].get_text(strip=True)
            break
    return issuer, inception


def fetch_etf_profile_fields(
    symbol: str,
    user_agent: str,
    *,
    timeout: int = 22,
) -> tuple[str, str, float | None]:
    """Issuer, inception date, past-year % (used as 52W performance)."""
    sym = re.sub(r"\s+", "", symbol).lower()
    if not sym:
        return "", "", None
    url = ETF_PAGE_TMPL.format(symbol=sym)
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.debug("ETF profile %s: %s", sym, e)
        return "", "", None
    issuer, inception = _parse_issuer_inception(BeautifulSoup(r.text, "html.parser"))
    pct = _parse_past_year_return(r.text)
    return issuer, inception, pct


def fetch_crypto_etps_list(
    user_agent: str | None = None,
    *,
    timeout: int = 45,
) -> CryptoEtpsResult:
    """List page only (no profile enrichment)."""
    ua = (user_agent or DEFAULT_USER_AGENT).strip()
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    out = CryptoEtpsResult(rows=[])
    try:
        r = requests.get(LIST_URL, headers=headers, timeout=timeout)
        r.raise_for_status()
    except requests.HTTPError as e:
        out.error = f"Could not load ETF list (HTTP {e.response.status_code if e.response else 'error'})."
        logger.warning("StockAnalysis HTTP: %s", e)
        return out
    except requests.RequestException as e:
        out.error = f"Network error loading ETF list: {e!s}"
        return out

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")
    if not table:
        out.error = "ETF table not found on the page (layout may have changed)."
        return out

    rows: list[CryptoEtpRow] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 5:
            continue
        sym_cell = cells[0]
        sym_text = sym_cell.get_text(strip=True)
        if not sym_text or sym_text.lower() == "symbol":
            continue
        name = cells[1].get_text(strip=True)
        price = cells[2].get_text(strip=True)
        pct = cells[3].get_text(strip=True)
        assets_disp = cells[4].get_text(strip=True)
        assets_usd = _parse_assets_usd(assets_disp)
        rows.append(
            CryptoEtpRow(
                symbol=sym_text,
                name=name,
                price=price,
                pct_change=pct,
                assets_display=assets_disp,
                assets_usd=assets_usd,
                issuer="",
                inception="",
                pct_52w=None,
            )
        )

    if not rows:
        out.error = "No ETF rows parsed from the page."
        return out

    out.rows = rows
    return out


def enrich_crypto_etps_rows(
    rows: list[CryptoEtpRow],
    user_agent: str,
    *,
    max_workers: int = 14,
) -> list[CryptoEtpRow]:
    """Parallel fetch of issuer, inception, past-year % for each symbol."""
    ua = (user_agent or DEFAULT_USER_AGENT).strip()
    symbols = [r.symbol for r in rows]
    results: dict[str, tuple[str, str, float | None]] = {}

    def one(sym: str) -> tuple[str, str, str, float | None]:
        iss, inc, p52 = fetch_etf_profile_fields(sym, ua)
        return sym, iss, inc, p52

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(one, sym): sym for sym in symbols}
        for fut in as_completed(futures):
            try:
                sym, iss, inc, p52 = fut.result()
                results[sym] = (iss, inc, p52)
            except Exception as e:
                logger.debug("enrich row: %s", e)

    out: list[CryptoEtpRow] = []
    for r in rows:
        iss, inc, p52 = results.get(r.symbol, ("", "", None))
        out.append(
            CryptoEtpRow(
                symbol=r.symbol,
                name=r.name,
                price=r.price,
                pct_change=r.pct_change,
                assets_display=r.assets_display,
                assets_usd=r.assets_usd,
                issuer=iss,
                inception=inc,
                pct_52w=p52,
            )
        )
    return out


def fetch_crypto_etps_enriched(
    user_agent: str | None = None,
    *,
    list_timeout: int = 45,
    max_workers: int = 14,
) -> CryptoEtpsResult:
    base = fetch_crypto_etps_list(user_agent, timeout=list_timeout)
    if base.error and not base.rows:
        return base
    rows = enrich_crypto_etps_rows(
        base.rows,
        (user_agent or DEFAULT_USER_AGENT).strip(),
        max_workers=max_workers,
    )
    return CryptoEtpsResult(rows=rows, error=base.error)


def total_aum_usd(rows: list[CryptoEtpRow]) -> float:
    return sum(r.assets_usd for r in rows if r.assets_usd is not None)


def format_usd_compact(n: float) -> str:
    if n >= 1e12:
        return f"${n / 1e12:.2f}T"
    if n >= 1e9:
        return f"${n / 1e9:.2f}B"
    if n >= 1e6:
        return f"${n / 1e6:.2f}M"
    if n >= 1e3:
        return f"${n / 1e3:.2f}K"
    return f"${n:,.2f}"


def sorted_by_assets(rows: list[CryptoEtpRow]) -> list[CryptoEtpRow]:
    return sorted(
        rows,
        key=lambda r: (r.assets_usd is None, -(r.assets_usd or 0.0)),
    )
