"""Fail CI if static HTML shows common UTF-8 corruption (question marks replacing punctuation)."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
STATIC = _REPO / "static_home"

# Substrings that indicate em dash / arrows / ellipsis were lost (ASCII '?' placeholders).
_BAD_MARKERS: list[tuple[str, str]] = [
    ("etps.html", "? Back to home"),
    ("etps.html", "ETPs ? Full List"),
    ("etps.html", "ETPs ? Digital Assets"),
    ("etps.html", 'placeholder="Filter by name or ticker?"'),
    ("etps.html", "Loading headlines?"),
    ("etps.html", "Loading fund list?"),
    ("etps.html", "Loading?"),
    ("etps.html", "headlines ?"),
    ("etps.html", "weekly closes ? each"),
]

# Prefer HTML entities on etps.html for UI punctuation (encoding-safe).
_GOOD_MARKERS: list[tuple[str, str]] = [
    ("etps.html", "&larr; Back to home"),
    ("etps.html", "&mdash;"),
]


def main() -> None:
    errors: list[str] = []
    for rel, needle in _BAD_MARKERS:
        path = STATIC / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if needle in text:
            errors.append(f"{rel}: found corrupted marker {needle!r}")

    for rel, needle in _GOOD_MARKERS:
        path = STATIC / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if needle not in text:
            errors.append(f"{rel}: missing expected safe marker {needle!r}")

    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        print(
            "\nFix: use HTML entities (&larr;, &mdash;, &hellip;, &middot;) or save the file as UTF-8.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("static HTML encoding check passed")


if __name__ == "__main__":
    main()
