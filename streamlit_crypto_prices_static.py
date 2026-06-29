"""Streamlit Crypto Prices full page — server-rendered iframe (parity with ``crypto-prices.html``)."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from streamlit_site_parity import DEEP_MARKET_TABLE_HEIGHT_VERSION
from streamlit_tmmf_static import (
    _STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH,
    _TMMF_SERVER_INLINE_HOST_MODAL_JS,
    _json_for_script,
    _read_js_files,
)

_REPO = Path(__file__).resolve().parent
_STATIC = _REPO / "static_home"
_DATA = _STATIC / "data"

_CRYPTO_IFRAME_CSS_VERSION = "11"
CRYPTO_CANVAS_OVERRIDE_VERSION = "8"
CRYPTO_TABLE_PANEL_VERSION = "6"

CRYPTO_GH_PAGE_WASH = "#f3f7fb"
CRYPTO_GH_ZONE_SOFT = "#f1f4f7"

_CRYPTO_JS_DEPS = (
    "static-base.js",
    "table-fullscreen.js",
    "table-download.js",
    "kpi-hints.js",
    "data-freshness.js",
    "page-methodology.js",
    "snapshot-kpi-shared.js",
    "etp-kpi-shared.js",
    "crypto-kpi-shared.js",
)
_CRYPTO_JS_BOOT = ("crypto-page.js",)

_CRYPTO_PATCH_LOAD_JSON_JS = """
(function () {
  var load = window.loadJson;
  if (typeof load !== "function") return;
  function loadJsonWithTimeout(name, ms) {
    var timeoutMs = ms == null ? 14000 : ms;
    return new Promise(function (resolve, reject) {
      var done = false;
      var timer = setTimeout(function () {
        if (done) return;
        done = true;
        reject(new Error("Timed out loading " + name));
      }, timeoutMs);
      load(name)
        .then(function (data) {
          if (done) return;
          done = true;
          clearTimeout(timer);
          resolve(data);
        })
        .catch(function (err) {
          if (done) return;
          done = true;
          clearTimeout(timer);
          reject(err);
        });
    });
  }
  if (window.__DATA_FRESHNESS) {
    window.__DATA_FRESHNESS.loadJsonWithTimeout = loadJsonWithTimeout;
  }
  window.loadJsonWithTimeout = loadJsonWithTimeout;
})();
"""

_CRYPTO_SERVER_TABLE_WIRE_JS = """
(function () {
  function wireCryptoTable() {
    var fs = window.__TABLE_FULLSCREEN;
    if (!fs || !fs.attachTableFullscreenButton) return;
    var tbody = document.getElementById("js-crypto-tbody");
    if (!tbody) return;
    var wrap = tbody.closest(".table-wrap");
    var table = wrap && wrap.querySelector("table");
    if (!wrap || !table) return;
    delete wrap._rwaFullscreenBound;
    delete wrap._rwaDownloadBound;
    var exportData =
      window.__CRYPTO_SERVER_EXPORTS && window.__CRYPTO_SERVER_EXPORTS["crypto-table"];
    fs.attachTableFullscreenButton(wrap, table, {
      title: "Crypto prices table",
      filename: "crypto-prices",
      sheetName: "Crypto Prices",
      downloadPlacement: "title-row",
      downloadAnchor: document.getElementById("js-crypto-table-actions"),
      actionRow: document.getElementById("js-crypto-table-fullscreen"),
      getExportData: exportData
        ? function () {
            return exportData;
          }
        : undefined,
    });
    var btn =
      (document.getElementById("js-crypto-table-fullscreen") &&
        document.getElementById("js-crypto-table-fullscreen").querySelector(
          '[data-rwa-fullscreen-btn="1"]'
        )) ||
      null;
    if (btn && fs.openTableModal) {
      btn.onclick = function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        fs.openTableModal(table, { title: "Crypto prices table" });
      };
    }
  }
  window.__cryptoWireServerTable = wireCryptoTable;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireCryptoTable);
  } else {
    wireCryptoTable();
  }
  setTimeout(wireCryptoTable, 0);
  setTimeout(wireCryptoTable, 400);
  setTimeout(wireCryptoTable, 1200);
})();
"""

_CRYPTO_MEASURE_HEIGHT_JS = """
function measureCryptoContentHeight() {
  if (window.__TMMF_MODAL_OPEN) return null;
  var scrollY = window.scrollY || document.documentElement.scrollTop || 0;
  var nodes = [
    document.querySelector(".page-back-below-header"),
    document.querySelector("main.page-shell.etp-mock-shell"),
    document.getElementById("js-crypto-cap-mix"),
    document.getElementById("crypto-market-cap-chart"),
    document.querySelector(".etp-mock-table-block"),
    document.getElementById("js-crypto-generated"),
  ];
  var maxBottom = 0;
  nodes.forEach(function (el) {
    if (!el) return;
    var rect = el.getBoundingClientRect();
    if (rect.height <= 0 && el.id === "js-crypto-generated" && !(el.textContent || "").trim()) {
      return;
    }
    maxBottom = Math.max(maxBottom, rect.bottom + scrollY);
  });
  if (!maxBottom) {
    var main = document.querySelector("main.page-shell.etp-mock-shell");
    if (main) {
      maxBottom = main.getBoundingClientRect().bottom + scrollY;
    }
  }
  if (!maxBottom) return null;
  return Math.ceil(maxBottom + 6);
}
"""

_CRYPTO_IFRAME_BACK_LINK = """
<div class="page-back-below-header">
  <p class="back-link back-link--below-header">
    <a class="crypto-server-back-anchor" data-deep-back="explore" href="{back_href}">{back_label_html}</a>
  </p>
