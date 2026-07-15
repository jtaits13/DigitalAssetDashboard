"""Rebuild key_observations_html for all section JSON bundles."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA = ROOT / "static_home" / "data"


def _load(name: str) -> dict:
    path = DATA / name
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save(name: str, payload: dict) -> None:
    path = DATA / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _articles() -> list:
    cached = _load("all_articles.json")
    items = cached.get("articles") or cached.get("items") or []
    if items:
        return items
    from key_observations.feeds import load_takeaway_articles

    return load_takeaway_articles()


def _explore_sections() -> dict:
    from key_observations.page_blend import explore_sections_from_payload

    explore = _load("rwa_explore_asset_type.json")
    return explore_sections_from_payload(explore)


def rebuild_tmmf(articles, explore) -> None:
    payload = _load("rwa_tokenized_mmf.json")
    if not payload:
        return
    from rwa_league.mmf import build_curated_mmf_dashboard_data
    from rwa_league.mmf_takeaways import build_mmf_key_observations_html

    fund_assets, rows_net, _rows_plat, _kpis, _err = build_curated_mmf_dashboard_data()
    if not fund_assets:
        print("Skip TMMF — no fund rows from RWA.xyz.", file=sys.stderr)
        return
    payload["key_observations_html"] = build_mmf_key_observations_html(
        fund_assets, list(rows_net), articles, explore=explore
    )
    _save("rwa_tokenized_mmf.json", payload)


def rebuild_stablecoins(articles, explore) -> None:
    payload = _load("rwa_stablecoins.json")
    from key_observations.page_ko import build_legacy_page_ko

    payload["key_observations_html"] = build_legacy_page_ko(
        "stablecoins", articles, explore=explore
    )
    _save("rwa_stablecoins.json", payload)


def rebuild_legacy(topic: str, filename: str, articles, explore, **kwargs) -> None:
    payload = _load(filename)
    if not payload:
        return
    from key_observations.page_ko import build_legacy_page_ko

    payload["key_observations_html"] = build_legacy_page_ko(
        topic, articles, explore=explore, **kwargs
    )
    _save(filename, payload)


def rebuild_etp(articles, explore) -> None:
    kpis = _load("etp_kpis.json")
    etps = _load("etps.json")
    from crypto_etps.client import CryptoEtpRow
    from crypto_etps.etp_takeaways import build_etp_key_observations_html

    rows: list[CryptoEtpRow] = []
    for r in etps.get("rows") or []:
        rows.append(
            CryptoEtpRow(
                symbol=str(r.get("symbol") or ""),
                name=str(r.get("name") or ""),
                price=str(r.get("price") or ""),
                pct_change=str(r.get("pct_change") or ""),
                assets_display=str(r.get("assets_display") or ""),
                assets_usd=r.get("assets_usd"),
                issuer=str(r.get("issuer") or ""),
                inception=str(r.get("inception") or ""),
                pct_52w=r.get("pct_52w"),
                fund_filing_url=str(r.get("fund_filing_url") or ""),
                custodian=str(r.get("custodian") or ""),
            )
        )
    kpis["key_observations_html"] = build_etp_key_observations_html(
        rows,
        net_flow_1m_display=str(kpis.get("net_flow_1m_display") or "—"),
        net_flow_1m_pct=kpis.get("net_flow_1m_pct"),
        aggregate_pct=kpis.get("aggregate_pct"),
        total_aum_display=str(kpis.get("total_aum_display") or "—"),
        articles=articles,
    )
    _save("etp_kpis.json", kpis)


def rebuild_crypto(articles, explore) -> None:
    kpis = _load("crypto_kpis.json")
    prices = _load("crypto_prices.json")
    from crypto_top_movers import crypto_key_takeaways_html

    kpis["key_observations_html"] = crypto_key_takeaways_html(
        prices.get("rows") or [],
        kpis,
        articles,
    )
    _save("crypto_kpis.json", kpis)


def main() -> None:
    articles = _articles()
    explore = _explore_sections()

    rebuild_tmmf(articles, explore)
    rebuild_stablecoins(articles, explore)
    rebuild_etp(articles, explore)
    rebuild_crypto(articles, explore)

    for topic, fname in (
        ("us_treasuries", "rwa_us_treasuries.json"),
        ("tokenized_stocks", "rwa_tokenized_stocks.json"),
        ("participants_networks", "rwa_participants_networks.json"),
        ("participants_platforms", "rwa_participants_platforms.json"),
        ("participants_asset_managers", "rwa_participants_asset_managers.json"),
    ):
        rebuild_legacy(topic, fname, articles, explore)

    print("Rebuilt key_observations_html for all section bundles.")


if __name__ == "__main__":
    main()
