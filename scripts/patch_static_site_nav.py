"""One-off / maintenance: rewrite static_home/*.html primary nav to dropdown version. Run from repo root."""
from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent

RWA_ASSET_CHILDREN: list[tuple[str, str]] = [
    ("rwa-stablecoins.html", "Stablecoins"),
    ("rwa-us-treasuries.html", "U.S. Treasuries"),
    ("rwa-tokenized-stocks.html", "Tokenized Stocks"),
    ("rwa-tokenized-mmf.html", "TMMFs"),
]

RWA_PART_CHILDREN: list[tuple[str, str]] = [
    ("rwa-participants-networks.html", "Networks"),
    ("rwa-participants-platforms.html", "Platforms"),
    ("rwa-participants-asset-managers.html", "Asset Managers"),
]

NAV_BY_FILE: dict[str, str | None] = {
    "index.html": None,
    "all-articles.html": "news",
    "all-regulatory.html": "news",
    "all-custodian-news.html": "news",
    "etf-news.html": "etf-news.html",
    "etps.html": "etps.html",
    "crypto-prices.html": "crypto-prices.html",
    "rwa-global.html": "rwa-global.html",
    "rwa-explore-asset-type.html": "rwa-explore-asset-type.html",
    "rwa-explore-market-participant.html": "rwa-explore-market-participant.html",
    "rwa-stablecoins.html": "rwa-stablecoins.html",
    "rwa-us-treasuries.html": "rwa-us-treasuries.html",
    "rwa-tokenized-mmf.html": "rwa-tokenized-mmf.html",
    "rwa-tokenized-stocks.html": "rwa-tokenized-stocks.html",
    "rwa-participants-networks.html": "rwa-participants-networks.html",
    "rwa-participants-platforms.html": "rwa-participants-platforms.html",
    "rwa-participants-asset-managers.html": "rwa-participants-asset-managers.html",
}


def _ia(active: str | None, href: str) -> str:
    return ' class="is-active"' if active == href else ""


def _flyout_item(
    parent_href: str,
    parent_label: str,
    children: list[tuple[str, str]],
    active: str | None,
    *,
    aria_label: str,
) -> str:
    child_hrefs = {href for href, _ in children}
    parent_active = active == parent_href or active in child_hrefs
    parent_cls = (
        "site-nav__parent-link is-active"
        if parent_active
        else "site-nav__parent-link"
    )
    nested = "\n".join(
        f'                  <li><a href="{href}"{_ia(active, href)}>{label}</a></li>'
        for href, label in children
    )
    return f"""              <li class="site-nav__item site-nav__item--flyout">
                <a href="{parent_href}" class="{parent_cls}">{parent_label}</a>
                <ul class="site-nav__sub site-nav__sub--nested" aria-label="{aria_label}">
{nested}
                </ul>
              </li>"""


def make_nav(active: str | None = None) -> str:
    home_ia = ' class="is-active"' if active is None else ""
    news_ia = ' class="is-active"' if active == "news" else ""
    crypto_ia = _ia(active, "crypto-prices.html")
    mo_ia = _ia(active, "rwa-global.html")

    assets_flyout = _flyout_item(
        "rwa-explore-asset-type.html",
        "RWA · Assets",
        RWA_ASSET_CHILDREN,
        active,
        aria_label="RWA asset pages",
    )
    part_flyout = _flyout_item(
        "rwa-explore-market-participant.html",
        "RWA · Participants",
        RWA_PART_CHILDREN,
        active,
        aria_label="RWA participant pages",
    )

    return f"""
        <nav class="site-nav" aria-label="Primary">
          <a href="index.html"{home_ia}>Home</a>
          <a href="index.html#section-news"{news_ia}>News Hub</a>
          <div class="site-nav__dropdown">
            <span class="site-nav__trigger">RWA Market</span>
            <ul class="site-nav__sub">
              <li><a href="rwa-global.html"{mo_ia}>Market Overview</a></li>
{assets_flyout}
{part_flyout}
            </ul>
          </div>
          <div class="site-nav__dropdown">
            <span class="site-nav__trigger">U.S. ETPs</span>
            <ul class="site-nav__sub">
              <li><a href="etps.html"{_ia(active, "etps.html")}>U.S. ETP Overview</a></li>
              <li><a href="etf-news.html"{_ia(active, "etf-news.html")}>ETF/ETP News</a></li>
            </ul>
          </div>
          <a href="crypto-prices.html"{crypto_ia}>Crypto Prices</a>
        </nav>"""


def main() -> None:
    static = _REPO / "static_home"
    pat = re.compile(r'\s*<nav\s+class="site-nav"[^>]*>[\s\S]*?</nav>', re.I)
    for fname, active in NAV_BY_FILE.items():
        path = static / fname
        if not path.is_file():
            print("skip missing:", path)
            continue
        text = path.read_text(encoding="utf-8")
        new_nav = make_nav(active)
        text2, n = pat.subn(new_nav, text, count=1)
        if n != 1:
            print("WARN: nav replace count", n, path)
            sys.exit(1)
        path.write_text(text2, encoding="utf-8")
        print("ok", fname)


if __name__ == "__main__":
    main()
