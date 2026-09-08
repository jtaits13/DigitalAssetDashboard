"""StockAnalysis crypto ETF list: header map + cache fallback when AUM is blank."""

from crypto_etps.client import _fallback_list_column_map, _list_column_index_map
from etp_live_cache import apply_etp_live_cache_fallback, aum_display_is_dollar


def test_list_column_map_with_leading_no_column() -> None:
    mapped = _list_column_index_map(
        ["No.", "Symbol", "Fund Name", "Stock Price", "% Change", "Assets"]
    )
    assert mapped is not None
    assert mapped["symbol"] == 1
    assert mapped["name"] == 2
    assert mapped["price"] == 3
    assert mapped["pct"] == 4
    assert mapped["assets"] == 5


def test_fallback_list_column_map_six_cells() -> None:
    mapped = _fallback_list_column_map(6)
    assert mapped["symbol"] == 1
    assert mapped["assets"] == 5


def test_aum_display_is_dollar() -> None:
    assert aum_display_is_dollar("$131.44B")
    assert not aum_display_is_dollar("—")
    assert not aum_display_is_dollar("")


def test_cache_fallback_restores_when_live_aum_is_emdash() -> None:
    live = {
        "etps.json": {"rows": [{"symbol": "1", "assets_usd": None}], "error": ""},
        "etp_kpis.json": {"total_aum_display": "—"},
        "aum_series.json": {"series": []},
        "etf_pulse.json": {"items": []},
    }
    cache = {
        "payloads": {
            "etps.json": {"rows": [{"symbol": "IBIT", "assets_usd": 6e10}]},
            "etp_kpis.json": {"total_aum_display": "$126.76B"},
            "aum_series.json": {
                "series": [{"date": f"2026-01-{i:02d}", "aum_billions": 100} for i in range(1, 12)]
            },
            "etf_pulse.json": {"items": [{"title": "x"}]},
        }
    }
    out = apply_etp_live_cache_fallback(live, cache=cache)
    assert out["etps.json"]["rows"][0]["symbol"] == "IBIT"
    assert out["etps.json"].get("stale") is True
    assert out["etp_kpis.json"]["total_aum_display"] == "$126.76B"
    assert out["etp_kpis.json"].get("stale") is True
    assert len(out["aum_series.json"]["series"]) == 11
