"""Find background seam Y on live RWA Global Market page (host + iframe)."""
from __future__ import annotations

import json
import sys

from playwright.sync_api import sync_playwright

SCAN_JS = r"""
() => {
  function sample(doc, win, x, y) {
    var el = doc.elementFromPoint(x, y);
    if (!el) return null;
    var cur = el;
    var chain = [];
    while (cur && cur !== doc.documentElement && chain.length < 10) {
      var cs = win.getComputedStyle(cur);
      chain.push({
        tag: cur.tagName.toLowerCase(),
        id: cur.id || "",
        cls: (cur.className && typeof cur.className === "string" ? cur.className : "").slice(0, 72),
        bg: cs.backgroundColor,
        img: cs.backgroundImage !== "none",
        shadow: cs.boxShadow !== "none",
        borderTop: cs.borderTopWidth + " " + cs.borderTopColor,
      });
      if (cs.backgroundColor && cs.backgroundColor !== "rgba(0, 0, 0, 0)") break;
      cur = cur.parentElement;
    }
    return { top: chain[0], paint: chain[chain.length - 1] || null };
  }

  var bodyFrame = null;
  document.querySelectorAll("iframe").forEach(function (f) {
    try {
      var b = f.contentDocument && f.contentDocument.body;
      if (b && b.classList.contains("page-rwa-global-iframe")) bodyFrame = f;
    } catch (e) {}
  });
  if (!bodyFrame) return { error: "no rwa global body frame" };

  var idoc = bodyFrame.contentDocument;
  var iwin = idoc.defaultView;
  var fr = bodyFrame.getBoundingClientRect();
  var explore = idoc.querySelector("#js-rwa-global-explore");
  var insights = idoc.querySelector("#js-rwa-global-insights");
  var zone = idoc.querySelector(".inner-rich-zone.zone--rwa");
  var zoneBody = idoc.querySelector(".inner-rich-zone__body");
  function rect(el) {
    if (!el) return null;
    var r = el.getBoundingClientRect();
    return { top: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height) };
  }
  function cs(el) {
    if (!el) return null;
    var s = iwin.getComputedStyle(el);
    return {
      bg: s.backgroundColor,
      img: s.backgroundImage.slice(0, 90),
      shadow: s.boxShadow.slice(0, 90),
      marginTop: s.marginTop,
      marginBottom: s.marginBottom,
    };
  }
  var transitions = [];
  var prev = null;
  for (var y = Math.max(350, Math.round(fr.top)); y <= Math.min(window.innerHeight - 20, Math.round(fr.bottom)); y += 4) {
    var hostLeft = sample(document, window, 24, y);
    var hostMid = sample(document, window, 700, y);
    var iframeMidLy = y - fr.top;
    var iframeMid = iframeMidLy >= 0 && iframeMidLy <= fr.height ? sample(idoc, iwin, 700, iframeMidLy) : null;
    var key = JSON.stringify({
      hl: hostLeft && hostLeft.paint ? hostLeft.paint.bg : null,
      hm: hostMid && hostMid.paint ? hostMid.paint.bg : null,
      im: iframeMid && iframeMid.paint ? iframeMid.paint.bg : null,
      ht: hostLeft && hostLeft.top ? hostLeft.top.cls : null,
    });
    if (prev && prev.key !== key) {
      transitions.push({ y: y, before: prev.key, after: key, hostLeftTop: hostLeft && hostLeft.top });
    }
    prev = { key: key };
  }
  return {
    iframe: { top: Math.round(fr.top), bottom: Math.round(fr.bottom), h: Math.round(fr.height) },
    explore: rect(explore),
    insights: rect(insights),
    insightsPanel: cs(idoc.querySelector(".etp-mock-insights__panel")),
    zone: cs(zone),
    zoneBody: cs(zoneBody),
    compact: cs(idoc.querySelector(".home-explore-compact")),
    transitions: transitions.slice(0, 16),
  };
}
"""


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else (
        "https://digitalassetdashboard-3ed9arieeyygjvfdjt9gg6.streamlit.app/RWA_Global_Market_Overview"
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 1500})
        page.goto(url, wait_until="domcontentloaded", timeout=180000)
        page.wait_for_timeout(45000)
        result = None
        for frame in page.frames:
            if "/~/" not in (frame.url or ""):
                continue
            try:
                result = frame.evaluate(SCAN_JS)
                result["frameUrl"] = frame.url
                break
            except Exception:
                pass
        print(json.dumps(result or {"error": "no frame"}, indent=2))
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
