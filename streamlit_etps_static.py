"""Streamlit U.S. ETPs full page — static HTML iframe (parity with ``etps.html``)."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from streamlit_crypto_prices_static import _CRYPTO_PATCH_LOAD_JSON_JS
from streamlit_tmmf_static import (
    _STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH,
    _TMMF_SERVER_INLINE_HOST_MODAL_JS,
    _json_for_script,
    _read_js_files,
)

_REPO = Path(__file__).resolve().parent
_STATIC = _REPO / "static_home"
_DATA = _STATIC / "data"

_ETP_IFRAME_CSS_VERSION = "3"
ETP_CANVAS_OVERRIDE_VERSION = "1"

ETP_GH_PAGE_WASH = "#f3f7fb"
ETP_GH_ZONE_SOFT = "#eef2f7"

_ETP_JS_DEPS = (
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
_ETP_JS_BOOT = ("etp-page.js",)

_ETP_MEASURE_HEIGHT_JS = """
function measureEtpContentHeight() {
  if (window.__TMMF_MODAL_OPEN) return null;
  var scrollY = window.scrollY || document.documentElement.scrollTop || 0;
  var nodes = [
    document.querySelector(".page-back-below-header"),
    document.querySelector("main.page-shell.etp-mock-shell"),
    document.getElementById("js-etp-generated"),
  ];
  var maxBottom = 0;
  nodes.forEach(function (el) {
    if (!el) return;
    var rect = el.getBoundingClientRect();
    if (rect.height <= 0 && el.id === "js-etp-generated" && !(el.textContent || "").trim()) {
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

_ETP_IFRAME_BACK_LINK = """
<div class="page-back-below-header">
  <p class="back-link back-link--below-header">
    <a class="etp-server-back-anchor" data-deep-back="markets" href="{back_href}">{back_label_html}</a>
  </p>
</div>
"""

_ETP_SERVER_TABLE_WIRE_JS = """
(function () {
  function wireEtpTable() {
    var fs = window.__TABLE_FULLSCREEN;
    if (!fs || !fs.attachTableFullscreenButton) return;
    var tbody = document.getElementById("js-etp-tbody");
    if (!tbody) return;
    var wrap = tbody.closest(".table-wrap");
    var table = wrap && wrap.querySelector("table");
    if (!wrap || !table) return;
    delete wrap._rwaFullscreenBound;
    delete wrap._rwaDownloadBound;
    var exportData =
      window.__ETP_SERVER_EXPORTS && window.__ETP_SERVER_EXPORTS["etp-table"];
    fs.attachTableFullscreenButton(wrap, table, {
      title: "U.S. ETP fund table",
      filename: "us-etp-funds",
      sheetName: "U.S. ETPs",
      downloadPlacement: "title-row",
      downloadAnchor: document.getElementById("js-etp-table-download"),
      actionRow: document.getElementById("js-etp-table-actions"),
      getExportData: exportData
        ? function () {
            return exportData;
          }
        : undefined,
    });
    var btn =
      (document.getElementById("js-etp-table-actions") &&
        document.getElementById("js-etp-table-actions").querySelector(
          '[data-rwa-fullscreen-btn="1"]'
        )) ||
      null;
    if (btn && fs.openTableModal) {
      btn.onclick = function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        fs.openTableModal(table, { title: "U.S. ETP fund table" });
      };
    }
  }
  window.__etpWireServerTable = wireEtpTable;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireEtpTable);
  } else {
    wireEtpTable();
  }
  setTimeout(wireEtpTable, 0);
  setTimeout(wireEtpTable, 400);
  setTimeout(wireEtpTable, 1200);
})();
"""


def load_etp_iframe_payloads(*, user_agent: str) -> dict[str, Any]:
    from scripts.export_static_site_data import build_etp_page_payloads

    pack = build_etp_page_payloads(
        user_agent=user_agent,
        live_cache_path=_DATA / "etp_live_cache.json",
        for_streamlit=True,
    )
    return pack["payloads"]


def _static_etp_payload_fallback(*, error: str = "") -> dict[str, Any]:
    from etp_live_cache import bundle_from_static_exports, load_etp_live_cache

    cached = load_etp_live_cache(_DATA / "etp_live_cache.json", static_dir=_DATA)
    if cached and isinstance(cached.get("payloads"), dict):
        out = dict(cached["payloads"])
    else:
        seeded = bundle_from_static_exports(_DATA)
        out = dict(seeded["payloads"]) if seeded else {}
    if error:
        for key in list(out):
            merged = dict(out[key])
            merged["error"] = error
            merged["stale"] = True
            out[key] = merged
    return out


def get_etp_iframe_payloads(*, user_agent: str) -> dict[str, Any]:
    from streamlit_payload_stale_first import load_static_first_with_live_fallback, mark_payload_map_stale

    return load_static_first_with_live_fallback(
        load_stale=lambda: _static_etp_payload_fallback() or None,
        load_live_cached=lambda: _cached_etp_iframe_payloads(user_agent),
        mark_stale=mark_payload_map_stale,
    )


@st.cache_resource(show_spinner=False)
def _cached_iframe_etp_stylesheet() -> str:
    """Same CSS stack as ``static_home/etps.html`` (iframe-safe, no mock banners)."""
    from streamlit_site_parity import (
        _iframe_etp_mock_css,
        deep_iframe_kpi_flatten_css,
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
    path = _STATIC / "mockups/etp-inner-page-mock.css"
    if path.is_file():
        chunks.append(_iframe_etp_mock_css(path.read_text(encoding="utf-8")))
    etp_xp = _STATIC / "css/etp-page-experience.css"
    if etp_xp.is_file():
        chunks.append(etp_xp.read_text(encoding="utf-8"))
    chunks.append(
        """
html, body.page-etp-iframe.site-experience {
  margin: 0;
  padding: 0;
  background: var(--wash, #f3f7fb) !important;
  background-image: none !important;
  overflow: hidden;
}
body.page-etp-iframe.site-experience.page-inner--rich,
body.page-etp-iframe.mock-etp-inner.site-experience {
  background: var(--wash, #f3f7fb) !important;
  background-image: none !important;
}
html::before, html::after,
body.page-etp-iframe::before,
body.page-etp-iframe::after {
  display: none !important;
  content: none !important;
  height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
}
body.page-etp-iframe .page-back-below-header {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0.35rem 1.25rem 0;
  box-sizing: border-box;
}
body.page-etp-iframe p.back-link.back-link--below-header {
  margin: 0.2rem 0 0.85rem;
}
body.page-etp-iframe.site-experience.page-inner--rich .back-link--below-header a {
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
body.page-etp-iframe.site-experience.page-inner--rich .back-link--below-header a:hover {
  color: var(--hx-etp-bright, #507188);
  border-color: rgb(80 113 136 / 0.45);
  background: #f8fcfe;
}
body.page-etp-iframe .page-shell.etp-mock-shell {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0 1.25rem 1.5rem;
  box-sizing: border-box;
  background: transparent !important;
}
body.page-etp-iframe .home-reveal {
  opacity: 1 !important;
  transform: none !important;
}
body.page-etp-iframe .inner-rich-zone.zone--etp,
body.page-etp-iframe.mock-etp-inner .etp-mock-zone.inner-rich-zone.zone--etp {
  background: var(--hx-etp-soft, #eef2f7) !important;
  background-image: none !important;
}
body.page-etp-iframe .inner-rich-zone.zone--etp .inner-rich-zone__body,
body.page-etp-iframe.mock-etp-inner .etp-mock-zone .inner-rich-zone__body {
  background: var(--hx-etp-soft, #eef2f7) !important;
  background-image: none !important;
}
body.page-etp-iframe.page-inner--rich .inner-rich-block,
body.page-etp-iframe .etp-mock-key-obs-block,
body.page-etp-iframe .etp-mock-key-obs-block .crypto-story-callout,
body.page-etp-iframe #js-etp-key-obs .crypto-story-callout {
  background: #fff !important;
  background-image: none !important;
  box-shadow: none !important;
}
body.page-etp-iframe .etp-mock-key-obs-block .crypto-story-callout__note,
body.page-etp-iframe #js-etp-key-obs .crypto-story-callout__note {
  background: rgb(62 92 116 / 0.06) !important;
  background-image: none !important;
}
body.page-etp-iframe .rwa-table-modal--streamlit-fallback:not([hidden]) {
  display: grid !important;
  place-items: center !important;
  padding: 1.25rem !important;
  box-sizing: border-box !important;
}
body.page-etp-iframe .rwa-table-modal--streamlit-fallback .rwa-table-modal__dialog {
  max-height: min(92vh, 980px);
  width: min(96%, 1400px);
}
"""
    )
    chunks.append(deep_iframe_kpi_flatten_css(scope="body.page-etp-iframe", zone="etp"))
    chunks.append(deep_iframe_table_panel_css(scope="body.page-etp-iframe"))
    return "\n".join(chunks)


def etp_github_canvas_override_css(*, version: str = ETP_CANVAS_OVERRIDE_VERSION) -> str:
    from streamlit_site_parity import deep_iframe_kpi_flatten_css

    wash = ETP_GH_PAGE_WASH
    soft = ETP_GH_ZONE_SOFT
    scope = "body.page-etp-iframe"
    return f"""
/* ETP GitHub Pages canvas override v{version} */
html, {scope}.site-experience,
{scope}.site-experience.page-inner--rich,
{scope}.mock-etp-inner.site-experience {{
  background: {wash} !important;
  background-color: {wash} !important;
  background-image: none !important;
}}
{scope} .page-shell.etp-mock-shell {{
  background: transparent !important;
  background-image: none !important;
}}
{scope} .inner-rich-zone.zone--etp,
{scope} .inner-rich-zone.zone--etp .inner-rich-zone__body,
{scope} .etp-mock-zone.inner-rich-zone.zone--etp,
{scope} .etp-mock-zone .inner-rich-zone__body {{
  background: {soft} !important;
  background-color: {soft} !important;
  background-image: none !important;
}}
{scope} .inner-rich-block,
{scope} .etp-mock-key-obs-block,
{scope} .etp-mock-key-obs-block .crypto-story-callout,
{scope} #js-etp-key-obs .crypto-story-callout,
{scope} .etp-mock-key-obs-block .review-note.ko-disclaimer,
{scope} .etp-mock-insights__panel,
{scope} .etp-mock-dash__panel,
{scope} .rwa-kpi-row--home-grid .rwa-kpi-cell,
{scope} .etp-mock-table-block {{
  background: #fff !important;
  background-color: #fff !important;
  background-image: none !important;
  box-shadow: none !important;
}}
{scope} .etp-mock-key-obs-block .crypto-story-callout__note,
{scope} #js-etp-key-obs .crypto-story-callout__note {{
  background: rgb(62 92 116 / 0.06) !important;
  background-image: none !important;
}}
""" + deep_iframe_kpi_flatten_css(scope=scope, zone="etp")


def etp_iframe_canvas_override_js(*, version: str = ETP_CANVAS_OVERRIDE_VERSION) -> str:
    wash = ETP_GH_PAGE_WASH
    soft = ETP_GH_ZONE_SOFT
    return f"""
<script id="etp-gh-canvas-override-js-v{version}">
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
  function paint() {{
    setBg(document.documentElement, WASH);
    setBg(document.body, WASH);
    var main = document.querySelector("main.page-shell.etp-mock-shell");
    if (main) {{
      main.style.setProperty("background", "transparent", "important");
      main.style.setProperty("background-image", "none", "important");
    }}
    document.querySelectorAll(
      ".inner-rich-zone.zone--etp, .inner-rich-zone.zone--etp .inner-rich-zone__body"
    ).forEach(function (el) {{ setBg(el, SOFT); }});
    document.querySelectorAll(
      ".inner-rich-block, .etp-mock-key-obs-block, .crypto-story-callout, .review-note.ko-disclaimer, .etp-mock-insights__panel, .etp-mock-dash__panel, .rwa-kpi-row--home-grid .rwa-kpi-cell, .etp-mock-table-block"
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
      setBg(el, "rgb(62 92 116 / 0.06)");
    }});
  }}
  paint();
  window.addEventListener("load", paint);
  [50, 200, 800, 2000, 5000].forEach(function (ms) {{ setTimeout(paint, ms); }});
}})();
</script>
"""


def etp_host_canvas_override_css(*, version: str = ETP_CANVAS_OVERRIDE_VERSION) -> str:
    wash = ETP_GH_PAGE_WASH
    return f"""
<style id="etp-gh-host-canvas-override-v{version}">
.stApp:has(.streamlit-etps-iframe-page),
.withScreencast:has(.streamlit-etps-iframe-page),
[data-testid="stScreencast"]:has(.streamlit-etps-iframe-page),
.stApp:has(.streamlit-etps-iframe-page) [data-testid="stAppViewContainer"],
.stApp:has(.streamlit-etps-iframe-page) section.main,
.stApp:has(.streamlit-etps-iframe-page) [data-testid="stMain"],
.stApp:has(.streamlit-etps-iframe-page) [data-testid="stMainBlockContainer"],
.stApp:has(.streamlit-etps-iframe-page) .block-container,
.stApp:has(.streamlit-etps-iframe-page) [data-testid="stVerticalBlock"],
.stApp:has(.streamlit-etps-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe),
.stApp:has(.streamlit-etps-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe) [data-testid="stVerticalBlock"],
.stApp:has(.streamlit-etps-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe) [data-testid="stHtml"],
.stApp:has(.streamlit-etps-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe) [data-testid="stHtml"] > div {{
  background: {wash} !important;
  background-color: {wash} !important;
  background-image: none !important;
}}
</style>
"""


def etp_host_canvas_override_js(*, version: str = ETP_CANVAS_OVERRIDE_VERSION) -> str:
    wash = ETP_GH_PAGE_WASH
    return f"""
<script id="etp-gh-host-canvas-override-js-v{version}">
(function () {{
  var WASH = "{wash}";
  var doc = window.parent && window.parent.document ? window.parent.document : document;
  function paint() {{
    var app = doc.querySelector(".stApp");
    if (!app || !app.querySelector(".streamlit-etps-iframe-page")) return;
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
      if (!el.querySelector(".streamlit-etps-iframe-page")) return;
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


def inject_etp_host_canvas_override() -> None:
    st.markdown(etp_host_canvas_override_css(), unsafe_allow_html=True)
    components.html(etp_host_canvas_override_js(), height=0, width=0)


def inject_etp_iframe_table_actions(payloads: dict[str, Any]) -> None:
    """Wire download/fullscreen on the ETP body iframe via host script injection."""
    from streamlit_server_deep_page import build_etp_server_export_config

    etps = payloads.get("etps.json") if isinstance(payloads.get("etps.json"), dict) else {}
    rows = list(etps.get("rows") or [])
    js_libs = _read_js_files(("table-fullscreen.js", "table-download.js"))
    export_json = json.dumps(build_etp_server_export_config(rows))
    libs_json = json.dumps(js_libs)
    patch_json = json.dumps(_STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH.strip())
    wire_json = json.dumps(_ETP_SERVER_TABLE_WIRE_JS.strip())
    host_modal_json = json.dumps(_TMMF_SERVER_INLINE_HOST_MODAL_JS.strip())
    bootstrap = f"""
<script>
(function () {{
  var win = window.parent;
  var doc = win.document;
  if (win.__jpmEtpIframeTableHostBound) return;
  win.__jpmEtpIframeTableHostBound = true;

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

  function findEtpInner() {{
    var frames = doc.querySelectorAll("iframe");
    for (var i = 0; i < frames.length; i++) {{
      try {{
        var inner = frames[i].contentDocument;
        if (
          inner &&
          inner.body &&
          inner.body.classList &&
          inner.body.classList.contains("mock-etp-inner")
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
      hit.win.__ETP_SERVER_EXPORTS = {export_json};
      injectIntoInner(hit.doc, {patch_json});
      injectIntoInner(hit.doc, {wire_json});
      return true;
    }}
    if (!hit.win.__ST_TMMF_FULLSCREEN_PATCHED) {{
      hit.win.__ETP_SERVER_EXPORTS = {export_json};
      injectIntoInner(hit.doc, {patch_json});
      injectIntoInner(hit.doc, {wire_json});
      return true;
    }}
    if (typeof hit.win.__etpWireServerTable === "function") {{
      hit.win.__etpWireServerTable();
    }}
    return true;
  }}

  function boot() {{
    if (!doc.querySelector(".streamlit-etps-iframe-page")) return false;
    ensureHostModal();
    var hit = findEtpInner();
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


def _etp_back_link_html(*, href: str, label: str) -> str:
    label_html = (
        escape(label)
        .replace("\u2190", "&larr;")
        .replace("\u00b7", "&middot;")
    )
    return _ETP_IFRAME_BACK_LINK.format(back_href=escape(href), back_label_html=label_html)


def build_etp_server_iframe_html(
    *,
    payloads: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=markets",
    back_label: str = "← Back to home · ETP preview",
) -> str:
    """Self-contained iframe with GitHub Pages CSS and pre-rendered body."""
    from streamlit_server_deep_page import (
        build_etp_server_export_config,
        build_etp_server_zone_html,
    )
    from streamlit_site_parity import iframe_internal_link_script

    css = _cached_iframe_etp_stylesheet()
    override_css = etp_github_canvas_override_css()
    back_link = _etp_back_link_html(href=back_href, label=back_label)
    zone = build_etp_server_zone_html(payloads=payloads, related_chips=related_chips)
    payloads_json = _json_for_script(payloads)
    etps = payloads.get("etps.json") if isinstance(payloads.get("etps.json"), dict) else {}
    export_json = json.dumps(build_etp_server_export_config(list(etps.get("rows") or [])))
    js_deps = _read_js_files(_ETP_JS_DEPS)
    js_boot = _read_js_files(_ETP_JS_BOOT)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
<style id="etp-gh-canvas-override-v{ETP_CANVAS_OVERRIDE_VERSION}">{override_css}</style>
</head>
<body
  class="page-etp page-etp-iframe site-experience page-inner--rich mock-etp-inner"
  data-methodology="etp"
>
{back_link}
{zone}
<script>
window.__ETP_PAGE_PAYLOADS = {payloads_json};
window.__ETP_SERVER_EXPORTS = {export_json};
</script>
<script defer src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
<script>
{js_deps}
</script>
<script>
window.loadJson = function (name) {{
  var key = String(name || "").split("/").pop();
  if (window.__ETP_PAGE_PAYLOADS && Object.prototype.hasOwnProperty.call(window.__ETP_PAGE_PAYLOADS, key)) {{
    return Promise.resolve(window.__ETP_PAGE_PAYLOADS[key]);
  }}
  return Promise.reject(new Error("Unknown ETP payload: " + name));
}};
{_CRYPTO_PATCH_LOAD_JSON_JS}
</script>
<script>
{_STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH}
</script>
<script>
{_ETP_SERVER_TABLE_WIRE_JS}
</script>
<script>
{js_boot}
</script>
<script>
{_ETP_MEASURE_HEIGHT_JS}
(function () {{
  function sendHeight() {{
    if (typeof window.parent.postMessage !== "function") return;
    var h = measureEtpContentHeight();
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
      "#js-etp-insights-conc",
      "#aum-chart",
      "#js-etp-tbody",
      "#js-etf-pulse",
      "#js-etp-generated",
      ".etp-mock-table-block",
    ].forEach(function (sel) {{
      var el = document.querySelector(sel);
      if (el) ro.observe(el);
    }});
    document.querySelectorAll(".plotly-graph-div").forEach(function (el) {{ ro.observe(el); }});
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
      "#js-etp-key-obs",
      "#js-etp-insights-conc",
      "#aum-chart",
      "#js-etp-tbody",
      "#js-etf-pulse",
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
{etp_iframe_canvas_override_js()}
{iframe_internal_link_script()}
</body>
</html>"""


# Back-compat alias for verify script and legacy callers.
build_etps_body_iframe_html = build_etp_server_iframe_html


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_etp_iframe_payloads(_user_agent: str) -> dict[str, Any]:
    return load_etp_iframe_payloads(user_agent=_user_agent)


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_etp_server_iframe_html(
    payloads_json: str,
    related_chips: str,
    back_href: str,
    back_label: str,
    *,
    _css_version: str = _ETP_IFRAME_CSS_VERSION,
) -> str:
    payloads = json.loads(payloads_json)
    return build_etp_server_iframe_html(
        payloads=payloads,
        related_chips=related_chips,
        back_href=back_href,
        back_label=back_label,
    )


def render_etps_body_iframe(
    *,
    payloads: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=markets",
    back_label: str = "← Back to home · ETP preview",
) -> None:
    from streamlit_site_parity import render_subpage_body_iframe

    payloads_json = _json_for_script(payloads)
    render_subpage_body_iframe(
        _cached_etp_server_iframe_html(
            payloads_json,
            related_chips,
            back_href,
            back_label,
        ),
        height=1500,
    )
    inject_etp_host_canvas_override()
    inject_etp_iframe_table_actions(payloads)
