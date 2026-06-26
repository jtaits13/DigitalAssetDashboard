"""Streamlit RWA Global Market Overview — static HTML iframe (parity with ``rwa-global.html``)."""

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
    _json_for_script,
    _read_js_files,
)

_REPO = Path(__file__).resolve().parent
_STATIC = _REPO / "static_home"
_DATA = _STATIC / "data"

_RWA_GLOBAL_JS_DEPS = (
    "static-base.js",
    "table-fullscreen.js",
    "table-download.js",
    "kpi-hints.js",
    "data-freshness.js",
    "page-methodology.js",
    "snapshot-kpi-shared.js",
    "rwa-onchain-home.js",
)
_RWA_GLOBAL_JS_BOOT = ("rwa-global-page.js",)

_RWA_GLOBAL_MEASURE_HEIGHT_JS = """
function measureRwaGlobalContentHeight() {
  if (window.__TMMF_MODAL_OPEN) return null;
  var scrollY = window.scrollY || document.documentElement.scrollTop || 0;
  var nodes = [
    document.querySelector(".page-back-below-header"),
    document.querySelector("main.page-shell.etp-mock-shell"),
    document.getElementById("js-rwa-global-footer-note"),
    document.getElementById("js-rwa-global-split"),
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

_RWA_GLOBAL_IFRAME_BACK_LINK = """
<div class="page-back-below-header">
  <p class="back-link back-link--below-header">
    <a href="{back_href}">{back_label_html}</a>
  </p>
</div>
"""

_RWA_GLOBAL_ZONE_BODY = """
<main class="page-shell etp-mock-shell">
  <article class="hub-section hub-section--panel inner-rich-zone zone--rwa home-zone home-zone--rwa etp-mock-zone">
    <div class="home-zone__stripe" aria-hidden="true"></div>
    <header class="home-zone__head">
      <span class="home-zone__badge" aria-hidden="true">RWA</span>
      <div class="home-zone__titles">
        <h1 class="page-intro__title">RWA Global Market Overview</h1>
        <div class="section-dek section-dek--wide page-intro__dek" id="js-rwa-global-dek"></div>
      </div>
    </header>
    <div class="home-zone__body inner-rich-zone__body etp-mock-zone__body">
      {related_chips}
      <div class="data-banner" id="js-rwa-global-banner" role="status" hidden></div>
      <p id="js-rwa-global-empty" class="alert info" hidden></p>
      <section class="etp-mock-snapshot" id="js-rwa-global-snapshot" aria-labelledby="rwa-gmo-snapshot-heading">
        <h2 class="subsection-head u-vh" id="rwa-gmo-snapshot-heading">Top-line snapshot</h2>
        <div id="js-rwa-global-kpis" aria-label="RWA Global Market KPI strip"></div>
        <p id="js-rwa-global-scope-note" class="rwa-scope-note" hidden></p>
        <div id="js-rwa-global-error-cta" class="cta-row" hidden></div>
      </section>
      <div id="js-rwa-global-detail-stack" hidden>
        <div
          class="inner-rich-block etp-mock-key-obs-block"
          id="js-rwa-global-ko-section"
          hidden
          aria-labelledby="rwa-gmo-ko-heading"
        >
          <h2 class="subsection-head u-vh" id="rwa-gmo-ko-heading">Key Observations</h2>
          <div id="js-rwa-global-macro"></div>
        </div>
        <div id="js-rwa-global-explore"></div>
        <section
          class="etp-mock-insights etp-mock-insights--crypto-full"
          id="js-rwa-global-insights"
          hidden
          aria-labelledby="js-rwa-global-insights-h"
        >
          <h2 class="u-vh" id="js-rwa-global-insights-h">Market structure</h2>
        </section>
        <section class="etp-mock-dashboard" id="js-rwa-global-dashboard" hidden aria-labelledby="js-rwa-global-dashboard-h">
          <h2 class="u-vh" id="js-rwa-global-dashboard-h">Chart and share movers</h2>
          <div class="etp-mock-dash__panel etp-mock-dash__panel--chart">
            <h3 class="etp-mock-dash__head">Top networks by value</h3>
            <div class="stable-dash-chart-body">
              <div
                id="js-rwa-global-dashboard-chart"
                class="aum-chart-host"
                role="img"
                aria-label="Top networks by total value"
              ></div>
            </div>
            <p class="etp-mock-chart__cap">
              Top <strong>5</strong> networks plus <strong>Other</strong> (remaining networks); market shares sum to
              <strong>100%</strong>. Bar length uses total value; labels show share.
            </p>
            <p class="etp-mock-chart__method">
              Plotly horizontal bars synced to the searchable networks table below.
            </p>
          </div>
          <div class="etp-mock-dash__panel etp-mock-dash__panel--movers">
            <h3 class="etp-mock-dash__head">Largest 30D share shifts (networks)</h3>
            <div id="js-rwa-global-share-movers"></div>
          </div>
        </section>
        <div id="js-rwa-global-split"></div>
        <div id="js-rwa-global-bottom-cta" class="cta-row rwa-deep-page-cta" hidden></div>
        <p class="timestamp-foot" id="js-rwa-global-footer-note"></p>
      </div>
    </div>
  </article>
  <p class="back-link">
    <a href="{back_href}">{back_label_html}</a>
  </p>