</div>
"""


def crypto_github_canvas_override_css(*, version: str = CRYPTO_CANVAS_OVERRIDE_VERSION) -> str:
    from streamlit_site_parity import (
        deep_iframe_kpi_flatten_css,
        deep_iframe_table_height_lock_css,
        deep_iframe_table_panel_css,
    )

    wash = CRYPTO_GH_PAGE_WASH
    soft = CRYPTO_GH_ZONE_SOFT
    scope = "body.page-crypto-iframe"
    height_lock = deep_iframe_table_height_lock_css(scope=scope)
    return f"""
/* Crypto GitHub Pages canvas override v{version} */
html, {scope}.site-experience,
{scope}.site-experience.page-inner--rich,
{scope}.mock-crypto-inner.site-experience {{
  background: {wash} !important;
  background-color: {wash} !important;
  background-image: none !important;
}}
{scope} .page-shell.etp-mock-shell {{
  background: transparent !important;
  background-image: none !important;
}}
{scope} .inner-rich-zone.zone--crypto,
{scope} .inner-rich-zone.zone--crypto .inner-rich-zone__body,
{scope} .etp-mock-zone.inner-rich-zone.zone--crypto,
{scope} .etp-mock-zone .inner-rich-zone__body {{
  background: {soft} !important;
  background-color: {soft} !important;
  background-image: none !important;
}}
{scope} .inner-rich-block,
{scope} .etp-mock-key-obs-block,
{scope}.page-inner--rich .inner-rich-zone .etp-mock-key-obs-block,
{scope}.page-inner--rich .inner-rich-zone.zone--crypto .inner-rich-block,
{scope} .etp-mock-key-obs-block .crypto-story-callout,
{scope}.page-inner--rich .inner-rich-zone .etp-mock-key-obs-block .crypto-story-callout,
{scope} #js-crypto-key-obs .crypto-story-callout,
{scope} .etp-mock-key-obs-block .review-note.ko-disclaimer,
{scope} #js-crypto-key-obs .review-note.ko-disclaimer,
{scope} .etp-mock-insights__panel,
{scope} .etp-mock-dash__panel,
{scope} .rwa-kpi-row--home-grid .rwa-kpi-cell,
{scope} .etp-mock-table-block:not(.etp-mock-table-block--funds) {{
  background: #fff !important;
  background-color: #fff !important;
  background-image: none !important;
  box-shadow: none !important;
}}
{scope} .etp-mock-key-obs-block .crypto-story-callout__note,
{scope} #js-crypto-key-obs .crypto-story-callout__note {{
  background: rgb(72 90 110 / 0.06) !important;
  background-image: none !important;
}}
""" + deep_iframe_kpi_flatten_css(scope=scope, zone="crypto") + deep_iframe_table_panel_css(scope=scope) + height_lock


def crypto_iframe_canvas_override_js(*, version: str = CRYPTO_CANVAS_OVERRIDE_VERSION) -> str:
    from streamlit_site_parity import deep_iframe_table_panel_paint_js

    wash = CRYPTO_GH_PAGE_WASH
    soft = CRYPTO_GH_ZONE_SOFT
    table_paint_js = deep_iframe_table_panel_paint_js()
    return f"""
