"""Track executive newsletter send state for scheduled / catch-up runs."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
STATE_PATH = ROOT / "logs" / "newsletter-last-send.json"


def read_send_state() -> dict | None:
    if not STATE_PATH.is_file():
        return None
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_send_state(*, week_label: str, to: str, draft: bool) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "week_label": week_label,
        "to": to,
        "draft": draft,
        "sent_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    STATE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def expected_week_label() -> str:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    from send_weekly_newsletter_outlook import _build_executive_html, _week_label

    _, week_end = _build_executive_html(outlook_body=False)
    return _week_label(week_end)


def already_sent_for_current_week() -> bool:
    state = read_send_state()
    if not state or state.get("draft"):
        return False
    try:
        return str(state.get("week_label") or "") == expected_week_label()
    except Exception:
        return False
