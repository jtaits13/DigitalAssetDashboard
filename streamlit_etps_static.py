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
    _json_for_script,
    _read_js_files,
)

_REPO = Path(__file__).resolve().parent
_STATIC = _REPO / "static_home"
_DATA = _STATIC / "data"

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
    <a href="{back_href}">{back_label_html}</a>
  </p>
</div>
"""

_ETP_ZONE_BODY = """
<main class="page-shell etp-mock-shell">
  <article class="hub-section hub-section--panel inner-rich-zone zone--etp home-zone home-zone--etp etp-mock-zone">
    <div class="home-zone__stripe" aria-hidden="true"></div>
    <header class="home-zone__head">
      <span class="home-zone__badge" aria-hidden="true">ETP</span>
      <div class="home-zone__titles">
        <h1 class="page-intro__title" id="page-title">U.S. Digital Asset ETPs</h1>
        <p class="section-dek section-dek--wide">
          <strong>U.S. crypto-related exchange-traded products</strong>, with a KPI strip, an estimated aggregate AUM
          trend chart, a searchable fund table, and a related ETF/ETP headlines panel. Reference:
          <a href="https://stockanalysis.com/list/crypto-etfs/" target="_blank" rel="noopener noreferrer"
            >StockAnalysis.com</a
          >
          (issuer, inception, <strong>1Y %</strong> past-year total return).
        </p>
      </div>
    </header>
    <div class="home-zone__body inner-rich-zone__body etp-mock-zone__body">
      {related_chips}
      <div class="data-banner" id="js-data-banner" role="status" hidden></div>
      <section class="etp-mock-snapshot" aria-labelledby="snapshot-heading">
        <h2 class="subsection-head u-vh" id="snapshot-heading">Top-line snapshot</h2>
        <p class="data-freshness etp-mock-freshness" id="js-etp-snapshot-as-of" hidden></p>
        <div id="js-etp-kpi" aria-label="U.S. ETP KPI strip"></div>
      </section>
      <div class="inner-rich-block etp-mock-key-obs-block" aria-labelledby="obs-heading">
        <h2 class="subsection-head u-vh" id="obs-heading">Key Observations</h2>
        <div id="js-etp-key-obs" hidden></div>
      </div>
      <section class="etp-mock-insights" aria-labelledby="insights-heading">
        <h2 class="u-vh" id="insights-heading">Market structure</h2>
        <div class="etp-mock-insights__panel etp-mock-insights__panel--conc">
          <h3 class="etp-mock-insights__head">AUM concentration (top 5 funds)</h3>
          <p class="etp-mock-conc__dek">Share of total listed AUM (StockAnalysis snapshot).</p>
          <div
            id="js-etp-insights-conc"
            class="etp-mock-conc__rows"
            role="img"
            aria-label="Top five funds by share of total AUM"
          ></div>
        </div>
        <div class="etp-mock-insights__panel etp-mock-insights__panel--glance">
          <h3 class="etp-mock-insights__head">At a glance</h3>
          <div class="etp-mock-stats" id="js-etp-at-a-glance"></div>
        </div>
      </section>
      <section class="etp-mock-dashboard" aria-labelledby="dashboard-heading">
        <h2 class="u-vh" id="dashboard-heading">Chart and headlines</h2>
        <div class="etp-mock-dash__panel etp-mock-dash__panel--chart">
          <h3 class="etp-mock-dash__head" id="aum-heading">Aggregate AUM trend (12 months)</h3>
          <div id="aum-chart" class="aum-chart-host" role="img" aria-label="Aggregate estimated AUM chart"></div>
          <p class="etp-mock-chart__cap">
            Vertical axis: estimated aggregate AUM (<strong>billions USD</strong>; weekly points).
          </p>
          <p class="method-note etp-mock-chart__method">
            <strong>Yahoo Finance</strong> weekly closes &mdash; each fund&#39;s latest StockAnalysis AUM (constant-share
            approximation), summed across the table. Use the Plotly toolbar to zoom, pan, and reset.
          </p>
        </div>
        <div class="etp-mock-dash__panel etp-mock-dash__panel--news">
          <h3 class="etp-mock-dash__head" id="pulse-heading">ETF/ETP news feed</h3>
          <ul class="etp-mock-pulse pulse-list" id="js-etf-pulse">
            <li class="pulse-list__loading">Loading headlines&hellip;</li>
          </ul>
          <div class="etp-mock-dash__cta">
            <a class="btn btn-primary" href="/All_ETF_News">All ETF/ETP headlines &rarr;</a>
          </div>
        </div>
      </section>
      <section class="etp-mock-table-block" aria-labelledby="table-heading">
        <div class="rwa-split-table-head inner-table-head">
          <h2 class="subsection-head rwa-split-table-head__title" id="table-heading">Fund table</h2>
          <div class="rwa-split-table-head__actions" id="js-etp-table-download"></div>
        </div>
        <label class="search-field etp-mock-table-search">
          <span class="search-field__label">Search by fund name or ticker</span>
          <input
            type="search"
            class="search-field__input"
            id="js-etp-search"
            placeholder="Filter by name or ticker&hellip;"
          />
        </label>
        <div class="etp-mock-table-meta" aria-live="polite">
          <p class="etp-mock-table-meta__count toolbar-note" id="js-etp-toolbar">Loading fund list&hellip;</p>
          <div class="rwa-table-actions" id="js-etp-table-actions"></div>
        </div>
        <div class="table-wrap table-wrap--scroll">
          <table class="data-table data-table--dense data-table--sortable">
            <thead id="js-etp-thead">
              <tr>
                <th data-sort="symbol" class="th-sortable">Symbol</th>
                <th data-sort="name" class="th-sortable">Fund Name</th>
                <th class="num th-sortable" data-sort="price">Price</th>
                <th class="num th-sortable" data-sort="pct_52w">1Y %</th>
                <th class="num th-sortable" data-sort="flow_1y_usd">1Y Flow</th>
                <th class="num th-sortable" data-sort="assets_usd">Assets (B)</th>
                <th data-sort="issuer" class="th-sortable">Issuer</th>
                <th data-sort="custodian" class="th-sortable">Custodian</th>
                <th data-sort="inception" class="th-sortable">Inception</th>
                <th>Fund Filing</th>
              </tr>
            </thead>
            <tbody id="js-etp-tbody">
              <tr>
                <td colspan="10">Loading&hellip;</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="rwa-table-footnote-row">
          <p class="source-cap rwa-table-footnote-row__cap">
            Fund data: StockAnalysis (list and AUM). Spot BTC/ETH flows: Farside Investors (daily net
            creations/redemptions, USD).
          </p>
        </div>
      </section>
      <p class="timestamp-foot" id="js-etp-generated">&mdash;</p>
    </div>
  </article>
