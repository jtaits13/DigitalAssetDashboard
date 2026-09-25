"""Shared on-disk store for the client-meeting weekly intake server."""

from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import date
from pathlib import Path
from typing import Any

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COLUMNS = (
    "Date",
    "Client",
    "Meeting Purpose",
    "Owner(s)",
    "Client Attendee(s)",
)


def iso_week_id(day: date) -> str:
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def empty_store(week_id: str) -> dict[str, Any]:
    return {"weekId": week_id, "rows": []}


def _pick(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        if key in payload and payload[key] is not None:
            return str(payload[key]).strip()
    return ""


def coerce_row(payload: Any) -> dict[str, str] | None:
    if not isinstance(payload, dict):
        return None
    return {
        "id": str(payload.get("id") or "").strip(),
        "date": _pick(payload, "date", "Date"),
        "client": _pick(payload, "client", "Client"),
        "purpose": _pick(payload, "purpose", "Meeting Purpose", "meetingPurpose"),
        "owners": _pick(payload, "owners", "Owner(s)", "Owners"),
        "attendees": _pick(payload, "attendees", "Client Attendee(s)", "Attendees"),
    }


def normalize_row(payload: Any) -> dict[str, str]:
    row = coerce_row(payload) or {
        "id": "",
        "date": "",
        "client": "",
        "purpose": "",
        "owners": "",
        "attendees": "",
    }
    missing: list[str] = []
    if not DATE_RE.match(row["date"]):
        missing.append("Date")
    if not row["client"]:
        missing.append("Client")
    if not row["purpose"]:
        missing.append("Meeting Purpose")
    if not row["owners"]:
        missing.append("Owner(s)")
    if not row["attendees"]:
        missing.append("Client Attendee(s)")
    if missing:
        raise ValueError("Please fill in: " + ", ".join(missing) + ".")
    if not row["id"]:
        row["id"] = str(uuid.uuid4())
    return row


def row_signature(row: dict[str, str]) -> str:
    return "\0".join(
        row.get(key, "").strip().lower()
        for key in ("date", "client", "purpose", "owners", "attendees")
    )


def merge_rows(
    existing: list[dict[str, str]], incoming: list[Any]
) -> tuple[list[dict[str, str]], int]:
    rows = list(existing)
    seen = {row_signature(row) for row in rows}
    added = 0
    for item in incoming:
        try:
            row = normalize_row(item)
        except ValueError:
            continue
        sig = row_signature(row)
        if sig in seen:
            continue
        seen.add(sig)
        rows.append(row)
        added += 1
    return rows, added


class MeetingStore:
    def __init__(self, data_dir: Path, *, today: date | None = None) -> None:
        self.data_dir = Path(data_dir)
        self.week_path = self.data_dir / "week.json"
        self.backup_dir = self.data_dir / "backups"
        self._today = today
        self._lock = threading.Lock()

    def today(self) -> date:
        return self._today or date.today()

    def current_week_id(self) -> str:
        return iso_week_id(self.today())

    def load(self) -> tuple[dict[str, Any], dict[str, Any]]:
        with self._lock:
            return self._load_unlocked()

    def add_row(self, payload: Any) -> dict[str, Any]:
        row = normalize_row(payload)
        with self._lock:
            store, _meta = self._load_unlocked()
            store["rows"].append(row)
            self._write_unlocked(store)
            return store

    def update_row(self, payload: Any) -> dict[str, Any]:
        row = normalize_row(payload)
        with self._lock:
            store, _meta = self._load_unlocked()
            found = False
            next_rows = []
            for existing in store["rows"]:
                if existing.get("id") == row["id"]:
                    next_rows.append(row)
                    found = True
                else:
                    next_rows.append(existing)
            if not found:
                raise KeyError("Meeting row not found.")
            store["rows"] = next_rows
            self._write_unlocked(store)
            return store

    def delete_row(self, row_id: str) -> dict[str, Any]:
        wanted = str(row_id or "").strip()
        if not wanted:
            raise ValueError("Missing meeting id.")
        with self._lock:
            store, _meta = self._load_unlocked()
            store["rows"] = [row for row in store["rows"] if row.get("id") != wanted]
            self._write_unlocked(store)
            return store

    def import_rows(self, incoming: list[Any]) -> tuple[dict[str, Any], int]:
        with self._lock:
            store, _meta = self._load_unlocked()
            store["rows"], added = merge_rows(store["rows"], incoming)
            self._write_unlocked(store)
            return store, added

    def reset_week(self) -> dict[str, Any]:
        with self._lock:
            store, meta = self._load_unlocked()
            if store["rows"]:
                self._archive_unlocked(store)
            store = empty_store(self.current_week_id())
            self._write_unlocked(store)
            meta["reset"] = True
            return store

    def _load_unlocked(self) -> tuple[dict[str, Any], dict[str, Any]]:
        current = self.current_week_id()
        raw = self._read_file()
        meta: dict[str, Any] = {
            "rolledOver": False,
            "previousWeekId": "",
            "previousRowCount": 0,
        }
        store = self._parse_store(raw) or empty_store(current)
        if store["weekId"] != current:
            if store["rows"]:
                self._archive_unlocked(store)
                meta["rolledOver"] = True
                meta["previousWeekId"] = store["weekId"]
                meta["previousRowCount"] = len(store["rows"])
            store = empty_store(current)
            self._write_unlocked(store)
        elif raw is None:
            self._write_unlocked(store)
        return store, meta

    def _parse_store(self, raw: Any) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None
        week_id = str(raw.get("weekId") or "").strip()
        if not week_id:
            return None
        rows = []
        for item in raw.get("rows") or []:
            coerced = coerce_row(item)
            if coerced and coerced["date"] and coerced["client"]:
                if not coerced["id"]:
                    coerced["id"] = str(uuid.uuid4())
                rows.append(coerced)
        return {"weekId": week_id, "rows": rows}

    def _read_file(self) -> Any | None:
        if not self.week_path.is_file():
            return None
        try:
            return json.loads(self.week_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _write_unlocked(self, store: dict[str, Any]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.week_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(self.week_path)

    def _archive_unlocked(self, store: dict[str, Any]) -> None:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        week_id = str(store.get("weekId") or "week")
        path = self.backup_dir / f"{week_id}.json"
        path.write_text(json.dumps(store, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
