"""Click TMMF full-screen button and verify host modal opens."""
from __future__ import annotations

import json
import sys
import time

from playwright.sync_api import sync_playwright


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else "8772"
    url = f"http://localhost:{port}/RWA_Tokenized_MMF"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(url, wait_until="domcontentloaded", timeout=120000)
        for _ in range(40):
            ready = page.evaluate(
                """() => !!document.querySelector('.etp-mock-table-meta__expand')
                && typeof window.__jpmOpenTableFullscreenHost === 'function'"""
            )
            if ready:
                break
            time.sleep(0.5)
        page.locator(".etp-mock-table-meta__expand").first.click()
        time.sleep(0.5)
        report = page.evaluate(
            """() => ({
              modalVisible: (() => {
                var m = document.getElementById('js-table-fullscreen-streamlit-host');
                return !!(m && !m.hidden);
              })(),
              modalTitle: (document.getElementById('js-table-fullscreen-streamlit-title') || {}).textContent || '',
              expandButtons: document.querySelectorAll('.etp-mock-table-meta__expand').length,
              firstExpandText: (document.querySelector('.etp-mock-table-meta__expand span') || {}).textContent || ''
            })"""
        )
        print(json.dumps(report, indent=2))
        browser.close()
    return 0 if report.get("modalVisible") and report.get("expandButtons", 0) >= 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
