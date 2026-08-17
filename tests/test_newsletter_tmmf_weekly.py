"""TMMF chart keeps last week's printed newsletter figure."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from newsletter_live_kpis import tmmf_newsletter_weekly_points
from newsletter_weekly_charts import _tmmf_snapshot


def test_snapshot_recovers_printed_tmmf() -> None:
    snap = {
        "week_end": "2026-08-17",
        "latest": {
            "tmmf_distributed_usd": 13127825838.069447,
            "fingerprints": {"tmmf": "$13.13B|0.019"},
        },
        "history": [
            {
                "week_end": "2026-08-17",
                "tmmf_distributed_usd": 13127825838.069447,
                "fingerprints": {"tmmf": "$13.13B|0.019"},
            }
        ],
    }
    rows = tmmf_newsletter_weekly_points(snap)
    assert rows == [
        {
            "week_end": "2026-08-17",
            "value": 13127825838.069447,
            "source": "newsletter",
        }
    ]


def test_fingerprint_recovers_printed_tmmf() -> None:
    snap = {
        "week_end": "2026-08-17",
        "latest": {"fingerprints": {"tmmf": "$13.13B|0.019"}},
        "history": [{"week_end": "2026-08-10", "fingerprints": {"tmmf": "$12.95B|-0.011"}}],
    }
    rows = tmmf_newsletter_weekly_points(snap)
    by_week = {row["week_end"]: row["value"] for row in rows}
    assert by_week["2026-08-10"] == 12.95e9
    assert by_week["2026-08-17"] == 13.13e9


def test_val_7d_does_not_overwrite_last_week_newsletter() -> None:
    series = {
        "points": [
            {"week_end": "2026-08-17", "value": 13127825838.069447, "source": "newsletter"}
        ]
    }
    with (
        patch(
            "newsletter_live_kpis.tmmf_newsletter_weekly_points",
            return_value=[
                {
                    "week_end": "2026-08-17",
                    "value": 13127825838.069447,
                    "source": "newsletter",
                }
            ],
        ),
        patch(
            "newsletter_live_kpis.tmmf_history_points",
            return_value=[
                {"week_end": "2026-08-17", "value": 12.0e9, "source": "rwa_xyz_val_7d"},
                {"week_end": "2026-08-24", "value": 13.4e9, "source": "rwa_xyz"},
            ],
        ),
        patch("newsletter_live_kpis.tmmf_distributed_kpi", return_value=None),
    ):
        out = _tmmf_snapshot(date(2026, 8, 24), series)
    by_week = {row["week_end"]: row for row in out["points"]}
    assert by_week["2026-08-17"]["value"] == 13127825838.069447
    assert by_week["2026-08-17"]["source"] == "newsletter"
    assert by_week["2026-08-24"]["value"] == 13.4e9
    assert by_week["2026-08-24"]["source"] == "newsletter"


if __name__ == "__main__":
    test_snapshot_recovers_printed_tmmf()
    test_fingerprint_recovers_printed_tmmf()
    test_val_7d_does_not_overwrite_last_week_newsletter()
    print("test_newsletter_tmmf_weekly: ok")
