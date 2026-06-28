"""Streamlit RWA Explore pages — static HTML iframes (parity with ``rwa-explore-*.html``)."""

from __future__ import annotations

import json
from dataclasses import dataclass
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

_RWA_EXPLORE_JS_DEPS = (
    "static-base.js",
    "table-fullscreen.js",
    "table-download.js",
    "kpi-hints.js",
    "page-methodology.js",
    "rwa-onchain-home.js",
)
_RWA_EXPLORE_JS_BOOT = ("rwa-explore-asset-type-page.js",)

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
    var rect = el.getBoundingClientRect();
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

_RWA_EXPLORE_IFRAME_BACK_LINK = """
<div class="page-back-below-header">
  <p class="back-link back-link--below-header">
    <a data-exat-link="global" href="{back_href}">{back_label_html}</a>
  </p>
</div>
"""

_RWA_EXPLORE_ZONE_BODY = """
<main class="page-shell etp-mock-shell">
  <article
    class="hub-section hub-section--panel inner-rich-zone zone--rwa home-zone home-zone--rwa etp-mock-zone"
    aria-labelledby="page-title"
  >
    <div class="home-zone__stripe" aria-hidden="true"></div>
    <header class="home-zone__head">
      <span class="home-zone__badge" aria-hidden="true">RWA</span>
      <div class="home-zone__titles">
        <p class="band-label teal">{band_label}</p>
        <h1 class="page-intro__title" id="page-title">{title}</h1>
        <div class="section-dek section-dek--wide page-intro__dek" id="js-exat-subtitle"></div>
      </div>
    </header>
    <div class="home-zone__body inner-rich-zone__body etp-mock-zone__body">
      {related_chips}
      <div class="data-banner" id="js-exat-banner" role="status" hidden></div>
      <div class="rwa-exat-intro rwa-explore-mock-intro" id="js-exat-intro"></div>
      <nav class="rwa-explore-mock-jump" id="js-exat-jump" aria-label="{jump_aria}" hidden></nav>
      <div id="js-exat-sections" class="rwa-exat-sections"></div>
      <p class="timestamp-foot" id="js-exat-timestamp"></p>
    </div>
  </article>
</main>
"""


@dataclass(frozen=True)
class RwaExplorePageSpec:
    kind: str
    payload_key: str
    page_class: str
    iframe_class: str
    host_style_kind: str
    band_label: str
    title: str
    jump_aria: str
    default_back_href: str
    default_back_label: str


RWA_EXPLORE_SPECS: dict[str, RwaExplorePageSpec] = {
    "explore_asset": RwaExplorePageSpec(
        kind="explore_asset",
        payload_key="rwa_explore_asset_type.json",
        page_class="page-rwa-explore-at",
        iframe_class="page-rwa-explore-at-iframe",
        host_style_kind="rwa_explore_at",
        band_label="RWA · Assets",
        title="Explore by Asset Type",
        jump_aria="Jump to asset previews",
        default_back_href="/RWA_Global_Market_Overview",
        default_back_label="← RWA Global Market Overview",
    ),
    "explore_participant": RwaExplorePageSpec(
        kind="explore_participant",
        payload_key="rwa_explore_market_participant.json",
        page_class="page-rwa-explore-mp",
        iframe_class="page-rwa-explore-mp-iframe",
        host_style_kind="rwa_explore_mp",
        band_label="RWA · Participants",
        title="Explore by Market Participant",
        jump_aria="Jump to participant previews",
        default_back_href="/RWA_Global_Market_Overview",
        default_back_label="← RWA Global Market Overview",
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


@st.cache_resource(show_spinner=False)
def _cached_iframe_rwa_explore_stylesheet_v1(kind: str) -> str:
    from streamlit_site_parity import _iframe_rwa_explore_mock_css

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
body.{spec.iframe_class} .back-link--below-header a {{
  display: inline-block;
  font-weight: 650;
  font-size: 0.84rem;
  line-height: 1.35;
  color: var(--ink-soft, #1f4c67);
  text-decoration: none;
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
body.{spec.iframe_class} .rwa-table-modal--streamlit-fallback:not([hidden]) {{
  display: grid !important;
  place-items: center !important;
  padding: 1.25rem !important;
  box-sizing: border-box !important;
}}
body.{spec.iframe_class} .rwa-table-modal--streamlit-fallback .rwa-table-modal__dialog {{
  max-height: min(92vh, 980px);
  width: min(96%, 1400px);
}}
"""
    )
    from streamlit_site_parity import deep_iframe_back_link_clickable_css, deep_iframe_related_chips_css

    chunks.append(deep_iframe_related_chips_css(scope=f"body.{spec.iframe_class}", zone="rwa"))
    chunks.append(deep_iframe_back_link_clickable_css(scope=f"body.{spec.iframe_class}"))
    return "\n".join(chunks)


def _explore_back_label_html(label: str) -> str:
    return (
        escape(label)
        .replace("\u2190", "&larr;")
        .replace("\u00b7", "&middot;")
    )


def build_rwa_explore_body_iframe_html(
    *,
    kind: str,
    payloads: dict[str, Any],
    related_chips: str,
    back_href: str | None = None,
    back_label: str | None = None,
) -> str:
    from streamlit_site_parity import iframe_internal_link_script

    spec = RWA_EXPLORE_SPECS[kind]
    css = _cached_iframe_rwa_explore_stylesheet_v1(kind)
    href = back_href or spec.default_back_href
    label = back_label or spec.default_back_label
    label_html = _explore_back_label_html(label)
    back_link = _RWA_EXPLORE_IFRAME_BACK_LINK.format(
        back_href=escape(href),
        back_label_html=label_html,
    )
    zone = _RWA_EXPLORE_ZONE_BODY.format(
        band_label=escape(spec.band_label),
        title=escape(spec.title),
        jump_aria=escape(spec.jump_aria),
        related_chips=related_chips.strip(),
    )
    payloads_json = _json_for_script(payloads)
    js_deps = _read_js_files(_RWA_EXPLORE_JS_DEPS)
    js_boot = _read_js_files(_RWA_EXPLORE_JS_BOOT)
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
</head>
<body
  class="{body_classes}"
  data-explore-json="{escape(spec.payload_key)}"
>
{back_link}
{zone}
<script>
window.__RWA_EXPLORE_PAGE_PAYLOADS = {payloads_json};
</script>
<script>
{js_deps}
</script>
<script>
window.loadJson = function (name) {{
  var key = String(name || "").split("/").pop();
  if (
    window.__RWA_EXPLORE_PAGE_PAYLOADS &&
    Object.prototype.hasOwnProperty.call(window.__RWA_EXPLORE_PAGE_PAYLOADS, key)
  ) {{
    return Promise.resolve(window.__RWA_EXPLORE_PAGE_PAYLOADS[key]);
  }}
  return Promise.reject(new Error("Unknown RWA explore payload: " + name));
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
    [
      "article.etp-mock-zone",
      "#js-exat-sections",
      "#js-exat-jump",
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
def _cached_rwa_explore_iframe_payloads(kind: str) -> dict[str, Any]:
    return load_rwa_explore_iframe_payloads(kind)


def render_rwa_explore_body_iframe(
    *,
    kind: str,
    payloads: dict[str, Any],
    related_chips: str,
    back_href: str | None = None,
    back_label: str | None = None,
) -> None:
    from streamlit_site_parity import render_subpage_body_iframe

    render_subpage_body_iframe(
        build_rwa_explore_body_iframe_html(
            kind=kind,
            payloads=payloads,
            related_chips=related_chips,
            back_href=back_href,
            back_label=back_label,
        ),
        height=1800,
    )
