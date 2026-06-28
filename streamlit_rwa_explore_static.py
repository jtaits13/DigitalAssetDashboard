"""Streamlit RWA Explore pages — server-rendered deep iframes (parity with ``rwa-explore-*.html``)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from streamlit_tmmf_static import (
    _STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH,
    _TMMF_SERVER_INLINE_HOST_MODAL_JS,
    _json_for_script,
    _read_js_files,
)

_REPO = Path(__file__).resolve().parent
_STATIC = _REPO / "static_home"
_DATA = _STATIC / "data"

_RWA_EXPLORE_IFRAME_CSS_VERSION = "2"
RWA_EXPLORE_CANVAS_OVERRIDE_VERSION = "1"

RWA_EXPLORE_GH_PAGE_WASH = "#f3f7fb"
RWA_EXPLORE_GH_ZONE_SOFT = "#e8eff5"

_EXPLORE_ASSET_SECTION_SKIP = frozenset({"stablecoins", "tokenized_mmf"})

_RWA_EXPLORE_MEASURE_HEIGHT_JS = """
function measureRwaExploreContentHeight() {
  if (window.__TMMF_MODAL_OPEN) return null;
  var scrollY = window.scrollY || document.documentElement.scrollTop || 0;
  var nodes = [
    document.querySelector(".page-back-below-header"),
    document.querySelector("main.page-shell.etp-mock-shell"),
    document.getElementById("js-exat-sections"),
    document.getElementById("js-exat-timestamp"),
  ];
  var maxBottom = 0;
  nodes.forEach(function (el) {
    if (!el) return;
    maxBottom = Math.max(maxBottom, el.getBoundingClientRect().bottom + scrollY);
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

_RWA_EXPLORE_SERVER_TABLE_WIRE_JS = """
(function () {
  function $(id) {
    return document.getElementById(id);
  }
  function wireTableSearch(cfg) {
    var inp = $(cfg.inputId);
    var note = $(cfg.noteId);
    var tbody = cfg.tbody;
    if (!inp || !tbody) return;
    var entity = cfg.entityPlural || "rows";
    inp.addEventListener("input", function () {
      var q = String(inp.value || "").trim().toLowerCase();
      var rows = tbody.querySelectorAll("tr");
      var shown = 0;
      rows.forEach(function (tr) {
        if (tr.querySelector("td[colspan]")) return;
        var match = !q || tr.textContent.toLowerCase().indexOf(q) >= 0;
        tr.hidden = !match;
        if (match) shown++;
      });
      if (!note) return;
      var total = rows.length;
      if (!q) note.textContent = "Showing all " + total + " " + entity + ".";
      else note.textContent = "Showing " + shown + " of " + total + ' matching "' + q + '".';
    });
  }
  function wireBlock(cfg) {
    var host = $(cfg.hostId);
    if (!host) return;
    var wrap = host.querySelector(".table-wrap--scroll, .rwa-split-table-scroll");
    var table = wrap && wrap.querySelector("table");
    if (!wrap || !table) return;
    var fs = window.__TABLE_FULLSCREEN;
    if (!fs || !fs.attachTableFullscreenButton) return;
    delete wrap._rwaFullscreenBound;
    delete wrap._rwaDownloadBound;
    var exportData =
      window.__TMMF_SERVER_EXPORTS && window.__TMMF_SERVER_EXPORTS[cfg.exportKey];
    fs.attachTableFullscreenButton(wrap, table, {
      title: cfg.title,
      filename: cfg.filename,
      sheetName: cfg.sheetName,
      downloadPlacement: "title-row",
      downloadAnchor: $(cfg.actionsId),
      actionRow: $(cfg.metaActionsId),
      getExportData: exportData ? function () { return exportData; } : undefined,
    });
    if (cfg.inputId && cfg.noteId) {
      wireTableSearch({
        inputId: cfg.inputId,
        noteId: cfg.noteId,
        tbody: table.querySelector("tbody"),
        entityPlural: cfg.entityPlural,
      });
    }
  }
  function boot() {
    (window.__RWA_EXPLORE_SERVER_WIRE || []).forEach(wireBlock);
  }
  window.__rwaExploreWireServerTables = boot;
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
  setTimeout(boot, 0);
  setTimeout(boot, 400);
  setTimeout(boot, 1200);
})();
"""

_RWA_EXPLORE_IFRAME_BACK_LINK = """
<div class="page-back-below-header">
  <p class="back-link back-link--below-header">
    <a data-exat-link="global" href="{back_href}">{back_label_html}</a>
  </p>
</div>
"""


@dataclass(frozen=True)
class RwaExplorePageSpec:
    kind: str
    payload_key: str
    page_class: str
    iframe_class: str
    host_style_kind: str
    host_marker_class: str
    band_label: str
    title: str
    jump_aria: str
    default_back_href: str
    default_back_label: str
    is_participant: bool


RWA_EXPLORE_SPECS: dict[str, RwaExplorePageSpec] = {
    "explore_asset": RwaExplorePageSpec(
        kind="explore_asset",
        payload_key="rwa_explore_asset_type.json",
        page_class="page-rwa-explore-at",
        iframe_class="page-rwa-explore-at-iframe",
        host_style_kind="rwa_explore_at",
        host_marker_class="streamlit-rwa-explore-at-iframe-page",
        band_label="RWA · Assets",
        title="Explore by Asset Type",
        jump_aria="Jump to asset previews",
        default_back_href="/RWA_Global_Market_Overview",
        default_back_label="← RWA Global Market Overview",
        is_participant=False,
    ),
    "explore_participant": RwaExplorePageSpec(
        kind="explore_participant",
        payload_key="rwa_explore_market_participant.json",
        page_class="page-rwa-explore-mp",
        iframe_class="page-rwa-explore-mp-iframe",
        host_style_kind="rwa_explore_mp",
        host_marker_class="streamlit-rwa-explore-mp-iframe-page",
        band_label="RWA · Participants",
        title="Explore by Market Participant",
        jump_aria="Jump to participant previews",
        default_back_href="/RWA_Global_Market_Overview",
        default_back_label="← RWA Global Market Overview",
        is_participant=True,
    ),
}


def _static_rwa_explore_payload_fallback(*, payload_key: str, error: str = "") -> dict[str, Any]:
    path = _DATA / payload_key
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    if error:
        merged = dict(data)
        merged["error"] = error
        merged["stale"] = True
        data = merged
    return {payload_key: data}


def load_rwa_explore_iframe_payloads(kind: str) -> dict[str, Any]:
    from rwa_explore_page_payloads import (
        build_rwa_explore_asset_type_page_payload,
        build_rwa_explore_market_participant_page_payload,
    )

    spec = RWA_EXPLORE_SPECS[kind]
    if kind == "explore_asset":
        payload = build_rwa_explore_asset_type_page_payload(for_streamlit=True)
    else:
        payload = build_rwa_explore_market_participant_page_payload(for_streamlit=True)
    return {spec.payload_key: payload}


def get_rwa_explore_iframe_payloads(kind: str) -> dict[str, Any]:
    from streamlit_payload_stale_first import load_static_first_with_live_fallback, mark_payload_map_stale

    spec = RWA_EXPLORE_SPECS[kind]

    return load_static_first_with_live_fallback(
        load_stale=lambda: _static_rwa_explore_payload_fallback(payload_key=spec.payload_key) or None,
        load_live_cached=lambda: _cached_rwa_explore_iframe_payloads(kind),
        mark_stale=mark_payload_map_stale,
    )


def _explore_wire_blocks(payload: dict[str, Any], *, is_participant: bool) -> list[dict[str, str]]:
    from streamlit_server_deep_page import _explore_preview_entity, _explore_table_block_title

    sections = list(payload.get("sections") or [])
    if not is_participant:
        sections = [s for s in sections if s.get("id") not in _EXPLORE_ASSET_SECTION_SKIP]
    blocks: list[dict[str, str]] = []
    for sec in sections:
        columns = list(sec.get("columns") or [])
        if not columns:
            continue
        sec_id = str(sec.get("id") or "section")
        prefix = f"explore-{sec_id}"
        entity, _, _, _ = _explore_preview_entity(columns)
        table_title = _explore_table_block_title(sec, entity=entity)
        slug = sec_id.lower().replace("_", "-")
        blocks.append(
            {
                "hostId": f"{prefix}-wrap",
                "actionsId": f"{prefix}-table-actions",
                "metaActionsId": f"{prefix}-meta-actions",
                "inputId": f"{prefix}-q",
                "noteId": f"{prefix}-note",
                "entityPlural": entity,
                "exportKey": sec_id,
                "title": table_title,
                "filename": f"rwa-explore-{slug}",
                "sheetName": str(sec.get("title") or "Data")[:31],
            }
        )
    return blocks


@st.cache_resource(show_spinner=False)
def _cached_iframe_rwa_explore_stylesheet(kind: str) -> str:
    from streamlit_site_parity import (
        _iframe_rwa_explore_mock_css,
        deep_iframe_back_link_clickable_css,
        deep_iframe_kpi_flatten_css,
        deep_iframe_related_chips_css,
        deep_iframe_table_panel_css,
    )

    spec = RWA_EXPLORE_SPECS[kind]
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
    for rel in ("mockups/etp-inner-page-mock.css", "mockups/rwa-global-inner-page-mock.css"):
        path = _STATIC / rel
        if path.is_file():
            chunks.append(_iframe_rwa_explore_mock_css(path.read_text(encoding="utf-8"), body_class=spec.iframe_class))
    path = _STATIC / "css/rwa-explore-page.css"
    if path.is_file():
        chunks.append(path.read_text(encoding="utf-8"))
    chunks.append(
        f"""
html, body.{spec.iframe_class}.site-experience {{
  margin: 0;
  padding: 0;
  background: var(--wash, #f3f7fb);
  overflow: hidden;
}}
html::before,
html::after,
body.{spec.iframe_class}::before,
body.{spec.iframe_class}::after {{
  display: none !important;
  content: none !important;
  height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
}}
body.{spec.iframe_class} .page-back-below-header {{
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0.35rem 1.25rem 0;
  box-sizing: border-box;
}}
body.{spec.iframe_class} p.back-link.back-link--below-header {{
  margin: 0.2rem 0 0.85rem;
}}
body.{spec.iframe_class}.site-experience.page-inner--rich .back-link--below-header a {{
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
}}
body.{spec.iframe_class} .page-shell.etp-mock-shell {{
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0 1.25rem 1.5rem;
  box-sizing: border-box;
}}
body.{spec.iframe_class} .home-reveal {{
  opacity: 1 !important;
  transform: none !important;
}}
"""
    )
    scope = f"body.{spec.iframe_class}"
    chunks.append(deep_iframe_kpi_flatten_css(scope=scope, zone="rwa"))
    chunks.append(deep_iframe_table_panel_css(scope=scope))
    chunks.append(deep_iframe_related_chips_css(scope=scope, zone="rwa"))
    chunks.append(deep_iframe_back_link_clickable_css(scope=scope))
    return "\n".join(chunks)


def rwa_explore_github_canvas_override_css(
    *,
    iframe_class: str,
    version: str = RWA_EXPLORE_CANVAS_OVERRIDE_VERSION,
) -> str:
    from streamlit_site_parity import deep_iframe_kpi_flatten_css

    wash = RWA_EXPLORE_GH_PAGE_WASH
    soft = RWA_EXPLORE_GH_ZONE_SOFT
    scope = f"body.{iframe_class}"
    return f"""
/* RWA Explore GitHub Pages canvas override v{version} */
html, {scope}.site-experience,
{scope}.site-experience.page-inner--rich,
{scope}.mock-rwa-global-inner.site-experience {{
  background: {wash} !important;
  background-color: {wash} !important;
  background-image: none !important;
}}
{scope} .page-shell.etp-mock-shell {{
  background: transparent !important;
  background-image: none !important;
}}
{scope} .inner-rich-zone.zone--rwa,
{scope} .inner-rich-zone.zone--rwa .inner-rich-zone__body,
{scope} .etp-mock-zone .inner-rich-zone__body {{
  background: {soft} !important;
  background-color: {soft} !important;
  background-image: none !important;
}}
{scope} .inner-rich-block,
{scope} .etp-mock-key-obs-block,
{scope} .etp-mock-insights__panel,
{scope} .etp-mock-table-block,
{scope} .rwa-kpi-row--home-grid .rwa-kpi-cell {{
  background: #fff !important;
  background-color: #fff !important;
  background-image: none !important;
}}
""" + deep_iframe_kpi_flatten_css(scope=scope, zone="rwa")


def rwa_explore_iframe_canvas_override_js(
    *, version: str = RWA_EXPLORE_CANVAS_OVERRIDE_VERSION
) -> str:
    wash = RWA_EXPLORE_GH_PAGE_WASH
    soft = RWA_EXPLORE_GH_ZONE_SOFT
    return f"""
<script id="rwa-explore-gh-canvas-override-js-v{version}">
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
      ".inner-rich-zone.zone--rwa, .inner-rich-zone.zone--rwa .inner-rich-zone__body"
    ).forEach(function (el) {{ setBg(el, SOFT); }});
    document.querySelectorAll(
      ".etp-mock-table-block, .rwa-kpi-row--home-grid .rwa-kpi-cell, .rwa-explore-preview"
    ).forEach(function (el) {{
      setBg(el, WHITE);
      el.style.setProperty("box-shadow", "none", "important");
    }});
    document.querySelectorAll(".rwa-kpi-panel-static").forEach(function (el) {{
      el.style.setProperty("background", "transparent", "important");
      el.style.setProperty("border", "none", "important");
      el.style.setProperty("box-shadow", "none", "important");
    }});
  }}
  paint();
  window.addEventListener("load", paint);
  [50, 200, 800, 2000, 5000].forEach(function (ms) {{ setTimeout(paint, ms); }});
}})();
</script>
"""


def rwa_explore_host_canvas_override_css(
    *,
    host_marker_class: str,
    version: str = RWA_EXPLORE_CANVAS_OVERRIDE_VERSION,
) -> str:
    wash = RWA_EXPLORE_GH_PAGE_WASH
    return f"""
<style id="rwa-explore-gh-host-canvas-override-v{version}-{host_marker_class}">
.stApp:has(.{host_marker_class}),
.withScreencast:has(.{host_marker_class}),
[data-testid="stScreencast"]:has(.{host_marker_class}),
.stApp:has(.{host_marker_class}) [data-testid="stAppViewContainer"],
.stApp:has(.{host_marker_class}) section.main,
.stApp:has(.{host_marker_class}) [data-testid="stMain"],
.stApp:has(.{host_marker_class}) [data-testid="stMainBlockContainer"] {{
  background: {wash} !important;
  background-color: {wash} !important;
  background-image: none !important;
}}
</style>
"""


def rwa_explore_host_canvas_override_js(
    *,
    host_marker_class: str,
    version: str = RWA_EXPLORE_CANVAS_OVERRIDE_VERSION,
) -> str:
    wash = RWA_EXPLORE_GH_PAGE_WASH
    return f"""
<script id="rwa-explore-gh-host-canvas-override-js-v{version}-{host_marker_class}">
(function () {{
  var WASH = "{wash}";
  var MARKER = "{host_marker_class}";
  function paint() {{
    if (!document.querySelector(".stApp:has(." + MARKER + ")")) return;
    document.querySelectorAll(
      ".stApp, [data-testid='stAppViewContainer'], section.main, [data-testid='stMain'], [data-testid='stMainBlockContainer']"
    ).forEach(function (el) {{
      el.style.setProperty("background", WASH, "important");
      el.style.setProperty("background-color", WASH, "important");
      el.style.setProperty("background-image", "none", "important");
    }});
  }}
  paint();
  window.addEventListener("load", paint);
  [50, 300, 1000, 3000].forEach(function (ms) {{ setTimeout(paint, ms); }});
}})();
</script>
"""


def inject_rwa_explore_host_canvas_override(*, kind: str) -> None:
    spec = RWA_EXPLORE_SPECS[kind]
    st.markdown(
        rwa_explore_host_canvas_override_css(host_marker_class=spec.host_marker_class)
        + rwa_explore_host_canvas_override_js(host_marker_class=spec.host_marker_class),
        unsafe_allow_html=True,
    )


def inject_rwa_explore_iframe_table_actions(*, kind: str, payload: dict[str, Any]) -> None:
    from streamlit_server_deep_page import build_rwa_explore_server_export_config

    spec = RWA_EXPLORE_SPECS[kind]
    js_libs = _read_js_files(("table-fullscreen.js", "table-download.js"))
    export_json = json.dumps(build_rwa_explore_server_export_config(payload))
    wire_blocks_json = json.dumps(_explore_wire_blocks(payload, is_participant=spec.is_participant))
    libs_json = json.dumps(js_libs)
    patch_json = json.dumps(_STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH.strip())
    wire_json = json.dumps(_RWA_EXPLORE_SERVER_TABLE_WIRE_JS.strip())
    host_modal_json = json.dumps(_TMMF_SERVER_INLINE_HOST_MODAL_JS.strip())
    marker = spec.host_marker_class
    inner_marker = "mock-rwa-global-inner"
    bootstrap = f"""
<script>
(function () {{
  var win = window.parent;
  var doc = win.document;
  if (win.__jpmRwaExploreIframeTableHostBound_{kind}) return;
  win.__jpmRwaExploreIframeTableHostBound_{kind} = true;

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

  function findExploreInner() {{
    var frames = doc.querySelectorAll("iframe");
    for (var i = 0; i < frames.length; i++) {{
      try {{
        var inner = frames[i].contentDocument;
        if (
          inner &&
          inner.body &&
          inner.body.classList &&
          inner.body.classList.contains("{inner_marker}") &&
          inner.body.classList.contains("{spec.iframe_class}")
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
    hit.win.__RWA_EXPLORE_SERVER_WIRE = {wire_blocks_json};
    if (!hit.win.__TABLE_FULLSCREEN) {{
      injectIntoInner(hit.doc, {libs_json});
      hit.win.__TMMF_SERVER_EXPORTS = {export_json};
      injectIntoInner(hit.doc, {patch_json});
      injectIntoInner(hit.doc, {wire_json});
      return true;
    }}
    if (!hit.win.__ST_TMMF_FULLSCREEN_PATCHED) {{
      hit.win.__TMMF_SERVER_EXPORTS = {export_json};
      injectIntoInner(hit.doc, {patch_json});
      injectIntoInner(hit.doc, {wire_json});
      return true;
    }}
    if (typeof hit.win.__rwaExploreWireServerTables === "function") {{
      hit.win.__rwaExploreWireServerTables();
    }}
    return true;
  }}

  function boot() {{
    if (!doc.querySelector(".{marker}")) return false;
    ensureHostModal();
    var hit = findExploreInner();
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


def _explore_back_label_html(label: str) -> str:
    return (
        escape(label)
        .replace("\u2190", "&larr;")
        .replace("\u00b7", "&middot;")
    )


def build_rwa_explore_server_iframe_html(
    *,
    kind: str,
    payload: dict[str, Any],
    related_chips: str,
    back_href: str | None = None,
    back_label: str | None = None,
) -> str:
    from streamlit_server_deep_page import build_rwa_explore_server_zone_html
    from streamlit_site_parity import iframe_internal_link_script

    spec = RWA_EXPLORE_SPECS[kind]
    css = _cached_iframe_rwa_explore_stylesheet(kind)
    override_css = rwa_explore_github_canvas_override_css(iframe_class=spec.iframe_class)
    href = back_href or spec.default_back_href
    label = back_label or spec.default_back_label
    label_html = _explore_back_label_html(label)
    back_link = _RWA_EXPLORE_IFRAME_BACK_LINK.format(
        back_href=escape(href),
        back_label_html=label_html,
    )
    zone = build_rwa_explore_server_zone_html(
        payload=payload,
        related_chips=related_chips,
        band_label=spec.band_label,
        title=spec.title,
        jump_aria=spec.jump_aria,
        is_participant=spec.is_participant,
    )
    body_classes = (
        f"{spec.page_class} {spec.iframe_class} site-experience page-inner--rich "
        "mock-rwa-global-inner rwa-explore-inner"
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
<style id="rwa-explore-gh-canvas-override-v{RWA_EXPLORE_CANVAS_OVERRIDE_VERSION}">{override_css}</style>
</head>
<body class="{body_classes}" data-explore-json="{escape(spec.payload_key)}">
{back_link}
{zone}
<script>
{_RWA_EXPLORE_MEASURE_HEIGHT_JS}
(function () {{
  function sendHeight() {{
    if (typeof window.parent.postMessage !== "function") return;
    var h = measureRwaExploreContentHeight();
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
      "#js-exat-sections",
      "#js-exat-jump",
      "#js-exat-timestamp",
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
    ["article.etp-mock-zone", "#js-exat-sections", "#js-exat-jump"].forEach(function (sel) {{
      var el = document.querySelector(sel);
      if (el) mo.observe(el, {{ childList: true, subtree: true, attributes: true }});
    }});
  }}
  [100, 400, 1000, 2500, 5000, 8000].forEach(function (ms) {{
    setTimeout(sendHeight, ms);
  }});
}})();
</script>
{rwa_explore_iframe_canvas_override_js()}
{iframe_internal_link_script()}
</body>
</html>"""


build_rwa_explore_body_iframe_html = build_rwa_explore_server_iframe_html


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_rwa_explore_iframe_payloads(kind: str) -> dict[str, Any]:
    return load_rwa_explore_iframe_payloads(kind)


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_rwa_explore_server_iframe_html(
    kind: str,
    payload_json: str,
    related_chips: str,
    back_href: str,
    back_label: str,
    *,
    _css_version: str = _RWA_EXPLORE_IFRAME_CSS_VERSION,
) -> str:
    payload = json.loads(payload_json)
    return build_rwa_explore_server_iframe_html(
        kind=kind,
        payload=payload,
        related_chips=related_chips,
        back_href=back_href,
        back_label=back_label,
    )


def render_rwa_explore_body_iframe(
    *,
    kind: str,
    payloads: dict[str, Any],
    related_chips: str,
    back_href: str | None = None,
    back_label: str | None = None,
) -> None:
    from streamlit_site_parity import render_subpage_body_iframe

    spec = RWA_EXPLORE_SPECS[kind]
    payload = dict((payloads or {}).get(spec.payload_key) or {})
    href = back_href or spec.default_back_href
    label = back_label or spec.default_back_label
    payload_json = _json_for_script(payload)
    render_subpage_body_iframe(
        _cached_rwa_explore_server_iframe_html(
            kind,
            payload_json,
            related_chips,
            href,
            label,
        ),
        height=1800,
    )
    inject_rwa_explore_host_canvas_override(kind=kind)
    inject_rwa_explore_iframe_table_actions(kind=kind, payload=payload)
