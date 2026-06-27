"""Inspect TMMF back-link DOM on local Streamlit (debug phantom blue pill)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

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
    var hasStBack = !!c.querySelector(".tmmf-st-back-wrap");
    if (!hasHost && !hasBack && !hasStBack) return;
    var d = describe(c);
    out.containers.push({
      idx: idx,
      hasHost: hasHost,
      hasBack: hasBack,
      hasStBack: hasStBack,
      hasHtml: !!c.querySelector('[data-testid="stHtml"]'),
      hasMd: !!c.querySelector('[data-testid="stMarkdownContainer"]'),
      rect: { width: d.width, height: d.height, top: d.top },
      border: d.border,
      display: d.display,
    });
  });
  out.emptyPhantomPills = 0;
  document.querySelectorAll("a").forEach(function (a) {
    var cs = getComputedStyle(a);
    var br = parseFloat(cs.borderRadius) || 0;
    var r = a.getBoundingClientRect();
    var text = (a.textContent || "").replace(/\\s+/g, " ").trim();
    if (br >= 100 && r.width > 200 && r.height > 8 && r.height < 80 && r.top < 250 && cs.display !== "none" && !text) {
      out.emptyPhantomPills++;
      out.pillLike.push(describe(a));
    }
  });
  out.marker = {
    streamlitTmmfServerPage: !!document.querySelector(".streamlit-tmmf-server-page"),
    tmmfStBackWrap: document.querySelectorAll(".tmmf-st-back-wrap").length,
    pageBackBelowHeader: document.querySelectorAll(".page-back-below-header").length,
  };
  return out;
}
"""


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else "8765"
    if arg.startswith("http://") or arg.startswith("https://"):
        url = arg.rstrip("/")
        if not url.endswith("RWA_Tokenized_MMF"):
            url = f"{url}/RWA_Tokenized_MMF"
    else:
        url = f"http://localhost:{arg}/RWA_Tokenized_MMF"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(url, wait_until="domcontentloaded", timeout=120000)
        try:
            page.wait_for_selector(".stApp, [data-testid='stAppViewContainer']", timeout=120000)
        except Exception:
            pass
        for _ in range(24):
            ready = page.evaluate(
                """() => !!document.querySelector('.streamlit-tmmf-server-page')
                || !!document.querySelector('.tmmf-st-back-wrap')
                || !!document.querySelector('.streamlit-tmmf-server-host')
                || !!document.querySelector('[data-testid=\"stHtml\"]')"""
            )
            if ready:
                break
            page.wait_for_timeout(5000)
        page.wait_for_timeout(3000)
        report = page.evaluate(INSPECT_JS)
        report["finalUrl"] = page.url
        report["title"] = page.title()
        body_text = page.evaluate(
            """() => (document.body && document.body.innerText || "").replace(/\\s+/g, " ").trim().slice(0, 280)"""
        )
        report["bodyTextPreview"] = body_text
        report["authWall"] = (
            "sign in" in body_text.lower()
            or "do not have access" in body_text.lower()
            or "not found" in (page.title() or "").lower()
        )
        report["pageLoaded"] = bool(
            report.get("marker", {}).get("streamlitTmmfServerPage")
            or report.get("marker", {}).get("tmmfStBackWrap")
        )
        if url.startswith("https://"):
            shot = Path(__file__).resolve().parent / "live_tmmf_inspect.png"
            page.screenshot(path=str(shot), full_page=True)
            report["screenshot"] = str(shot)
        print(json.dumps(report, indent=2))
        if report["authWall"] and not report["pageLoaded"]:
            print(
                "\nAUTH WALL: headless browser cannot reach TMMF DOM. "
                "Make the Streamlit app public temporarily or sign in manually, then re-run.",
                file=sys.stderr,
            )
            browser.close()
            return 2
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