</main>
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
    from streamlit_payload_stale_first import mark_payload_map_stale, resolve_payload_stale_first

    stale = _static_etp_payload_fallback()

    return resolve_payload_stale_first(
        page_key="etps",
        load_stale=lambda: stale or None,
        load_live_cached=lambda: _cached_etp_iframe_payloads(user_agent),
        mark_stale=lambda payloads, err: mark_payload_map_stale(payloads, err),
    )


@st.cache_resource(show_spinner=False)
def _cached_iframe_etp_stylesheet_v1() -> str:
    from streamlit_site_parity import _iframe_etp_mock_css

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
  background: var(--wash, #f3f7fb);
  overflow: hidden;
}
html::before,
html::after,
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
body.page-etp-iframe .back-link--below-header a {
  display: inline-block;
  font-weight: 650;
  font-size: 0.84rem;
  line-height: 1.35;
  color: var(--ink-soft, #1f4c67);
  text-decoration: none;
}
body.page-etp-iframe .back-link--below-header a:hover {
  color: var(--hx-etp-bright, #507188);
}
body.page-etp-iframe .page-shell.etp-mock-shell {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0 1.25rem 1.5rem;
  box-sizing: border-box;
}
body.page-etp-iframe .home-reveal {
  opacity: 1 !important;
  transform: none !important;
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
    return "\n".join(chunks)


def _etp_back_link_html(*, href: str, label: str) -> str:
    label_html = (
        escape(label)
        .replace("\u2190", "&larr;")
        .replace("\u00b7", "&middot;")
    )
    return _ETP_IFRAME_BACK_LINK.format(back_href=escape(href), back_label_html=label_html)


def build_etps_body_iframe_html(
    *,
    payloads: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=markets",
    back_label: str = "← Back to home · ETP preview",
) -> str:
    from streamlit_site_parity import iframe_internal_link_script

    css = _cached_iframe_etp_stylesheet_v1()
    back_link = _etp_back_link_html(href=back_href, label=back_label)
    zone = _ETP_ZONE_BODY.format(related_chips=related_chips.strip())
    payloads_json = _json_for_script(payloads)
    js_deps = _read_js_files(_ETP_JS_DEPS)
    js_boot = _read_js_files(_ETP_JS_BOOT)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
</head>
<body
  class="page-etp page-etp-iframe site-experience page-inner--rich mock-etp-inner"
  data-methodology="etp"
>
{back_link}
{zone}
<script>
window.__ETP_PAGE_PAYLOADS = {payloads_json};
</script>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
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
  [100, 400, 1000, 2500, 5000, 8000, 12000, 18000].forEach(function (ms) {{
    setTimeout(sendHeight, ms);
  }});
}})();
</script>
{iframe_internal_link_script()}
</body>
</html>"""


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_etp_iframe_payloads(_user_agent: str) -> dict[str, Any]:
    return get_etp_iframe_payloads(user_agent=_user_agent)


def render_etps_body_iframe(
    *,
    payloads: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=markets",
    back_label: str = "← Back to home · ETP preview",
) -> None:
    components.html(
        build_etps_body_iframe_html(
            payloads=payloads,
            related_chips=related_chips,
            back_href=back_href,
            back_label=back_label,
        ),
        height=1500,
        scrolling=False,
    )
