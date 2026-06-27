"""Streamlit TMMF full page — static HTML iframe (parity with ``rwa-tokenized-mmf.html``)."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

_REPO = Path(__file__).resolve().parent
_STATIC = _REPO / "static_home"
_DATA = _STATIC / "data"

_TMMF_JS_DEPS = (
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
_TMMF_JS_BOOT = ("rwa-asset-deep-page.js",)

_STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH = """
(function () {
  // st-tmmf-fullscreen-postmessage
  var fs = window.__TABLE_FULLSCREEN;
  if (!fs || window.__ST_TMMF_FULLSCREEN_PATCHED) return;
  window.__ST_TMMF_FULLSCREEN_PATCHED = true;

  var IFRAME_MODAL_ID = "js-table-fullscreen-modal";
  var origOpen = fs.openTableModal;
  var origClose = fs.closeTableModal;
  var origAttach = fs.attachTableFullscreenButton;

  function stripElementIds(node) {
    if (!node || node.nodeType !== 1) return;
    node.removeAttribute("id");
    Array.prototype.forEach.call(node.children || [], stripElementIds);
  }

  function tableHtmlForHost(tableEl) {
    if (!tableEl || !tableEl.cloneNode) return "";
    var clone = tableEl.cloneNode(true);
    stripElementIds(clone);
    return clone.outerHTML || "";
  }

  function postOpenToHost(tableEl, opts) {
    if (typeof window.parent.postMessage !== "function") return false;
    var html = tableHtmlForHost(tableEl);
    if (!html) return false;
    try {
      window.parent.postMessage(
        {
          type: "jpm-table-fullscreen-open",
          title:
            (opts && opts.title) ||
            tableEl.getAttribute("aria-label") ||
            "Full-screen table",
          tableHtml: html,
        },
        "*"
      );
      window.__TMMF_MODAL_OPEN = true;
      return true;
    } catch (e) {
      return false;
    }
  }

  function postCloseToHost() {
    if (typeof window.parent.postMessage !== "function") return;
    try {
      window.parent.postMessage({ type: "jpm-table-fullscreen-close" }, "*");
    } catch (e) {}
  }

  function findHostIframe() {
    if (window.frameElement) return window.frameElement;
    try {
      var frames = window.parent.document.querySelectorAll("iframe");
      for (var i = 0; i < frames.length; i++) {
        try {
          if (frames[i].contentWindow === window) return frames[i];
        } catch (e) {}
      }
    } catch (e) {}
    return null;
  }

  function getVisibleIframeSlice() {
    var frame = findHostIframe();
    var parentWin = window.parent;
    if (!parentWin || parentWin === window) {
      return { top: 0, left: 0, width: window.innerWidth, height: window.innerHeight };
    }
    if (!frame) {
      return {
        top: 0,
        left: 0,
        width: window.innerWidth,
        height: parentWin.visualViewport ? parentWin.visualViewport.height : window.innerHeight,
      };
    }
    var rect = frame.getBoundingClientRect();
    var vv = parentWin.visualViewport;
    var vTop = vv ? vv.offsetTop : 0;
    var vLeft = vv ? vv.offsetLeft : 0;
    var vBottom = vTop + (vv ? vv.height : parentWin.innerHeight);
    var vRight = vLeft + (vv ? vv.width : parentWin.innerWidth);
    return {
      top: Math.max(rect.top, vTop) - rect.top,
      left: Math.max(rect.left, vLeft) - rect.left,
      width: Math.max(0, Math.min(rect.right, vRight) - Math.max(rect.left, vLeft)),
      height: Math.max(0, Math.min(rect.bottom, vBottom) - Math.max(rect.top, vTop)),
    };
  }

  function pinIframeModalToViewport(root) {
    if (!root) return;
    var slice = getVisibleIframeSlice();
    if (!slice || slice.width < 40 || slice.height < 40) {
      root.style.position = "fixed";
      root.style.inset = "0";
      root.style.width = "100%";
      root.style.height = "100%";
    } else {
      root.style.position = "fixed";
      root.style.top = slice.top + "px";
      root.style.left = slice.left + "px";
      root.style.width = slice.width + "px";
      root.style.height = slice.height + "px";
      root.style.right = "auto";
      root.style.bottom = "auto";
    }
    root.style.zIndex = "999999";
    root.style.display = "grid";
    root.style.placeItems = "center";
    root.style.padding = "1.25rem";
    root.style.boxSizing = "border-box";
    root.hidden = false;
  }

  function openIframeFallbackModal(tableEl, opts) {
    origOpen.call(fs, tableEl, opts || {});
    var root = document.getElementById(IFRAME_MODAL_ID);
    if (!root) return;
    root.classList.add("rwa-table-modal--streamlit-fallback");
    pinIframeModalToViewport(root);
    window.__TMMF_MODAL_OPEN = true;
    var dialog = root.querySelector(".rwa-table-modal__dialog");
    if (dialog && dialog.scrollIntoView) {
      try {
        dialog.scrollIntoView({ block: "center", inline: "nearest" });
      } catch (e) {}
    }
  }

  function openCenteredModal(tableEl, opts) {
    if (!tableEl) return;
    if (postOpenToHost(tableEl, opts || {})) return;
    openIframeFallbackModal(tableEl, opts);
  }

  function closeCenteredModal() {
    postCloseToHost();
    var iframeRoot = document.getElementById(IFRAME_MODAL_ID);
    if (iframeRoot) {
      iframeRoot.hidden = true;
      iframeRoot.classList.remove("rwa-table-modal--streamlit-fallback");
    }
    origClose.call(fs);
    window.__TMMF_MODAL_OPEN = false;
  }

  function resolveTableFromButton(btn) {
    var block = btn.closest(
      ".etp-mock-table-block, .rwa-deep-league-panel, #js-deep-extra-before-leagues"
    );
    if (!block) block = btn.closest("section, article, main");
    if (!block) return null;
    var wrap = block.querySelector(".table-wrap--scroll, .rwa-split-table-scroll, .table-wrap");
    if (!wrap) return null;
    var table = wrap.querySelector("table");
    if (!table) return null;
    return {
      table: table,
      title:
        wrap.getAttribute("data-fullscreen-title") ||
        table.getAttribute("aria-label") ||
        "Full-screen table",
    };
  }

  function handleExpandClick(ev) {
    var btn =
      ev.target && ev.target.closest
        ? ev.target.closest('.etp-mock-table-meta__expand, [data-rwa-fullscreen-btn="1"]')
        : null;
    if (!btn || btn.disabled) return;
    var resolved = resolveTableFromButton(btn);
    if (!resolved || !resolved.table) return;
    ev.preventDefault();
    ev.stopImmediatePropagation();
    openCenteredModal(resolved.table, { title: resolved.title });
  }

  document.addEventListener("click", handleExpandClick, true);
  document.addEventListener(
    "keydown",
    function (ev) {
      if (ev.key === "Escape" && window.__TMMF_MODAL_OPEN) closeCenteredModal();
    },
    true
  );

  fs.openTableModal = openCenteredModal;
  fs.closeTableModal = closeCenteredModal;
  fs.attachTableFullscreenButton = function (tableWrap, tableEl, opts) {
    var actions = origAttach.call(fs, tableWrap, tableEl, opts);
    if (actions && tableEl) {
      var btn = actions.querySelector('[data-rwa-fullscreen-btn="1"]');
      if (btn && !btn._stTmmfHostBound) {
        btn._stTmmfHostBound = true;
        btn.addEventListener(
          "click",
          function (ev) {
            ev.preventDefault();
            ev.stopImmediatePropagation();
            openCenteredModal(tableEl, opts || {});
          },
          true
        );
      }
    }
    return actions;
  };

  if (window.__RWA_STATIC_HELPERS) {
    window.__RWA_STATIC_HELPERS.openRwaTableModal = openCenteredModal;
    window.__RWA_STATIC_HELPERS.closeRwaTableModal = closeCenteredModal;
    window.__RWA_STATIC_HELPERS.attachRwaTableFullscreenButton = fs.attachTableFullscreenButton;
  }

  function rewireExistingButtons() {
    document
      .querySelectorAll('[data-rwa-fullscreen-btn="1"], .etp-mock-table-meta__expand')
      .forEach(function (btn) {
        if (btn._stTmmfHostBound) return;
        btn._stTmmfHostBound = true;
        btn.addEventListener(
          "click",
          function (ev) {
            var resolved = resolveTableFromButton(btn);
            if (!resolved || !resolved.table) return;
            ev.preventDefault();
            ev.stopImmediatePropagation();
            openCenteredModal(resolved.table, { title: resolved.title });
          },
          true
        );
      });
  }

  var loadJsonFn = window.loadJson;
  if (typeof loadJsonFn === "function" && !loadJsonFn._stTmmfWrapped) {
    window.loadJson = function () {
      return Promise.resolve(loadJsonFn.apply(this, arguments)).then(function (payload) {
        setTimeout(rewireExistingButtons, 0);
        setTimeout(rewireExistingButtons, 400);
        return payload;
      });
    };
    window.loadJson._stTmmfWrapped = true;
  }
  setTimeout(rewireExistingButtons, 0);
  setTimeout(rewireExistingButtons, 800);
  setTimeout(rewireExistingButtons, 2500);
})();
"""

_TMMF_MEASURE_HEIGHT_JS = """
function measureTmmfContentHeight() {
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

_TMMF_IFRAME_BACK_LINK = """
<div class="page-back-below-header tmmf-server-back-row">
  <a class="tmmf-server-back-anchor back-link back-link--below-header" data-deep-back="explore" href="{back_href}">{back_label_html}</a>
</div>
"""

_TMMF_ZONE_BODY = """
<main class="page-shell etp-mock-shell">
  <article class="hub-section hub-section--panel inner-rich-zone zone--tmmf home-zone home-zone--tmmf etp-mock-zone">
    <div class="home-zone__stripe" aria-hidden="true"></div>
    <header class="home-zone__head">
      <span class="home-zone__badge" aria-hidden="true">MMF</span>
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
        <div id="js-deep-kpis" aria-label="Tokenized money market funds headline KPI strip"></div>
      </section>
      <div class="inner-rich-block etp-mock-key-obs-block" id="js-deep-ko-section" hidden aria-labelledby="js-deep-ko-h">
        <h2 class="subsection-head u-vh" id="js-deep-ko-h">Key Observations</h2>
        <p class="data-freshness" id="js-deep-ko-as-of" hidden></p>
        <div id="js-deep-ko"></div>
      </div>
      <section class="etp-mock-insights" id="js-deep-insights" hidden aria-labelledby="js-deep-insights-h">
        <h2 class="u-vh" id="js-deep-insights-h">Market structure</h2>
      </section>
      <section
        id="js-deep-extra-before-leagues"
        class="etp-mock-table-block etp-mock-table-block--funds"
        hidden
        aria-labelledby="funds-heading"
      ></section>
      <div id="deep-net-wrap"></div>
      <div id="js-deep-extra-after-network" hidden></div>
      <hr class="jd-divider" id="js-deep-rule-mid" hidden aria-hidden="true" />
      <div id="deep-plat-wrap"></div>
      <div id="js-deep-bottom-cta" class="cta-row rwa-deep-page-cta"></div>
      <p class="timestamp-foot" id="js-deep-footer-note"></p>
    </div>
  </article>
</main>
"""


def _static_tmmf_deep_fallback(*, error: str = "") -> dict[str, Any]:
    path = _DATA / "rwa_tokenized_mmf.json"
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


def load_tmmf_deep_payload() -> dict[str, Any]:
    """Live TMMF deep-page JSON (same shape as ``static_home/data/rwa_tokenized_mmf.json``)."""
    from rwa_league.mmf import build_curated_mmf_dashboard_data
    from scripts.export_static_site_data import _build_rwa_tokenized_mmf_deep_payload

    fund_assets, rows_net, rows_plat, kpis, err = build_curated_mmf_dashboard_data()
    mmf_pack = (rows_net, rows_plat, kpis, err)
    manifest: dict[str, Any] = {"errors": []}
    payload = _build_rwa_tokenized_mmf_deep_payload(
        mmf_pack,
        manifest,
        [],
        fund_assets=fund_assets,
    )
    payload["back_href"] = "/?jd_scroll=tmmf"
    return payload


def get_tmmf_deep_payload() -> dict[str, Any]:
    from streamlit_payload_stale_first import load_static_first_with_live_fallback, mark_dict_stale

    return load_static_first_with_live_fallback(
        load_stale=lambda: _static_tmmf_deep_fallback() or None,
        load_live_cached=_cached_tmmf_deep_payload,
        mark_stale=mark_dict_stale,
    )


def _json_for_script(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, default=str)
    return raw.replace("</", "<\\/")


@st.cache_resource(show_spinner=False)
def _cached_iframe_tmmf_stylesheet_v5() -> str:
    """Same CSS stack as ``static_home/rwa-tokenized-mmf.html`` (iframe-safe, no mock banners)."""
    from streamlit_site_parity import _iframe_tmmf_mock_css

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
    for rel in ("mockups/etp-inner-page-mock.css", "mockups/tmmf-inner-page-mock.css"):
        path = _STATIC / rel
        if path.is_file():
            chunks.append(_iframe_tmmf_mock_css(path.read_text(encoding="utf-8")))
    chunks.append(
        """
html, body.page-rwa-deep-mmf.site-experience {
  margin: 0;
  padding: 0;
  background: var(--wash, #f3f7fb);
  overflow: hidden;
}
html::before,
html::after,
body.page-rwa-deep-mmf::before,
body.page-rwa-deep-mmf::after {
  display: none !important;
  content: none !important;
  height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
}
body.page-rwa-deep-mmf .page-back-below-header {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0.35rem 1.25rem 0;
  box-sizing: border-box;
}
body.page-rwa-deep-mmf p.back-link.back-link--below-header {
  margin: 0.2rem 0 0.85rem;
}
body.page-rwa-deep-mmf.site-experience.page-inner--rich .back-link--below-header a {
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
body.page-rwa-deep-mmf.site-experience.page-inner--rich .back-link--below-header a:hover {
  color: var(--hx-tmmf-bright, #507188);
  border-color: rgb(80 113 136 / 0.45);
  background: #f8fcfe;
}
body.page-rwa-deep-mmf .page-shell.etp-mock-shell {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0 1.25rem 1.5rem;
  box-sizing: border-box;
}
body.page-rwa-deep-mmf .home-reveal {
  opacity: 1 !important;
  transform: none !important;
}
body.page-rwa-deep-mmf .rwa-table-modal--streamlit-fallback:not([hidden]) {
  display: grid !important;
  place-items: center !important;
  padding: 1.25rem !important;
  box-sizing: border-box !important;
}
body.page-rwa-deep-mmf .rwa-table-modal--streamlit-fallback .rwa-table-modal__dialog {
  max-height: min(92vh, 980px);
  width: min(96%, 1400px);
}
"""
    )
    return "\n".join(chunks)


@st.cache_resource(show_spinner=False)
def _cached_tmmf_server_host_stylesheet() -> str:
    """TMMF mock CSS scoped onto the Streamlit host (not a giant components.html blob)."""
    import re

    raw = _cached_iframe_tmmf_stylesheet_v5()
    css_lines = [
        line
        for line in raw.splitlines()
        if not ("@import url(" in line and "fonts.googleapis.com" in line)
    ]
    css = "\n".join(css_lines)
    scope = ".stApp:has(.streamlit-tmmf-server-page) .streamlit-tmmf-server-host"
    css = css.replace("body.page-rwa-deep-mmf", scope)
    css = css.replace("html, body.page-rwa-deep-mmf.site-experience", scope)
    css = re.sub(
        r"html::before,\s*html::after,\s*" + re.escape(scope) + r"::before,\s*" + re.escape(scope) + r"::after",
        f"{scope}::before, {scope}::after",
        css,
    )
    css = css.replace("overflow: hidden;", "overflow: visible;")
    # Mock CSS scoped with :has() beats site-experience transparent KPI panel rules — restore GH Pages parity.
    css += f"""
{scope}.site-experience.page-inner--rich .inner-rich-zone__body .rwa-kpi-panel-static,
{scope}.site-experience[class*="page-rwa"] .etp-mock-snapshot .rwa-kpi-panel-static {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin-top: 0 !important;
  margin-bottom: 0.5rem !important;
}}
{scope}.site-experience.page-inner--rich .inner-rich-zone .jd-kpi-window-note {{
  display: block !important;
  margin: 0 0 0.5rem !important;
  font-size: 0.72rem !important;
  line-height: 1.45 !important;
  color: var(--muted, #5c6b7a) !important;
}}
"""
    return css


def inject_tmmf_server_host_styles() -> None:
    """Inject GitHub Pages TMMF styling on the Streamlit host for server-rendered pages."""
    st.markdown(
        f"<style>{_cached_tmmf_server_host_stylesheet()}</style>",
        unsafe_allow_html=True,
    )


def _read_js_files(names: tuple[str, ...]) -> str:
    parts: list[str] = []
    for name in names:
        path = _STATIC / "js" / name
        if path.is_file():
            parts.append(f"/* ---- {name} ---- */\n")
            parts.append(path.read_text(encoding="utf-8"))
            parts.append("\n")
    return "\n".join(parts)


def _tmmf_back_link_html(*, href: str, label: str) -> str:
    label_html = (
        escape(label)
        .replace("\u2190", "&larr;")
        .replace("\u00b7", "&middot;")
    )
    return _TMMF_IFRAME_BACK_LINK.format(back_href=escape(href), back_label_html=label_html)


def build_tmmf_body_iframe_html(
    *,
    payload: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=tmmf",
    back_label: str = "← Back to home · TMMF preview",
) -> str:
    """Self-contained iframe document — hydrates via ``rwa-asset-deep-page.js``."""
    from streamlit_site_parity import iframe_internal_link_script

    css = _cached_iframe_tmmf_stylesheet_v5()
    back_link = _tmmf_back_link_html(href=back_href, label=back_label)
    zone = _TMMF_ZONE_BODY.format(related_chips=related_chips.strip())
    payload_json = _json_for_script(payload)
    js_deps = _read_js_files(_TMMF_JS_DEPS)
    js_boot = _read_js_files(_TMMF_JS_BOOT)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
</head>
<body
  class="page-rwa-deep page-rwa-deep-mmf site-experience page-inner--rich mock-tmmf-inner"
  data-rwa-deep-json="rwa_tokenized_mmf.json"
  data-methodology="rwa-mmf"
>
{back_link}
{zone}
<script>
window.__RWA_DEEP_PAYLOAD = {payload_json};
</script>
<script defer src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
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
{_TMMF_MEASURE_HEIGHT_JS}
(function () {{
  function sendHeight() {{
    if (typeof window.parent.postMessage !== "function") return;
    var h = measureTmmfContentHeight();
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
      "#js-deep-extra-before-leagues",
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
      "#js-deep-extra-before-leagues",
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
def _cached_tmmf_deep_payload() -> dict[str, Any]:
    return load_tmmf_deep_payload()


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_tmmf_body_iframe_html(
    payload_json: str,
    related_chips: str,
    back_href: str,
    back_label: str,
) -> str:
    payload = json.loads(payload_json)
    return build_tmmf_body_iframe_html(
        payload=payload,
        related_chips=related_chips,
        back_href=back_href,
        back_label=back_label,
    )


def render_tmmf_body_iframe(
    *,
    payload: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=tmmf",
    back_label: str = "← Back to home · TMMF preview",
) -> None:
    """Render the GitHub Pages TMMF zone inside a Streamlit iframe."""
    payload_json = _json_for_script(payload)
    html = _cached_tmmf_body_iframe_html(
        payload_json,
        related_chips,
        back_href,
        back_label,
    )
    components.html(
        html,
        height=1200,
        scrolling=False,
    )


def build_tmmf_server_zone_html(
    *,
    payload: dict[str, Any],
    related_chips: str,
) -> str:
    """Server-rendered TMMF zone body (mock-parity markup, filled at build time)."""
    from streamlit_server_deep_page import (
        funds_table_html,
        key_observations_html,
        kpis_html_from_payload,
        league_table_html,
        tmmf_mock_insights_html,
    )

    title = str(payload.get("page_title") or "Tokenized Money Market Funds")
    title = title.replace(" — Digital Assets Dashboard", "").strip()
    band = str(payload.get("band_label") or "Tokenized Money Market Funds")
    subtitle = str(payload.get("page_subtitle_html") or "")
    footer = str(payload.get("footer_note") or "")
    err = str(payload.get("error") or payload.get("error_detail") or "").strip()
    banner = (
        f'<div class="data-banner" id="js-deep-banner" role="status">{escape(err)}</div>'
        if err
        else '<div class="data-banner" id="js-deep-banner" role="status" hidden></div>'
    )
    cta = payload.get("bottom_cta") or {}
    cta_href = str(cta.get("href") or "").strip()
    cta_label = str(cta.get("label") or "See US Treasuries on RWA.xyz")
    cta_html = (
        f'<div class="cta-row rwa-deep-page-cta" id="js-deep-bottom-cta">'
        f'<a class="btn btn-primary" href="{escape(cta_href)}" target="_blank" rel="noopener noreferrer">'
        f"{escape(cta_label)}</a></div>"
        if cta_href
        else '<div class="cta-row rwa-deep-page-cta" id="js-deep-bottom-cta"></div>'
    )
    has_net = bool((payload.get("networks") or {}).get("rows_full"))
    has_plat = bool((payload.get("platforms") or {}).get("rows_full"))
    mid_rule = (
        '<hr class="jd-divider" id="js-deep-rule-mid" aria-hidden="true" />'
        if has_net and has_plat
        else '<hr class="jd-divider" id="js-deep-rule-mid" hidden aria-hidden="true" />'
    )
    return (
        '<main class="page-shell etp-mock-shell">'
        '<article class="hub-section hub-section--panel inner-rich-zone zone--tmmf home-zone home-zone--tmmf etp-mock-zone">'
        '<div class="home-zone__stripe" aria-hidden="true"></div>'
        '<header class="home-zone__head">'
        '<span class="home-zone__badge" aria-hidden="true">MMF</span>'
        '<div class="home-zone__titles">'
        f'<p class="band-label teal" id="js-deep-band">{escape(band)}</p>'
        f'<h1 class="page-intro__title" id="js-deep-title">{escape(title)}</h1>'
        f'<div class="section-dek section-dek--wide page-intro__dek" id="js-deep-subtitle">{subtitle}</div>'
        "</div></header>"
        '<div class="home-zone__body inner-rich-zone__body etp-mock-zone__body">'
        f"{related_chips.strip()}"
        f"{banner}"
        f"{kpis_html_from_payload(list(payload.get('kpis') or []), note=str(payload.get('kpi_window_note') or ''))}"
        f"{key_observations_html(str(payload.get('key_observations_html') or ''))}"
        f"{tmmf_mock_insights_html(payload)}"
        f"{funds_table_html(payload.get('funds_table'))}"
        f"{league_table_html(payload.get('networks'), wrap_id='deep-net-wrap', is_network=True)}"
        f"{mid_rule}"
        f"{league_table_html(payload.get('platforms'), wrap_id='deep-plat-wrap', is_network=False)}"
        f"{cta_html}"
        f'<p class="timestamp-foot" id="js-deep-footer-note">{escape(footer)}</p>'
        "</div></article></main>"
    )


def build_tmmf_server_iframe_html(
    *,
    payload: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=tmmf",
    back_label: str = "← Back to home · TMMF preview",
) -> str:
    """Self-contained iframe with full TMMF CSS and server-rendered body (no JS hydration)."""
    from streamlit_site_parity import iframe_internal_link_script

    css = _cached_iframe_tmmf_stylesheet_v5()
    back_link = _tmmf_back_link_html(href=back_href, label=back_label)
    zone = build_tmmf_server_zone_html(payload=payload, related_chips=related_chips)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
</head>
<body
  class="page-rwa-deep page-rwa-deep-mmf site-experience page-inner--rich mock-tmmf-inner"
  data-methodology="rwa-mmf"
>
{back_link}
{zone}
<script>
{_TMMF_MEASURE_HEIGHT_JS}
(function () {{
  function sendHeight() {{
    if (typeof window.parent.postMessage !== "function") return;
    var h = measureTmmfContentHeight();
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
      "#js-deep-extra-before-leagues",
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
{iframe_internal_link_script()}
</body>
</html>"""


def render_tmmf_body_server(
    *,
    payload: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=tmmf",
    back_label: str = "← Back to home · TMMF preview",
) -> None:
    """Render TMMF on the Streamlit host: CSS in page head, body via st.html."""
    back_link = _tmmf_back_link_html(href=back_href, label=back_label)
    zone = build_tmmf_server_zone_html(payload=payload, related_chips=related_chips)
    st.html(
        f'<div class="streamlit-tmmf-server-host page-rwa-deep page-rwa-deep-mmf '
        f'site-experience page-inner--rich mock-tmmf-inner">'
        f"{back_link}{zone}</div>"
    )
