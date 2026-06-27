"""Inspect pill-shaped elements on live Streamlit TMMF page (shadow-DOM aware)."""
from __future__ import annotations

import json
import sys

from playwright.sync_api import sync_playwright

INSPECT_JS = r"""
() => {
  function allRoots() {
    var roots = [document];
    document.querySelectorAll("*").forEach(function (el) {
      if (el.shadowRoot) roots.push(el.shadowRoot);
    });
    return roots;
  }
  function q(sel) {
    var out = [];
    allRoots().forEach(function (root) {
      root.querySelectorAll(sel).forEach(function (el) {
        out.push(el);
      });
    });
    return out;
  }
  function d(el) {
    var cs = getComputedStyle(el);
    var r = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(),
      classes: (el.className || "").slice(0, 120),
      text: (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 80),
      w: Math.round(r.width),
      h: Math.round(r.height),
      top: Math.round(r.top),
      left: Math.round(r.left),
      br: cs.borderRadius,
      border: cs.border,
      display: cs.display,
    };
  }
  var backs = q(
    ".tmmf-st-back-pill, .page-back-below-header, p.back-link.back-link--below-header"
  );
  var pills = [];
  q("a, div, p, span").forEach(function (el) {
    var info = d(el);
    if (info.top < 280 && info.top > 35 && info.w > 280 && info.h > 2 && info.h < 60) {
      var brNum = parseFloat(info.br) || 0;
      if (info.br.indexOf("999") >= 0 || brNum > 40 || /solid/.test(info.border)) {
        pills.push(info);
      }
    }
  });
  return {
    backs: backs.map(d),
    pills: pills,
    hostCount: q(".streamlit-tmmf-server-host").length,
    serverPage: q(".streamlit-tmmf-server-page").length,
    stHtmlCount: q('[data-testid="stHtml"]').length,
  };
}
"""


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else (
        "https://digitalassetdashboard-3ed9arieeyygjvfdjt9gg6.streamlit.app/RWA_Tokenized_MMF"
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(url, wait_until="networkidle", timeout=180000)
        page.locator("text=Tokenized Money Market Funds").first.wait_for(timeout=180000)
        page.wait_for_timeout(4000)
        report = page.evaluate(INSPECT_JS)
        page.screenshot(path="scripts/live_tmmf_inspect3.png", full_page=False)
        print(json.dumps(report, indent=2))
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
