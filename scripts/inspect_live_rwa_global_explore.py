"""Inspect live RWA Global Market page explore markup in Streamlit iframe."""
from __future__ import annotations

import json
import sys

from playwright.sync_api import sync_playwright

CHECK_JS = r"""
() => {
  var out = {
    marker: (document.querySelector(".streamlit-subpage-active") || {}).className || "",
    bodyIframes: [],
  };
  document.querySelectorAll("iframe").forEach(function (frame, i) {
    var srcdoc = frame.getAttribute("srcdoc") || "";
    var info = {
      i: i,
      srcdocLen: srcdoc.length,
      height: frame.getAttribute("height"),
      hasCompactHtml: srcdoc.indexOf('<nav class="home-explore-compact"') >= 0,
      hasLegacyRowHtml: srcdoc.indexOf('<section class="rwa-explore-row"') >= 0,
      hasLegacyCardHtml: srcdoc.indexOf('<div class="rwa-explore-card"') >= 0,
      buildTag: (srcdoc.match(/rwa-global-build-v(\d+)/) || [])[0] || "",
      canvasVer: (srcdoc.match(/rwa-global-gh-canvas-override-v(\d+)/) || [])[0] || "",
      cssVer: (srcdoc.match(/rwa-global-iframe-css-v(\d+)/) || [])[0] || "",
    };
    if (info.hasCompactHtml || info.hasLegacyRowHtml || srcdoc.indexOf("js-rwa-global-explore") >= 0) {
      var m = srcdoc.match(/<div id="js-rwa-global-explore">([\s\S]{0,400}?)<\/div>/);
      info.exploreSnippet = m ? m[1].slice(0, 320) : "";
    }
    out.bodyIframes.push(info);
  });
  return out;
}
"""


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else (
        "https://digitalassetdashboard-3ed9arieeyygjvfdjt9gg6.streamlit.app/RWA_Global_Market_Overview"
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(url, wait_until="domcontentloaded", timeout=180000)
        page.wait_for_timeout(40000)
        app_frame = None
        for frame in page.frames:
            u = frame.url or ""
            if "/~/" in u and "RWA_Global" in u:
                app_frame = frame
                break
        if not app_frame:
            print(json.dumps({"error": "no app frame", "frames": [f.url for f in page.frames]}, indent=2))
            browser.close()
            return 1
        report = app_frame.evaluate(CHECK_JS)
        report["frameUrl"] = app_frame.url
        print(json.dumps(report, indent=2))
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