<script id="crypto-gh-canvas-override-js-v{version}">
(function () {{
  var WASH = "{wash}";
  var SOFT = "{soft}";
  var WHITE = "#ffffff";
  function setBg(el, color) {{
    if (!el) return;
    el.style.setProperty("background", color, "important");
    el.style.setProperty("background-color", color, "important");
    el.style.setProperty("background-image", "none", "important");
  }}
{table_paint_js}
  function paint() {{
    setBg(document.documentElement, WASH);
    setBg(document.body, WASH);
    var main = document.querySelector("main.page-shell.etp-mock-shell");
    if (main) {{
      main.style.setProperty("background", "transparent", "important");
      main.style.setProperty("background-image", "none", "important");
    }}
    document.querySelectorAll(
      ".inner-rich-zone.zone--crypto, .inner-rich-zone.zone--crypto .inner-rich-zone__body, .etp-mock-zone.inner-rich-zone.zone--crypto, .etp-mock-zone .inner-rich-zone__body"
    ).forEach(function (el) {{ setBg(el, SOFT); }});
    document.querySelectorAll(
      ".inner-rich-block, .etp-mock-key-obs-block, .crypto-story-callout, .review-note.ko-disclaimer, .etp-mock-insights__panel, .etp-mock-dash__panel, .rwa-kpi-row--home-grid .rwa-kpi-cell, .etp-mock-table-block:not(.etp-mock-table-block--funds)"
    ).forEach(function (el) {{
      setBg(el, WHITE);
      el.style.setProperty("box-shadow", "none", "important");
    }});
    document.querySelectorAll(".rwa-kpi-panel-static").forEach(function (el) {{
      el.style.setProperty("background", "transparent", "important");
      el.style.setProperty("background-image", "none", "important");
      el.style.setProperty("border", "none", "important");
      el.style.setProperty("box-shadow", "none", "important");
    }});
    document.querySelectorAll(".crypto-story-callout__note").forEach(function (el) {{
      setBg(el, "rgb(72 90 110 / 0.06)");
    }});
    paintMarketTablePanels();
  }}
  paint();
  window.addEventListener("load", paint);
  [50, 200, 800, 2000, 5000].forEach(function (ms) {{ setTimeout(paint, ms); }});
}})();
</script>
"""


def crypto_host_canvas_override_css(*, version: str = CRYPTO_CANVAS_OVERRIDE_VERSION) -> str:
    wash = CRYPTO_GH_PAGE_WASH
    return f"""
<style id="crypto-gh-host-canvas-override-v{version}">
.stApp:has(.streamlit-crypto-iframe-page),
.withScreencast:has(.streamlit-crypto-iframe-page),
[data-testid="stScreencast"]:has(.streamlit-crypto-iframe-page),
.stApp:has(.streamlit-crypto-iframe-page) [data-testid="stAppViewContainer"],
.stApp:has(.streamlit-crypto-iframe-page) section.main,
.stApp:has(.streamlit-crypto-iframe-page) [data-testid="stMain"],
.stApp:has(.streamlit-crypto-iframe-page) [data-testid="stMainBlockContainer"],
.stApp:has(.streamlit-crypto-iframe-page) .block-container,
.stApp:has(.streamlit-crypto-iframe-page) [data-testid="stVerticalBlock"],
.stApp:has(.streamlit-crypto-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe),
.stApp:has(.streamlit-crypto-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe) [data-testid="stVerticalBlock"],
.stApp:has(.streamlit-crypto-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe) [data-testid="stHtml"],
.stApp:has(.streamlit-crypto-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe) [data-testid="stHtml"] > div {{
  background: {wash} !important;
  background-color: {wash} !important;
  background-image: none !important;
}}
</style>
"""


def crypto_host_canvas_override_js(*, version: str = CRYPTO_CANVAS_OVERRIDE_VERSION) -> str:
    wash = CRYPTO_GH_PAGE_WASH
    return f"""
