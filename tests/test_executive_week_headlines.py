"""Executive newsletter headline scope tests."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from key_observations.week_headlines import (
    executive_news_text_allowed,
    pick_executive_week_headlines,
    pick_executive_week_headlines_with_launches,
)


def _art(title: str, *, summary: str = "", source: str = "CoinDesk") -> dict:
    return {
        "title": title,
        "summary": summary,
        "source": source,
        "link": f"https://example.com/{abs(hash(title)) % 10_000}",
        "published": datetime.now(timezone.utc) - timedelta(days=1),
    }


def test_executive_news_text_allowed_topics() -> None:
    assert executive_news_text_allowed(
        "State Street launches stablecoin reserves money market fund under GENIUS Act"
    )
    assert executive_news_text_allowed(
        "BlackRock launches BITA, a covered-call Bitcoin ETF for monthly income"
    )
    assert executive_news_text_allowed(
        "SEC proposes new crypto custody rule for tokenized assets"
    )
    assert executive_news_text_allowed("Circle expands USDC bank integration in Europe")
    assert not executive_news_text_allowed("Kalshi faces insider trading probe on prediction markets")
    assert not executive_news_text_allowed("Bitcoin tumbles 8% as crypto market sells off")


def test_pick_executive_week_headlines_excludes_off_topic() -> None:
    articles = [
        _art("Kalshi insider trading probe widens on prediction markets"),
        _art("Bitcoin tumbles 8% as crypto market sells off"),
        _art("SEC unveils crypto custody rule for digital asset brokers"),
        _art("Visa pilots stablecoin settlement with major US bank partner"),
    ]
    picks = pick_executive_week_headlines(articles, n=3)
    titles = " ".join(p.title.lower() for p in picks)
    assert "kalshi" not in titles
    assert "tumbles" not in titles
    assert any(k in titles for k in ("sec", "stablecoin", "visa"))


def test_pick_executive_week_headlines_with_launches_prioritizes_fund_launch() -> None:
    articles = [
        _art("BlackRock launches BITA, a covered-call Bitcoin ETF for monthly income"),
        _art("SEC proposes crypto custody rule"),
        _art("Circle expands USDC reserves transparency program"),
    ]
    picks, launches = pick_executive_week_headlines_with_launches(articles, n=3)
    assert launches.get("crypto_etf") is not None
    assert picks
    assert "bita" in picks[0].title.lower() or "blackrock" in picks[0].title.lower()


if __name__ == "__main__":
    test_executive_news_text_allowed_topics()
    test_pick_executive_week_headlines_excludes_off_topic()
    test_pick_executive_week_headlines_with_launches_prioritizes_fund_launch()
    print("test_executive_week_headlines: ok")
