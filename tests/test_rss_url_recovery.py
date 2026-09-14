"""Automatic RSS URL recovery when a configured feed path 404s."""

from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError, URLError

import news_feeds


def _http_404(url: str) -> HTTPError:
    return HTTPError(url, 404, "Not Found", hdrs=None, fp=None)


def test_topic_feed_candidates_include_sitewide_feed() -> None:
    dead = "https://www.benzinga.com/topic/etfs/feed"
    candidates = news_feeds.rss_url_candidates(dead, mode="gone")
    assert "https://www.benzinga.com/feed" in candidates
    assert dead in candidates


def test_blocked_mode_does_not_collapse_topic_path() -> None:
    dead = "https://www.benzinga.com/topic/etfs/feed"
    candidates = news_feeds.rss_url_candidates(dead, mode="blocked")
    assert "https://www.benzinga.com/feed" not in candidates
    assert "https://benzinga.com/topic/etfs/feed" in candidates


def test_load_one_rss_remaps_404_topic_feed_and_persists(
    monkeypatch, tmp_path: Path
) -> None:
    override = tmp_path / "rss_feed_overrides.json"
    monkeypatch.setenv("RSS_FEED_OVERRIDE_PATH", str(override))
    calls: list[str] = []

    def fake_fetch(source_name: str, url: str):
        calls.append(url)
        if "/topic/" in url:
            raise _http_404(url)
        return [
            {
                "title": "ETF inflow",
                "link": "https://www.benzinga.com/markets/etfs/1",
                "source": source_name,
                "published": None,
                "summary": "",
            }
        ]

    monkeypatch.setattr(news_feeds, "fetch_feed", fake_fetch)
    rows, err = news_feeds._load_one_rss("Benzinga", "https://www.benzinga.com/topic/etfs/feed")
    assert err is None
    assert rows[0]["title"] == "ETF inflow"
    assert "https://www.benzinga.com/feed" in calls
    saved = news_feeds._saved_override_url("https://www.benzinga.com/topic/etfs/feed")
    assert saved == "https://www.benzinga.com/feed"


def test_load_one_rss_uses_saved_override_first(monkeypatch, tmp_path: Path) -> None:
    override = tmp_path / "rss_feed_overrides.json"
    monkeypatch.setenv("RSS_FEED_OVERRIDE_PATH", str(override))
    news_feeds._save_rss_override(
        source="Benzinga",
        configured_url="https://www.benzinga.com/topic/etfs/feed",
        resolved_url="https://www.benzinga.com/feed",
    )
    calls: list[str] = []

    def fake_fetch(source_name: str, url: str):
        calls.append(url)
        if url.endswith("/feed"):
            return [{"title": "ok", "link": "https://x", "source": source_name, "published": None, "summary": ""}]
        raise _http_404(url)

    monkeypatch.setattr(news_feeds, "fetch_feed", fake_fetch)
    rows, err = news_feeds._load_one_rss("Benzinga", "https://www.benzinga.com/topic/etfs/feed")
    assert err is None
    assert rows[0]["title"] == "ok"
    assert calls[0] == "https://www.benzinga.com/feed"


def test_load_one_rss_does_not_remap_timeouts(monkeypatch, tmp_path: Path) -> None:
    override = tmp_path / "rss_feed_overrides.json"
    monkeypatch.setenv("RSS_FEED_OVERRIDE_PATH", str(override))
    calls: list[str] = []

    def fake_fetch(source_name: str, url: str):
        calls.append(url)
        raise URLError("timed out")

    monkeypatch.setattr(news_feeds, "fetch_feed", fake_fetch)
    rows, err = news_feeds._load_one_rss("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/")
    assert rows == []
    assert err is not None and "timed out" in err
    assert len(calls) == 1
