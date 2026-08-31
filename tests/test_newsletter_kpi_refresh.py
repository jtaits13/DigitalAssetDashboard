"""Freshness rules for weekly newsletter KPIs."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from newsletter_live_kpis import (
    _manual_override_in_week,
    _patch_kpi_rows,
    _refresh_issues,
    _snapshot_source,
    kpi_stale_banner_html,
)


def test_live_sources_are_fresh() -> None:
    week = date(2026, 8, 17)
    live = {
        "sources": {"tmmf": "live", "stable": "live", "rwa": "live", "crypto": "live", "etp": "live"},
        "fingerprints": {},
        "etp_aum_series": [{"date": "2026-08-15", "aum_billions": 97.7}],
    }
    assert _refresh_issues(live, None, week) == []


def test_prior_week_snapshot_is_an_error() -> None:
    week = date(2026, 8, 17)
    snap = {
        "week_end": "2026-08-10",
        "latest": {
            "sources": {"tmmf": "live"},
            "fingerprints": {"tmmf": "$12.95B|-0.011"},
        },
    }
    live = {
        "sources": {
            "tmmf": "stale_snapshot",
            "stable": "live",
            "rwa": "live",
            "crypto": "live",
            "etp": "live",
        },
        "fingerprints": {"tmmf": "$12.95B|-0.011"},
        "etp_aum_series": [{"date": "2026-08-15", "aum_billions": 97.7}],
    }
    issues = _refresh_issues(live, snap, week)
    assert len(issues) == 1
    assert "TMMF" in issues[0]
    assert "12.95B" in issues[0]
    assert "do not send" in kpi_stale_banner_html(issues).lower()


def test_same_week_live_snapshot_is_ok() -> None:
    week = date(2026, 8, 17)
    snap = {"week_end": "2026-08-17", "latest": {"sources": {"tmmf": "live"}}}
    assert _snapshot_source(snap, week, "tmmf") == "snapshot"
    assert _snapshot_source(snap, date(2026, 8, 24), "tmmf") == "stale_snapshot"


def test_lagging_etp_series_is_an_error() -> None:
    week = date(2026, 8, 17)
    live = {
        "sources": {"tmmf": "live", "stable": "live", "rwa": "live", "crypto": "live", "etp": "live"},
        "fingerprints": {},
        "etp_aum_series": [{"date": "2026-07-20", "aum_billions": 98.8}],
    }
    issues = _refresh_issues(live, None, week)
    assert issues
    assert "AUM series last point is 2026-07-20" in issues[0]


def test_manual_kpi_patch_updates_matching_label() -> None:
    from datetime import timedelta

    rows = _patch_kpi_rows(
        [{"label": "Market Cap", "value_display": "$302.27B", "delta_30d_pct": 0.01}],
        {"Market Cap": {"value_display": "$303.24B", "delta_30d_pct": 0.0259}},
    )
    assert rows[0]["value_display"] == "$303.24B"
    assert rows[0]["delta_30d_pct"] == 0.0259
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    assert _manual_override_in_week(monday.isoformat()) is True
    assert _manual_override_in_week((monday - timedelta(days=14)).isoformat()) is False


if __name__ == "__main__":
    test_live_sources_are_fresh()
    test_prior_week_snapshot_is_an_error()
    test_same_week_live_snapshot_is_ok()
    test_lagging_etp_series_is_an_error()
    test_manual_kpi_patch_updates_matching_label()
    print("test_newsletter_kpi_refresh: ok")
