"""Copy rows_full from RWA deep-dive JSON into explore index JSON (offline, no API)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "static_home" / "data"

ASSET_TYPE_MAP = {
    "stablecoins": ("rwa_stablecoins.json", "networks"),
    "treasuries": ("rwa_us_treasuries.json", "networks"),
    "tokenized_stocks": ("rwa_tokenized_stocks.json", "networks"),
    "tokenized_mmf": ("rwa_tokenized_mmf.json", "networks"),
}

PARTICIPANT_MAP = {
    "participant_networks": ("rwa_participants_networks.json", "networks"),
    "participant_platforms": ("rwa_participants_platforms.json", "networks"),
    "participant_asset_managers": ("rwa_participants_asset_managers.json", "networks"),
}


def _league_rows(deep_path: Path, league_key: str) -> list[dict] | None:
    if not deep_path.is_file():
        return None
    payload = json.loads(deep_path.read_text(encoding="utf-8"))
    league = payload.get(league_key)
    if not isinstance(league, dict):
        return None
    rows = league.get("rows_full")
    return rows if isinstance(rows, list) and rows else None


def patch_explore(explore_name: str, section_map: dict[str, tuple[str, str]]) -> None:
    path = ROOT / explore_name
    data = json.loads(path.read_text(encoding="utf-8"))
    for sec in data.get("sections") or []:
        sid = sec.get("id")
        if not sid or sid not in section_map:
            continue
        deep_file, league_key = section_map[sid]
        rows_full = _league_rows(ROOT / deep_file, league_key)
        if not rows_full:
            continue
        sec_cols = sec.get("columns") or []
        if rows_full and sec_cols and sec_cols != list(rows_full[0].keys()):
            print(f"  skip {sid}: column mismatch explore vs deep")
            continue
        sec["rows_full"] = rows_full
        preview_n = min(8, len(rows_full))
        sec["rows"] = rows_full[:preview_n]
        print(f"  {sid}: rows_full={len(rows_full)} preview={preview_n}")
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    print("rwa_explore_asset_type.json")
    patch_explore("rwa_explore_asset_type.json", ASSET_TYPE_MAP)
    print("rwa_explore_market_participant.json")
    patch_explore("rwa_explore_market_participant.json", PARTICIPANT_MAP)


if __name__ == "__main__":
    main()
