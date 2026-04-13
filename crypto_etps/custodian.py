"""Bitcoin / digital-asset ETP custodian labels (ticker → string).

Public ETF listing pages (StockAnalysis, Yahoo Finance) generally do **not** expose a stable
HTML field for “Custodian,” and Yahoo’s JSON APIs often return 401 outside of specialized
clients. This module resolves custodian text from a **curated JSON map** shipped with the app
(``data/custodian_by_ticker.json``), which you can extend or override with issuer / prospectus
data. Unknown tickers return an empty string (displayed as “—” in the table).
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_FILE = Path(__file__).resolve().parent / "data" / "custodian_by_ticker.json"


@lru_cache(maxsize=1)
def _load_map() -> dict[str, str]:
    if not _DATA_FILE.is_file():
        logger.warning("Custodian data file missing: %s", _DATA_FILE)
        return {}
    try:
        raw = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not load custodian map: %s", e)
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        key = k.strip().upper()
        if key:
            out[key] = v.strip()
    return out


def resolve_custodian(ticker: str) -> str:
    """Return custodian description for ``ticker``, or empty string if unknown."""
    sym = (ticker or "").strip().upper()
    if not sym:
        return ""
    return _load_map().get(sym, "")
