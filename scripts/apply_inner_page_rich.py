"""Wrap non-home static pages in the inner-rich zone layout. Revert: remove page-inner--rich + inner-page-experience.css."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "static_home"
CSS_LINK = '    <link rel="stylesheet" href="css/inner-page-experience.css?v=1" />'

RENAME_MAP = {
    "page-etp--rich": "page-inner--rich",
    "etp-rich-zone": "inner-rich-zone",
    "etp-rich-zone__body": "inner-rich-zone__body",
    "etp-rich-block": "inner-rich-block",
    "etp-rich-rule": "inner-rich-rule",
    "css/etp-page-experience.css": "css/inner-page-experience.css",
}


def zone_for_body(body_class: str) -> tuple[str, str, str]:
    if "page-etp" in body_class:
        return "zone--etp", "ETP", "home-zone--etp"
    if "page-crypto" in body_class:
        return "zone--crypto", "CRY", "home-zone--crypto"
    if "page-article-feed" in body_class or "page-full-feed" in body_class:
        return "zone--news", "NEWS", ""
    return "zone--rwa", "RWA", "home-zone--rwa"


def patch_head(text: str) -> str:
    text = re.sub(
        r'\s*<link rel="stylesheet" href="css/etp-page-experience\.css\?v=\d+" />\s*',
        "\n",
        text,
    )
    if "inner-page-experience.css" not in text:
        text = text.replace(
            '<link rel="stylesheet" href="css/site-experience.css?v=2" />',
            '<link rel="stylesheet" href="css/site-experience.css?v=2" />\n' + CSS_LINK,
        )
    return text


def patch_body_class(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        cls = match.group(2).replace("page-etp--rich", "").strip()
        if "page-inner--rich" not in cls:
            cls = f"{cls} page-inner--rich".strip()
        return f'{match.group(1)}{cls}{match.group(3)}'

    return re.sub(
        r'(<body\b[^>]*\sclass=")([^"]+)(")',
        repl,
        text,
        count=1,
    )


def migrate_legacy(text: str, zone: str) -> str:
    for old, new in RENAME_MAP.items():
        text = text.replace(old, new)
    if "inner-rich-zone" in text and zone not in text:
        text = text.replace(
            "inner-rich-zone home-zone",
            f"inner-rich-zone {zone} home-zone",
            1,
        )
    return text


def transform_main(text: str, zone: str, badge: str, home_zone: str) -> str:
    if "inner-rich-zone" in text or "etp-rich-zone" in text:
        return migrate_legacy(text, zone)

    main_m = re.search(r"<main class=\"page-shell\">(.*?)</main>", text, re.S)
    if not main_m:
        return text

    inner = main_m.group(1)
    back_m = re.search(r"(\s*<p class=\"back-link\">.*?</p>\s*)$", inner, re.S)
    back_link = back_m.group(1) if back_m else ""
    body_inner = inner[: back_m.start()] if back_m else inner

    intro_m = re.search(r"<header class=\"page-intro\">(.*?)</header>\s*", body_inner, re.S)
    if intro_m:
        titles = intro_m.group(1).strip()
        content = body_inner[intro_m.end() :].strip()
    else:
        titles = '<h1 class="page-intro__title">Page</h1>'
        content = body_inner.strip()

    content = re.sub(r"^<hr class=\"section-rule\"\s*/>\s*", "", content)
    content = content.replace('class="section-rule"', 'class="inner-rich-rule"')

    home_zone_class = f" home-zone {home_zone}" if home_zone else ""
    article = (
        f'\n      <article class="hub-section hub-section--panel inner-rich-zone {zone}{home_zone_class}">\n'
        f'        <div class="home-zone__stripe" aria-hidden="true"></div>\n'
        f"        <header class=\"home-zone__head\">\n"
        f'          <span class="home-zone__badge" aria-hidden="true">{badge}</span>\n'
        f'          <div class="home-zone__titles">\n'
        f"            {titles}\n"
        f"          </div>\n"
        f"        </header>\n"
        f'        <div class="home-zone__body inner-rich-zone__body">\n'
        f"          {content}\n"
        f"        </div>\n"
        f"      </article>\n"
        f"{back_link}"
    )

    return text[: main_m.start()] + "<main class=\"page-shell\">" + article + "</main>" + text[main_m.end() :]


def normalize_scripts(text: str) -> str:
    return re.sub(
        r"\n\s{6}(<script defer src=\"js/site-experience\.js)",
        r"\n    \1",
        text,
    )


def main() -> None:
    for path in sorted(ROOT.glob("*.html")):
        if path.name == "index.html":
            continue
        orig = path.read_text(encoding="utf-8")
        body_m = re.search(r'<body class="([^"]+)"', orig)
        if not body_m:
            body_m = re.search(r"<body[^>]*\sclass=\"([^\"]+)\"", orig, re.S)
        body_class = body_m.group(1) if body_m else ""
        zone, badge, home_zone = zone_for_body(body_class)

        text = patch_head(orig)
        text = patch_body_class(text)
        text = transform_main(text, zone, badge, home_zone)
        text = normalize_scripts(text)

        if text != orig:
            path.write_text(text, encoding="utf-8", newline="\n")
            print("updated", path.name)


if __name__ == "__main__":
    main()
