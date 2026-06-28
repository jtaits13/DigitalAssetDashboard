"""Streamlit Stablecoins full page — server-rendered iframe (parity with ``rwa-stablecoins.html``)."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from streamlit_tmmf_static import (
    _STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH,
    _TMMF_SERVER_TABLE_WIRE_JS,
    _json_for_script,
    _read_js_files,
)

_REPO = Path(__file__).resolve().parent
_STATIC = _REPO / "static_home"
_DATA = _STATIC / "data"

_STABLE_IFRAME_CSS_VERSION = "3"
STABLE_CANVAS_OVERRIDE_VERSION = "2"

# GitHub Pages canvas tokens (static_home/styles.css --wash; zone --hx-stable-soft).
STABLE_GH_PAGE_WASH = "#f3f7fb"
STABLE_GH_ZONE_SOFT = "#ebf2f7"

_STABLE_MEASURE_HEIGHT_JS = """
function measureStableContentHeight() {
  if (window.__TMMF_MODAL_OPEN) return null;
  var scrollY = window.scrollY || document.documentElement.scrollTop || 0;
  var nodes = [
    document.querySelector(".page-back-below-header"),
    document.querySelector("main.page-shell.etp-mock-shell"),
    document.getElementById("js-deep-footer-note"),
  ];
  var maxBottom = 0;
  nodes.forEach(function (el) {
    if (!el) return;
    var rect = el.getBoundingClientRect();
    if (rect.height <= 0 && el.id === "js-deep-footer-note" && !(el.textContent || "").trim()) {
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

_STABLE_SERVER_CHART_BOOT_JS = """
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
  function drawStableDashboardChart() {
    var cfg = window.__STABLE_SERVER_CHART;
    var chartEl = document.getElementById("js-deep-dashboard-chart");
    if (!cfg || !chartEl || typeof Plotly === "undefined") return;
    var league = cfg.league || {};
    var payload = cfg.payload || {};
    var rowsFiltered = league.rows_full || [];
    var nameCol = league.name_column || "Network";
    var valCol = league.value_column || "Total Value";
    var maxBars = 5;
    try { Plotly.purge(chartEl); } catch (e) {}
    if (!rowsFiltered.length) { chartEl.innerHTML = ""; return; }
    var built = typeof window.buildTopNPlusOtherChartRows === "function"
      ? window.buildTopNPlusOtherChartRows(rowsFiltered, {
          nameCol: nameCol, valCol: valCol, topN: maxBars, includeOther: true,
        })
      : null;
    var y, x, text, barCount;
    if (built) {
      y = built.y; x = built.x; text = built.text; barCount = built.barCount;
    } else {
      return;
    }
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
    var barThickness = Math.min(0.9, Math.max(0.52, 0.86 - barCount * 0.028));
    var trace = {
      type: "bar", x: x, y: y, orientation: "h", width: barThickness,
      marker: { color: barColor, line: { color: barLine, width: 0.5 } },
      showlegend: false, text: text, textposition: "outside",
      textfont: { family: CHART_FONT, size: 11, color: inkMuted },
      cliponaxis: false,
      hovertemplate: "<b>%{y}</b><br>Value: %{x:$,.0f}<br>%{text}<extra></extra>",
    };
    var heightPx = 286;
    var layout = {
      height: heightPx, autosize: true,
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
    }, 0);
  }
  function bootChart() {
    drawStableDashboardChart();
    window.addEventListener("resize", function () {
      setTimeout(drawStableDashboardChart, 120);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bootChart);
  else bootChart();
})();
"""

_STABLE_IFRAME_TABLE_HOST_BOOTSTRAP_JS = """
<script>
(function () {
  var win = window.parent && window.parent !== window ? window.parent : window;
  var doc = win.document;
  if (win.__jpmStableIframeTableHostBound) return;
  win.__jpmStableIframeTableHostBound = true;

  function stableBodyFrame() {
    var frames = doc.querySelectorAll("iframe");
    for (var i = 0; i < frames.length; i++) {
      try {
        var inner = frames[i].contentDocument;
        if (
          inner &&
          inner.body &&
          inner.body.classList &&
          inner.body.classList.contains("mock-stable-inner")
        ) {
          return { frame: frames[i], inner: inner, win: inner.defaultView || inner.parentWindow };
        }
      } catch (e) {}
    }
    return null;
  }

  function bootTables() {
    var hit = stableBodyFrame();
    if (!hit || !hit.win) return false;
    if (typeof hit.win.__tmmfWireServerTables === "function") {
      hit.win.__tmmfWireServerTables();
      return true;
    }
    return false;
  }

  function boot() {
    bootTables();
  }

  boot();
  win.addEventListener("load", boot);
  [100, 400, 1200, 3000, 6000, 10000].forEach(function (ms) {
    win.setTimeout(boot, ms);
  });
  if (typeof MutationObserver !== "undefined") {
    var mo = new MutationObserver(boot);
    mo.observe(doc.body, { childList: true, subtree: true });
    win.setTimeout(function () { mo.disconnect(); }, 20000);
  }
})();
</script>
"""

_STABLE_IFRAME_BACK_LINK = """
<div class="page-back-below-header">
  <p class="back-link back-link--below-header">
    <a class="stable-server-back-anchor" data-deep-back="explore" href="{back_href}">{back_label_html}</a>
  </p>
</div>
"""


def stablecoins_github_canvas_override_css(*, version: str = STABLE_CANVAS_OVERRIDE_VERSION) -> str:
    wash = STABLE_GH_PAGE_WASH
    soft = STABLE_GH_ZONE_SOFT
    scope = "body.page-rwa-deep-stablecoins"
    return f"""
/* Stablecoins GitHub Pages canvas override v{version} */
html, {scope}.site-experience,
{scope}.site-experience.page-inner--rich,
{scope}.mock-stable-inner.site-experience {{
  background: {wash} !important;
  background-color: {wash} !important;
  background-image: none !important;
}}
{scope} .page-shell.etp-mock-shell {{
  background: transparent !important;
  background-image: none !important;
}}
{scope} .inner-rich-zone.zone--stable,
{scope} .inner-rich-zone.zone--stable .inner-rich-zone__body,
{scope} .etp-mock-zone.inner-rich-zone.zone--stable,
{scope} .etp-mock-zone .inner-rich-zone__body,
{scope} .methodology-panel {{
  background: {soft} !important;
  background-color: {soft} !important;
  background-image: none !important;
}}
{scope} .inner-rich-block,
{scope} .etp-mock-key-obs-block,
{scope} .etp-mock-key-obs-block .crypto-story-callout,
{scope} #js-deep-ko .crypto-story-callout,
{scope} .etp-mock-key-obs-block .review-note.ko-disclaimer,
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
"""


def stablecoins_iframe_canvas_override_js(*, version: str = STABLE_CANVAS_OVERRIDE_VERSION) -> str:
    wash = STABLE_GH_PAGE_WASH
    soft = STABLE_GH_ZONE_SOFT
    return f"""
<script id="stable-gh-canvas-override-js-v{version}">
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
      ".inner-rich-zone.zone--stable, .inner-rich-zone.zone--stable .inner-rich-zone__body, .methodology-panel"
    ).forEach(function (el) {{ setBg(el, SOFT); }});
    document.querySelectorAll(
      ".inner-rich-block, .etp-mock-key-obs-block, .crypto-story-callout, .review-note.ko-disclaimer, .etp-mock-insights__panel, .etp-mock-dash__panel, .rwa-kpi-row--home-grid .rwa-kpi-cell"
    ).forEach(function (el) {{ setBg(el, WHITE); }});
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


def stablecoins_host_canvas_override_css(*, version: str = STABLE_CANVAS_OVERRIDE_VERSION) -> str:
    wash = STABLE_GH_PAGE_WASH
    return f"""
<style id="stable-gh-host-canvas-override-v{version}">
.stApp:has(.streamlit-stablecoins-iframe-page),
.withScreencast:has(.streamlit-stablecoins-iframe-page),
[data-testid="stScreencast"]:has(.streamlit-stablecoins-iframe-page),
.stApp:has(.streamlit-stablecoins-iframe-page) [data-testid="stAppViewContainer"],
.stApp:has(.streamlit-stablecoins-iframe-page) section.main,
.stApp:has(.streamlit-stablecoins-iframe-page) [data-testid="stMain"],
.stApp:has(.streamlit-stablecoins-iframe-page) [data-testid="stMainBlockContainer"],
.stApp:has(.streamlit-stablecoins-iframe-page) .block-container,
.stApp:has(.streamlit-stablecoins-iframe-page) [data-testid="stVerticalBlock"],
.stApp:has(.streamlit-stablecoins-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe),
.stApp:has(.streamlit-stablecoins-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe) [data-testid="stVerticalBlock"],
.stApp:has(.streamlit-stablecoins-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe) [data-testid="stHtml"],
.stApp:has(.streamlit-stablecoins-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe) [data-testid="stHtml"] > div {{
  background: {wash} !important;
  background-color: {wash} !important;
  background-image: none !important;
}}
</style>
"""


def stablecoins_host_canvas_override_js(*, version: str = STABLE_CANVAS_OVERRIDE_VERSION) -> str:
    wash = STABLE_GH_PAGE_WASH
    return f"""
<script id="stable-gh-host-canvas-override-js-v{version}">
(function () {{
  var WASH = "{wash}";
  var doc = window.parent && window.parent.document ? window.parent.document : document;
  function paint() {{
    var app = doc.querySelector(".stApp");
    if (!app || !app.querySelector(".streamlit-stablecoins-iframe-page")) return;
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
      if (!el.querySelector(".streamlit-stablecoins-iframe-page")) return;
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


def inject_stablecoins_iframe_table_bootstrap() -> None:
    """Re-wire table fullscreen/download on the Stablecoins body iframe from the Streamlit host."""
    components.html(_STABLE_IFRAME_TABLE_HOST_BOOTSTRAP_JS, height=0, width=0)


def inject_stablecoins_host_canvas_override() -> None:
    """Apply GitHub Pages wash to the Streamlit host shell on the Stablecoins route."""
    st.markdown(stablecoins_host_canvas_override_css(), unsafe_allow_html=True)
    components.html(stablecoins_host_canvas_override_js(), height=0, width=0)


def _static_stablecoins_deep_fallback(*, error: str = "") -> dict[str, Any]:
    path = _DATA / "rwa_stablecoins.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    if error:
        data = dict(data)
        data["error"] = error
        data["stale"] = True
    return data


def load_stablecoins_deep_payload() -> dict[str, Any]:
    """Live Stablecoins deep-page JSON (same shape as ``static_home/data/rwa_stablecoins.json``)."""
    from rwa_streamlit_fetch_cache import cached_rwa_stablecoins_data
    from scripts.export_static_site_data import _build_rwa_stablecoins_deep_payload

    sc_pack = cached_rwa_stablecoins_data()
    manifest: dict[str, Any] = {"errors": []}
    payload = _build_rwa_stablecoins_deep_payload(
        sc_pack,
        manifest,
        [],
    )
    payload["back_href"] = "/?jd_scroll=stablecoins"
    return payload


def get_stablecoins_deep_payload() -> dict[str, Any]:
    from streamlit_payload_stale_first import load_static_first_with_live_fallback, mark_dict_stale

    return load_static_first_with_live_fallback(
        load_stale=lambda: _static_stablecoins_deep_fallback() or None,
        load_live_cached=_cached_stablecoins_deep_payload,
        mark_stale=mark_dict_stale,
    )


@st.cache_resource(show_spinner=False)
def _cached_iframe_stable_stylesheet() -> str:
    """Same CSS stack as ``static_home/rwa-stablecoins.html`` (iframe-safe, no mock banners)."""
    from streamlit_site_parity import _iframe_stable_mock_css

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
    for rel in ("mockups/etp-inner-page-mock.css", "mockups/stable-inner-page-mock.css"):
        path = _STATIC / rel
        if path.is_file():
            chunks.append(_iframe_stable_mock_css(path.read_text(encoding="utf-8")))
    chunks.append(
        """
html, body.page-rwa-deep-stablecoins.site-experience {
  margin: 0;
  padding: 0;
  background: var(--wash, #f3f7fb) !important;
  background-image: none !important;
  overflow: hidden;
}
body.page-rwa-deep-stablecoins.site-experience.page-inner--rich,
body.page-rwa-deep-stablecoins.mock-stable-inner.site-experience {
  background: var(--wash, #f3f7fb) !important;
  background-image: none !important;
}
html::before, html::after,
body.page-rwa-deep-stablecoins::before,
body.page-rwa-deep-stablecoins::after {
  display: none !important;
  content: none !important;
  height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
}
body.page-rwa-deep-stablecoins .page-back-below-header {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0.35rem 1.25rem 0;
  box-sizing: border-box;
}
body.page-rwa-deep-stablecoins p.back-link.back-link--below-header {
  margin: 0.2rem 0 0.85rem;
}
body.page-rwa-deep-stablecoins.site-experience.page-inner--rich .back-link--below-header a {
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
body.page-rwa-deep-stablecoins.site-experience.page-inner--rich .back-link--below-header a:hover {
  color: var(--hx-stable-bright, #507188);
  border-color: rgb(80 113 136 / 0.45);
  background: #f8fcfe;
}
body.page-rwa-deep-stablecoins .page-shell.etp-mock-shell {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0 1.25rem 1.5rem;
  box-sizing: border-box;
  background: transparent !important;
}
body.page-rwa-deep-stablecoins .home-reveal {
  opacity: 1 !important;
  transform: none !important;
}
body.page-rwa-deep-stablecoins .inner-rich-zone.zone--stable,
body.page-rwa-deep-stablecoins.mock-stable-inner .etp-mock-zone.inner-rich-zone.zone--stable {
  background: var(--hx-stable-soft, #ebf2f7) !important;
  background-image: none !important;
}
body.page-rwa-deep-stablecoins .inner-rich-zone.zone--stable .inner-rich-zone__body,
body.page-rwa-deep-stablecoins.mock-stable-inner .etp-mock-zone .inner-rich-zone__body {
  background: var(--hx-stable-soft, #ebf2f7) !important;
  background-image: none !important;
}
body.page-rwa-deep-stablecoins .methodology-panel {
  background: var(--hx-stable-soft, #ebf2f7) !important;
}
body.page-rwa-deep-stablecoins.page-inner--rich .inner-rich-block,
body.page-rwa-deep-stablecoins .etp-mock-key-obs-block,
body.page-rwa-deep-stablecoins .etp-mock-key-obs-block .crypto-story-callout,
body.page-rwa-deep-stablecoins #js-deep-ko .crypto-story-callout {
  background: #fff !important;
  background-image: none !important;
}
body.page-rwa-deep-stablecoins .rwa-table-modal--streamlit-fallback:not([hidden]) {
  display: grid !important;
  place-items: center !important;
  padding: 1.25rem !important;
  box-sizing: border-box !important;
}
body.page-rwa-deep-stablecoins .rwa-table-modal--streamlit-fallback .rwa-table-modal__dialog {
  max-height: min(92vh, 980px);
  width: min(96%, 1400px);
}
"""
    )
    return "\n".join(chunks)


def _stable_back_link_html(*, href: str, label: str) -> str:
    label_html = (
        escape(label)
        .replace("\u2190", "&larr;")
        .replace("\u00b7", "&middot;")
    )
    return _STABLE_IFRAME_BACK_LINK.format(back_href=escape(href), back_label_html=label_html)


def build_stablecoins_server_iframe_html(
    *,
    payload: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=stablecoins",
    back_label: str = "← Back to home · Stablecoins preview",
) -> str:
    """Self-contained iframe with GitHub Pages CSS and pre-rendered body."""
    from streamlit_server_deep_page import (
        build_stablecoins_server_export_config,
        build_stablecoins_server_zone_html,
    )
    from streamlit_site_parity import iframe_internal_link_script

    css = _cached_iframe_stable_stylesheet()
    override_css = stablecoins_github_canvas_override_css()
    back_link = _stable_back_link_html(href=back_href, label=back_label)
    zone = build_stablecoins_server_zone_html(payload=payload, related_chips=related_chips)
    table_js_libs = _read_js_files(("table-fullscreen.js", "table-download.js"))
    chart_js_libs = _read_js_files(("static-base.js",))
    export_json = json.dumps(build_stablecoins_server_export_config(payload))
    net = payload.get("networks") or {}
    chart_cfg = json.dumps(
        {
            "league": {
                "rows_full": net.get("rows_full") or [],
                "name_column": net.get("name_column") or "Network",
                "value_column": net.get("value_column") or "Total Value",
            },
            "payload": {"chart_max_bars": 5, "chart_include_other": True},
        }
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
<style id="stable-gh-canvas-override-v{STABLE_CANVAS_OVERRIDE_VERSION}">{override_css}</style>
</head>
<body
  class="page-rwa-deep page-rwa-deep-stablecoins site-experience page-inner--rich mock-stable-inner"
  data-methodology="rwa-stablecoins"
>
{back_link}
{zone}
<script defer src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
<script>
{table_js_libs}
window.__TMMF_SERVER_EXPORTS = {export_json};
</script>
<script>
{_STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH}
</script>
<script>
{_TMMF_SERVER_TABLE_WIRE_JS}
</script>
<script>
{chart_js_libs}
window.__STABLE_SERVER_CHART = {chart_cfg};
</script>
<script>
{_STABLE_SERVER_CHART_BOOT_JS}
</script>
<script>
{_STABLE_MEASURE_HEIGHT_JS}
(function () {{
  function sendHeight() {{
    if (typeof window.parent.postMessage !== "function") return;
    var h = measureStableContentHeight();
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
      "#js-deep-insights",
      "#deep-net-wrap",
      "#deep-plat-wrap",
      "#js-deep-footer-note",
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
    ["article.etp-mock-zone", "#deep-net-wrap", "#deep-plat-wrap"].forEach(function (sel) {{
      var el = document.querySelector(sel);
      if (el) mo.observe(el, {{ childList: true, subtree: true, attributes: true }});
    }});
  }}
  [100, 400, 1000, 2500, 5000, 8000].forEach(function (ms) {{
    setTimeout(sendHeight, ms);
  }});
}})();
</script>
{stablecoins_iframe_canvas_override_js()}
{iframe_internal_link_script()}
</body>
</html>"""


# Back-compat alias for verify script and any legacy callers.
build_stablecoins_body_iframe_html = build_stablecoins_server_iframe_html


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_stablecoins_deep_payload() -> dict[str, Any]:
    return load_stablecoins_deep_payload()


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_stablecoins_server_iframe_html(
    payload_json: str,
    related_chips: str,
    back_href: str,
    back_label: str,
    *,
    _css_version: str = _STABLE_IFRAME_CSS_VERSION,
) -> str:
    payload = json.loads(payload_json)
    return build_stablecoins_server_iframe_html(
        payload=payload,
        related_chips=related_chips,
        back_href=back_href,
        back_label=back_label,
    )


def render_stablecoins_body_iframe(
    *,
    payload: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=stablecoins",
    back_label: str = "← Back to home · Stablecoins preview",
) -> None:
    """Render the GitHub Pages Stablecoins zone inside a Streamlit iframe."""
    from streamlit_site_parity import render_subpage_body_iframe

    payload_json = _json_for_script(payload)
    render_subpage_body_iframe(
        _cached_stablecoins_server_iframe_html(
            payload_json,
            related_chips,
            back_href,
            back_label,
        ),
        height=1200,
    )
    inject_stablecoins_host_canvas_override()
    inject_stablecoins_iframe_table_bootstrap()
