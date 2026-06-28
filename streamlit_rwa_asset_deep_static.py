"""Streamlit US Treasuries / Tokenized Stocks — server-rendered iframes (GitHub Pages parity)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from streamlit_stablecoins_static import (
    STABLE_GH_PAGE_WASH,
    _STABLE_MEASURE_HEIGHT_JS,
    _STABLE_SERVER_CHART_BOOT_JS,
)
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

_RWA_ASSET_IFRAME_CSS_VERSION = "1"
RWA_ASSET_CANVAS_OVERRIDE_VERSION = "1"
RWA_ASSET_GH_ZONE_SOFT = "#e8eff5"

_IFRAME_BACK_LINK = """
<div class="page-back-below-header">
  <p class="back-link back-link--below-header">
    <a class="rwa-asset-server-back-anchor" data-deep-back="explore" href="{back_href}">{back_label_html}</a>
  </p>
</div>
"""


@dataclass(frozen=True)
class RwaAssetDeepSpec:
    kind: str
    payload_file: str
    page_body_class: str
    mock_inner_class: str
    host_marker_class: str
    style_kind: str
    methodology: str
    mock_css_files: tuple[str, ...]
    chart_aria: str
    movers_footer: str
    default_back_label: str


RWA_ASSET_DEEP_SPECS: dict[str, RwaAssetDeepSpec] = {
    "treasuries": RwaAssetDeepSpec(
        kind="treasuries",
        payload_file="rwa_us_treasuries.json",
        page_body_class="page-rwa-deep-treasuries",
        mock_inner_class="mock-treasuries-inner",
        host_marker_class="streamlit-treasuries-iframe-page",
        style_kind="treasuries",
        methodology="rwa-treasuries",
        mock_css_files=(
            "mockups/etp-inner-page-mock.css",
            "mockups/rwa-global-inner-page-mock.css",
            "mockups/treasuries-inner-page-mock.css",
        ),
        chart_aria="Top networks by U.S. Treasuries distributed value",
        movers_footer=(
            "<strong>30D Δ share</strong> is 30-day change in market share (%). "
            "Top 15 networks by U.S. Treasuries distributed value."
        ),
        default_back_label="← Explore by Asset Type",
    ),
    "stocks": RwaAssetDeepSpec(
        kind="stocks",
        payload_file="rwa_tokenized_stocks.json",
        page_body_class="page-rwa-deep-stocks",
        mock_inner_class="mock-stocks-inner",
        host_marker_class="streamlit-stocks-iframe-page",
        style_kind="stocks",
        methodology="rwa-tokenized-stocks",
        mock_css_files=(
            "mockups/etp-inner-page-mock.css",
            "mockups/rwa-global-inner-page-mock.css",
            "mockups/tokenized-stocks-inner-page-mock.css",
        ),
        chart_aria="Top networks by tokenized stock distributed value",
        movers_footer=(
            "<strong>30D Δ share</strong> is 30-day change in market share (%). "
            "Top 15 networks by tokenized stock value."
        ),
        default_back_label="← Explore by Asset Type",
    ),
}


def _spec(kind: str) -> RwaAssetDeepSpec:
    return RWA_ASSET_DEEP_SPECS[kind]


def _static_payload_fallback(*, payload_file: str, error: str = "") -> dict[str, Any] | None:
    path = _DATA / payload_file
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if error:
        merged = dict(data)
        merged["error"] = error
        merged["stale"] = True
        return merged
    return data


def load_rwa_asset_deep_payload(kind: str) -> dict[str, Any]:
    spec = _spec(kind)
    if kind == "treasuries":
        from scripts.export_static_site_data import _build_rwa_us_treasuries_deep_payload
        from rwa_streamlit_fetch_cache import cached_rwa_treasuries_data

        pack = cached_rwa_treasuries_data()
        build = _build_rwa_us_treasuries_deep_payload
    else:
        from scripts.export_static_site_data import _build_rwa_tokenized_stocks_deep_payload
        from rwa_streamlit_fetch_cache import cached_rwa_tokenized_stocks_data

        pack = cached_rwa_tokenized_stocks_data()
        build = _build_rwa_tokenized_stocks_deep_payload

    payload = build(pack, {"errors": []}, [])
    from streamlit_site_parity import _streamlit_page_href

    payload["back_href"] = _streamlit_page_href("explore_asset")
    return payload


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_rwa_asset_deep_payload(kind: str) -> dict[str, Any]:
    return load_rwa_asset_deep_payload(kind)


def get_rwa_asset_deep_payload(kind: str) -> dict[str, Any]:
    from streamlit_payload_stale_first import load_static_first_with_live_fallback, mark_dict_stale

    spec = _spec(kind)
    return load_static_first_with_live_fallback(
        load_stale=lambda: _static_payload_fallback(payload_file=spec.payload_file) or None,
        load_live_cached=lambda: _cached_rwa_asset_deep_payload(kind),
        mark_stale=mark_dict_stale,
    )


@st.cache_resource(show_spinner=False)
def _cached_iframe_rwa_asset_stylesheet(kind: str, *, _css_version: str = _RWA_ASSET_IFRAME_CSS_VERSION) -> str:
    from streamlit_site_parity import (
        _iframe_rwa_asset_mock_css,
        deep_iframe_back_link_clickable_css,
        deep_iframe_kpi_flatten_css,
        deep_iframe_related_chips_css,
        deep_iframe_rwa_zone_body_flatten_css,
    )

    spec = _spec(kind)
    scope = f"body.{spec.page_body_class}"
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
    for rel in spec.mock_css_files:
        path = _STATIC / rel
        if path.is_file():
            chunks.append(
                _iframe_rwa_asset_mock_css(
                    path.read_text(encoding="utf-8"),
                    mock_inner=spec.mock_inner_class,
                    body_class=spec.page_body_class,
                )
            )
    chunks.append(
        f"""
