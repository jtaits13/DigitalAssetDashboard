"""One-off / maintenance: rewrite static_home/*.html primary nav to dropdown version. Run from repo root."""
from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent


def _ia(on: bool) -> str:
    return ' class="is-active"' if on else ""


def make_nav(
    *,
    home: bool = False,
    news: bool = False,
    etf_news: bool = False,
    etf_data: bool = False,
    mo: bool = False,
    rwa_assets: bool = False,
    rwa_part: bool = False,
) -> str:
    # Leading newline: regex consumes ``\\s*`` before ``<nav``, so this restores the line break after ``</a>``.
    return f"""
        <nav class="site-nav" aria-label="Primary">
          <a href="index.html"{_ia(home)}>Home</a>
          <a href="index.html#section-news"{_ia(news)}>Digital Asset News</a>
          <div class="site-nav__dropdown">
            <span class="site-nav__trigger">U.S. ETPs</span>
            <ul class="site-nav__sub">
              <li><a href="etf-news.html"{_ia(etf_news)}>ETF News</a></li>
              <li><a href="etps.html"{_ia(etf_data)}>ETF Data</a></li>
            </ul>
          </div>
          <div class="site-nav__dropdown">
            <span class="site-nav__trigger">RWA Market</span>
            <ul class="site-nav__sub">
              <li><a href="rwa-global.html"{_ia(mo)}>Market Overview</a></li>
              <li><a href="rwa-explore-asset-type.html"{_ia(rwa_assets)}>RWA · Assets</a></li>
              <li><a href="rwa-explore-market-participant.html"{_ia(rwa_part)}>RWA · Participants</a></li>
            </ul>
          </div>
        </nav>"""


NAV_BY_FILE: dict[str, dict[str, bool]] = {
    "index.html": {"home": True},
    "etf-news.html": {"etf_news": True},
    "etps.html": {"etf_data": True},
    "rwa-global.html": {"mo": True},
    "rwa-explore-asset-type.html": {"rwa_assets": True},
    "rwa-explore-market-participant.html": {"rwa_part": True},
    "rwa-stablecoins.html": {"rwa_assets": True},
    "rwa-us-treasuries.html": {"rwa_assets": True},
    "rwa-tokenized-stocks.html": {"rwa_assets": True},
    "rwa-participants-networks.html": {"rwa_part": True},
    "rwa-participants-platforms.html": {"rwa_part": True},
    "rwa-participants-asset-managers.html": {"rwa_part": True},
}


def main() -> None:
    static = _REPO / "static_home"
    # Consume leading whitespace so we do not double the indent before ``<nav>``.
    pat = re.compile(r'\s*<nav\s+class="site-nav"[^>]*>[\s\S]*?</nav>', re.I)
    for fname, flags in NAV_BY_FILE.items():
        path = static / fname
        if not path.is_file():
            print("skip missing:", path)
            continue
        text = path.read_text(encoding="utf-8")
        new_nav = make_nav(**flags)
        text2, n = pat.subn(new_nav, text, count=1)
        if n != 1:
            print("WARN: nav replace count", n, path)
            sys.exit(1)
        path.write_text(text2, encoding="utf-8")
        print("ok", fname)


if __name__ == "__main__":
    main()
