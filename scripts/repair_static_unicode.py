#!/usr/bin/env python3
"""Repair common UTF-8 corruption in static_home HTML (arrows, dashes, ellipses).

Also re-encodes Windows-1252 HTML files as UTF-8 so GitHub Pages (UTF-8) does not
show ``?`` for em dashes, middots, and arrows.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "static_home"


def read_text(path: Path) -> tuple[str, bool]:
    """Return ``(text, was_non_utf8)``."""
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8"), False
    except UnicodeDecodeError:
        return raw.decode("cp1252"), True


def fix_text(text: str) -> str:
    # Literal ``?`` placeholders left by prior encoding loss.
    text = text.replace("? Back to", "\u2190 Back to")
    text = text.replace("??? Back to", "\u2190 Back to")
    text = text.replace("? Explore by", "\u2190 Explore by")
    text = text.replace("? RWA Global", "\u2190 RWA Global")
    text = text.replace("All ETF/ETP headlines ?", "All ETF/ETP headlines \u2192")
    text = text.replace("All digital asset headlines ?", "All digital asset headlines \u2192")
    text = text.replace("All regulatory headlines ?", "All regulatory headlines \u2192")
    text = text.replace("TOTAL chart ?", "TOTAL chart \u2192")

    text = re.sub(r"Crypto Prices \? Digital", "Crypto Prices \u2014 Digital", text)
    text = re.sub(r"Crypto Prices \? Top", "Crypto Prices \u2014 Top", text)
    text = re.sub(r"ETPs \? Digital", "ETPs \u2014 Digital", text)
    text = re.sub(r"ETPs \? Full", "ETPs \u2014 Full", text)
    text = re.sub(r"RWA \?\? Assets", "RWA \u00b7 Assets", text)
    text = re.sub(r"RWA \?\? Participants", "RWA \u00b7 Participants", text)
    text = re.sub(r"RWA\s+\?\s+Assets", "RWA \u00b7 Assets", text)
    text = re.sub(r"RWA\s+\?\s+Participants", "RWA \u00b7 Participants", text)

    text = text.replace("CoinGecko?s", "CoinGecko\u2019s")
    text = text.replace("fund?s", "fund\u2019s")

    text = re.sub(
        r'placeholder="Filter by name or ticker\?"',
        'placeholder="Filter by name or ticker\u2026"',
        text,
    )
    text = re.sub(
        r'placeholder="Filter by name or ticker[^"]*"',
        'placeholder="Filter by name or ticker\u2026"',
        text,
    )
    text = re.sub(r"Loading market table\?", "Loading market table\u2026", text)
    text = re.sub(
        r"Loading fund list[^<]*</p>",
        '<p class="toolbar-note" id="js-etp-toolbar">Loading fund list\u2026</p>',
        text,
    )
    text = re.sub(r"<td colspan=\"8\">Loading\?</td>", '<td colspan="8">Loading\u2026</td>', text)
    text = re.sub(r"<td colspan=\"10\">Loading[^<]*</td>", '<td colspan="10">Loading\u2026</td>', text)
    text = re.sub(
        r'<p class="timestamp-foot" id="js-crypto-generated">\?</p>',
        '<p class="timestamp-foot" id="js-crypto-generated">\u2014</p>',
        text,
    )

    # Replacement character (U+FFFD) from UTF-8 mis-decode of cp1252 punctuation.
    text = re.sub(r"RWA\s+\ufffd\s+Assets", "RWA \u00b7 Assets", text)
    text = re.sub(r"RWA\s+\ufffd\s+Participants", "RWA \u00b7 Participants", text)
    text = re.sub(r"headlines \ufffd", "headlines \u2192", text)
    text = re.sub(r"\ufffd\?\?</a>", " \u2192</a>", text)
    text = re.sub(r"\ufffd\?\?", " \u2014", text)
    text = text.replace("\ufffd", "\u2014")

    text = re.sub(
        r'<li class="headline-list__loading">Loading headlines[^<]*</li>',
        '<li class="headline-list__loading">Loading headlines\u2026</li>',
        text,
    )
    text = re.sub(
        r'<li class="headline-list__loading">Loading[^<]*</li>',
        '<li class="headline-list__loading">Loading\u2026</li>',
        text,
    )
    text = re.sub(r"Loading crypto snapshot[^<]*</td>", "Loading crypto snapshot\u2026</td>", text)
    text = re.sub(r"Loading ETP snapshot[^<]*</td>", "Loading ETP snapshot\u2026</td>", text)
    text = re.sub(r"Loading on-chain preview[^<]*</td>", "Loading on-chain preview\u2026</td>", text)

    # Prefer HTML entities in markup so future Windows saves cannot re-corrupt punctuation.
    text = text.replace("\u2190 Back to", "&larr; Back to")
    text = text.replace("headlines \u2192", "headlines &rarr;")
    text = text.replace("chart \u2192", "chart &rarr;")
    text = text.replace("Full overview \u2192", "Full overview &rarr;")
    text = text.replace("Open full page \u2192", "Open full page &rarr;")
    text = text.replace("Open live dashboard \u2192", "Open live dashboard &rarr;")
    text = text.replace("RWA \u00b7 Assets", "RWA &middot; Assets")
    text = text.replace("RWA \u00b7 Participants", "RWA &middot; Participants")
    # Title / footer em dashes between words (avoid touching HTML comments).
    text = re.sub(r"(?<=\w) \u2014 (?=\w)", " &mdash; ", text)
    text = re.sub(r"(?<=\w)\u2014(?=\w)", "&mdash;", text)

    return text


def main() -> None:
    changed: list[str] = []
    for path in sorted(ROOT.rglob("*.html")):
        original, was_non_utf8 = read_text(path)
        fixed = fix_text(original)
        if fixed != original or was_non_utf8:
            path.write_text(fixed, encoding="utf-8", newline="\n")
            tag = " (re-encoded from cp1252)" if was_non_utf8 else ""
            changed.append(f"{path.relative_to(ROOT.parent)}{tag}")
    print(f"Repaired {len(changed)} HTML file(s):")
    for name in changed:
        print(f"  {name}")


if __name__ == "__main__":
    main()
