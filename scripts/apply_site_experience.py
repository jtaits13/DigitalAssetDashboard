"""Apply site-experience styling to all static_home HTML pages."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static_home"
CSS_DST = STATIC / "css" / "site-experience.css"
JS_DST = STATIC / "js" / "site-experience.js"

SITE_CSS_V = "1"
SITE_JS_V = "1"
STYLES_LINK = f'<link rel="stylesheet" href="css/site-experience.css?v={SITE_CSS_V}" />'
SITE_JS_TAG = f'<script defer src="js/site-experience.js?v={SITE_JS_V}"></script>'

INNER_PAGE_CSS = """
/* —— Site-wide inner pages —— */
.site-experience[class*="page-rwa"] {
  --hx-stripe: var(--hx-rwa-bright);
}

.site-experience.page-etp {
  --hx-stripe: var(--hx-etp-bright);
}

.site-experience.page-crypto {
  --hx-stripe: var(--hx-crypto-bright);
}

.site-experience.page-article-feed,
.site-experience.page-full-feed {
  --hx-stripe: #5eb8d4;
}

.site-experience:not(.page-home) .page-shell {
  padding-top: 0.35rem;
}

.site-experience:not(.page-home) .page-intro {
  position: relative;
  margin: 0 0 1.15rem;
  padding: 1.1rem 1.25rem 1.05rem;
  border-radius: 14px;
  border: 1px solid rgba(199, 216, 232, 0.9);
  background: #ffffff;
  box-shadow:
    0 1px 2px rgba(2, 29, 65, 0.04),
    0 8px 26px rgba(2, 29, 65, 0.06);
  overflow: hidden;
}

.site-experience:not(.page-home) .page-intro::before {
  content: "";
  display: block;
  height: 4px;
  margin: -1.1rem -1.25rem 0.9rem;
  background: linear-gradient(90deg, var(--hx-stripe, var(--hx-rwa-bright)) 0%, transparent 88%);
}

.site-experience[class*="page-rwa"]:not(.page-home) .page-intro {
  background: var(--hx-rwa-head);
}

.site-experience.page-etp:not(.page-home) .page-intro {
  background: var(--hx-etp-head);
}

.site-experience.page-crypto:not(.page-home) .page-intro {
  background: var(--hx-crypto-head);
}

.site-experience.page-article-feed:not(.page-home) .page-intro {
  background: linear-gradient(180deg, #eef6fa 0%, #ffffff 100%);
}

.site-experience:not(.page-home) .page-intro__title {
  font-size: clamp(1.45rem, 3vw, 1.85rem);
  letter-spacing: -0.02em;
}

.site-experience[class*="page-rwa"]:not(.page-home) .page-intro .band-label.teal {
  color: var(--hx-rwa);
}

.site-experience.page-etp:not(.page-home) .page-intro .band-label.teal {
  color: var(--hx-etp);
}

.site-experience.page-crypto:not(.page-home) .page-intro .band-label.teal {
  color: var(--hx-crypto);
}

.site-experience .page-back-below-header {
  max-width: calc(var(--max) + 17.5rem);
  margin: 0 auto;
  padding: 0.5rem 1.5rem 0;
}

.site-experience .back-link--below-header a {
  display: inline-block;
  font-weight: 650;
  font-size: 0.84rem;
  color: var(--ink-soft);
  text-decoration: none;
  padding: 0.35rem 0.65rem;
  border-radius: 999px;
  border: 1px solid rgba(199, 216, 232, 0.85);
  background: rgba(255, 255, 255, 0.85);
  transition:
    border-color 0.15s ease,
    color 0.15s ease,
    background 0.15s ease;
}

.site-experience .back-link--below-header a:hover {
  color: var(--teal);
  border-color: rgba(37, 128, 156, 0.35);
  background: #f8fcfe;
}

.site-experience:not(.page-home) .page-shell > .hub-section,
.site-experience:not(.page-home) .page-shell > section.hub-section,
.site-experience:not(.page-home) .page-shell #js-rwa-global-snapshot > .hub-section,
.site-experience:not(.page-home) .page-shell #js-rwa-global-detail-stack > .hub-section {
  border: 1px solid rgba(199, 216, 232, 0.85);
  border-radius: 14px;
  padding: 1rem 1.25rem 1.25rem;
  margin-bottom: 1.15rem;
  background: #ffffff;
  box-shadow:
    0 1px 2px rgba(2, 29, 65, 0.04),
    0 6px 22px rgba(2, 29, 65, 0.05);
}

