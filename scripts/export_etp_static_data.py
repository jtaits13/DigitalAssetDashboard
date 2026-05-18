"""
Fast partial refresh for the static site: U.S. ETP fund list, KPI strip, and AUM chart only.

Rewrites ``static_home/data/etps.json``, ``etp_kpis.json``, and ``aum_series.json``.
Patches ``manifest.json`` with ``etp_refreshed_at`` and ETP-scoped errors only.
All other JSON (crypto, RWA, news, etc.) is left unchanged.

Run:  python scripts/export_etp_static_data.py
Typical runtime: ~2–4 minutes (StockAnalysis scrape + Yahoo AUM chart + Farside flows).
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

sys.path.insert(0, str(_REPO / "scripts"))
from export_static_site_data import (  # noqa: E402
    OUT,
    export_etp_json_bundle,
    merge_etp_refresh_into_manifest,
)


def main() -> None:
    summary = export_etp_json_bundle()
    merge_etp_refresh_into_manifest(summary)
    print(
        f"Wrote ETP JSON to {OUT} ({summary['etp_count']} funds, "
        f"{summary['aum_points']} chart points). "
        "Other static_home/data/*.json unchanged."
    )
    if summary["errors"]:
        print("Warnings:", summary["errors"])


if __name__ == "__main__":
    main()
