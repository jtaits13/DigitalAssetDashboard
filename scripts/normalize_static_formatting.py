"""Align static_home HTML asset versions, footers, and shared intro patterns."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "static_home"
CSS_V = "49"
STATIC_BASE_V = "13"

DEEP_INTRO_OLD = """      <header class="page-intro">
        <p class="band-label teal" id="js-deep-band"></p>
        <motion class="page-intro__dek" id="js-deep-subtitle"></motion>
      </header>

      <motion class="data-banner" id="js-deep-banner" role="status" hidden></motion>
""".replace("<motion class", "<motion class").replace(
    '<motion class="page-intro__dek" id="js-deep-subtitle"></motion>',
    '<div class="page-intro__dek" id="js-deep-subtitle"></div>',
).replace(
    '<motion class="data-banner" id="js-deep-banner" role="status" hidden></motion>',
    '<motion class="data-banner" id="js-deep-banner" role="status" hidden></motion>',
)

DEEP_INTRO_OLD = """      <header class="page-intro">
        <p class="band-label teal" id="js-deep-band"></p>
        <div class="page-intro__dek" id="js-deep-subtitle"></div>
      </header>

      <div class="data-banner" id="js-deep-banner" role="status" hidden></motion>
""".replace("</motion>", "</div>")

DEEP_INTRO_NEW = """      <header class="page-intro">
        <p class="band-label teal" id="js-deep-band"></p>
        <h1 class="page-intro__title" id="js-deep-title"></h1>
        <div class="page-intro__dek" id="js-deep-subtitle"></div>
      </header>

      <div class="data-banner" id="js-deep-banner" role="status" hidden></div>
      <hr class="section-rule" />
"""

DEEP_FILES = [
    "rwa-stablecoins.html",
    "rwa-us-treasuries.html",
    "rwa-tokenized-stocks.html",
    "rwa-participants-networks.html",
    "rwa-participants-platforms.html",
    "rwa-participants-asset-managers.html",
]

FOOTER_DASH = re.compile(
    r"Digital Assets Dashboard\s*[—·]\s*([^<·]+?)\s*[—·]\s*<time",
    re.I,
)


def bump_assets(text: str) -> str:
    text = re.sub(r"styles\.css\?v=\d+", f"styles.css?v={CSS_V}", text)
    text = re.sub(r"static-base\.js\?v=\d+", f"static-base.js?v={STATIC_BASE_V}", text)
    text = re.sub(
        r'<script src="js/static-base\.js"></script>',
        f'<script defer src="js/static-base.js?v={STATIC_BASE_V}"></script>',
        text,
    )
    text = re.sub(r"rwa-onchain-home\.js\?v=6", "rwa-onchain-home.js?v=7", text)
    text = re.sub(
        r'<script src="js/rwa-onchain-home\.js"></script>',
        '<script defer src="js/rwa-onchain-home.js?v=7"></script>',
        text,
    )
    return text


def normalize_footer(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        label = m.group(1).strip()
        return f"Digital Assets Dashboard · {label} · <time"

    return FOOTER_DASH.sub(repl, text)


def main() -> None:
    for path in sorted(ROOT.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        orig = text
        text = bump_assets(text)
        text = normalize_footer(text)
        if path.name in DEEP_FILES:
            if DEEP_INTRO_OLD in text:
                text = text.replace(DEEP_INTRO_OLD, DEEP_INTRO_NEW, 1)
                print("deep intro", path.name)
            else:
                print("WARN deep intro miss", path.name)
        if text != orig:
            path.write_text(text, encoding="utf-8", newline="\n")
            print("updated", path.name)


if __name__ == "__main__":
    main()
