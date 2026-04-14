"""
Distributed (Global Market) value over time via the official RWA.xyz API.

The public homepage embed does not include historical points; weekly series require
``GET /v4/assets/aggregates/timeseries`` with a valid API key (see docs.rwa.xyz).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd
import requests
import streamlit as st

logger = logging.getLogger(__name__)

RWA_API_TIMESERIES = "https://api.rwa.xyz/v4/assets/aggregates/timeseries"

# Try filters that restrict to **distributed** tokenization; fall back to measure-only.
_FILTER_CANDIDATES: tuple[tuple[str, list[dict[str, Any]]], ...] = (
    (
        "distributed_flag",
        [{"operator": "equals", "field": "is_distributed", "value": True}],
    ),
    (
        "distributed_field",
        [{"operator": "equals", "field": "distributed", "value": True}],
    ),
    (
        "tokenization_distributed_upper",
        [{"operator": "equals", "field": "tokenization_type", "value": "DISTRIBUTED"}],
    ),
    (
        "tokenization_distributed_lower",
        [{"operator": "equals", "field": "tokenization_type", "value": "distributed"}],
    ),
    ("measure_only", []),
)


def _merge_timeseries_blocks(results: list[dict[str, Any]]) -> list[tuple[str, float]]:
    """Sum values by date across one or more API result blocks."""
    by_date: dict[str, float] = {}
    for block in results:
        for pt in block.get("points") or []:
            if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                continue
            d = str(pt[0])
            try:
                v = float(pt[1])
            except (TypeError, ValueError):
                continue
            by_date[d] = by_date.get(d, 0.0) + v
    return sorted(by_date.items(), key=lambda x: x[0])


def _fetch_timeseries_once(
    api_key: str,
    extra_filters: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]] | None, int | None, str | None]:
    filters: list[dict[str, Any]] = [
        {"operator": "equals", "field": "measure_slug", "value": "circulating_asset_value_dollar"},
        *extra_filters,
    ]
    query: dict[str, Any] = {
        "filter": {"operator": "and", "filters": filters},
        "aggregate": {
            "groupBy": "date",
            "aggregateFunction": "sum",
            "interval": "week",
            "mode": "stock",
        },
        "sort": {"field": "date", "direction": "asc"},
        "pagination": {"page": 1, "perPage": 96},
    }
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Accept": "application/json",
    }
    try:
        r = requests.get(
            RWA_API_TIMESERIES,
            params={"query": json.dumps(query, separators=(",", ":"))},
            headers=headers,
            timeout=120,
        )
    except (requests.RequestException, OSError) as e:
        return None, None, str(e)

    if r.status_code == 401:
        return None, 401, "Invalid or expired RWA API key (401)."

    if r.status_code >= 400:
        try:
            body = r.json()
            msg = body.get("message") or body.get("error") or r.text[:500]
        except (json.JSONDecodeError, ValueError, TypeError):
            msg = r.text[:500]
        logger.debug("RWA timeseries %s: %s", r.status_code, msg)
        return None, r.status_code, str(msg)

    try:
        payload = r.json()
    except json.JSONDecodeError as e:
        return None, None, f"Invalid JSON from RWA API: {e}"

    results = payload.get("results")
    if not isinstance(results, list):
        return None, None, "Unexpected RWA API response (no results list)."

    return results, 200, None


def fetch_distributed_global_timeseries(api_key: str) -> tuple[pd.DataFrame | None, str | None]:
    """
    Weekly points for distributed circulating asset value (USD), ascending by date.

    Tries several API filters so we stay aligned with the homepage **Distributed Asset Value**
    definition when the schema exposes a boolean or tokenization field.
    """
    if not (api_key or "").strip():
        return None, None

    last_http_error: str | None = None
    for _name, extras in _FILTER_CANDIDATES:
        blocks, status, err = _fetch_timeseries_once(api_key, extras)
        if err and status not in (None, 200):
            last_http_error = err
            if status == 401:
                return None, err
            continue
        if not blocks:
            continue
        merged = _merge_timeseries_blocks(blocks)
        if not merged:
            continue
        dates, vals = zip(*merged)
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(dates, utc=False),
                "value_usd": vals,
            }
        )
        df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
        return df, None

    if last_http_error:
        return None, last_http_error
    return None, "Could not load a weekly series from the RWA API (empty or unrecognized response)."


@st.cache_data(ttl=3600, show_spinner=False)
def load_rwa_global_market_timeseries_cached(
    api_key: str,
    *,
    _series_schema: int = 1,
) -> tuple[pd.DataFrame | None, str | None]:
    """Bump ``_series_schema`` to invalidate cache after query/filter changes."""
    _ = _series_schema
    return fetch_distributed_global_timeseries(api_key)


def build_rwa_global_market_plot_df(df: pd.DataFrame) -> pd.DataFrame:
    """Column names expected by ``crypto_etps.aum_history.build_aggregate_aum_plotly_figure``."""
    out = df.copy()
    out["aum_billions_usd"] = out["value_usd"].astype(float) / 1e9
    return out
