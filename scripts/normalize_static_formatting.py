"""Align static_home HTML: cache versions, nav labels, back links, footers, script defer."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "static_home"

CSS_V = "70"
STATIC_BASE_V = "14"
TABLE_FULLSCREEN_V = "1"
TABLE_DOWNLOAD_V = "1"
KPI_HINTS_V = "3"
DATA_FRESHNESS_V = "1"
PAGE_METHODOLOGY_V = "3"
SNAPSHOT_KPI_V = "4"
ETP_KPI_V = "2"
CRYPTO_KPI_V = "9"
HOME_CRYPTO_V = "11"
HOME_PAGE_V = "11"
RWA_ONCHAIN_V = "10"
RWA_GLOBAL_V = "6"
RWA_DEEP_V = "7"
RWA_EXPLORE_PAGE_V = "6"
ETP_PAGE_V = "14"
CRYPTO_PAGE_V = "19"
ETF_NEWS_V = "2"
FULL_ARTICLE_FEED_V = "5"

DEEP_INTRO_BLOCK = """      <header class="page-intro">
        <p class="band-label teal" id="js-deep-band"></p>
        <h1 class="page-intro__title" id="js-deep-title"></h1>
        <div class="page-intro__dek" id="js-deep-subtitle"></div>
      </header>

      <div class="data-banner" id="js-deep-banner" role="status" hidden></div>
      <hr class="section-rule" />
