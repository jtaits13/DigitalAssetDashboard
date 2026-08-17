"""Chart freshness flags for weekly newsletter sections."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from newsletter_weekly_charts import _series_lag_issue, _with_previous_series


def _two_points(last_day: str, last_value: float = 2.0) -> dict:
    return {
        "points": [
            {"week_end": "2026-08-03", "value": 1.0},
            {"week_end": last_day, "value": last_value},
        ]
    }


def test_tmmf_requires_this_monday() -> None:
    week = date(2026, 8, 24)
    issue = _series_lag_issue("TMMF", _two_points("2026-08-17"), week, 0)
    assert issue is not None
    assert "2026-08-17" in issue
    assert _series_lag_issue("TMMF", _two_points("2026-08-24"), week, 0) is None


def test_stablecoin_week_old_point_is_ok() -> None:
    week = date(2026, 8, 17)
    assert _series_lag_issue("Stablecoins", _two_points("2026-08-10"), week, 8) is None
    issue = _series_lag_issue("Stablecoins", _two_points("2026-08-03"), week, 8)
    assert issue is not None
    assert "2026-08-03" in issue


def test_live_miss_reuses_last_week_and_flags() -> None:
    prev = _two_points("2026-08-10")
    out, issue = _with_previous_series(
        label="Crypto",
        live={"points": []},
        previous=prev,
        week_end=date(2026, 8, 17),
        max_lag_days=4,
    )
    assert out["points"] == prev["points"]
    assert issue is not None
    assert "did not refresh" in issue


def test_fresh_live_series_has_no_flag() -> None:
    live = _two_points("2026-08-17")
    out, issue = _with_previous_series(
        label="RWA",
        live=live,
        previous=_two_points("2026-08-10"),
        week_end=date(2026, 8, 17),
        max_lag_days=8,
    )
    assert out["points"] == live["points"]
    assert issue is None


if __name__ == "__main__":
    test_tmmf_requires_this_monday()
    test_stablecoin_week_old_point_is_ok()
    test_live_miss_reuses_last_week_and_flags()
    test_fresh_live_series_has_no_flag()
    print("test_newsletter_chart_refresh: ok")
