"""Streamlit RWA Global Market Overview — server-rendered deep iframe (parity with ``rwa-global.html``)."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from streamlit_tmmf_static import (
    _STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH,
    _TMMF_SERVER_INLINE_HOST_MODAL_JS,
    _TMMF_SERVER_TABLE_WIRE_JS,
    _json_for_script,
    _read_js_files,
)

_REPO = Path(__file__).resolve().parent
_STATIC = _REPO / "static_home"
_DATA = _STATIC / "data"

_RWA_GLOBAL_IFRAME_CSS_VERSION = "5"
RWA_GLOBAL_IFRAME_BUILD = "5"
RWA_GLOBAL_CANVAS_OVERRIDE_VERSION = "5"
RWA_GLOBAL_TABLE_PANEL_VERSION = "1"

RWA_GLOBAL_GH_PAGE_WASH = "#f3f7fb"
RWA_GLOBAL_GH_ZONE_SOFT = "#e8eff5"

_RWA_GLOBAL_MEASURE_HEIGHT_JS = """
function measureRwaGlobalContentHeight() {
  if (window.__TMMF_MODAL_OPEN) return null;
  var scrollY = window.scrollY || document.documentElement.scrollTop || 0;
  var nodes = [
    document.querySelector(".page-back-below-header"),
    document.querySelector("main.page-shell.etp-mock-shell"),
    document.getElementById("js-rwa-global-footer-note"),
    document.getElementById("rwa-global-net-wrap"),
    document.getElementById("js-rwa-global-dashboard"),
  ];
  var maxBottom = 0;
  nodes.forEach(function (el) {
    if (!el) return;
    var rect = el.getBoundingClientRect();
    if (
      rect.height <= 0 &&
      el.id === "js-rwa-global-footer-note" &&
      !(el.textContent || "").trim()
    ) {
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

_RWA_GLOBAL_SERVER_CHART_BOOT_JS = """
(function () {
  var CHART_FONT = 'Outfit, "Segoe UI", system-ui, sans-serif';
  function estimateChartMargins(yLabels, textLabels, shellWidth) {
    var i, maxLab = 4, maxPct = 6;
    for (i = 0; i < yLabels.length; i++) {
      maxLab = Math.max(maxLab, String(yLabels[i] || "").length);
    }
    for (i = 0; i < textLabels.length; i++) {
      maxPct = Math.max(maxPct, String(textLabels[i] || "").length);
    }
    var sw = typeof shellWidth === "number" && shellWidth > 0 ? shellWidth : 560;
    var fromText = Math.round(maxLab * 6.25 + 48);
    var minByWidth = Math.round(sw * 0.24);
    var marginLeft = Math.min(312, Math.max(140, Math.max(fromText, minByWidth) + 12));
    var marginRight = Math.min(188, Math.max(96, Math.round(maxPct * 5.5 + 64)));
    return { l: marginLeft, r: marginRight };
  }
  function formatUsdAxisTick(v) {
    var n = Number(v) || 0, abs = Math.abs(n);
    if (abs >= 1e9) return "$" + (n / 1e9).toFixed(abs >= 10e9 ? 0 : 1).replace(/\\.0$/, "") + "B";
    if (abs >= 1e6) return "$" + (n / 1e6).toFixed(abs >= 10e6 ? 0 : 1).replace(/\\.0$/, "") + "M";
    if (abs >= 1e3) return "$" + (n / 1e3).toFixed(abs >= 10e3 ? 0 : 1).replace(/\\.0$/, "") + "K";
    return "$" + Math.round(n).toLocaleString();
  }
  function niceTickStep(rawStep) {
    if (!(rawStep > 0)) return 1;
    var pow = Math.pow(10, Math.floor(Math.log(rawStep) / Math.LN10));
    var base = rawStep / pow;
    var mult = base <= 1 ? 1 : base <= 2 ? 2 : base <= 5 ? 5 : 10;
    return mult * pow;
  }
  function buildCurrencyAxisProps(values, plotWidth, theme) {
    var maxVal = 0, i;
    for (i = 0; i < values.length; i++) maxVal = Math.max(maxVal, Number(values[i]) || 0);
    var width = typeof plotWidth === "number" && plotWidth > 0 ? plotWidth : 260;
    var tickCount = width < 150 ? 2 : width < 240 ? 3 : width < 360 ? 4 : 5;
    var step = niceTickStep(maxVal / Math.max(1, tickCount - 1));
    var maxTick = step * Math.max(1, Math.ceil(maxVal / step));
    var vals = [];
    for (i = 0; i <= maxTick + step * 0.2; i += step) {
      vals.push(i);
      if (vals.length > 8) break;
    }
    var ink = theme && theme.ink ? theme.ink : "#1a3d5c";
    return {
      tickangle: -30,
      tickvals: vals,
      ticktext: vals.map(formatUsdAxisTick),
      tickfont: { family: CHART_FONT, size: width < 220 ? 10 : 11, color: ink },
    };
  }
  function drawRwaGlobalDashboardChart() {
    var cfg = window.__RWA_GLOBAL_SERVER_CHART;
    var chartEl = document.getElementById("js-rwa-global-dashboard-chart");
    if (!cfg || !chartEl || typeof Plotly === "undefined") return;
    var league = cfg.league || {};
    var rowsFiltered = league.rows_full || [];
    var nameCol = league.name_column || "Network";
    var valCol = league.value_column || "Total Value";
    try { Plotly.purge(chartEl); } catch (e) {}
    if (!rowsFiltered.length) { chartEl.innerHTML = ""; return; }
    var built = typeof window.buildTopNPlusOtherChartRows === "function"
      ? window.buildTopNPlusOtherChartRows(rowsFiltered, {
          nameCol: nameCol, valCol: valCol, topN: 5, includeOther: true,
        })
      : null;
    if (!built) return;
    var y = built.y, x = built.x, text = built.text, barCount = built.barCount;
    var theme = typeof window.getZoneChartTheme === "function"
      ? window.getZoneChartTheme(chartEl) : null;
    var barColor = theme ? theme.bar : "#2a5f82";
    var barLine = theme ? theme.barLine : "#1a3d5c";
    var ink = theme ? theme.ink : "#1a3d5c";
    var inkMuted = theme ? theme.inkMuted : "#2a5f82";
    var shell = chartEl.closest(".stable-dash-chart-body") || chartEl.parentElement;
    var shellW = shell && shell.clientWidth ? shell.clientWidth : chartEl.offsetWidth || 560;
    var m = estimateChartMargins(y, text, shellW);
    var axisProps = buildCurrencyAxisProps(x, Math.max(120, shellW - m.l - m.r), theme);
    var trace = {
      type: "bar", x: x, y: y, orientation: "h",
      width: Math.min(0.9, Math.max(0.52, 0.86 - barCount * 0.028)),
      marker: { color: barColor, line: { color: barLine, width: 0.5 } },
      showlegend: false, text: text, textposition: "outside",
      textfont: { family: CHART_FONT, size: 11, color: inkMuted },
      cliponaxis: false,
      hovertemplate: "<b>%{y}</b><br>Total value: %{x:$,.0f}<br>%{text}<extra></extra>",
    };
    var layout = {
      height: 286, autosize: true,
      margin: { l: m.l, r: m.r, t: 12, b: 56, pad: 2 },
      bargap: barCount >= 6 ? 0.11 : 0.14,
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "#f8fafc",
      font: { family: CHART_FONT, size: 12, color: ink }, showlegend: false,
      xaxis: Object.assign({ gridcolor: "rgba(199,216,232,0.45)", zeroline: false }, axisProps),
      yaxis: { automargin: true, tickfont: { family: CHART_FONT, size: 11, color: ink } },
    };
    Plotly.react(chartEl, [trace], layout, { displayModeBar: false, responsive: true, scrollZoom: false });
    setTimeout(function () {
      try { Plotly.Plots.resize(chartEl); } catch (e2) {}
      if (typeof window.parent.postMessage === "function") {
        var h = typeof measureRwaGlobalContentHeight === "function" ? measureRwaGlobalContentHeight() : null;
        if (h !== null && h > 200) {
          window.parent.postMessage({ type: "streamlit:setFrameHeight", height: h }, "*");
          window.parent.postMessage({ type: "jpm-tmmf-height", height: h }, "*");
        }
      }
    }, 0);
  }
  function bootChart() {
    drawRwaGlobalDashboardChart();
    window.addEventListener("resize", function () {
      setTimeout(drawRwaGlobalDashboardChart, 120);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bootChart);
  else bootChart();
  [100, 500, 1500].forEach(function (ms) { setTimeout(bootChart, ms); });
})();
"""

_RWA_GLOBAL_SERVER_TABLE_WIRE_JS = """
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
    wireBlock({
      hostId: "rwa-global-net-wrap",
      actionsId: "rwa-global-net-table-actions",
      metaActionsId: "rwa-global-net-meta-actions",
      inputId: "rwa-global-net-q",
      noteId: "rwa-global-net-note",
      entityPlural: "networks",
      exportKey: "rwa-global-net",
      title: "Networks table",
      filename: "rwa-global-networks",
      sheetName: "Networks",
    });
  }
  window.__rwaGlobalWireServerTables = boot;
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
  setTimeout(boot, 0);
  setTimeout(boot, 400);
  setTimeout(boot, 1200);
})();
"""

_RWA_GLOBAL_IFRAME_BACK_LINK = """
<div class="page-back-below-header">
  <p class="back-link back-link--below-header">
    <a href="{back_href}">{back_label_html}</a>
  </p>
</div>
"""


def _static_rwa_global_payload_fallback(*, error: str = "") -> dict[str, Any]:
    path = _DATA / "rwa_global_market.json"
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
    return {"rwa_global_market.json": data}


def load_rwa_global_iframe_payloads() -> dict[str, Any]:
    from rwa_global_page_payloads import build_rwa_global_page_payload

    payload = build_rwa_global_page_payload(for_streamlit=True)
    return {"rwa_global_market.json": payload}


def get_rwa_global_iframe_payloads() -> dict[str, Any]:
    from streamlit_payload_stale_first import load_static_first_with_live_fallback, mark_payload_map_stale

    return load_static_first_with_live_fallback(
        load_stale=lambda: _static_rwa_global_payload_fallback() or None,
        load_live_cached=_cached_rwa_global_iframe_payloads,
        mark_stale=mark_payload_map_stale,
    )


@st.cache_resource(show_spinner=False)
def _cached_iframe_rwa_global_stylesheet(*, _css_version: str = _RWA_GLOBAL_IFRAME_CSS_VERSION) -> str:
    from streamlit_site_parity import (
        _iframe_rwa_global_mock_css,
        deep_iframe_back_link_clickable_css,
        deep_iframe_kpi_flatten_css,
        deep_iframe_related_chips_css,
        deep_iframe_rwa_zone_body_flatten_css,
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
    for rel in ("mockups/etp-inner-page-mock.css", "mockups/rwa-global-inner-page-mock.css"):
        path = _STATIC / rel
        if path.is_file():
            chunks.append(_iframe_rwa_global_mock_css(path.read_text(encoding="utf-8")))
    chunks.append(
        """
html, body.page-rwa-global-iframe.site-experience {
  margin: 0;
  padding: 0;
  background: var(--wash, #f3f7fb);
  overflow: hidden;
}
html::before,
html::after,
body.page-rwa-global-iframe::before,
body.page-rwa-global-iframe::after {
  display: none !important;
  content: none !important;
  height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
}
body.page-rwa-global-iframe .page-back-below-header {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0.35rem 1.25rem 0;
  box-sizing: border-box;
}
body.page-rwa-global-iframe p.back-link.back-link--below-header {
  margin: 0.2rem 0 0.85rem;
}
body.page-rwa-global-iframe.site-experience.page-inner--rich .back-link--below-header a {
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
body.page-rwa-global-iframe .page-shell.etp-mock-shell {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0 1.25rem 1.5rem;
  box-sizing: border-box;
}
body.page-rwa-global-iframe .home-reveal {
  opacity: 1 !important;
  transform: none !important;
}
"""
    )
    scope = "body.page-rwa-global-iframe"
    chunks.append(deep_iframe_kpi_flatten_css(scope=scope, zone="rwa"))
    chunks.append(deep_iframe_rwa_zone_body_flatten_css(scope=scope, soft=RWA_GLOBAL_GH_ZONE_SOFT))
    chunks.append(deep_iframe_table_panel_css(scope=scope))
    chunks.append(deep_iframe_table_height_lock_css(scope=scope))
    chunks.append(deep_iframe_related_chips_css(scope=scope, zone="rwa"))
    chunks.append(deep_iframe_back_link_clickable_css(scope=scope))
    return "\n".join(chunks)


def rwa_global_github_canvas_override_css(
    *, version: str = RWA_GLOBAL_CANVAS_OVERRIDE_VERSION
) -> str:
    from streamlit_site_parity import deep_iframe_kpi_flatten_css

    wash = RWA_GLOBAL_GH_PAGE_WASH
    soft = RWA_GLOBAL_GH_ZONE_SOFT
    scope = "body.page-rwa-global-iframe"
    return f"""
/* RWA Global GitHub Pages canvas override v{version} */
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
{scope} .etp-mock-zone.inner-rich-zone.zone--rwa,
{scope} .etp-mock-zone .inner-rich-zone__body {{
  background: {soft} !important;
  background-color: {soft} !important;
  background-image: none !important;
}}
{scope} .inner-rich-block,
{scope} .etp-mock-key-obs-block,
{scope} .etp-mock-key-obs-block .crypto-story-callout,
{scope} #js-rwa-global-macro .crypto-story-callout,
{scope} .etp-mock-insights__panel,
{scope} .etp-mock-dash__panel,
{scope} .rwa-kpi-row--home-grid .rwa-kpi-cell,
{scope} .etp-mock-table-block,
{scope} .rwa-deep-league-panel {{
  background: #fff !important;
  background-color: #fff !important;
  background-image: none !important;
}}
{scope} .etp-mock-key-obs-block .crypto-story-callout__note {{
  background: rgb(62 92 116 / 0.06) !important;
  background-image: none !important;
}}
""" + deep_iframe_kpi_flatten_css(scope=scope, zone="rwa")


def rwa_global_iframe_canvas_override_js(
    *, version: str = RWA_GLOBAL_CANVAS_OVERRIDE_VERSION
) -> str:
    wash = RWA_GLOBAL_GH_PAGE_WASH
    soft = RWA_GLOBAL_GH_ZONE_SOFT
    return f"""
<script id="rwa-global-gh-canvas-override-js-v{version}">
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
      ".inner-rich-block, .etp-mock-key-obs-block, .crypto-story-callout, .etp-mock-insights__panel, .etp-mock-dash__panel, .rwa-kpi-row--home-grid .rwa-kpi-cell, .etp-mock-table-block"
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


def rwa_global_host_canvas_override_css(
    *, version: str = RWA_GLOBAL_CANVAS_OVERRIDE_VERSION
) -> str:
    wash = RWA_GLOBAL_GH_PAGE_WASH
    return f"""
<style id="rwa-global-gh-host-canvas-override-v{version}">
.stApp:has(.streamlit-rwa-global-iframe-page),
.withScreencast:has(.streamlit-rwa-global-iframe-page),
[data-testid="stScreencast"]:has(.streamlit-rwa-global-iframe-page),
.stApp:has(.streamlit-rwa-global-iframe-page) [data-testid="stAppViewContainer"],
.stApp:has(.streamlit-rwa-global-iframe-page) section.main,
.stApp:has(.streamlit-rwa-global-iframe-page) [data-testid="stMain"],
.stApp:has(.streamlit-rwa-global-iframe-page) [data-testid="stMainBlockContainer"] {{
  background: {wash} !important;
  background-color: {wash} !important;
  background-image: none !important;
}}
</style>
"""


def rwa_global_host_canvas_override_js(
    *, version: str = RWA_GLOBAL_CANVAS_OVERRIDE_VERSION
) -> str:
    wash = RWA_GLOBAL_GH_PAGE_WASH
    return f"""
<script id="rwa-global-gh-host-canvas-override-js-v{version}">
(function () {{
  var WASH = "{wash}";
  function paint() {{
    document.querySelectorAll(
      ".stApp, [data-testid='stAppViewContainer'], section.main, [data-testid='stMain'], [data-testid='stMainBlockContainer']"
    ).forEach(function (el) {{
      if (!el.closest || !el.closest(".stApp:has(.streamlit-rwa-global-iframe-page)")) return;
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


def inject_rwa_global_host_canvas_override() -> None:
    st.markdown(
        rwa_global_host_canvas_override_css() + rwa_global_host_canvas_override_js(),
        unsafe_allow_html=True,
    )


def inject_rwa_global_iframe_table_actions(payload: dict[str, Any]) -> None:
    from streamlit_server_deep_page import build_rwa_global_server_export_config

    js_libs = _read_js_files(("table-fullscreen.js", "table-download.js"))
    export_json = json.dumps(build_rwa_global_server_export_config(payload))
    libs_json = json.dumps(js_libs)
    patch_json = json.dumps(_STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH.strip())
    wire_json = json.dumps(_RWA_GLOBAL_SERVER_TABLE_WIRE_JS.strip())
    host_modal_json = json.dumps(_TMMF_SERVER_INLINE_HOST_MODAL_JS.strip())
    bootstrap = f"""
<script>
(function () {{
  var win = window.parent;
  var doc = win.document;
  if (win.__jpmRwaGlobalIframeTableHostBound) return;
  win.__jpmRwaGlobalIframeTableHostBound = true;

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

  function findRwaGlobalInner() {{
    var frames = doc.querySelectorAll("iframe");
    for (var i = 0; i < frames.length; i++) {{
      try {{
        var inner = frames[i].contentDocument;
        if (
          inner &&
          inner.body &&
          inner.body.classList &&
          inner.body.classList.contains("mock-rwa-global-inner")
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
    if (typeof hit.win.__rwaGlobalWireServerTables === "function") {{
      hit.win.__rwaGlobalWireServerTables();
    }}
    return true;
  }}

  function boot() {{
    if (!doc.querySelector(".streamlit-rwa-global-iframe-page")) return false;
    ensureHostModal();
    var hit = findRwaGlobalInner();
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


def _rwa_global_back_link_html(*, href: str, label: str) -> str:
    label_html = (
        escape(label)
        .replace("\u2190", "&larr;")
        .replace("\u00b7", "&middot;")
    )
    return _RWA_GLOBAL_IFRAME_BACK_LINK.format(
        back_href=escape(href),
        back_label_html=label_html,
    )


def build_rwa_global_server_iframe_html(
    *,
    payload: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=onchain",
    back_label: str = "← Back to home · On-chain preview",
) -> str:
    from streamlit_server_deep_page import build_rwa_global_server_zone_html
    from streamlit_site_parity import deep_iframe_table_panel_css, iframe_internal_link_script

    css = _cached_iframe_rwa_global_stylesheet(_css_version=_RWA_GLOBAL_IFRAME_CSS_VERSION)
    override_css = rwa_global_github_canvas_override_css()
    table_panel_css = deep_iframe_table_panel_css(scope="body.page-rwa-global-iframe")
    back_link = _rwa_global_back_link_html(href=back_href, label=back_label)
    zone = build_rwa_global_server_zone_html(payload=payload, related_chips=related_chips)
    chart_js_libs = _read_js_files(("static-base.js",))
    chart_cfg = json.dumps(
        {
            "league": {
                "rows_full": payload.get("rows") or [],
                "name_column": "Network",
                "value_column": "Total Value",
            },
            "payload": {"chart_max_bars": 5, "chart_include_other": True},
        }
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<!-- rwa-global-iframe-build-v{RWA_GLOBAL_IFRAME_BUILD} -->
<style id="rwa-global-iframe-css-v{_RWA_GLOBAL_IFRAME_CSS_VERSION}">{css}</style>
<style id="rwa-global-gh-canvas-override-v{RWA_GLOBAL_CANVAS_OVERRIDE_VERSION}">{override_css}</style>
<style id="rwa-global-table-panel-v{RWA_GLOBAL_TABLE_PANEL_VERSION}">{table_panel_css}</style>
</head>
<body
  class="page-rwa-global page-rwa-global-iframe site-experience page-inner--rich mock-rwa-global-inner"
  data-methodology="rwa-global"
>
{back_link}
{zone}
<script defer src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
<script>
{chart_js_libs}
window.__RWA_GLOBAL_SERVER_CHART = {chart_cfg};
</script>
<script>
{_RWA_GLOBAL_SERVER_CHART_BOOT_JS}
</script>
<script>
{_RWA_GLOBAL_MEASURE_HEIGHT_JS}
(function () {{
  function sendHeight() {{
    if (typeof window.parent.postMessage !== "function") return;
    var h = measureRwaGlobalContentHeight();
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
      "#js-rwa-global-insights",
      "#js-rwa-global-dashboard",
      "#rwa-global-net-wrap",
      "#js-rwa-global-footer-note",
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
    ["article.etp-mock-zone", "#js-rwa-global-dashboard", "#rwa-global-net-wrap"].forEach(function (sel) {{
      var el = document.querySelector(sel);
      if (el) mo.observe(el, {{ childList: true, subtree: true, attributes: true }});
    }});
  }}
  [100, 400, 1000, 2500, 5000, 8000].forEach(function (ms) {{
    setTimeout(sendHeight, ms);
  }});
}})();
</script>
{rwa_global_iframe_canvas_override_js()}
{iframe_internal_link_script()}
</body>
</html>"""


build_rwa_global_body_iframe_html = build_rwa_global_server_iframe_html


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_rwa_global_iframe_payloads() -> dict[str, Any]:
    return load_rwa_global_iframe_payloads()


def render_rwa_global_body_iframe(
    *,
    payloads: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=onchain",
    back_label: str = "← Back to home · On-chain preview",
) -> None:
    from streamlit_site_parity import render_subpage_body_iframe

    payload = dict((payloads or {}).get("rwa_global_market.json") or {})
    html = build_rwa_global_server_iframe_html(
        payload=payload,
        related_chips=related_chips,
        back_href=back_href,
        back_label=back_label,
    )
    render_subpage_body_iframe(
        html,
        height=1400,
    )
    inject_rwa_global_host_canvas_override()
    inject_rwa_global_iframe_table_actions(payload)