<script id="crypto-gh-host-canvas-override-js-v{version}">
(function () {{
  var WASH = "{wash}";
  var doc = window.parent && window.parent.document ? window.parent.document : document;
  function paint() {{
    var app = doc.querySelector(".stApp");
    if (!app || !app.querySelector(".streamlit-crypto-iframe-page")) return;
    [
      app,
      app.querySelector('[data-testid="stAppViewContainer"]'),
      app.querySelector("section.main"),
      app.querySelector('[data-testid="stMainBlockContainer"]'),
      app.querySelector(".block-container"),
    ].forEach(function (el) {{
      if (!el) return;
      el.style.setProperty("background", WASH, "important");
      el.style.setProperty("background-color", WASH, "important");
      el.style.setProperty("background-image", "none", "important");
    }});
    doc.querySelectorAll(".withScreencast, [data-testid='stScreencast']").forEach(function (el) {{
      if (!el.querySelector(".streamlit-crypto-iframe-page")) return;
      el.style.setProperty("background", WASH, "important");
      el.style.setProperty("background-image", "none", "important");
    }});
  }}
  paint();
  if (window.parent) window.parent.addEventListener("load", paint);
  [100, 400, 1200, 3000, 6000].forEach(function (ms) {{ setTimeout(paint, ms); }});
}})();
</script>
"""


def inject_crypto_iframe_table_actions(payloads: dict[str, Any]) -> None:
    """Wire download/fullscreen on the Crypto body iframe via host script injection."""
    from streamlit_server_deep_page import build_crypto_server_export_config

    prices = payloads.get("crypto_prices.json") if isinstance(payloads.get("crypto_prices.json"), dict) else {}
    rows = list(prices.get("rows") or [])
    js_libs = _read_js_files(("table-fullscreen.js", "table-download.js"))
    export_json = json.dumps(build_crypto_server_export_config(rows))
    libs_json = json.dumps(js_libs)
    patch_json = json.dumps(_STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH.strip())
    wire_json = json.dumps(_CRYPTO_SERVER_TABLE_WIRE_JS.strip())
    host_modal_json = json.dumps(_TMMF_SERVER_INLINE_HOST_MODAL_JS.strip())
    bootstrap = f"""