"""

DEEP_FILES = frozenset(
    {
        "rwa-stablecoins.html",
        "rwa-us-treasuries.html",
        "rwa-tokenized-mmf.html",
        "rwa-tokenized-stocks.html",
        "rwa-participants-networks.html",
        "rwa-participants-platforms.html",
        "rwa-participants-asset-managers.html",
    }
)

SCRIPT_VERSIONS: list[tuple[str, str]] = [
    (r"styles\.css\?v=\d+", f"styles.css?v={CSS_V}"),
    (r"static-base\.js\?v=\d+", f"static-base.js?v={STATIC_BASE_V}"),
    (r"table-fullscreen\.js\?v=\d+", f"table-fullscreen.js?v={TABLE_FULLSCREEN_V}"),
    (r"table-download\.js\?v=\d+", f"table-download.js?v={TABLE_DOWNLOAD_V}"),
    (r"kpi-hints\.js\?v=\d+", f"kpi-hints.js?v={KPI_HINTS_V}"),
    (r"data-freshness\.js\?v=\d+", f"data-freshness.js?v={DATA_FRESHNESS_V}"),
    (r"page-methodology\.js\?v=\d+", f"page-methodology.js?v={PAGE_METHODOLOGY_V}"),
    (r"snapshot-kpi-shared\.js\?v=\d+", f"snapshot-kpi-shared.js?v={SNAPSHOT_KPI_V}"),
    (r"etp-kpi-shared\.js\?v=\d+", f"etp-kpi-shared.js?v={ETP_KPI_V}"),
    (r"crypto-kpi-shared\.js\?v=\d+", f"crypto-kpi-shared.js?v={CRYPTO_KPI_V}"),
    (r"home-crypto\.js\?v=\d+", f"home-crypto.js?v={HOME_CRYPTO_V}"),
    (r"home-page\.js\?v=\d+", f"home-page.js?v={HOME_PAGE_V}"),
    (r"rwa-onchain-home\.js\?v=\d+", f"rwa-onchain-home.js?v={RWA_ONCHAIN_V}"),
    (r"rwa-global-page\.js\?v=\d+", f"rwa-global-page.js?v={RWA_GLOBAL_V}"),
    (r"rwa-asset-deep-page\.js\?v=\d+", f"rwa-asset-deep-page.js?v={RWA_DEEP_V}"),
    (r"rwa-explore-asset-type-page\.js\?v=\d+", f"rwa-explore-asset-type-page.js?v={RWA_EXPLORE_PAGE_V}"),
    (r"etp-page\.js\?v=\d+", f"etp-page.js?v={ETP_PAGE_V}"),
    (r"crypto-page\.js\?v=\d+", f"crypto-page.js?v={CRYPTO_PAGE_V}"),
    (r"etf-news-page\.js\?v=\d+", f"etf-news-page.js?v={ETF_NEWS_V}"),
    (r"full-article-feed-page\.js\?v=\d+", f"full-article-feed-page.js?v={FULL_ARTICLE_FEED_V}"),
]

FOOTER_DASH = re.compile(
    r"Digital Assets Dashboard\s*[—·]\s*([^<·]+?)\s*[—·]\s*<time",
    re.I,
)

NAV_NEWS_OLD = '<a href="index.html#section-news">Digital Asset News</a>'
NAV_NEWS_NEW = '<a href="index.html#section-news">News Hub</a>'
NAV_NEWS_ACTIVE_OLD = '<a href="index.html#section-news" class="is-active">Digital Asset News</a>'
NAV_NEWS_ACTIVE_NEW = '<a href="index.html#section-news" class="is-active">News Hub</a>'

BACK_NEWS_OLD = "← Back to home (News)"
BACK_NEWS_NEW = "← Back to home (News Hub)"


KPI_HINTS_TAG = f'<script defer src="js/kpi-hints.js?v={KPI_HINTS_V}"></script>'
TABLE_FULLSCREEN_TAG = f'<script defer src="js/table-fullscreen.js?v={TABLE_FULLSCREEN_V}"></script>'
TABLE_DOWNLOAD_TAG = f'<script defer src="js/table-download.js?v={TABLE_DOWNLOAD_V}"></script>'


def ensure_kpi_hints_script(text: str) -> str:
    if "kpi-hints.js" in text:
        return text
    needle = re.search(
        r'<script defer src="js/static-base\.js\?v=\d+"></script>',
        text,
    )
    if not needle:
        return text
    insert_at = needle.end()
    return text[:insert_at] + "\n    " + KPI_HINTS_TAG + text[insert_at:]


def ensure_table_fullscreen_script(text: str) -> str:
    if "table-fullscreen.js" in text:
        return text
    if "table-wrap" not in text and "rwa-onchain-home.js" not in text:
        return text
    needle = re.search(
        r'<script defer src="js/static-base\.js\?v=\d+"></script>',
        text,
    )
    if not needle:
        return text
    insert_at = needle.end()
    return text[:insert_at] + "\n    " + TABLE_FULLSCREEN_TAG + text[insert_at:]


def ensure_table_download_script(text: str) -> str:
    if "table-download.js" in text:
        return text
    if "table-fullscreen.js" not in text:
        return text
    needle = re.search(
        r'<script defer src="js/table-fullscreen\.js\?v=\d+"></script>',
        text,
    )
    if not needle:
        return text
    insert_at = needle.end()
    return text[:insert_at] + "\n    " + TABLE_DOWNLOAD_TAG + text[insert_at:]


def strip_monthly_review_script(text: str) -> str:
    return re.sub(
        r'\s*<script defer src="js/monthly-review-note\.js\?v=\d+"></script>',
        "",
        text,
    )


def bump_assets(text: str) -> str:
    for pat, repl in SCRIPT_VERSIONS:
        text = re.sub(pat, repl, text)
    text = text.replace(
        '<script src="js/static-base.js"></script>',
        f'<script defer src="js/static-base.js?v={STATIC_BASE_V}"></script>',
    )
    text = ensure_kpi_hints_script(text)
    text = ensure_table_fullscreen_script(text)
    text = ensure_table_download_script(text)
    text = strip_monthly_review_script(text)
    # Prefer defer on local JS (skip plotly CDN)
    text = re.sub(
        r'<script src="(js/[^"]+\.js\?v=\d+)"></script>',
        r'<script defer src="\1"></script>',
        text,
    )
    return text


def normalize_nav_and_back(text: str) -> str:
    text = text.replace(NAV_NEWS_ACTIVE_OLD, NAV_NEWS_ACTIVE_NEW)
    text = text.replace(NAV_NEWS_OLD, NAV_NEWS_NEW)
    text = text.replace(BACK_NEWS_OLD, BACK_NEWS_NEW)
    return text


def normalize_footer(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        label = m.group(1).strip()
        return f"Digital Assets Dashboard · {label} · <time"

    return FOOTER_DASH.sub(repl, text)


def ensure_deep_intro(path: Path, text: str) -> str:
    if path.name not in DEEP_FILES:
        return text
    if DEEP_INTRO_BLOCK in text:
        return text
    # Legacy: missing h1 or wrong closing tags
    legacy = re.search(
        r'<header class="page-intro">[\s\S]*?</header>\s*'
        r'<(?:div|motion)[^>]*id="js-deep-banner"[\s\S]*?>\s*'
        r'<hr class="section-rule"\s*/>',
        text,
    )
    if legacy:
        text = text[: legacy.start()] + DEEP_INTRO_BLOCK + text[legacy.end() :]
        print("  fixed deep intro", path.name)
    else:
        print("  WARN deep intro", path.name)
    return text


def main() -> None:
    for path in sorted(ROOT.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        orig = text
        text = bump_assets(text)
        text = normalize_nav_and_back(text)
        text = normalize_footer(text)
        text = ensure_deep_intro(path, text)
        if text != orig:
            path.write_text(text, encoding="utf-8", newline="\n")
            print("updated", path.name)


if __name__ == "__main__":
    main()
