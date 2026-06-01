"""Trim participant KPI JSON to five tiles and drop Total Stablecoin Holders on Networks/Platforms."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "static_home" / "data"
DROP = "Total Stablecoin Holders"
MAX = 5


def filter_kpis(kpis: list[dict], *, drop_stablecoin: bool) -> list[dict]:
    out: list[dict] = []
    for row in kpis or []:
        if drop_stablecoin and row.get("label") == DROP:
            continue
        out.append(row)
        if len(out) >= MAX:
            break
    return out


def patch_object(data: dict, *, drop_stablecoin: bool) -> None:
    if "kpis" in data and isinstance(data["kpis"], list):
        data["kpis"] = filter_kpis(data["kpis"], drop_stablecoin=drop_stablecoin)


def main() -> None:
    explore = json.loads((ROOT / "rwa_explore_market_participant.json").read_text(encoding="utf-8"))
    for sec in explore.get("sections") or []:
        sid = sec.get("id")
        drop = sid in ("participant_networks", "participant_platforms")
        if sid in ("participant_networks", "participant_platforms", "participant_asset_managers"):
            sec["kpis"] = filter_kpis(sec.get("kpis") or [], drop_stablecoin=drop)
    (ROOT / "rwa_explore_market_participant.json").write_text(
        json.dumps(explore, indent=2) + "\n", encoding="utf-8"
    )
    print("rwa_explore_market_participant.json")

    deep_files = {
        "rwa_participants_networks.json": True,
        "rwa_participants_platforms.json": True,
        "rwa_participants_asset_managers.json": False,
    }
    for name, drop in deep_files.items():
        path = ROOT / name
        data = json.loads(path.read_text(encoding="utf-8"))
        patch_object(data, drop_stablecoin=drop)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(name, "->", len(data["kpis"]), "KPIs")


if __name__ == "__main__":
    main()