<script>
(function () {{
  var win = window.parent;
  var doc = win.document;
  if (win.__jpmCryptoIframeTableHostBound) return;
  win.__jpmCryptoIframeTableHostBound = true;

  function injectIntoInner(innerDoc, text) {{
    var s = innerDoc.createElement("script");
    s.textContent = text;
    innerDoc.body.appendChild(s);
  }}

  function injectHost(text) {{
    var s = doc.createElement("script");
    s.textContent = text;
    doc.body.appendChild(s);
  }}

  function findCryptoInner() {{
    var frames = doc.querySelectorAll("iframe");
    for (var i = 0; i < frames.length; i++) {{
      try {{
        var inner = frames[i].contentDocument;
        if (
          inner &&
          inner.body &&
          inner.body.classList &&
          inner.body.classList.contains("mock-crypto-inner")
        ) {{
          return {{ frame: frames[i], doc: inner, win: inner.defaultView || inner.parentWindow }};
        }}
      }} catch (e) {{}}
    }}
    return null;
  }}

  function ensureHostModal() {{
    if (typeof win.__jpmOpenTableFullscreenHost === "function") return;
    injectHost({host_modal_json});
  }}

  function ensureInnerTableLibs(hit) {{
    if (!hit || !hit.win || !hit.doc) return false;
    if (!hit.win.__TABLE_FULLSCREEN) {{
      injectIntoInner(hit.doc, {libs_json});
      hit.win.__CRYPTO_SERVER_EXPORTS = {export_json};
      injectIntoInner(hit.doc, {patch_json});
      injectIntoInner(hit.doc, {wire_json});
      return true;
    }}
    if (!hit.win.__ST_TMMF_FULLSCREEN_PATCHED) {{
      hit.win.__CRYPTO_SERVER_EXPORTS = {export_json};
      injectIntoInner(hit.doc, {patch_json});
      injectIntoInner(hit.doc, {wire_json});
      return true;
    }}
    if (typeof hit.win.__cryptoWireServerTable === "function") {{
      hit.win.__cryptoWireServerTable();
    }}
    return true;
  }}

  function boot() {{
    if (!doc.querySelector(".streamlit-crypto-iframe-page")) return false;
    ensureHostModal();
    var hit = findCryptoInner();
    if (!hit) return false;
    return ensureInnerTableLibs(hit);
  }}

  if (!boot()) {{
    var tries = 0;
    var timer = win.setInterval(function () {{
      tries += 1;
      if (boot() || tries > 80) win.clearInterval(timer);
    }}, 250);
  }}
  win.addEventListener("load", boot);
  [100, 400, 1200, 3000, 6000, 10000].forEach(function (ms) {{
    win.setTimeout(boot, ms);
  }});
  if (typeof MutationObserver !== "undefined") {{
    var mo = new MutationObserver(boot);
    mo.observe(doc.body, {{ childList: true, subtree: true }});
    win.setTimeout(function () {{ mo.disconnect(); }}, 25000);
  }}
}})();
</script>
"""
    components.html(bootstrap, height=0, width=0)


def inject_crypto_host_canvas_override() -> None:
    """Apply GitHub Pages wash to the Streamlit host shell on the Crypto route."""
    st.markdown(crypto_host_canvas_override_css(), unsafe_allow_html=True)
    components.html(crypto_host_canvas_override_js(), height=0, width=0)


def _static_crypto_payload_fallback(*, error: str = "") -> dict[str, Any]:
    """Last-resort payloads from runtime cache or committed static JSON exports."""
    from crypto_live_cache import bundle_from_static_exports, load_crypto_live_cache

    cached = load_crypto_live_cache(_DATA / "crypto_live_cache.json", static_dir=_DATA)
    if cached:
        out = {
            "crypto_kpis.json": dict(cached.get("kpis") or {}),
            "crypto_prices.json": dict(cached.get("prices") or {}),
            "crypto_market_cap_series.json": dict(cached.get("chart") or {}),
        }
    else:
        out = {}
        for name in ("crypto_kpis.json", "crypto_prices.json", "crypto_market_cap_series.json"):
            path = _DATA / name
            if path.is_file():
                out[name] = json.loads(path.read_text(encoding="utf-8"))
    if not out:
        seeded = bundle_from_static_exports(_DATA)
        if seeded:
            out = {
                "crypto_kpis.json": seeded.get("kpis") or {},
                "crypto_prices.json": seeded.get("prices") or {},
                "crypto_market_cap_series.json": seeded.get("chart") or {},
            }
    if error:
        for key in list(out):
            merged = dict(out[key])
            merged["error"] = error
            merged["stale"] = True
            out[key] = merged
    return out


def load_crypto_prices_iframe_payloads() -> dict[str, Any]:
    """Live crypto page JSON (kpis, prices, chart) matching static export shape."""
    from scripts.export_static_site_data import build_crypto_prices_page_payloads

    pack = build_crypto_prices_page_payloads(
        news_articles=None,
        blurb_cache_path=_DATA / "crypto_about_blurbs_cache.json",
        skip_about_blurbs=True,
        live_cache_path=_DATA / "crypto_live_cache.json",
    )
    return {
        "crypto_kpis.json": pack["kpis"],
        "crypto_prices.json": pack["prices"],
        "crypto_market_cap_series.json": pack["chart"],
    }


def get_crypto_iframe_payloads() -> dict[str, Any]:
    """Static JSON first; live fetch only when committed exports are missing."""
    from streamlit_payload_stale_first import load_static_first_with_live_fallback, mark_payload_map_stale

    return load_static_first_with_live_fallback(
        load_stale=lambda: _static_crypto_payload_fallback() or None,
        load_live_cached=_cached_crypto_prices_iframe_payloads,
        mark_stale=mark_payload_map_stale,
    )


@st.cache_resource(show_spinner=False)
def _cached_iframe_crypto_stylesheet_v10() -> str:
    """Same CSS stack as ``static_home/crypto-prices.html`` (iframe-safe, no mock banners)."""
    from streamlit_site_parity import (
        _iframe_crypto_mock_css,
        deep_iframe_kpi_flatten_css,
        deep_iframe_table_height_lock_css,
        deep_iframe_table_panel_css,
    )

    chunks: list[str] = [
        "@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;780&display=swap');",
    ]
    for rel in ("styles.css",):
        path = _STATIC / rel
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))
    for rel in (
        "css/site-experience.css",
        "css/inner-page-experience.css",
        "css/inner-page-zone-parity.css",
    ):
        path = _STATIC / rel
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))
    for rel in ("mockups/etp-inner-page-mock.css", "mockups/crypto-inner-page-mock.css"):
        path = _STATIC / rel
        if path.is_file():
            chunks.append(_iframe_crypto_mock_css(path.read_text(encoding="utf-8")))
    chunks.append(
        """
