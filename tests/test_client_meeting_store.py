"""Shared weekly store and HTTP API for client meeting intake."""

from __future__ import annotations

import json
import threading
from datetime import date
from http.client import HTTPConnection
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "tools" / "client_meeting_updates"
import sys

sys.path.insert(0, str(ROOT))

from server import IntakeHandler, ThreadingHTTPServer  # noqa: E402
from store import MeetingStore, iso_week_id, merge_rows, normalize_row  # noqa: E402


def test_iso_week_id_matches_monday_sunday_weeks() -> None:
    assert iso_week_id(date(2026, 9, 21)) == "2026-W39"
    assert iso_week_id(date(2026, 9, 25)) == "2026-W39"
    assert iso_week_id(date(2026, 9, 28)) == "2026-W40"


def test_store_adds_two_rows_and_skips_import_duplicates(tmp_path: Path) -> None:
    store = MeetingStore(tmp_path, today=date(2026, 9, 25))
    store.add_row(
        {
            "date": "2026-09-22",
            "client": "Northwind",
            "purpose": "Update",
            "owners": "Alex",
            "attendees": "Pat",
        }
    )
    store.add_row(
        {
            "date": "2026-09-23",
            "client": "Contoso",
            "purpose": "Walkthrough",
            "owners": "Riley",
            "attendees": "Jo",
        }
    )
    data, added = store.import_rows(
        [
            {
                "date": "2026-09-22",
                "client": "Northwind",
                "purpose": "Update",
                "owners": "Alex",
                "attendees": "Pat",
            },
            {
                "date": "2026-09-24",
                "client": "Gamma",
                "purpose": "Check-in",
                "owners": "Sam",
                "attendees": "Chris",
            },
        ]
    )
    assert added == 1
    assert len(data["rows"]) == 3
    assert data["weekId"] == "2026-W39"


def test_week_rollover_archives_previous_rows(tmp_path: Path) -> None:
    stale = MeetingStore(tmp_path, today=date(2026, 9, 18))
    stale.add_row(
        {
            "date": "2026-09-16",
            "client": "Acme",
            "purpose": "Intro",
            "owners": "Alex",
            "attendees": "Pat",
        }
    )
    next_week = MeetingStore(tmp_path, today=date(2026, 9, 25))
    store, meta = next_week.load()
    assert store["weekId"] == "2026-W39"
    assert store["rows"] == []
    assert meta["rolledOver"] is True
    assert meta["previousRowCount"] == 1
    backup = tmp_path / "backups" / "2026-W38.json"
    assert backup.is_file()
    archived = json.loads(backup.read_text(encoding="utf-8"))
    assert archived["rows"][0]["client"] == "Acme"


def test_normalize_row_requires_every_column() -> None:
    with pytest.raises(ValueError, match="Meeting Purpose"):
        normalize_row(
            {
                "date": "2026-09-22",
                "client": "Acme",
                "purpose": "",
                "owners": "Alex",
                "attendees": "Pat",
            }
        )


def test_merge_rows_helper_skips_exact_duplicates() -> None:
    existing = [
        normalize_row(
            {
                "date": "2026-09-22",
                "client": "Acme",
                "purpose": "Intro",
                "owners": "Alex",
                "attendees": "Pat",
            }
        )
    ]
    rows, added = merge_rows(
        existing,
        [
            existing[0],
            {
                "date": "2026-09-23",
                "client": "Beta",
                "purpose": "Review",
                "owners": "Sam",
                "attendees": "Jo",
            },
        ],
    )
    assert added == 1
    assert len(rows) == 2


def test_http_api_shares_rows_across_requests(tmp_path: Path) -> None:
    IntakeHandler.store = MeetingStore(tmp_path, today=date(2026, 9, 25))
    IntakeHandler.static_root = ROOT
    server = ThreadingHTTPServer(("127.0.0.1", 0), IntakeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        first = _json_request(host, port, "POST", "/api/meetings", {
            "date": "2026-09-22",
            "client": "Northwind",
            "purpose": "Update",
            "owners": "Alex",
            "attendees": "Pat",
        })
        second = _json_request(host, port, "POST", "/api/meetings", {
            "date": "2026-09-23",
            "client": "Contoso",
            "purpose": "Walkthrough",
            "owners": "Riley",
            "attendees": "Jo",
        })
        week = _json_request(host, port, "GET", "/api/week")
        assert len(first["store"]["rows"]) == 1
        assert len(second["store"]["rows"]) == 2
        assert len(week["store"]["rows"]) == 2
        blocked = _raw_request(host, port, "GET", "/data/week.json")
        assert blocked.status == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _json_request(host: str, port: int, method: str, path: str, body: dict | None = None) -> dict:
    conn = HTTPConnection(host, port, timeout=5)
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    conn.request(method, path, body=payload, headers=headers)
    res = conn.getresponse()
    data = json.loads(res.read().decode("utf-8"))
    conn.close()
    assert res.status == 200, data
    return data


def _raw_request(host: str, port: int, method: str, path: str):
    conn = HTTPConnection(host, port, timeout=5)
    conn.request(method, path)
    res = conn.getresponse()
    res.read()
    conn.close()
    return res
