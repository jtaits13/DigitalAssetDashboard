#!/usr/bin/env python3
"""Restore UTF-8 punctuation and arrows in static_home HTML/JS/CSS."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "static_home"
EXTENSIONS = {".html", ".js", ".css"}


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


def fix_text(text: str) -> str:
    # Arrows written as ASCII "?".
    text = text.replace("? Back to", "← Back to")
    text = text.replace("? Explore by", "← Explore by")
    text = text.replace("? RWA Global", "← RWA Global")
    text = text.replace("All ETF/ETP headlines ?", "All ETF/ETP headlines →")

    # Mojibake: U+FFFD + "??" from UTF-8 round-trips.
    text = re.sub(r"headlines \ufffd\?\?</a>", "headlines →</a>", text)
    text = re.sub(r"RWA\.xyz</strong>\ufffd\?\?in\b", "RWA.xyz</strong>—in", text)
    text = re.sub(r"\ufffd\?\?</a>", " →</a>", text)
    text = re.sub(r"\ufffd\?\?", " —", text)

    # Nav labels: middle dot before Assets/Participants.
    text = re.sub(r"RWA\s*[—\ufffd]\s*Assets", "RWA · Assets", text)
    text = re.sub(r"RWA\s*[—\ufffd]\s*Participants", "RWA · Participants", text)

    # Lone replacement characters (usually em dash in titles / intros).
    text = text.replace("\ufffd", "—")

    # Loading ellipsis mojibake.
    text = re.sub(
        r'<li class="headline-list__loading">Loading headlines[^<]*</li>',
        '<li class="headline-list__loading">Loading headlines…</li>',
        text,
    )
    text = re.sub(
        r'<li class="headline-list__loading">Loading[^<]*</li>',
        '<li class="headline-list__loading">Loading…</li>',
        text,
    )
    text = re.sub(
        r'<li class="pulse-list__loading">Loading headlines[^<]*</li>',
        '<li class="pulse-list__loading">Loading headlines…</li>',
        text,
    )

    return text


def main() -> None:
    changed: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if path.suffix.lower() not in EXTENSIONS:
            continue
        original = read_text(path)
        fixed = fix_text(original)
        if fixed != original:
            path.write_text(fixed, encoding="utf-8", newline="\n")
            changed.append(str(path.relative_to(ROOT.parent)))

    print(f"Updated {len(changed)} file(s):")
    for name in changed:
        print(f"  {name}")


if __name__ == "__main__":
    main()
