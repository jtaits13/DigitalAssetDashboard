"""Inspect TMMF back-link DOM on local Streamlit (debug phantom blue pill)."""
from __future__ import annotations

import json
import sys

from playwright.sync_api import sync_playwright

INSPECT_JS = """
() => {
  function describe(el) {
    if (!el) return null;
    var cs = getComputedStyle(el);
    var r = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(),
      id: el.id || "",
      classes: el.className || "",
      text: (el.textContent || "").replace(/\\s+/g, " ").trim().slice(0, 120),
      href: (el.getAttribute && el.getAttribute("href")) || "",
      display: cs.display,
      width: Math.round(r.width),
      height: Math.round(r.height),
      top: Math.round(r.top),
      border: cs.border,
      borderRadius: cs.borderRadius,
      padding: cs.padding,
    };
  }
  var out = {
    url: location.href,
    anchors: [],
    backRows: [],
    stHtmlBlocks: [],
    containers: [],
    pillLike: [],
  };
  document.querySelectorAll("a.tmmf-st-back-pill, a.tmmf-server-back-anchor, a.back-link--below-header").forEach(function (a) {
    out.anchors.push(describe(a));
  });
  document.querySelectorAll(".tmmf-st-back-wrap, .page-back-below-header, .tmmf-server-back-row").forEach(function (el) {
      out.backRows.push(describe(el));
    });
  document.querySelectorAll('[data-testid="stHtml"]').forEach(function (stHtml, idx) {
    var direct = Array.from(stHtml.children).map(function (child) {
      var d = describe(child);
      d.directChildren = Array.from(child.children).slice(0, 6).map(describe);
      return d;
    });
    out.stHtmlBlocks.push({
      idx: idx,
      self: describe(stHtml),
      directChildren: direct,
    });
  });
  document.querySelectorAll("*").forEach(function (el) {
    if (el.children.length > 5) return;
    var cs = getComputedStyle(el);
    var br = parseFloat(cs.borderRadius) || 0;
    if (br < 100) return;
    var r = el.getBoundingClientRect();
    if (r.width < 200 || r.height < 8 || r.height > 80) return;
    if (r.top > 250 || r.top < 40) return;
    if (cs.display === "none" || cs.visibility === "hidden") return;
    var d = describe(el);
    d.borderWidth = cs.borderWidth;
    out.pillLike.push(d);
  });
  document.querySelectorAll('[data-testid="stElementContainer"]').forEach(function (c, idx) {
    var hasHost = !!c.querySelector(".streamlit-tmmf-server-host");
    var hasBack = !!c.querySelector(".page-back-below-header");
    if (!hasHost && !hasBack) return;
    var d = describe(c);
    out.containers.push({
      idx: idx,
      hasHost: hasHost,
      hasBack: hasBack,
      hasHtml: !!c.querySelector('[data-testid="stHtml"]'),
      hasMd: !!c.querySelector('[data-testid="stMarkdownContainer"]'),
      rect: { width: d.width, height: d.height, top: d.top },
      border: d.border,
      display: d.display,
    });
  });
  return out;
}
"""


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else "8765"
    url = f"http://localhost:{port}/RWA_Tokenized_MMF"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(url, wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(8000)
        report = page.evaluate(INSPECT_JS)
        print(json.dumps(report, indent=2))
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