.site-experience:not(.page-home) .subsection-head {
  font-size: 1.05rem;
  font-weight: 780;
  letter-spacing: -0.02em;
  color: var(--ink);
  padding-bottom: 0.45rem;
  border-bottom: 1px solid rgba(199, 216, 232, 0.55);
  margin-bottom: 0.85rem;
}

.site-experience[class*="page-rwa"]:not(.page-home) .subsection-head {
  color: var(--hx-rwa);
}

.site-experience.page-etp:not(.page-home) .subsection-head {
  color: var(--hx-etp);
}

.site-experience.page-crypto:not(.page-home) .subsection-head {
  color: var(--hx-crypto);
}

.site-experience.page-article-feed:not(.page-home) .subsection-head {
  color: #1a5570;
}

.site-experience:not(.page-home) .section-rule {
  border: none;
  height: 1px;
  margin: 0 0 1rem;
  background: linear-gradient(90deg, rgba(199, 216, 232, 0.9), rgba(199, 216, 232, 0.2), transparent);
}

.site-experience .rwa-kpi-panel-static {
  background: transparent;
  border: none;
  box-shadow: none;
  padding: 0.35rem 0 0.5rem;
  margin: 0.35rem 0 0.65rem;
}

.site-experience .rwa-kpi-row--home-grid .rwa-kpi-cell {
  border-radius: 10px;
  padding: 0.6rem 0.72rem;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    background 0.2s ease;
}

.site-experience[class*="page-rwa"] .rwa-kpi-row--home-grid .rwa-kpi-cell,
.site-experience.page-home .home-zone--rwa .rwa-kpi-row--home-grid .rwa-kpi-cell {
  border: 1px solid rgba(37, 128, 156, 0.14);
  border-left: 3px solid rgba(37, 128, 156, 0.42);
  background: linear-gradient(145deg, rgba(232, 244, 248, 0.92) 0%, rgba(255, 255, 255, 0.88) 68%);
}

.site-experience.page-etp .rwa-kpi-row--home-grid .rwa-kpi-cell,
.site-experience.page-home .home-zone--etp .rwa-kpi-row--home-grid .rwa-kpi-cell {
  border: 1px solid rgba(166, 111, 18, 0.14);
  border-left: 3px solid rgba(166, 111, 18, 0.42);
  background: linear-gradient(145deg, rgba(250, 244, 232, 0.92) 0%, rgba(255, 255, 255, 0.88) 68%);
}

.site-experience.page-crypto .rwa-kpi-row--home-grid .rwa-kpi-cell,
.site-experience.page-home .home-zone--crypto .rwa-kpi-row--home-grid .rwa-kpi-cell {
  border: 1px solid rgba(61, 106, 158, 0.14);
  border-left: 3px solid rgba(61, 106, 158, 0.42);
  background: linear-gradient(145deg, rgba(238, 243, 250, 0.92) 0%, rgba(255, 255, 255, 0.88) 68%);
}

.site-experience[class*="page-rwa"] .rwa-kpi-row--home-grid .rwa-kpi-cell:hover,
.site-experience.page-home .home-zone--rwa .rwa-kpi-row--home-grid .rwa-kpi-cell:hover {
  border-color: rgba(37, 128, 156, 0.22);
  box-shadow: 0 4px 12px rgba(37, 128, 156, 0.1);
  background: linear-gradient(145deg, rgba(232, 244, 248, 0.98) 0%, rgba(255, 255, 255, 0.92) 68%);
}

.site-experience.page-etp .rwa-kpi-row--home-grid .rwa-kpi-cell:hover,
.site-experience.page-home .home-zone--etp .rwa-kpi-row--home-grid .rwa-kpi-cell:hover {
  border-color: rgba(166, 111, 18, 0.22);
  box-shadow: 0 4px 12px rgba(166, 111, 18, 0.1);
  background: linear-gradient(145deg, rgba(250, 244, 232, 0.98) 0%, rgba(255, 255, 255, 0.92) 68%);
}

