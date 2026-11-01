"""Presentation checks for newsletter captions, share points, and flow wording."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from key_observations.newsletter_week import (  # noqa: E402
    SectionKpiMove,
    _interpret_news_for_market,
    _wow_market_read,
    _wow_takeaway,
)
from newsletter_weekly_charts import _rwa_caption, _stable_caption  # noqa: E402
from scripts.build_weekly_newsletter import (  # noqa: E402
    _fmt_pct,
    _week_in_brief_watch_etp,
)


def _series(value: float) -> dict:
    return {"points": [{"week_end": "2026-11-01", "value": value, "source": "defillama"}]}


def test_stable_caption_names_both_levels() -> None:
    text = _stable_caption(_series(300.16e9), "$286.24B")
    assert "$300.16B" in text
    assert "$286.24B" in text
    assert "slightly" not in text.lower()
    assert "different measures" in text


def test_rwa_caption_names_protocol_tvl_and_distributed_value() -> None:
    text = _rwa_caption(_series(3.667e9), "$39.03B")
    assert "largest RWA protocols" in text
    assert "$3.67B" in text
    assert "distributed asset value at $39.03B" in text
    assert "can differ" not in text.lower()


def test_network_share_delta_is_percentage_points() -> None:
    assert _fmt_pct(-0.08835225295736782, unit="pp") == "-8.8 pp"
    assert _fmt_pct(-0.0553, unit="fraction") == "-5.5%"


def test_smaller_inflow_is_not_described_as_risk_leaving() -> None:
    move = SectionKpiMove(
        label="30D net flow",
        value_display="+$2.69B",
        delta_pct=-56.0,
        delta_display="-56.0%",
    )
    body = _wow_market_read("etp", move)
    assert "net inflow" in body
    assert "smaller than the prior 30 days" in body
    assert "net risk coming out" not in body
    takeaway = _wow_takeaway(move, lane="U.S. ETP", section_id="etp")
    assert takeaway is not None
    assert "slowed 56.0%" in takeaway.lead
    assert "fell 56.0%" not in takeaway.lead


def test_actual_outflow_still_reads_as_risk_leaving() -> None:
    move = SectionKpiMove(
        label="30D net flow",
        value_display="−$1.20B",
        delta_pct=-20.0,
        delta_display="-20.0%",
    )
    body = _wow_market_read("etp", move)
    assert "net risk coming out" in body


def test_week_in_brief_keeps_a_positive_flow_positive() -> None:
    text = _week_in_brief_watch_etp(
        {
            "net_flow_1m_display": "+$2.69B",
            "net_flow_1m_pct": -56.0,
            "net_flow_1m_usd": 2_689_700_000,
        },
        "-10.9%",
        {},
    )
    assert "stayed positive" in text
    assert "+$2.69B" in text
    assert "-56.0%" in text
    assert "stayed negative" not in text
    assert "turned positive" not in text


def test_non_etf_outflow_headline_is_not_called_listed_outflows() -> None:
    text = _interpret_news_for_market(
        "etp",
        "Bubblemaps Traces $2.7 Million Outflow From Polymarket Breach",
        "",
    )
    assert "listed outflows" not in text
    etf = _interpret_news_for_market("etp", "Spot bitcoin ETF recorded a large outflow", "")
    assert "listed outflows" in etf


if __name__ == "__main__":
    test_stable_caption_names_both_levels()
    test_rwa_caption_names_protocol_tvl_and_distributed_value()
    test_network_share_delta_is_percentage_points()
    test_smaller_inflow_is_not_described_as_risk_leaving()
    test_actual_outflow_still_reads_as_risk_leaving()
    test_week_in_brief_keeps_a_positive_flow_positive()
    test_non_etf_outflow_headline_is_not_called_listed_outflows()
    print("test_newsletter_presentation: ok")
