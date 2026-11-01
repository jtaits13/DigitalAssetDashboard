"""Chart freshness flags for weekly newsletter sections."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from newsletter_weekly_charts import (
    _series_lag_issue,
    _weekly_points_from_daily,
    _with_previous_series,
    chart_plot_points,
)


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


def test_monday_value_is_that_day_and_series_ends_on_latest_day() -> None:
    by_day = {
        date(2026, 9, 21): 90.0,
        date(2026, 9, 28): 95.0,
        date(2026, 10, 5): 97.0,
        date(2026, 10, 12): 100.0,
        date(2026, 10, 18): 200.0,
        date(2026, 10, 19): 110.0,
        date(2026, 10, 25): 180.0,
        date(2026, 10, 26): 120.0,
        date(2026, 11, 1): 130.0,
    }
    out = _weekly_points_from_daily(by_day, date(2026, 11, 2), "defillama")
    values = {row["week_end"]: row["value"] for row in out}
    assert values["2026-10-12"] == 100.0
    assert values["2026-10-19"] == 110.0
    assert values["2026-10-26"] == 120.0
    assert values["2026-11-01"] == 130.0
    assert out[-1]["week_end"] == "2026-11-01"


def test_tmmf_chart_is_one_month_and_weekly() -> None:
    series = {
        "points": [
            {"week_end": "2026-07-13", "value": 13.2e9, "source": "git_snapshot"},
            {"week_end": "2026-08-17", "value": 13.1e9, "source": "newsletter"},
            {"week_end": "2026-08-21", "value": 14.6e9, "source": "rwa_xyz_val_30d"},
            {"week_end": "2026-09-28", "value": 13.51e9, "source": "newsletter"},
            {"week_end": "2026-09-29", "value": 13.510e9, "source": "newsletter"},
            {"week_end": "2026-10-02", "value": 13.52e9, "source": "rwa_xyz_val_30d"},
            {"week_end": "2026-10-05", "value": 13.59e9, "source": "newsletter"},
            {"week_end": "2026-10-12", "value": 13.60e9, "source": "newsletter"},
            {"week_end": "2026-10-25", "value": 13.23e9, "source": "rwa_xyz_val_7d"},
            {"week_end": "2026-11-01", "value": 12.773e9, "source": "newsletter"},
            {"week_end": "2026-11-02", "value": 12.770e9, "source": "newsletter"},
        ]
    }
    plotted = [day.isoformat() for day, _ in chart_plot_points(series)]
    assert plotted == ["2026-09-28", "2026-10-05", "2026-10-12", "2026-11-01"]


if __name__ == "__main__":
    test_tmmf_requires_this_monday()
    test_stablecoin_week_old_point_is_ok()
    test_live_miss_reuses_last_week_and_flags()
    test_fresh_live_series_has_no_flag()
    test_monday_value_is_that_day_and_series_ends_on_latest_day()
    test_tmmf_chart_is_one_month_and_weekly()
    print("test_newsletter_chart_refresh: ok")