.site-experience.page-crypto .rwa-kpi-row--home-grid .rwa-kpi-cell:hover,
.site-experience.page-home .home-zone--crypto .rwa-kpi-row--home-grid .rwa-kpi-cell:hover {
  border-color: rgba(61, 106, 158, 0.22);
  box-shadow: 0 4px 12px rgba(61, 106, 158, 0.1);
  background: linear-gradient(145deg, rgba(238, 243, 250, 0.98) 0%, rgba(255, 255, 255, 0.92) 68%);
}

.site-experience[class*="page-rwa"] .table-wrap:not(.table-wrap--no-clip),
.site-experience.page-home .home-zone--rwa .table-wrap:not(.table-wrap--no-clip) {
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(37, 128, 156, 0.14);
}

.site-experience.page-etp .table-wrap:not(.table-wrap--no-clip),
.site-experience.page-home .home-zone--etp .table-wrap:not(.table-wrap--no-clip) {
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(166, 111, 18, 0.14);
}

.site-experience.page-crypto .table-wrap:not(.table-wrap--no-clip),
.site-experience.page-home .home-zone--crypto .table-wrap:not(.table-wrap--no-clip) {
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(61, 106, 158, 0.14);
}

.site-experience .data-table tbody tr {
  transition: background-color 0.15s ease;
}

.site-experience .data-table tbody tr:hover {
  background: rgba(2, 29, 65, 0.03);
}

.site-experience .data-banner:not([hidden]) {
  border-radius: 10px;
}

