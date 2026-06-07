"""
Validate committed static_home/data JSON before GitHub Pages deploy.

Ensures required snapshot files exist, parse as JSON, and meet minimum shape checks
so pages do not silently render empty after a code-only deploy.

Run from repo root:  python scripts/validate_static_json.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

_REPO = Path(__file__).resolve().parent.parent
DATA = _REPO / "static_home" / "data"


class Check:
    def __init__(self, path: str, validate: Callable[[dict[str, Any] | list[Any], Path], str | None]):
        self.path = path
        self.validate = validate


def _load(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_keys(data: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    missing = [k for k in keys if k not in data]
    if missing:
        return f"missing keys: {', '.join(missing)}"
    return None


def _min_rows(field: str = "rows", minimum: int = 1) -> Callable[[dict[str, Any] | list[Any], Path], str | None]:
    def _check(data: dict[str, Any] | list[Any], _path: Path) -> str | None:
        rows = data.get(field, []) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            return f"{field} must be a list"
        if len(rows) < minimum:
            return f"{field} has {len(rows)} item(s); need at least {minimum}"
        return None

    return _check


def _min_series(minimum: int = 1) -> Callable[[dict[str, Any] | list[Any], Path], str | None]:
    def _check(data: dict[str, Any] | list[Any], _path: Path) -> str | None:
        if not isinstance(data, dict):
            return "expected object with series[]"
        series = data.get("series")
        if not isinstance(series, list) or len(series) < minimum:
            return f"series has {0 if not isinstance(series, list) else len(series)} point(s); need at least {minimum}"
        return None

    return _check


def _etp_kpis(data: dict[str, Any] | list[Any], _path: Path) -> str | None:
    if not isinstance(data, dict):
        return "expected object"
    err = _require_keys(data, ("generated_at", "total_aum_display"))
    if err:
        return err
    if not re.search(r"\$[\d.,]+[KMBT]?", str(data.get("total_aum_display", ""))):
        return "total_aum_display is missing or not a dollar display string"
    return None


def _etp_rows(data: dict[str, Any] | list[Any], _path: Path) -> str | None:
    if not isinstance(data, dict):
        return "expected object"
    err = _require_keys(data, ("generated_at", "rows"))
    if err:
        return err
    return _min_rows("rows", 50)(data, _path)


def _etp_kpi_row_sum(data: dict[str, Any] | list[Any], path: Path) -> str | None:
    """Cross-check etp_kpis.json total vs etps.json row sum when both exist."""
    if path.name != "etp_kpis.json":
        return None
    if not isinstance(data, dict):
        return "expected object"
    etps_path = DATA / "etps.json"
    if not etps_path.is_file():
        return None
    etps = _load(etps_path)
    rows = etps.get("rows") or []
    row_sum = sum(float(r.get("assets_usd") or 0) for r in rows if isinstance(r, dict))
    display = str(data.get("total_aum_display", ""))
    m = re.search(r"\$([\d.,]+)([KMBT])?", display)
    if not m or row_sum <= 0:
        return None
    val = float(m.group(1).replace(",", ""))
    mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}.get((m.group(2) or "B").upper(), 1e9)
    kpi_usd = val * mult
    if abs(row_sum - kpi_usd) / row_sum > 0.12:
        return (
            f"total_aum_display ({display}) differs from etps.json row sum "
            f"(${row_sum/1e9:.2f}B) by more than 12% — re-run export_etp_static_data.py"
        )
    return None


REQUIRED: tuple[Check, ...] = (
    Check("etps.json", _etp_rows),
    Check("etp_kpis.json", lambda d, p: _etp_kpis(d, p) or _etp_kpi_row_sum(d, p)),
    Check("aum_series.json", _min_series(10)),
    Check("etf_pulse.json", _min_rows("items", 1)),
    Check("manifest.json", lambda d, p: None if isinstance(d, dict) else "expected object"),
)


def main() -> int:
    failures: list[str] = []
    print("=== Static JSON deploy validation ===\n")

    for check in REQUIRED:
        path = DATA / check.path
        label = check.path
        if not path.is_file():
            failures.append(f"{label}: file missing (not committed — ETP page will be empty on deploy)")
            print(f"[FAIL] {label}")
            print("       file missing")
            continue
        try:
            payload = _load(path)
        except json.JSONDecodeError as exc:
            failures.append(f"{label}: invalid JSON — {exc}")
            print(f"[FAIL] {label}")
            print(f"       invalid JSON: {exc}")
            continue
        detail = check.validate(payload, path)
        if detail:
            failures.append(f"{label}: {detail}")
            print(f"[FAIL] {label}")
            print(f"       {detail}")
        else:
            print(f"[OK]   {label}")

    print(f"\nSummary: {len(REQUIRED) - len(failures)} OK, {len(failures)} FAIL")
    if failures:
        print("\nFix: python scripts/export_etp_static_data.py")
        print("Then ensure static_home/data/etps.json (and related files) are committed — see .gitignore exceptions.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
