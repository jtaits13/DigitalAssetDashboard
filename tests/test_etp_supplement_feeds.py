"""ETF supplement RSS URLs used by the GitHub Pages news export."""

import re

from news_feeds import ETP_SUPPLEMENT_FEEDS


def _user_facing_manifest_errors(errors: list[str]) -> list[str]:
    """Mirrors static_home/js/data-freshness.js userFacingManifestErrors."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in errors:
        s = str(raw or "").strip()
        if not s:
            continue
        if s.startswith("Crypto global snapshot:"):
            continue
        if re.search(r"HTTP Error 403|HTTP 403", s, re.I):
            continue
        if re.search(r"ETF news RSS:|news RSS \(", s, re.I) and re.search(
            r"HTTP Error 404|HTTP 404", s, re.I
        ):
            continue
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def test_benzinga_feed_is_not_the_dead_topic_url() -> None:
    feeds = dict(ETP_SUPPLEMENT_FEEDS)
    assert "Benzinga" in feeds
    assert "topic/etfs/feed" not in feeds["Benzinga"]
    assert feeds["Benzinga"] == "https://www.benzinga.com/feed"


def test_etfdb_feed_uses_apex_host() -> None:
    feeds = dict(ETP_SUPPLEMENT_FEEDS)
    assert feeds["ETFdb"] == "https://etfdb.com/feed/"


def test_home_banner_hides_live_etf_rss_warnings() -> None:
    live_errors = [
        "ETF news RSS: ETFdb: HTTP Error 403: Forbidden",
        "ETF news RSS: ETF Trends (VettaFi): HTTP Error 403: Forbidden",
        "ETF news RSS: Benzinga ETFs: HTTP Error 404: Not Found",
        "ETF news RSS: ETFdb: HTTP Error 403: Forbidden",
        "ETF news RSS: ETF Trends (VettaFi): HTTP Error 403: Forbidden",
        "ETF news RSS: Benzinga ETFs: HTTP Error 404: Not Found",
    ]
    assert _user_facing_manifest_errors(live_errors) == []


def test_home_banner_still_shows_non_rss_failures() -> None:
    assert _user_facing_manifest_errors(["RWA home overview: timeout"]) == [
        "RWA home overview: timeout"
    ]
