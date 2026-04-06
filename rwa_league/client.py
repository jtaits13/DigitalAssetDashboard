"""
Fetch RWA.xyz homepage embedded league table (Networks) from Next.js __NEXT_DATA__.

Not an official API; structure may change. For production use RWA.xyz's data products.
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
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
    network_slug: str | None  # e.g. ethereum — for matching gigatable rows
    rwa_count: int
    total_value_usd: float
    # Implied 30d total-value change (fraction), from aggregating asset pct_change_30d; None if no assets match slug
    value_change_30d_raw: float | None
    market_share_raw: float  # fraction 0–1


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


def _slug_from_network_href(href: str | None) -> str | None:
    if not href or not isinstance(href, str):
        return None
    m = re.search(r"/networks/([^/?#]+)", href.strip())
    return m.group(1) if m else None


def _value_change_30d_by_network_slug(gigatable_rows: list[dict[str, Any]]) -> dict[str, float]:
    """
    For each chain slug, estimate network 30d total-value change from assets:

    For each asset, value_30d_ago ≈ value / (1 + pct_change_30d). Split value and
    value_30d_ago evenly across listed networks (pro-rata), then
    network_change = (sum(value) - sum(value_30d_ago)) / sum(value_30d_ago).

    This approximates “change in total value” and may differ from RWA’s parent-network rollup.
    """
    current: dict[str, float] = defaultdict(float)
    ago: dict[str, float] = defaultdict(float)
    for row in gigatable_rows:
        if not isinstance(row, dict):
            continue
        v = row.get("value")
        p30 = row.get("pct_change_30d")
        nets = row.get("networks") or []
        if not isinstance(v, (int, float)) or not nets:
            continue
        if not isinstance(p30, (int, float)):
            continue
        v = float(v)
        p30 = float(p30)
        if abs(1.0 + p30) < 1e-15:
            continue
        v_ago = v / (1.0 + p30)
        n = len(nets)
        for net in nets:
            if not isinstance(net, dict):
                continue
            slug = net.get("slug")
            if not slug or not isinstance(slug, str):
                continue
            current[slug] += v / n
            ago[slug] += v_ago / n
    out: dict[str, float] = {}
    for slug, c in current.items():
        a = ago[slug]
        if a > 0:
            out[slug] = (c - a) / a
    return out


def fetch_rwa_network_league() -> tuple[list[RwaNetworkLeagueRow], str | None]:
    """
    Return Networks league table for the 'All' view (same as homepage default).

    30D% is the estimated change in total value over 30 days, derived from
    gigatableRows asset `pct_change_30d` (see `_value_change_30d_by_network_slug`).
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

    page_props = payload.get("props", {}).get("pageProps", {})
    giga = page_props.get("gigatableRows")
    slug_to_chg: dict[str, float] = {}
    if isinstance(giga, list):
        slug_to_chg = _value_change_30d_by_network_slug(giga)

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
        slug = _slug_from_network_href(network_href)

        ri = row.get("rowIndex")
        rank = int(ri) + 1 if isinstance(ri, int) else len(out) + 1

        ac = row.get("asset_count")
        rwa_count = int(ac) if isinstance(ac, (int, float)) else 0

        val = row.get("value")
        total = float(val) if isinstance(val, (int, float)) else 0.0

        ms = row.get("market_share_pct")
        msf = float(ms) if isinstance(ms, (int, float)) else 0.0

        v30: float | None = None
        if slug:
            v30 = slug_to_chg.get(slug)

        out.append(
            RwaNetworkLeagueRow(
                rank=rank,
                network=name,
                network_href=network_href,
                network_slug=slug,
                rwa_count=rwa_count,
                total_value_usd=total,
                value_change_30d_raw=v30,
                market_share_raw=msf,
            )
        )

    return out, None