html, body.page-crypto-iframe.site-experience {
  margin: 0;
  padding: 0;
  background: var(--wash, #f3f7fb) !important;
  background-image: none !important;
  overflow: hidden;
}
body.page-crypto-iframe.site-experience.page-inner--rich,
body.page-crypto-iframe.mock-crypto-inner.site-experience {
  background: var(--wash, #f3f7fb) !important;
  background-image: none !important;
}
html::before, html::after,
body.page-crypto-iframe::before,
body.page-crypto-iframe::after {
  display: none !important;
  content: none !important;
  height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
}
body.page-crypto-iframe .page-back-below-header {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0.35rem 1.25rem 0;
  box-sizing: border-box;
}
body.page-crypto-iframe p.back-link.back-link--below-header {
  margin: 0.2rem 0 0.85rem;
}
body.page-crypto-iframe.site-experience.page-inner--rich .back-link--below-header a {
  display: inline-block;
  font-weight: 650;
  font-size: 0.84rem;
  line-height: 1.35;
  color: var(--ink-soft, #1f4c67);
  text-decoration: none;
  padding: 0.35rem 0.65rem;
  border-radius: 999px;
  border: 1px solid rgb(var(--hx-accent-bright-rgb, 80 113 136) / 0.18);
  background: rgba(251, 254, 255, 0.85);
}
body.page-crypto-iframe.site-experience.page-inner--rich .back-link--below-header a:hover {
  color: var(--hx-crypto-bright, #6e869e);
  border-color: rgb(110 134 158 / 0.45);
  background: #f8fcfe;
}
body.page-crypto-iframe .page-shell.etp-mock-shell {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0 1.25rem 1.5rem;
  box-sizing: border-box;
  background: transparent !important;
}
body.page-crypto-iframe .home-reveal {
  opacity: 1 !important;
  transform: none !important;
}
body.page-crypto-iframe .inner-rich-zone.zone--crypto,
body.page-crypto-iframe.mock-crypto-inner .etp-mock-zone.inner-rich-zone.zone--crypto {
  background: var(--hx-etp-soft, #f1f4f7) !important;
  background-image: none !important;
}
body.page-crypto-iframe .inner-rich-zone.zone--crypto .home-zone__head,
body.page-crypto-iframe.mock-crypto-inner .etp-mock-zone .home-zone__head {
  background: var(--hx-etp-head, linear-gradient(180deg, #f4f6f9 0%, #ffffff 100%)) !important;
}
body.page-crypto-iframe .inner-rich-zone.zone--crypto .inner-rich-zone__body,
body.page-crypto-iframe.mock-crypto-inner.page-inner--rich .etp-mock-zone .inner-rich-zone__body,
body.page-crypto-iframe.mock-crypto-inner .etp-mock-zone__body.inner-rich-zone__body {
  background: var(--hx-etp-soft, #f1f4f7) !important;
  background-image: none !important;
}
/* Key observations — mock CSS keeps gradient + rgba block; reads as a horizontal seam mid-card. */
body.page-crypto-iframe.page-inner--rich .inner-rich-zone.zone--crypto .inner-rich-block,
body.page-crypto-iframe.page-inner--rich .inner-rich-zone .etp-mock-key-obs-block,
body.page-crypto-iframe .etp-mock-key-obs-block.inner-rich-block,
body.page-crypto-iframe.site-experience.page-inner--rich .inner-rich-zone.zone--crypto .inner-rich-block,
body.page-crypto-iframe.page-inner--rich .inner-rich-zone .etp-mock-key-obs-block .crypto-story-callout,
body.page-crypto-iframe.page-inner--rich .inner-rich-zone #js-crypto-key-obs .crypto-story-callout,
body.page-crypto-iframe .etp-mock-key-obs-block .crypto-story-callout,
body.page-crypto-iframe #js-crypto-key-obs .crypto-story-callout {
  background: #fff !important;
  background-color: #fff !important;
  background-image: none !important;
  box-shadow: none !important;
}
body.page-crypto-iframe .etp-mock-key-obs-block .crypto-story-callout__note,
body.page-crypto-iframe #js-crypto-key-obs .crypto-story-callout__note {
  background: rgb(72 90 110 / 0.06) !important;
  background-image: none !important;
}
body.page-crypto-iframe .etp-mock-key-obs-block .review-note.ko-disclaimer,
body.page-crypto-iframe #js-crypto-key-obs .review-note.ko-disclaimer {
  background: #fff !important;
  background-color: #fff !important;
  background-image: none !important;
}
body.page-crypto-iframe .rwa-table-modal--streamlit-fallback:not([hidden]) {
  display: grid !important;
  place-items: center !important;
  padding: 1.25rem !important;
  box-sizing: border-box !important;
}
body.page-crypto-iframe .rwa-table-modal--streamlit-fallback .rwa-table-modal__dialog {
  max-height: min(92vh, 980px);
  width: min(96%, 1400px);
}
"""
    )
    from streamlit_site_parity import (
        deep_iframe_back_link_clickable_css,
        deep_iframe_kpi_flatten_css,
        deep_iframe_related_chips_css,
        deep_iframe_table_height_lock_css,
        deep_iframe_table_panel_css,
    )

    chunks.append(deep_iframe_kpi_flatten_css(scope="body.page-crypto-iframe", zone="crypto"))
    chunks.append(deep_iframe_table_panel_css(scope="body.page-crypto-iframe"))
    chunks.append(deep_iframe_table_height_lock_css(scope="body.page-crypto-iframe"))
    chunks.append(deep_iframe_related_chips_css(scope="body.page-crypto-iframe", zone="crypto"))
    chunks.append(deep_iframe_back_link_clickable_css(scope="body.page-crypto-iframe"))
    return "\n".join(chunks)


def _crypto_back_link_html(*, href: str, label: str) -> str:
    label_html = (
        escape(label)
        .replace("\u2190", "&larr;")
        .replace("\u00b7", "&middot;")
    )
    return _CRYPTO_IFRAME_BACK_LINK.format(back_href=escape(href), back_label_html=label_html)


def build_crypto_server_iframe_html(
    *,
    payloads: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=crypto",
    back_label: str = "← Back to home · Crypto preview",
) -> str:
    """Self-contained iframe with GitHub Pages CSS and pre-rendered body."""
    from streamlit_server_deep_page import (
        build_crypto_server_export_config,
        build_crypto_server_zone_html,
    )
    from streamlit_site_parity import (
        DEEP_MARKET_TABLE_HEIGHT_VERSION,
        deep_iframe_table_height_lock_css,
        deep_iframe_table_panel_css,
        iframe_internal_link_script,
    )

    css = _cached_iframe_crypto_stylesheet_v10()
    override_css = crypto_github_canvas_override_css()
    table_panel_css = deep_iframe_table_panel_css(scope="body.page-crypto-iframe")
    height_lock_css = deep_iframe_table_height_lock_css(scope="body.page-crypto-iframe")
    back_link = _crypto_back_link_html(href=back_href, label=back_label)
    zone = build_crypto_server_zone_html(payloads=payloads, related_chips=related_chips)
    payloads_json = _json_for_script(payloads)
    prices = payloads.get("crypto_prices.json") if isinstance(payloads.get("crypto_prices.json"), dict) else {}
    export_json = json.dumps(build_crypto_server_export_config(list(prices.get("rows") or [])))
    js_deps = _read_js_files(_CRYPTO_JS_DEPS)
    js_boot = _read_js_files(_CRYPTO_JS_BOOT)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
<style id="crypto-gh-canvas-override-v{CRYPTO_CANVAS_OVERRIDE_VERSION}">{override_css}</style>
<style id="crypto-table-panel-v{CRYPTO_TABLE_PANEL_VERSION}">{table_panel_css}</style>
<style id="deep-market-table-height-lock-v{DEEP_MARKET_TABLE_HEIGHT_VERSION}">{height_lock_css}</style>
</head>
<body
  class="page-crypto page-crypto-iframe site-experience page-inner--rich mock-crypto-inner"
  data-methodology="crypto"
>
{back_link}
{zone}
<script>
window.__CRYPTO_PAGE_PAYLOADS = {payloads_json};
window.__CRYPTO_SERVER_EXPORTS = {export_json};
</script>
<script>
{js_deps}
</script>
<script>
window.loadJson = function (name) {{
  var key = String(name || "").split("/").pop();
  if (window.__CRYPTO_PAGE_PAYLOADS && Object.prototype.hasOwnProperty.call(window.__CRYPTO_PAGE_PAYLOADS, key)) {{
    return Promise.resolve(window.__CRYPTO_PAGE_PAYLOADS[key]);
  }}
  return Promise.reject(new Error("Unknown crypto payload: " + name));
}};
{_CRYPTO_PATCH_LOAD_JSON_JS}
</script>
<script>
{_STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH}
</script>
<script>
{_CRYPTO_SERVER_TABLE_WIRE_JS}
</script>
<script>
{js_boot}
</script>
<script>
{_CRYPTO_MEASURE_HEIGHT_JS}
(function () {{
  function sendHeight() {{
    if (typeof window.parent.postMessage !== "function") return;
    var h = measureCryptoContentHeight();
    if (h === null || h < 200) return;
    window.parent.postMessage({{ type: "streamlit:setFrameHeight", height: h }}, "*");
    try {{
      window.parent.postMessage({{ type: "jpm-tmmf-height", height: h }}, "*");
    }} catch (e) {{}}
  }}
  function bindObservers() {{
    if (typeof ResizeObserver === "undefined") return;
    var ro = new ResizeObserver(sendHeight);
    [
      "main.page-shell.etp-mock-shell",
      "article.etp-mock-zone",
      "#js-crypto-cap-mix",
      "#crypto-market-cap-chart",
      "#js-crypto-tbody",
      ".etp-mock-table-block",
      "#js-crypto-generated",
    ].forEach(function (sel) {{
      var el = document.querySelector(sel);
      if (el) ro.observe(el);
    }});
  }}
  sendHeight();
  window.addEventListener("load", function () {{
    sendHeight();
    bindObservers();
  }});
  if (typeof MutationObserver !== "undefined") {{
    var mo = new MutationObserver(function () {{
      sendHeight();
      bindObservers();
    }});
    [
      "article.etp-mock-zone",
      "#js-crypto-key-obs",
      "#js-crypto-cap-mix",
      "#crypto-market-cap-chart",
      "#js-crypto-tbody",
    ].forEach(function (sel) {{
      var el = document.querySelector(sel);
      if (el) mo.observe(el, {{ childList: true, subtree: true, attributes: true }});
    }});
  }}
  [100, 400, 1000, 2500, 5000, 8000, 12000].forEach(function (ms) {{
    setTimeout(sendHeight, ms);
  }});
}})();
</script>
{crypto_iframe_canvas_override_js()}
{iframe_internal_link_script()}
</body>
</html>"""


# Back-compat alias for verify script and legacy callers.
build_crypto_prices_body_iframe_html = build_crypto_server_iframe_html


@st.cache_data(show_spinner=False, ttl=300)
def _cached_crypto_prices_iframe_payloads() -> dict[str, Any]:
    return load_crypto_prices_iframe_payloads()


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_crypto_server_iframe_html(
    payloads_json: str,
    related_chips: str,
    back_href: str,
    back_label: str,
    *,
    _css_version: str = _CRYPTO_IFRAME_CSS_VERSION,
    _table_height_version: str = DEEP_MARKET_TABLE_HEIGHT_VERSION,
) -> str:
    payloads = json.loads(payloads_json)
    return build_crypto_server_iframe_html(
        payloads=payloads,
        related_chips=related_chips,
        back_href=back_href,
        back_label=back_label,
    )


def render_crypto_prices_body_iframe(
    *,
    payloads: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=crypto",
    back_label: str = "← Back to home · Crypto preview",
) -> None:
    """Render the GitHub Pages Crypto Prices zone inside a Streamlit iframe."""
    from streamlit_site_parity import render_subpage_body_iframe

    payloads_json = _json_for_script(payloads)
    render_subpage_body_iframe(
        _cached_crypto_server_iframe_html(
            payloads_json,
            related_chips,
            back_href,
            back_label,
        ),
        height=1200,
        back_href=back_href,
        back_label=back_label,
    )
    inject_crypto_host_canvas_override()
    inject_crypto_iframe_table_actions(payloads)