.site-experience[class*="page-rwa"] .jd-hub-explore-card-static,
.site-experience.page-home .home-zone--rwa .jd-hub-explore-card-static {
  background: linear-gradient(180deg, #f6fbfd 0%, #ffffff 100%);
  border: 1px solid rgba(37, 128, 156, 0.18);
  border-left: 3px solid var(--hx-rwa-bright);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(26, 107, 130, 0.06);
}

.site-experience[class*="page-rwa"] .jd-hub-explore-card-static:hover,
.site-experience.page-home .home-zone--rwa .jd-hub-explore-card-static:hover {
  border-color: rgba(37, 128, 156, 0.32);
  box-shadow: 0 6px 18px rgba(26, 107, 130, 0.1);
  transform: translateY(-1px);
}

.site-experience[class*="page-rwa"] .jd-hub-explore-eyebrow,
.site-experience.page-home .home-zone--rwa .jd-hub-explore-eyebrow {
  color: var(--hx-rwa);
}

.site-experience.page-article-feed .article-feed-toolbar,
.site-experience.page-full-feed .article-feed-toolbar {
  padding: 0.85rem 1rem;
  margin-bottom: 1rem;
  border-radius: 12px;
  border: 1px solid rgba(199, 216, 232, 0.85);
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
}

.site-experience.page-article-feed .headline-list,
.site-experience.page-full-feed .headline-list {
  border-radius: 12px;
  border: 1px solid rgba(199, 216, 232, 0.85);
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  overflow: hidden;
}

.site-experience .search-field__input:focus {
  border-color: var(--hx-rwa-bright);
  box-shadow: 0 0 0 3px rgba(37, 128, 156, 0.12);
}

.site-experience.page-etp .search-field__input:focus {
  border-color: var(--hx-etp-bright);
  box-shadow: 0 0 0 3px rgba(166, 111, 18, 0.12);
}

.site-experience.page-crypto .search-field__input:focus {
  border-color: var(--hx-crypto-bright);
  box-shadow: 0 0 0 3px rgba(61, 106, 158, 0.12);
}

.site-experience .back-link a:focus-visible,
.site-experience .search-field__input:focus-visible {
  outline: 2px solid var(--teal);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .site-experience[class*="page-rwa"] .jd-hub-explore-card-static:hover,
  .site-experience.page-home .home-zone--rwa .jd-hub-explore-card-static:hover {
    transform: none;
  }
}
"""


def build_site_css() -> str:
    src = CSS_SRC.read_text(encoding="utf-8")
    src = src.replace(
        "/* Home experience v5 — contrast + polish (revert: remove page-home--experience + this file) */",
        "/* Site experience — unified dashboard styling (home + inner pages) */",
    )
    css = src.replace(".page-home--experience", ".site-experience.page-home")

    css = css.replace(".site-experience.page-home {", ".site-experience {", 1)
    css = css.replace(
        ".site-experience.page-home .site-header {",
        ".site-experience .site-header {",
    )
    css = css.replace(
        ".site-experience.page-home .site-header.site-header--elevated {",
        ".site-experience .site-header.site-header--elevated {",
    )
    css = css.replace(
        ".site-experience.page-home .site-footer {",
        ".site-experience .site-footer {",
    )

    # Remove duplicate KPI/footer/table blocks from home section; site-wide rules live in INNER_PAGE_CSS.
    start = css.find("/* —— Zone KPIs, explore cards, tables, footer —— */")
    end = css.find("@media (prefers-reduced-motion: reduce) {", start)
    if start != -1 and end != -1:
        css = css[:start] + css[end:]

    css = css.rstrip() + "\n" + INNER_PAGE_CSS.strip() + "\n"
    return css


def build_site_js() -> str:
    src = JS_SRC.read_text(encoding="utf-8")
    return src.replace(
        "/**\n * Home page UX: scroll reveal, jump-nav highlighting, headline stagger hook.\n * Revert by removing page-home--experience from body and this script tag.\n */\n(function () {\n  if (!document.body.classList.contains(\"page-home--experience\")) return;\n\n  var reducedMotion",
        "/**\n * Site experience UX: header elevation (all pages); home scroll reveal + jump nav.\n */\n(function () {\n  if (!document.body.classList.contains(\"site-experience\")) return;\n\n  var isHome = document.body.classList.contains(\"page-home\");\n  var reducedMotion",
    ).replace(
        "  function init() {\n    initReveal();\n    initJumpNav();\n    watchNewsList();\n    initHeaderScroll();\n  }",
        "  function init() {\n    initHeaderScroll();\n    if (!isHome) return;\n    initReveal();\n    initJumpNav();\n    watchNewsList();\n  }",
    )


def patch_body_class(text: str) -> str:
    text = text.replace("page-home--experience", "")
    text = re.sub(r'class="page-home\s+"', 'class="page-home site-experience"', text)

    def add_site_experience(match: re.Match[str]) -> str:
        prefix, cls, suffix = match.group(1), match.group(2), match.group(3)
        if "site-experience" in cls:
            return match.group(0)
        return f'{prefix}{cls.strip()} site-experience{suffix}'

    return re.sub(
        r'(<body\b[^>]*\sclass=")([^"]+)(")',
        add_site_experience,
        text,
        count=1,
        flags=re.DOTALL,
    )


def patch_html(text: str, path: Path) -> str:
    text = re.sub(r'\s*<link rel="stylesheet" href="css/home-experience\.css\?v=\d+" />\s*', "\n", text)
    if "site-experience.css" not in text:
        text = text.replace(
            f'<link rel="stylesheet" href="styles.css?v=77" />',
            f'<link rel="stylesheet" href="styles.css?v=77" />\n    {STYLES_LINK}',
        )

    text = re.sub(r'\s*<script defer src="js/home-experience\.js\?v=\d+"></script>\s*', "\n", text)
    if "site-experience.js" not in text:
        if "</body>" in text:
            text = text.replace("</body>", f"    {SITE_JS_TAG}\n  </body>")

    text = patch_body_class(text)

    if path.name == "index.html":
        text = text.replace("Live market dashboard", "Market dashboard")
        text = text.replace("Live Market Dashboard", "Market Dashboard")

    return text


def main() -> None:
    seen: set[str] = set()
    for path in sorted(STATIC.glob("*.html")):
        key = path.name.lower()
        if key in seen:
            continue
        seen.add(key)
        orig = path.read_text(encoding="utf-8")
        updated = patch_html(orig, path)
        if updated != orig:
            path.write_text(updated, encoding="utf-8", newline="\n")
            print("updated", path.name)


if __name__ == "__main__":
    main()