html, {scope}.site-experience {{
  margin: 0;
  padding: 0;
  background: var(--wash, {STABLE_GH_PAGE_WASH}) !important;
  background-image: none !important;
  overflow: hidden;
}}
html::before, html::after,
{scope}::before,
{scope}::after {{
  display: none !important;
  content: none !important;
  height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
}}
{scope} .page-back-below-header {{
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0.35rem 1.25rem 0;
  box-sizing: border-box;
}}
{scope} p.back-link.back-link--below-header {{
  margin: 0.2rem 0 0.85rem;
}}
{scope}.site-experience.page-inner--rich .back-link--below-header a {{
  display: inline-block;
  font-weight: 650;
  font-size: 0.84rem;
  line-height: 1.35;
  color: var(--ink-soft, #1f4c67);
  text-decoration: none;
  padding: 0.35rem 0.65rem;
  border-radius: 999px;
  border: 1px solid rgb(var(--hx-rwa-bright-rgb, 80 113 136) / 0.18);
  background: rgba(251, 254, 255, 0.85);
}}
{scope} .page-shell.etp-mock-shell {{
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0 1.25rem 1.5rem;
  box-sizing: border-box;
  background: transparent !important;
}}
{scope} .home-reveal {{
  opacity: 1 !important;
  transform: none !important;
}}
"""
    )
    chunks.append(deep_iframe_rwa_zone_body_flatten_css(scope=scope, soft=RWA_ASSET_GH_ZONE_SOFT))
    chunks.append(deep_iframe_kpi_flatten_css(scope=scope, zone="rwa"))
    chunks.append(deep_iframe_related_chips_css(scope=scope, zone="rwa"))
    chunks.append(deep_iframe_back_link_clickable_css(scope=scope))
    return "\n".join(chunks)


def rwa_asset_github_canvas_override_css(*, kind: str, version: str = RWA_ASSET_CANVAS_OVERRIDE_VERSION) -> str:
    from streamlit_site_parity import deep_iframe_kpi_flatten_css

    spec = _spec(kind)
    wash = STABLE_GH_PAGE_WASH
    soft = RWA_ASSET_GH_ZONE_SOFT
    scope = f"body.{spec.page_body_class}"
    return f"""
/* RWA asset deep canvas override v{version} ({kind}) */
html, {scope}.site-experience,
{scope}.site-experience.page-inner--rich,
{scope}.{spec.mock_inner_class}.site-experience {{
  background: {wash} !important;
  background-color: {wash} !important;
  background-image: none !important;
}}
{scope} .inner-rich-zone.zone--rwa,
{scope} .inner-rich-zone.zone--rwa .inner-rich-zone__body {{
  background: {soft} !important;
  background-color: {soft} !important;
  background-image: none !important;
}}
{scope} .inner-rich-block,
{scope} .etp-mock-key-obs-block,
{scope} .etp-mock-insights__panel,
{scope} .etp-mock-dash__panel,
{scope} .etp-mock-table-block,
{scope} .rwa-kpi-row--home-grid .rwa-kpi-cell {{
  background: #fff !important;
  background-color: #fff !important;
  background-image: none !important;
}}
""" + deep_iframe_kpi_flatten_css(scope=scope, zone="rwa")


def rwa_asset_iframe_canvas_override_js(*, kind: str, version: str = RWA_ASSET_CANVAS_OVERRIDE_VERSION) -> str:
    wash = STABLE_GH_PAGE_WASH
    soft = RWA_ASSET_GH_ZONE_SOFT
    return f"""
<script id="rwa-asset-gh-canvas-override-js-v{version}-{kind}">
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
    document.querySelectorAll(
      ".inner-rich-zone.zone--rwa, .inner-rich-zone.zone--rwa .inner-rich-zone__body"
    ).forEach(function (el) {{ setBg(el, SOFT); }});
    document.querySelectorAll(
      ".etp-mock-key-obs-block, .etp-mock-insights__panel, .etp-mock-dash__panel, .etp-mock-table-block, .rwa-kpi-row--home-grid .rwa-kpi-cell"
    ).forEach(function (el) {{
      setBg(el, WHITE);
      el.style.setProperty("box-shadow", "none", "important");
    }});
  }}
  paint();
  window.addEventListener("load", paint);
  [50, 200, 800, 2000].forEach(function (ms) {{ setTimeout(paint, ms); }});
}})();
</script>
"""


def rwa_asset_host_canvas_override_css(*, kind: str, version: str = RWA_ASSET_CANVAS_OVERRIDE_VERSION) -> str:
    spec = _spec(kind)
    wash = STABLE_GH_PAGE_WASH
    marker = spec.host_marker_class
    return f"""
