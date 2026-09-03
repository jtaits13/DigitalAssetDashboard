"""Home news rail: ignore RSS lastBuildDate restamps and diversify sources."""

from datetime import datetime, timezone
from types import SimpleNamespace

from news_feeds import (
    demote_feed_rebuild_timestamps,
    parse_feed_build_datetime,
    select_home_news_preview,
)


def _dt(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc)


def test_demote_feed_rebuild_timestamps_clears_featured_restamps() -> None:
    built = _dt("2026-09-03T19:50:13")
    items = [
        {"title": "Revolut EURR", "published": built, "source": "The Defiant"},
        {"title": "SEC custody", "published": built, "source": "The Defiant"},
        {"title": "Bitcoin 80k", "published": _dt("2026-09-03T16:30:34"), "source": "The Defiant"},
    ]
    demote_feed_rebuild_timestamps(items, built)
    assert items[0]["published"] is None
    assert items[1]["published"] is None
    assert items[2]["published"] == _dt("2026-09-03T16:30:34")


def test_demote_feed_rebuild_timestamps_keeps_single_matching_item() -> None:
    built = _dt("2026-09-03T19:50:13")
    items = [
        {"title": "Just published", "published": built},
        {"title": "Earlier", "published": _dt("2026-09-03T16:30:34")},
    ]
    demote_feed_rebuild_timestamps(items, built)
    assert items[0]["published"] == built


def test_demote_feed_rebuild_timestamps_skips_when_all_items_match() -> None:
    built = _dt("2026-09-03T19:50:13")
    items = [
        {"title": "A", "published": built},
        {"title": "B", "published": built},
    ]
    demote_feed_rebuild_timestamps(items, built)
    assert items[0]["published"] == built
    assert items[1]["published"] == built


def test_parse_feed_build_datetime_from_updated_parsed() -> None:
    built = datetime(2026, 9, 3, 19, 50, 13, tzinfo=timezone.utc)
    parsed = SimpleNamespace(feed={"updated_parsed": built.timetuple()})
    assert parse_feed_build_datetime(parsed) == datetime(2026, 9, 3, 19, 50, 13, tzinfo=timezone.utc)


def test_select_home_news_preview_prefers_dated_unique_sources() -> None:
    defiant_pinned = {
        "title": "Revolut EURR",
        "link": "https://thedefiant.io/revolut",
        "source": "The Defiant",
        "published": None,
    }
    items = [
        defiant_pinned,
        {
            "title": "BTC 80k",
            "link": "https://thedefiant.io/btc",
            "source": "The Defiant",
            "published": _dt("2026-09-03T16:30:34"),
        },
        {
            "title": "Sony PS5",
            "link": "https://decrypt.co/sony",
            "source": "Decrypt",
            "published": _dt("2026-09-03T16:28:27"),
        },
        {
            "title": "Standard Chartered Dubai",
            "link": "https://www.coindesk.com/sc",
            "source": "CoinDesk",
            "published": _dt("2026-09-03T15:58:02"),
        },
        {
            "title": "Diameter Pay",
            "link": "https://www.theblock.co/diameter",
            "source": "The Block",
            "published": _dt("2026-09-03T16:00:03"),
        },
        {
            "title": "Second Defiant",
            "link": "https://thedefiant.io/second",
            "source": "The Defiant",
            "published": _dt("2026-09-03T17:36:04"),
        },
    ]
    picked = select_home_news_preview(items, n=4)
    titles = [row["title"] for row in picked]
    sources = [row["source"] for row in picked]
    assert "Revolut EURR" not in titles
    assert titles[0] == "Second Defiant"
    assert len(sources) == 4
    assert len(set(sources)) == 4
    assert set(sources) == {"The Defiant", "Decrypt", "CoinDesk", "The Block"}
