"""Presentation checks for newsletter captions, share points, and flow wording."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import date  # noqa: E402

from key_observations.newsletter_week import (  # noqa: E402
    SectionKpiMove,
    WeekContext,
    _compose_news_body,
    _interpret_news_for_market,
    _tmmf_no_launch_takeaway,
    _wow_market_read,
    _wow_takeaway,
    headline_so_what,
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


def test_actual_outflow_states_the_outflow() -> None:
    move = SectionKpiMove(
        label="30D net flow",
        value_display="−$1.20B",
        delta_pct=-20.0,
        delta_display="-20.0%",
    )
    body = _wow_market_read("etp", move)
    assert "net outflow" in body
    assert "net risk coming out" not in body


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


def _week_context() -> WeekContext:
    explore = {
        "tokenized_mmf": {
            "kpis": [
                {"label": "Distributed value", "value_display": "$12.77B", "delta_30d_pct": -0.0553},
                {
                    "label": "Top network share",
                    "value_display": "32.5% · Ethereum",
                    "delta_30d_pct": -0.08835,
                },
            ]
        },
        "stablecoins": {
            "kpis": [
                {"label": "Market Cap", "value_display": "$286.24B", "delta_30d_pct": -0.029},
                {
                    "label": "Monthly Transfer Volume",
                    "value_display": "$9.92T",
                    "delta_30d_pct": 0.3709,
                },
            ]
        },
    }
    return WeekContext(
        current_week=date(2026, 11, 2),
        prior={
            "tmmf": (date(2026, 10, 12), "$13.60B"),
            "stablecoins": (date(2026, 10, 12), "$293.16B"),
        },
        explore=explore,
        etp=None,
        crypto=None,
        levels={"tmmf": "$12.77B", "stablecoins": "$286.24B"},
    )


def test_directional_sentence_then_uses_the_prior_reading() -> None:
    ctx = _week_context()
    move = SectionKpiMove(
        label="Distributed value",
        value_display="$12.77B",
        delta_pct=-5.5,
        delta_display="-5.5%",
    )
    body = _wow_market_read("tmmf", move, ctx)
    assert body.startswith("With distributed value at $12.77B (5.5% lower over 30D).")
    assert "That is -6.1% from the 12 Oct reading of $13.60B" in body
    assert "-8.8 pp over 30D" in body
    assert "operational liquidity" not in body
    assert "pulled liquidity" not in body


def test_no_launch_line_stays_on_the_launch_headline() -> None:
    body = _tmmf_no_launch_takeaway(_week_context()).body
    assert "No new fund launch" in body
    assert "12 Oct" not in body
    assert "$13.60B" not in body
    assert "carried the TMMF story" not in body


def test_second_bullet_stays_on_the_headline() -> None:
    summary = (
        "The 18,270 BTC haul is worth about $1.4 billion and comes within 442 coins of SpaceX's disclosed holdings. "
        "The coins moved out of Binance wallets over the weekend."
    )
    body = _compose_news_body(
        "etp",
        {"title": "Bitcoin stolen from Binance tops Tesla's holdings", "summary": summary},
        _week_context(),
    )
    assert body.startswith("The 18,270 BTC haul is worth about $1.4 billion")
    assert "moved out of Binance wallets" in body
    assert "Aggregate AUM" not in body
    assert "12 Oct" not in body
    assert "IBIT" not in body


def test_headline_so_what_follows_that_story_market() -> None:
    class Pick:
        title = "Experts divided over Binance hack asset freezes, warn recovery is another matter"
        theme_family = "stablecoins"

    line = headline_so_what(Pick(), context=_week_context())
    assert line.startswith("Experts divided over Binance hack")
    assert "$293.16B" in line
    assert "payments and reserve rails remain" not in line


if __name__ == "__main__":
    test_stable_caption_names_both_levels()
    test_rwa_caption_names_protocol_tvl_and_distributed_value()
    test_network_share_delta_is_percentage_points()
    test_smaller_inflow_is_not_described_as_risk_leaving()
    test_actual_outflow_states_the_outflow()
    test_week_in_brief_keeps_a_positive_flow_positive()
    test_non_etf_outflow_headline_is_not_called_listed_outflows()
    test_directional_sentence_then_uses_the_prior_reading()
    test_no_launch_line_stays_on_the_launch_headline()
    test_second_bullet_stays_on_the_headline()
    test_headline_so_what_follows_that_story_market()
    print("test_newsletter_presentation: ok")
