"""
Fetch RWA.xyz homepage embedded league table (Networks) from Next.js __NEXT_DATA__.

Not an official API; structure may change. For production use RWA.xyz's data products.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)

APP_HOME = "https://app.rwa.xyz/"
USER_AGENT = "JPM-Digital/1.0 (RWA league widget; contact via app maintainer)"


@dataclass(frozen=True)
class RwaNetworkLeagueRow:
    rank: int
    network: str
    network_href: str | None  # path e.g. /networks/ethereum
    rwa_count: int
    total_value_usd: float
    # Fractional change in total value — from embedded field `value_7d_change` (7 calendar days).
    # There is no value_30d_change in the public __NEXT_DATA__ payload.
    value_change_7d_raw: float | None
    market_share_raw: float  # fraction 0–1
    # Optional fractional 7D change in market share (if present in embedded payload).
    market_share_change_7d_raw: float | None


def _extract_next_data(html: str) -> dict[str, Any] | None:
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
        html,
        re.DOTALL,
    )
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as e:
        logger.debug("__NEXT_DATA__ JSON: %s", e)
        return None


def _network_rows_from_props(props: dict[str, Any]) -> list[dict[str, Any]] | None:
    lt = props.get("pageProps", {}).get("leagueTableTabs", {})
    all_tabs = lt.get("all")
    if not isinstance(all_tabs, list):
        return None
    for tab in all_tabs:
        if isinstance(tab, dict) and tab.get("key") == "parent_networks":
            data = tab.get("data") or {}
            rows = data.get("rows")
            if isinstance(rows, list):
                return rows
    return None


def fetch_rwa_network_league() -> tuple[list[RwaNetworkLeagueRow], str | None]:
    """
    Return Networks league table for the 'All' view (same as homepage default).

    Percentage change in total value comes from **`value_7d_change`** on each row.
    The embed does **not** include a 30-day total-value change field.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    try:
        r = requests.get(APP_HOME, headers=headers, timeout=60)
        r.raise_for_status()
    except (requests.RequestException, OSError) as e:
        logger.debug("RWA fetch: %s", e)
        return [], str(e)

    payload = _extract_next_data(r.text)
    if not payload:
        return [], "Could not parse __NEXT_DATA__ from app.rwa.xyz (layout may have changed)."

    raw_rows = _network_rows_from_props(payload.get("props", {}))
    if not raw_rows:
        return [], "Networks league table not found in page data."

    out: list[RwaNetworkLeagueRow] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        group = row.get("group") or {}
        name = str(group.get("name") or "").strip() or "—"
        link = group.get("linkTo") or {}
        href = link.get("href") if isinstance(link, dict) else None
        if isinstance(href, str) and href.strip():
            network_href = href.strip()
        else:
            network_href = None

        ri = row.get("rowIndex")
        rank = int(ri) + 1 if isinstance(ri, int) else len(out) + 1

        ac = row.get("asset_count")
        rwa_count = int(ac) if isinstance(ac, (int, float)) else 0

        val = row.get("value")
        total = float(val) if isinstance(val, (int, float)) else 0.0

        ms = row.get("market_share_pct")
        msf = float(ms) if isinstance(ms, (int, float)) else 0.0

        ms7 = None
        for k in (
            "market_share_7d_change",
            "market_share_pct_7d_change",
            "market_share_change_7d",
            "market_share_change",
        ):
            raw = row.get(k)
            if isinstance(raw, (int, float)):
                ms7 = float(raw)
                break

        v7 = row.get("value_7d_change")
        v7f = float(v7) if isinstance(v7, (int, float)) else None

        out.append(
            RwaNetworkLeagueRow(
                rank=rank,
                network=name,
                network_href=network_href,
                rwa_count=rwa_count,
                total_value_usd=total,
                value_change_7d_raw=v7f,
                market_share_raw=msf,
                market_share_change_7d_raw=ms7,
            )
        )

    return out, None
