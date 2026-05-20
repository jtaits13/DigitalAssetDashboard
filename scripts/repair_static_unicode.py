#!/usr/bin/env python3
"""Repair common UTF-8 corruption in static_home HTML (arrows, dashes, ellipses)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "static_home"


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


def fix_text(text: str) -> str:
    text = text.replace("? Back to", "\u2190 Back to")
    text = text.replace("??? Back to", "\u2190 Back to")
    text = text.replace("? Explore by", "\u2190 Explore by")
    text = text.replace("? RWA Global", "\u2190 RWA Global")
    text = text.replace("All ETF/ETP headlines ?", "All ETF/ETP headlines \u2192")
    text = text.replace("All digital asset headlines ?", "All digital asset headlines \u2192")
    text = text.replace("All regulatory headlines ?", "All regulatory headlines \u2192")
    text = text.replace("TOTAL chart ?", "TOTAL chart \u2192")
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
    text = text.replace("fund?s", "fund\u2019s")

    text = re.sub(r'placeholder="Filter by name or ticker\?"', 'placeholder="Filter by name or ticker\u2026"', text)
    text = re.sub(r'placeholder="Filter by name or ticker[^"]*"', 'placeholder="Filter by name or ticker\u2026"', text)
    text = re.sub(r"Loading market table\?", "Loading market table\u2026", text)
    text = re.sub(r"Loading fund list[^<]*</p>", "<p class=\"toolbar-note\" id=\"js-etp-toolbar\">Loading fund list\u2026</p>", text)
    text = re.sub(r"<td colspan=\"8\">Loading\?</td>", '<td colspan="8">Loading\u2026</td>', text)
    text = re.sub(r"<td colspan=\"10\">Loading[^<]*</td>", '<td colspan="10">Loading\u2026</td>', text)
    text = re.sub(
        r'<p class="timestamp-foot" id="js-crypto-generated">\?</p>',
        '<p class="timestamp-foot" id="js-crypto-generated">\u2014</p>',
        text,
    )

    text = re.sub(r"headlines \ufffd\?\?</a>", "headlines \u2192</a>", text)
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

    # Em dash between words (not ternary ? in URLs)
    text = re.sub(r" — ", " \u2014 ", text)
    text = re.sub(r"—", "\u2014", text)

    return text


def main() -> None:
    changed: list[str] = []
    for path in sorted(ROOT.rglob("*.html")):
        original = read_text(path)
        fixed = fix_text(original)
        if fixed != original:
            path.write_text(fixed, encoding="utf-8", newline="\n")
            changed.append(str(path.relative_to(ROOT.parent)))
    print(f"Repaired {len(changed)} HTML file(s):")
    for name in changed:
        print(f"  {name}")


if __name__ == "__main__":
    main()
