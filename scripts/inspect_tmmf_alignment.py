"""Measure TMMF back pill vs main card left alignment."""
from __future__ import annotations

import json
import sys

from playwright.sync_api import sync_playwright

INSPECT_JS = """
() => {
  function left(el) {
    return el ? Math.round(el.getBoundingClientRect().left) : null;
  }
  var phantoms = [];
  document.querySelectorAll("*").forEach(function (el) {
    var cs = getComputedStyle(el);
    var br = parseFloat(cs.borderTopLeftRadius) || 0;
    var r = el.getBoundingClientRect();
    var bw = parseFloat(cs.borderTopWidth) || 0;
    var text = (el.textContent || "").replace(/\\s+/g, " ").trim();
    if (r.top > 50 && r.top < 130 && r.width > 500 && (br >= 100 || bw >= 0.5) && r.height < 40) {
      phantoms.push({
        tag: el.tagName.toLowerCase(),
        cls: (el.className || "").toString().slice(0, 100),
        text: text.slice(0, 40),
        l: Math.round(r.left),
        w: Math.round(r.width),
        h: Math.round(r.height),
        t: Math.round(r.top),
        border: cs.border,
        br: cs.borderRadius,
      });
    }
  });
  return {
    backLeft: left(document.querySelector(".tmmf-st-back-pill")),
    backWrapLeft: left(document.querySelector(".tmmf-st-back-wrap")),
    cardLeft: left(document.querySelector(".streamlit-tmmf-server-host .inner-rich-zone.zone--tmmf")),
    shellLeft: left(document.querySelector(".streamlit-tmmf-server-host .page-shell")),
    hostLeft: left(document.querySelector(".streamlit-tmmf-server-host")),
    deltaBackToCard: left(document.querySelector(".tmmf-st-back-pill")) - left(document.querySelector(".streamlit-tmmf-server-host .inner-rich-zone.zone--tmmf")),
    phantoms: phantoms,
  };
}
"""


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else "8773"
    url = f"http://localhost:{port}/RWA_Tokenized_MMF"
    with sync_playwright() as p:
        page = p.chromium.launch(headless=True).new_page(viewport={"width": 1400, "height": 900})
        page.goto(url, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(10000)
        print(json.dumps(page.evaluate(INSPECT_JS), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