</main>
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
def _cached_iframe_rwa_global_stylesheet_v1() -> str:
    from streamlit_site_parity import _iframe_rwa_global_mock_css

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
body.page-rwa-global-iframe .back-link--below-header a {
  display: inline-block;
  font-weight: 650;
  font-size: 0.84rem;
  line-height: 1.35;
  color: var(--ink-soft, #1f4c67);
  text-decoration: none;
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
body.page-rwa-global-iframe .rwa-table-modal--streamlit-fallback:not([hidden]) {
  display: grid !important;
  place-items: center !important;
  padding: 1.25rem !important;
  box-sizing: border-box !important;
}
body.page-rwa-global-iframe .rwa-table-modal--streamlit-fallback .rwa-table-modal__dialog {
  max-height: min(92vh, 980px);
  width: min(96%, 1400px);
}
"""
    )
    return "\n".join(chunks)


def build_rwa_global_body_iframe_html(
    *,
    payloads: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=onchain",
    back_label: str = "← Back to home · On-chain preview",
) -> str:
    from streamlit_site_parity import iframe_internal_link_script

    css = _cached_iframe_rwa_global_stylesheet_v1()
    label_html = (
        escape(back_label)
        .replace("\u2190", "&larr;")
        .replace("\u00b7", "&middot;")
    )
    back_link = _RWA_GLOBAL_IFRAME_BACK_LINK.format(
        back_href=escape(back_href),
        back_label_html=label_html,
    )
    zone = _RWA_GLOBAL_ZONE_BODY.format(
        related_chips=related_chips.strip(),
        back_href=escape(back_href),
        back_label_html=label_html,
    )
    payloads_json = _json_for_script(payloads)
    js_deps = _read_js_files(_RWA_GLOBAL_JS_DEPS)
    js_boot = _read_js_files(_RWA_GLOBAL_JS_BOOT)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
</head>
<body
  class="page-rwa-global page-rwa-global-iframe site-experience page-inner--rich mock-rwa-global-inner"
  data-methodology="rwa-global"
>
{back_link}
{zone}
<script>
window.__RWA_GLOBAL_PAGE_PAYLOADS = {payloads_json};
</script>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
<script>
{js_deps}
</script>
<script>
window.loadJson = function (name) {{
  var key = String(name || "").split("/").pop();
  if (
    window.__RWA_GLOBAL_PAGE_PAYLOADS &&
    Object.prototype.hasOwnProperty.call(window.__RWA_GLOBAL_PAGE_PAYLOADS, key)
  ) {{
    return Promise.resolve(window.__RWA_GLOBAL_PAGE_PAYLOADS[key]);
  }}
  return Promise.reject(new Error("Unknown RWA global payload: " + name));
}};
{_CRYPTO_PATCH_LOAD_JSON_JS}
</script>
<script>
{_STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH}
</script>
<script>
{js_boot}
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
      "#js-rwa-global-split",
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
    [
      "article.etp-mock-zone",
      "#js-rwa-global-detail-stack",
      "#js-rwa-global-insights",
      "#js-rwa-global-dashboard",
      "#js-rwa-global-split",
    ].forEach(function (sel) {{
      var el = document.querySelector(sel);
      if (el) mo.observe(el, {{ childList: true, subtree: true, attributes: true }});
    }});
  }}
  [100, 400, 1000, 2500, 5000, 8000, 12000, 18000].forEach(function (ms) {{
    setTimeout(sendHeight, ms);
  }});
}})();
</script>
{iframe_internal_link_script()}
</body>
</html>"""


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
    components.html(
        build_rwa_global_body_iframe_html(
            payloads=payloads,
            related_chips=related_chips,
            back_href=back_href,
            back_label=back_label,
        ),
        height=1600,
        scrolling=False,
    )
