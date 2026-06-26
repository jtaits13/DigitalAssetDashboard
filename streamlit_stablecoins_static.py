"""Streamlit Stablecoins full page — static HTML iframe (parity with ``rwa-stablecoins.html``)."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from streamlit_tmmf_static import (
    _STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH,
    _json_for_script,
    _read_js_files,
)

_REPO = Path(__file__).resolve().parent
_STATIC = _REPO / "static_home"
_DATA = _STATIC / "data"

_STABLE_JS_DEPS = (
    "static-base.js",
    "table-fullscreen.js",
    "table-download.js",
    "kpi-hints.js",
    "data-freshness.js",
    "page-methodology.js",
    "snapshot-kpi-shared.js",
    "crypto-kpi-shared.js",
    "rwa-onchain-home.js",
)
_STABLE_JS_BOOT = ("rwa-asset-deep-page.js",)

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

_STABLE_IFRAME_BACK_LINK = """
<div class="page-back-below-header">
  <p class="back-link back-link--below-header">
    <a data-deep-back="explore" href="{back_href}">{back_label_html}</a>
  </p>
</div>
"""

_STABLE_ZONE_BODY = """
<main class="page-shell etp-mock-shell">
  <article class="hub-section hub-section--panel inner-rich-zone zone--stable home-zone home-zone--stable etp-mock-zone">
    <div class="home-zone__stripe" aria-hidden="true"></div>
    <header class="home-zone__head">
      <span class="home-zone__badge" aria-hidden="true">SC</span>
      <div class="home-zone__titles">
        <p class="band-label teal" id="js-deep-band"></p>
        <h1 class="page-intro__title" id="js-deep-title"></h1>
        <div class="section-dek section-dek--wide page-intro__dek" id="js-deep-subtitle"></div>
      </div>
    </header>
    <div class="home-zone__body inner-rich-zone__body etp-mock-zone__body">
      {related_chips}
      <div class="data-banner" id="js-deep-banner" role="status" hidden></div>
      <section class="etp-mock-snapshot" id="js-deep-snapshot" aria-labelledby="js-deep-snap-h">
        <h2 class="subsection-head u-vh" id="js-deep-snap-h">Top-line snapshot</h2>
        <div id="js-deep-kpis" aria-label="Stablecoins headline KPI strip"></div>
      </section>
      <div class="inner-rich-block etp-mock-key-obs-block" id="js-deep-ko-section" hidden aria-labelledby="js-deep-ko-h">
        <h2 class="subsection-head u-vh" id="js-deep-ko-h">Key Observations</h2>
        <div id="js-deep-ko"></div>
      </div>
      <section class="etp-mock-insights etp-mock-insights--crypto-full" id="js-deep-insights" hidden aria-labelledby="js-deep-insights-h">
        <h2 class="u-vh" id="js-deep-insights-h">Market structure</h2>
      </section>
      <section class="etp-mock-dashboard" id="js-deep-dashboard" hidden aria-labelledby="js-deep-dashboard-h">
        <h2 class="u-vh" id="js-deep-dashboard-h">Chart and share movers</h2>
        <div class="etp-mock-dash__panel etp-mock-dash__panel--chart">
          <h3 class="etp-mock-dash__head">Stablecoin market cap by network</h3>
          <div class="stable-dash-chart-body">
            <div
              id="js-deep-dashboard-chart"
              class="aum-chart-host"
              role="img"
              aria-label="Stablecoin market cap by network"
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
          <div id="js-stable-share-movers"></div>
        </div>
      </section>
      <div id="js-deep-extra-before-leagues" class="rwa-deep-optional-msg" hidden></div>
      <div id="deep-net-wrap"></div>
      <div id="js-deep-extra-after-network" class="rwa-deep-optional-msg" hidden></div>
      <hr class="jd-divider" id="js-deep-rule-mid" hidden aria-hidden="true" />
      <div id="deep-plat-wrap"></div>
      <div id="js-deep-bottom-cta" class="cta-row rwa-deep-page-cta"></div>
      <p class="timestamp-foot" id="js-deep-footer-note"></p>
    </div>
  </article>
