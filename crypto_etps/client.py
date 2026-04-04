"""
Fetch and parse the public crypto ETF list at stockanalysis.com/list/crypto-etfs/.

No API key; HTML parsing only. Respect site terms of use and rate limits in production.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

LIST_URL = "https://stockanalysis.com/list/crypto-etfs/"

DEFAULT_USER_AGENT = (
    "JPM-Digital/1.0 (U.S. crypto ETP widget; contact per site terms; "
    "set a custom User-Agent in app secrets if needed)"
)


@dataclass(frozen=True)
class CryptoEtpRow:
    symbol: str
    name: str
    price: str
    pct_change: str
    assets_display: str
    assets_usd: float | None


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


def fetch_crypto_etps_list(
    user_agent: str | None = None,
    *,
    timeout: int = 45,
) -> CryptoEtpsResult:
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
            )
        )

    if not rows:
        out.error = "No ETF rows parsed from the page."
        return out

    out.rows = rows
    return out


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
