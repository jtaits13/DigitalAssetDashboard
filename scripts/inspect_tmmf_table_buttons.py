"""Check TMMF table download/fullscreen buttons on Streamlit."""
from __future__ import annotations

import json
import sys
import time

from playwright.sync_api import sync_playwright

CHECK_JS = """
() => {
  function checkDoc(doc) {
    if (!doc) return null;
    return {
      download: doc.querySelectorAll('[data-table-download-btn="1"]').length,
      fullscreen: doc.querySelectorAll(
        '[data-rwa-fullscreen-btn="1"], .etp-mock-table-meta__expand:not([disabled])'
      ).length,
      fsApi: typeof doc.defaultView.__TABLE_FULLSCREEN !== "undefined",
      dlApi: typeof doc.defaultView.__TABLE_DOWNLOAD !== "undefined",
      booted: !!doc.defaultView.__TMMF_SERVER_TABLE_BOOTED,
      host: !!doc.querySelector(".streamlit-tmmf-server-host"),
      actionAnchors: doc.querySelectorAll(
        "#tmmf-funds-table-actions, #deep-net-table-actions, #deep-plat-table-actions"
      ).length,
    };
  }
  var main = checkDoc(document);
  var stHtml = document.querySelector('[data-testid="stHtml"]');
  var iframe = stHtml && stHtml.querySelector("iframe");
  var iframeDoc = iframe && iframe.contentDocument;
  var iframeReport = checkDoc(iframeDoc);
  return { main: main, iframe: iframeReport, hasStHtmlIframe: !!iframe };
}
"""


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else "8768"
    url = f"http://localhost:{port}/RWA_Tokenized_MMF"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(url, wait_until="domcontentloaded", timeout=120000)
        report = None
        for _ in range(30):
            report = page.evaluate(CHECK_JS)
            main = report.get("main") or {}
            iframe = report.get("iframe") or {}
            dl = max(main.get("download", 0), iframe.get("download", 0))
            fs = max(main.get("fullscreen", 0), iframe.get("fullscreen", 0))
            if dl > 0 or fs > 0:
                break
            time.sleep(2)
        report = report or page.evaluate(CHECK_JS)
        report["url"] = page.url
        print(json.dumps(report, indent=2))
        browser.close()
    main = (report or {}).get("main") or report or {}
    iframe = (report or {}).get("iframe") or {}
    dl = max(main.get("download", 0), iframe.get("download", 0))
    fs = max(main.get("fullscreen", 0), iframe.get("fullscreen", 0))
    ok = dl >= 3 and fs >= 3
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