</main>
"""


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
    from streamlit_payload_stale_first import load_live_with_static_fallback, mark_dict_stale

    return load_live_with_static_fallback(
        load_live_cached=_cached_stablecoins_deep_payload,
        load_stale=lambda: _static_stablecoins_deep_fallback() or None,
        mark_stale=mark_dict_stale,
    )


@st.cache_resource(show_spinner=False)
def _cached_iframe_stable_stylesheet_v1() -> str:
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
  background: var(--wash, #f3f7fb);
  overflow: hidden;
}
html::before,
html::after,
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
body.page-rwa-deep-stablecoins .back-link--below-header a {
  display: inline-block;
  font-weight: 650;
  font-size: 0.84rem;
  line-height: 1.35;
  color: var(--ink-soft, #1f4c67);
  text-decoration: none;
}
body.page-rwa-deep-stablecoins .back-link--below-header a:hover {
  color: var(--hx-stable-bright, #507188);
}
body.page-rwa-deep-stablecoins .page-shell.etp-mock-shell {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0 1.25rem 1.5rem;
  box-sizing: border-box;
}
body.page-rwa-deep-stablecoins .home-reveal {
  opacity: 1 !important;
  transform: none !important;
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


def build_stablecoins_body_iframe_html(
    *,
    payload: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=stablecoins",
    back_label: str = "← Back to home · Stablecoins preview",
) -> str:
    """Self-contained iframe document — hydrates via ``rwa-asset-deep-page.js``."""
    from streamlit_site_parity import iframe_internal_link_script

    css = _cached_iframe_stable_stylesheet_v1()
    back_link = _stable_back_link_html(href=back_href, label=back_label)
    zone = _STABLE_ZONE_BODY.format(related_chips=related_chips.strip())
    payload_json = _json_for_script(payload)
    js_deps = _read_js_files(_STABLE_JS_DEPS)
    js_boot = _read_js_files(_STABLE_JS_BOOT)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
</head>
<body
  class="page-rwa-deep page-rwa-deep-stablecoins site-experience page-inner--rich mock-stable-inner"
  data-rwa-deep-json="rwa_stablecoins.json"
  data-methodology="rwa-stablecoins"
>
{back_link}
{zone}
<script>
window.__RWA_DEEP_PAYLOAD = {payload_json};
</script>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
<script>
{js_deps}
</script>
<script>
window.loadJson = function () {{
  return Promise.resolve(window.__RWA_DEEP_PAYLOAD);
}};
</script>
<script>
{_STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH}
</script>
<script>
{js_boot}
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
      "#js-deep-dashboard",
      "#js-stable-share-movers",
      "#deep-net-wrap",
      "#deep-plat-wrap",
      "#js-deep-footer-note",
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
      "#js-deep-insights",
      "#js-deep-dashboard",
      "#deep-net-wrap",
      "#deep-plat-wrap",
    ].forEach(function (sel) {{
      var el = document.querySelector(sel);
      if (el) mo.observe(el, {{ childList: true, subtree: true, attributes: true }});
    }});
  }}
  [100, 400, 1000, 2500, 5000, 8000].forEach(function (ms) {{
    setTimeout(sendHeight, ms);
  }});
}})();
</script>
{iframe_internal_link_script()}
</body>
</html>"""


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_stablecoins_deep_payload() -> dict[str, Any]:
    return load_stablecoins_deep_payload()


def render_stablecoins_body_iframe(
    *,
    payload: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=stablecoins",
    back_label: str = "← Back to home · Stablecoins preview",
) -> None:
    """Render the GitHub Pages Stablecoins zone inside a Streamlit iframe."""
    components.html(
        build_stablecoins_body_iframe_html(
            payload=payload,
            related_chips=related_chips,
            back_href=back_href,
            back_label=back_label,
        ),
        height=1200,
        scrolling=False,
    )