<style id="rwa-asset-gh-host-canvas-override-v{version}-{marker}">
.stApp:has(.{marker}),
.withScreencast:has(.{marker}),
[data-testid="stScreencast"]:has(.{marker}),
.stApp:has(.{marker}) [data-testid="stAppViewContainer"],
.stApp:has(.{marker}) section.main,
.stApp:has(.{marker}) [data-testid="stMain"],
.stApp:has(.{marker}) [data-testid="stMainBlockContainer"] {{
  background: {wash} !important;
  background-color: {wash} !important;
  background-image: none !important;
}}
</style>
"""


def rwa_asset_host_canvas_override_js(*, kind: str, version: str = RWA_ASSET_CANVAS_OVERRIDE_VERSION) -> str:
    spec = _spec(kind)
    wash = STABLE_GH_PAGE_WASH
    marker = spec.host_marker_class
    return f"""
<script id="rwa-asset-gh-host-canvas-override-js-v{version}-{marker}">
(function () {{
  var WASH = "{wash}";
  var MARKER = "{marker}";
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


def inject_rwa_asset_host_canvas_override(*, kind: str) -> None:
    st.markdown(
        rwa_asset_host_canvas_override_css(kind=kind) + rwa_asset_host_canvas_override_js(kind=kind),
        unsafe_allow_html=True,
    )


def inject_rwa_asset_iframe_table_actions(*, kind: str, payload: dict[str, Any]) -> None:
    from streamlit_server_deep_page import build_rwa_asset_deep_server_export_config

    spec = _spec(kind)
    js_libs = _read_js_files(("table-fullscreen.js", "table-download.js"))
    export_json = json.dumps(build_rwa_asset_deep_server_export_config(payload))
    libs_json = json.dumps(js_libs)
    patch_json = json.dumps(_STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH.strip())
    wire_json = json.dumps(_TMMF_SERVER_TABLE_WIRE_JS.strip())
    host_modal_json = json.dumps(_TMMF_SERVER_INLINE_HOST_MODAL_JS.strip())
    marker = spec.host_marker_class
    inner_marker = spec.mock_inner_class
    bootstrap = f"""
<script>
(function () {{
  var win = window.parent;
  var doc = win.document;
  if (win.__jpmRwaAssetIframeTableHostBound_{kind}) return;
  win.__jpmRwaAssetIframeTableHostBound_{kind} = true;

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

  function findInner() {{
    var frames = doc.querySelectorAll("iframe");
    for (var i = 0; i < frames.length; i++) {{
      try {{
        var inner = frames[i].contentDocument;
        if (
          inner &&
          inner.body &&
          inner.body.classList &&
          inner.body.classList.contains("{inner_marker}")
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
    if (typeof hit.win.__tmmfWireServerTables === "function") {{
      hit.win.__tmmfWireServerTables();
    }}
    return true;
  }}

  function boot() {{
    if (!doc.querySelector(".{marker}")) return false;
    ensureHostModal();
    var hit = findInner();
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


def _back_link_html(*, href: str, label: str) -> str:
    label_html = escape(label).replace("\u2190", "&larr;").replace("\u00b7", "&middot;")
    return _IFRAME_BACK_LINK.format(back_href=escape(href), back_label_html=label_html)


def build_rwa_asset_deep_server_iframe_html(
    *,
    kind: str,
    payload: dict[str, Any],
    related_chips: str,
    back_href: str | None = None,
    back_label: str | None = None,
) -> str:
    from streamlit_server_deep_page import (
        build_rwa_asset_deep_server_export_config,
        build_rwa_asset_deep_server_zone_html,
    )
    from streamlit_site_parity import iframe_internal_link_script

    spec = _spec(kind)
    css = _cached_iframe_rwa_asset_stylesheet(kind)
    override_css = rwa_asset_github_canvas_override_css(kind=kind)
    href = back_href or str(payload.get("back_href") or "/RWA_Explore_By_Asset_Type")
    label = back_label or spec.default_back_label
    back_link = _back_link_html(href=href, label=label)
    zone = build_rwa_asset_deep_server_zone_html(
        payload=payload,
        related_chips=related_chips,
        asset_kind=kind,
        chart_aria=spec.chart_aria,
        movers_footer=spec.movers_footer,
    )
    table_js_libs = _read_js_files(("table-fullscreen.js", "table-download.js"))
    chart_js_libs = _read_js_files(("static-base.js",))
    export_json = json.dumps(build_rwa_asset_deep_server_export_config(payload))
    net = payload.get("networks") or {}
    chart_cfg = json.dumps(
        {
            "league": {
                "rows_full": net.get("rows_full") or [],
                "name_column": net.get("name_column") or "Network",
                "value_column": net.get("value_column") or "Distributed Value",
            },
            "payload": {"chart_max_bars": 5, "chart_include_other": True},
        }
    )
    body_classes = (
        f"page-rwa-deep {spec.page_body_class} site-experience page-inner--rich "
        f"{spec.mock_inner_class} mock-rwa-global-inner"
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
<style id="rwa-asset-gh-canvas-override-v{RWA_ASSET_CANVAS_OVERRIDE_VERSION}-{kind}">{override_css}</style>
</head>
<body class="{body_classes}" data-methodology="{spec.methodology}">
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
      "#js-deep-dashboard",
      "#js-deep-dashboard-chart",
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
    ["article.etp-mock-zone", "#js-deep-dashboard", "#deep-net-wrap", "#deep-plat-wrap"].forEach(function (sel) {{
      var el = document.querySelector(sel);
      if (el) mo.observe(el, {{ childList: true, subtree: true, attributes: true }});
    }});
  }}
  [100, 400, 1000, 2500, 5000, 8000].forEach(function (ms) {{
    setTimeout(sendHeight, ms);
  }});
}})();
</script>
{rwa_asset_iframe_canvas_override_js(kind=kind)}
{iframe_internal_link_script()}
</body>
</html>"""


def render_rwa_asset_deep_body_iframe(
    *,
    kind: str,
    payload: dict[str, Any],
    related_chips: str,
    back_href: str | None = None,
    back_label: str | None = None,
) -> None:
    from streamlit_site_parity import render_subpage_body_iframe

    html = build_rwa_asset_deep_server_iframe_html(
        kind=kind,
        payload=payload,
        related_chips=related_chips,
        back_href=back_href,
        back_label=back_label,
    )
    render_subpage_body_iframe(html, height=1600)
    inject_rwa_asset_host_canvas_override(kind=kind)
    inject_rwa_asset_iframe_table_actions(kind=kind, payload=payload)
