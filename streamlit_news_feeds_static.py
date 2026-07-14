"""Streamlit full news-feed pages — server-rendered iframes (parity with static_home/*.html)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Literal

import streamlit as st
import streamlit.components.v1 as components

from streamlit_tmmf_static import _json_for_script, _read_js_files

_REPO = Path(__file__).resolve().parent
_STATIC = _REPO / "static_home"
_DATA = _STATIC / "data"

_NEWS_IFRAME_CSS_VERSION = "12"
NEWS_CANVAS_OVERRIDE_VERSION = "1"
NEWS_FEED_PANEL_VERSION = "1"

NEWS_GH_PAGE_WASH = "#f3f7fb"
NEWS_GH_ZONE_SOFT_NEWS = "#eef4f8"
NEWS_GH_ZONE_SOFT_ETP = "#eef2f7"

_NEWS_JS_DEPS = ("static-base.js", "kpi-hints.js")
_NEWS_JS_FULL_FEED = ("full-article-feed-page.js",)
_NEWS_JS_ETF = ("etf-news-page.js",)
_NEWS_JS_HUB = ("news-hub-page.js",)

_NEWS_HUB_FEED_KEYS = (
    "all_articles.json",
    "etf_news.json",
    "all_regulatory.json",
    "all_custodian_news.json",
)

_LANE_TO_KIND = {
    "digital": "all_articles",
    "etf": "etf_news",
    "regulatory": "regulatory",
    "custody": "custodian",
}

_NEWS_MEASURE_HEIGHT_JS = """
function measureNewsFeedContentHeight() {
  if (window.__TMMF_MODAL_OPEN) return null;
  var scrollY = window.scrollY || document.documentElement.scrollTop || 0;
  var navEl =
    document.getElementById("js-article-feed-nav") ||
    document.getElementById("js-etf-news-nav");
  var nodes = [
    document.querySelector(".page-back-below-header"),
    document.querySelector("main.page-shell.etp-mock-shell"),
    document.querySelector("main.page-shell"),
    navEl,
  ];
  var maxBottom = 0;
  nodes.forEach(function (el) {
    if (!el) return;
    var rect = el.getBoundingClientRect();
    maxBottom = Math.max(maxBottom, rect.bottom + scrollY);
  });
  if (!maxBottom) return null;
  return Math.ceil(maxBottom + 6);
}
"""

_NEWS_IFRAME_BACK_LINK = """
<div class="page-back-below-header">
  <p class="back-link back-link--below-header">
    <a class="news-server-back-anchor" data-deep-back="explore" href="{back_href}">{back_label_html}</a>
  </p>
</div>
"""


@dataclass(frozen=True)
class NewsFeedPageSpec:
    kind: str
    feed_key: str
    use_full_article_feed_js: bool
    canvas_zone: Literal["news", "etp"]
    body_classes: str
    body_data_attrs: str
    zone_classes: str
    badge: str
    title: str
    dek_html: str
    search_placeholder: str
    default_back_href: str
    default_back_label: str
    configure_active: str


NEWS_FEED_SPECS: dict[str, NewsFeedPageSpec] = {
    "all_articles": NewsFeedPageSpec(
        kind="all_articles",
        feed_key="all_articles.json",
        use_full_article_feed_js=True,
        canvas_zone="news",
        body_classes=(
            "page-full-feed page-article-feed page-article-feed-iframe "
            "site-experience page-inner--rich"
        ),
        body_data_attrs='data-methodology="news" data-article-feed="all_articles.json" data-article-feed-page-size="20"',
        zone_classes="zone--news home-zone home-zone--news",
        badge="NEWS",
        title="All digital asset headlines",
        dek_html=(
            "Digital-asset headlines from <strong>CoinDesk</strong> and <strong>The Block</strong> only. "
            "Near-duplicate topics are collapsed to one story; at most <strong>8</strong> headlines per UTC day. "
            "Stories from the rolling <strong>last five days</strong>."
        ),
        search_placeholder="Keyword in title, summary, or source&hellip;",
        default_back_href="/?jd_scroll=news",
        default_back_label="← Back to home · News Hub",
        configure_active="news",
    ),
    "regulatory": NewsFeedPageSpec(
        kind="regulatory",
        feed_key="all_regulatory.json",
        use_full_article_feed_js=True,
        canvas_zone="news",
        body_classes=(
            "page-full-feed page-article-feed page-article-feed-iframe "
            "site-experience page-inner--rich"
        ),
        body_data_attrs=(
            'data-methodology="news" data-article-feed="all_regulatory.json" '
            'data-article-feed-country="1"'
        ),
        zone_classes="zone--news home-zone home-zone--news",
        badge="NEWS",
        title="All regulatory headlines",
        dek_html=(
            "Digital-asset regulatory and policy headlines from regulator, central-bank, and news feeds. "
            "Up to <strong>five</strong> ranked stories per <strong>UTC day</strong>; "
            "<strong>20</strong> per page with search."
        ),
        search_placeholder="Keyword in title, summary, source, or country&hellip;",
        default_back_href="/?jd_scroll=news",
        default_back_label="← Back to home · News Hub",
        configure_active="news",
    ),
    "custodian": NewsFeedPageSpec(
        kind="custodian",
        feed_key="all_custodian_news.json",
        use_full_article_feed_js=True,
        canvas_zone="news",
        body_classes=(
            "page-full-feed page-article-feed page-article-feed-iframe "
            "site-experience page-inner--rich"
        ),
        body_data_attrs=(
            'data-methodology="news" data-article-feed="all_custodian_news.json" '
            'data-article-feed-access="1"'
        ),
        zone_classes="zone--news home-zone home-zone--news",
        badge="NEWS",
        title="All custody headlines",
        dek_html=(
            "Crypto and digital-asset stories from "
            '<a href="https://www.globalcustodian.com/" target="_blank" rel="noopener noreferrer">'
            "Global Custodian</a> (digital-asset category RSS plus site search). "
            "Access badges are best-effort (Free / Subscriber / Check site)."
        ),
        search_placeholder="Keyword in title, summary, source, or category&hellip;",
        default_back_href="/?jd_scroll=news",
        default_back_label="← Back to home · News Hub",
        configure_active="news",
    ),
    "etf_news": NewsFeedPageSpec(
        kind="etf_news",
        feed_key="etf_news.json",
        use_full_article_feed_js=False,
        canvas_zone="etp",
        body_classes=(
            "page-full-feed page-article-feed page-article-feed-iframe page-etp "
            "site-experience page-inner--rich mock-etp-inner"
        ),
        body_data_attrs='data-methodology="etp"',
        zone_classes="zone--etp home-zone home-zone--etp",
        badge="ETP",
        title="ETF/ETP News",
        dek_html=(
            "ETF and ETP-related headlines from crypto and finance news sources. Up to "
            "<strong>five</strong> ranked stories per <strong>UTC day</strong> across a rolling "
            "<strong>five</strong>-day window, with search and pagination."
        ),
        search_placeholder="",
        default_back_href="/US_Crypto_ETPs",
        default_back_label="← Back to U.S. ETP Overview",
        configure_active="etps",
    ),
}


def _static_news_feed_fallback(*, feed_key: str, error: str = "") -> dict[str, Any]:
    path = _DATA / feed_key
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
    return {feed_key: data}


def load_news_feed_iframe_payloads(kind: str) -> dict[str, Any]:
    from news_feed_page_payloads import NEWS_FEED_BUILDERS

    builder = NEWS_FEED_BUILDERS[kind]
    pack = builder()
    payloads = dict(pack["payloads"])
    errors = list(pack.get("feed_errors") or [])
    if errors:
        feed_key = NEWS_FEED_SPECS[kind].feed_key
        merged = dict(payloads.get(feed_key) or {})
        merged["feed_errors"] = errors[:8]
        payloads[feed_key] = merged
    return payloads


def get_news_feed_iframe_payloads(kind: str) -> dict[str, Any]:
    from streamlit_payload_stale_first import load_static_first_with_live_fallback, mark_payload_map_stale

    spec = NEWS_FEED_SPECS[kind]

    return load_static_first_with_live_fallback(
        load_stale=lambda: _static_news_feed_fallback(feed_key=spec.feed_key) or None,
        load_live_cached=lambda: _cached_news_feed_iframe_payloads(kind),
        mark_stale=mark_payload_map_stale,
    )


def _news_zone_soft(zone: str) -> str:
    return NEWS_GH_ZONE_SOFT_ETP if zone == "etp" else NEWS_GH_ZONE_SOFT_NEWS


def _news_back_label_html(label: str) -> str:
    return (
        escape(label)
        .replace("\u2190", "&larr;")
        .replace("\u2192", "&rarr;")
        .replace("\u00b7", "&middot;")
    )


@st.cache_resource(show_spinner=False)
def _cached_iframe_news_stylesheet_v4() -> str:
    from streamlit_site_parity import deep_iframe_news_feed_panel_css

    chunks: list[str] = [
        "@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;780&display=swap');",
    ]
    for rel in (
        "styles.css",
        "css/site-experience.css",
        "css/inner-page-experience.css",
        "css/inner-page-zone-parity.css",
        "css/news-hub.css",
    ):
        path = _STATIC / rel
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))
    chunks.append(
        """
html, body.page-article-feed-iframe.site-experience {
  margin: 0;
  padding: 0;
  background: var(--wash, #f3f7fb) !important;
  background-image: none !important;
  overflow: hidden;
}
html::before, html::after,
body.page-article-feed-iframe::before,
body.page-article-feed-iframe::after {
  display: none !important;
  content: none !important;
  height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
}
body.page-article-feed-iframe .page-back-below-header {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0.35rem 1.25rem 0;
  box-sizing: border-box;
}
body.page-article-feed-iframe p.back-link.back-link--below-header {
  margin: 0.2rem 0 0.85rem;
}
body.page-article-feed-iframe main.page-shell.etp-mock-shell {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0 1.25rem 1.5rem;
  box-sizing: border-box;
}
body.page-article-feed-iframe .home-reveal {
  opacity: 1 !important;
  transform: none !important;
}
body.page-article-feed-iframe.page-etp.site-experience.page-inner--rich {
  background: var(--wash, #f3f7fb) !important;
  background-image: none !important;
}
"""
    )
    from streamlit_site_parity import (
        deep_iframe_back_link_clickable_css,
        deep_iframe_news_feed_panel_css,
        deep_iframe_related_chips_css,
    )

    chunks.append(deep_iframe_news_feed_panel_css(scope="body.page-article-feed-iframe", zone="news"))
    chunks.append(deep_iframe_news_feed_panel_css(scope="body.page-article-feed-iframe.page-etp", zone="etp"))
    chunks.append(deep_iframe_related_chips_css(scope="body.page-article-feed-iframe", zone="news"))
    chunks.append(deep_iframe_related_chips_css(scope="body.page-article-feed-iframe.page-etp", zone="etp"))
    chunks.append(deep_iframe_back_link_clickable_css(scope="body.page-article-feed-iframe"))
    return "\n".join(chunks)


def news_github_canvas_override_css(*, zone: str, version: str = NEWS_CANVAS_OVERRIDE_VERSION) -> str:
    from streamlit_site_parity import deep_iframe_news_feed_panel_css

    wash = NEWS_GH_PAGE_WASH
    soft = _news_zone_soft(zone)
    scope = "body.page-article-feed-iframe"
    zone_sel = "zone--etp" if zone == "etp" else "zone--news"
    scope_etp = f"{scope}.page-etp" if zone == "etp" else scope
    panel_css = deep_iframe_news_feed_panel_css(scope=scope_etp, zone=zone)
    return f"""
/* News feed GitHub Pages canvas override v{version} ({zone}) */
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
{scope} .inner-rich-zone.{zone_sel},
{scope} .inner-rich-zone.{zone_sel} .inner-rich-zone__body,
{scope} .etp-mock-zone.inner-rich-zone.{zone_sel},
{scope} .etp-mock-zone .inner-rich-zone__body {{
  background: {soft} !important;
  background-color: {soft} !important;
  background-image: none !important;
}}
{scope} .etp-mock-zone .hub-section.hub-section--panel {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}}
{panel_css}
"""


def news_iframe_canvas_override_js(*, zone: str, version: str = NEWS_CANVAS_OVERRIDE_VERSION) -> str:
    from streamlit_site_parity import deep_iframe_news_feed_panel_paint_js

    wash = NEWS_GH_PAGE_WASH
    soft = _news_zone_soft(zone)
    zone_sel = "zone--etp" if zone == "etp" else "zone--news"
    panel_paint_js = deep_iframe_news_feed_panel_paint_js()
    return f"""
<script id="news-gh-canvas-override-js-v{version}-{zone}">
(function () {{
  var WASH = "{wash}";
  var SOFT = "{soft}";
  var ZONE_SEL = ".inner-rich-zone.{zone_sel}";
  function setBg(el, color) {{
    if (!el) return;
    el.style.setProperty("background", color, "important");
    el.style.setProperty("background-color", color, "important");
    el.style.setProperty("background-image", "none", "important");
  }}
{panel_paint_js}
  function paint() {{
    setBg(document.documentElement, WASH);
    setBg(document.body, WASH);
    var main = document.querySelector("main.page-shell.etp-mock-shell");
    if (main) {{
      main.style.setProperty("background", "transparent", "important");
      main.style.setProperty("background-image", "none", "important");
    }}
    document.querySelectorAll(
      ZONE_SEL + ", " + ZONE_SEL + " .inner-rich-zone__body, .etp-mock-zone .inner-rich-zone__body"
    ).forEach(function (el) {{ setBg(el, SOFT); }});
    document.querySelectorAll(".etp-mock-zone .hub-section.hub-section--panel").forEach(function (el) {{
      el.style.setProperty("background", "transparent", "important");
      el.style.setProperty("border", "none", "important");
      el.style.setProperty("box-shadow", "none", "important");
    }});
    paintNewsFeedPanels();
  }}
  paint();
  window.addEventListener("load", paint);
  [50, 200, 800, 2000, 5000].forEach(function (ms) {{ setTimeout(paint, ms); }});
}})();
</script>
"""


def news_host_canvas_override_css(*, version: str = NEWS_CANVAS_OVERRIDE_VERSION) -> str:
    wash = NEWS_GH_PAGE_WASH
    return f"""
<style id="news-gh-host-canvas-override-v{version}">
.stApp:has(.streamlit-news-feed-iframe-page),
.withScreencast:has(.streamlit-news-feed-iframe-page),
[data-testid="stScreencast"]:has(.streamlit-news-feed-iframe-page),
.stApp:has(.streamlit-news-feed-iframe-page) [data-testid="stAppViewContainer"],
.stApp:has(.streamlit-news-feed-iframe-page) section.main,
.stApp:has(.streamlit-news-feed-iframe-page) [data-testid="stMain"],
.stApp:has(.streamlit-news-feed-iframe-page) [data-testid="stMainBlockContainer"],
.stApp:has(.streamlit-news-feed-iframe-page) .block-container,
.stApp:has(.streamlit-news-feed-iframe-page) [data-testid="stVerticalBlock"],
.stApp:has(.streamlit-news-feed-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe),
.stApp:has(.streamlit-news-feed-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe) [data-testid="stVerticalBlock"],
.stApp:has(.streamlit-news-feed-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe) [data-testid="stHtml"],
.stApp:has(.streamlit-news-feed-iframe-page) [data-testid="stElementContainer"]:has(.subpage-body-iframe-marker) + [data-testid="stElementContainer"]:has(iframe) [data-testid="stHtml"] > div {{
  background: {wash} !important;
  background-color: {wash} !important;
  background-image: none !important;
}}
</style>
"""


def news_host_canvas_override_js(*, version: str = NEWS_CANVAS_OVERRIDE_VERSION) -> str:
    wash = NEWS_GH_PAGE_WASH
    return f"""
<script id="news-gh-host-canvas-override-js-v{version}">
(function () {{
  var WASH = "{wash}";
  var doc = window.parent && window.parent.document ? window.parent.document : document;
  function paint() {{
    var app = doc.querySelector(".stApp");
    if (!app || !app.querySelector(".streamlit-news-feed-iframe-page")) return;
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
      if (!el.querySelector(".streamlit-news-feed-iframe-page")) return;
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


def inject_news_host_canvas_override() -> None:
    st.markdown(news_host_canvas_override_css(), unsafe_allow_html=True)
    components.html(news_host_canvas_override_js(), height=0, width=0)


def _feed_banner_html(feed_errors: list[str]) -> str:
    if not feed_errors:
        return ""
    banner_text = escape("; ".join(str(e) for e in feed_errors[:4]))
    return (
        f'<div class="data-banner" id="js-data-banner" role="status">'
        f"Partial feed warnings: {banner_text}</div>"
    )


def build_news_server_iframe_html(
    *,
    kind: str,
    payloads: dict[str, Any],
    related_chips: str = "",
    back_href: str | None = None,
    back_label: str | None = None,
) -> str:
    """Self-contained news-feed iframe with GitHub Pages CSS and server-rendered zone."""
    from streamlit_server_deep_page import build_news_feed_server_zone_html
    from streamlit_site_parity import deep_iframe_news_feed_panel_css, iframe_internal_link_script

    spec = NEWS_FEED_SPECS[kind]
    css = _cached_iframe_news_stylesheet_v4()
    override_css = news_github_canvas_override_css(zone=spec.canvas_zone)
    panel_css = deep_iframe_news_feed_panel_css(
        scope="body.page-article-feed-iframe.page-etp" if spec.canvas_zone == "etp" else "body.page-article-feed-iframe",
        zone=spec.canvas_zone,
    )
    href = back_href or spec.default_back_href
    label = back_label or spec.default_back_label
    label_html = _news_back_label_html(label)
    back_link = _NEWS_IFRAME_BACK_LINK.format(back_href=escape(href), back_label_html=label_html)

    feed_data = payloads.get(spec.feed_key) if isinstance(payloads.get(spec.feed_key), dict) else {}
    feed_errors = feed_data.get("feed_errors") if isinstance(feed_data.get("feed_errors"), list) else []
    zone = build_news_feed_server_zone_html(
        zone_classes=spec.zone_classes,
        badge=spec.badge,
        title=spec.title,
        dek_html=spec.dek_html,
        search_placeholder=spec.search_placeholder,
        related_chips=related_chips,
        feed_banner_html=_feed_banner_html(list(feed_errors)),
        use_etf_news_ids=not spec.use_full_article_feed_js,
    )
    payloads_json = _json_for_script(payloads)
    js_deps = _read_js_files(_NEWS_JS_DEPS)
    js_boot = _read_js_files(_NEWS_JS_FULL_FEED if spec.use_full_article_feed_js else _NEWS_JS_ETF)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
<style id="news-gh-canvas-override-v{NEWS_CANVAS_OVERRIDE_VERSION}-{spec.canvas_zone}">{override_css}</style>
<style id="news-feed-panel-v{NEWS_FEED_PANEL_VERSION}">{panel_css}</style>
</head>
<body class="{spec.body_classes.strip()}" {spec.body_data_attrs}>
{back_link}
{zone}
<script>
window.__NEWS_FEED_PAYLOADS = {payloads_json};
</script>
<script>
{js_deps}
</script>
<script>
window.loadJson = function (name) {{
  var key = String(name || "").split("/").pop();
  if (window.__NEWS_FEED_PAYLOADS && Object.prototype.hasOwnProperty.call(window.__NEWS_FEED_PAYLOADS, key)) {{
    return Promise.resolve(window.__NEWS_FEED_PAYLOADS[key]);
  }}
  return Promise.reject(new Error("Unknown news payload: " + name));
}};
</script>
<script>
{js_boot}
</script>
<script>
{_NEWS_MEASURE_HEIGHT_JS}
(function () {{
  function sendHeight() {{
    if (typeof window.parent.postMessage !== "function") return;
    var h = measureNewsFeedContentHeight();
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
      "#js-article-feed-list",
      "#js-article-feed-nav",
      "#js-etf-news-list",
      "#js-etf-news-nav",
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
      "#js-article-feed-list",
      "#js-etf-news-list",
      "#js-article-feed-nav",
      "#js-etf-news-nav",
    ].forEach(function (sel) {{
      var el = document.querySelector(sel);
      if (el) mo.observe(el, {{ childList: true, subtree: true }});
    }});
  }}
  [100, 400, 1000, 2500, 5000, 8000, 12000].forEach(function (ms) {{
    setTimeout(sendHeight, ms);
  }});
}})();
</script>
{news_iframe_canvas_override_js(zone=spec.canvas_zone)}
{iframe_internal_link_script()}
</body>
</html>"""


# Back-compat aliases for verify scripts and legacy callers.
build_news_feed_body_iframe_html = build_news_server_iframe_html


def _static_news_hub_fallback() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in _NEWS_HUB_FEED_KEYS:
        path = _DATA / key
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            out[key] = data
    return out


def load_news_hub_iframe_payloads() -> dict[str, Any]:
    """Load all four lane JSON payloads for the unified news hub."""
    payloads: dict[str, Any] = {}
    errors: list[str] = []
    for kind in ("all_articles", "etf_news", "regulatory", "custodian"):
        try:
            pack = load_news_feed_iframe_payloads(kind)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{kind}: {exc}")
            continue
        for key, val in pack.items():
            if isinstance(val, dict):
                payloads[key] = val
    if errors and not payloads:
        raise RuntimeError("; ".join(errors[:4]))
    return payloads


def get_news_hub_iframe_payloads() -> dict[str, Any]:
    from streamlit_payload_stale_first import load_static_first_with_live_fallback, mark_payload_map_stale

    return load_static_first_with_live_fallback(
        load_stale=lambda: _static_news_hub_fallback() or None,
        load_live_cached=lambda: _cached_news_hub_iframe_payloads(),
        mark_stale=mark_payload_map_stale,
    )


@st.cache_data(show_spinner=False, ttl=300)
def _cached_news_hub_iframe_payloads() -> dict[str, Any]:
    return load_news_hub_iframe_payloads()


def build_news_hub_iframe_html(
    *,
    payloads: dict[str, Any],
    initial_lane: str = "digital",
    back_href: str = "/?jd_scroll=news",
    back_label: str = "← Back to home · News Hub",
) -> str:
    from streamlit_server_deep_page import build_news_hub_server_zone_html
    from streamlit_site_parity import deep_iframe_news_feed_panel_css, iframe_internal_link_script

    lane = (initial_lane or "digital").strip().lower()
    if lane not in _LANE_TO_KIND:
        lane = "digital"
    zone = "etp" if lane == "etf" else "news"
    css = _cached_iframe_news_stylesheet_v4()
    override_css = news_github_canvas_override_css(zone=zone)
    panel_css = deep_iframe_news_feed_panel_css(
        scope="body.page-article-feed-iframe.page-etp" if zone == "etp" else "body.page-article-feed-iframe",
        zone=zone,
    )
    label_html = _news_back_label_html(back_label)
    back_link = _NEWS_IFRAME_BACK_LINK.format(back_href=escape(back_href), back_label_html=label_html)

    err_bits: list[str] = []
    for key in _NEWS_HUB_FEED_KEYS:
        feed = payloads.get(key) if isinstance(payloads.get(key), dict) else {}
        fe = feed.get("feed_errors") if isinstance(feed, dict) else None
        if isinstance(fe, list):
            err_bits.extend(str(e) for e in fe[:2])
    zone_html = build_news_hub_server_zone_html(
        initial_lane=lane,
        feed_banner_html=_feed_banner_html(err_bits[:4]),
    )
    payloads_json = _json_for_script(payloads)
    js_deps = _read_js_files(_NEWS_JS_DEPS)
    js_boot = _read_js_files(_NEWS_JS_HUB)
    body_etp = " page-etp" if lane == "etf" else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
<style id="news-gh-canvas-override-v{NEWS_CANVAS_OVERRIDE_VERSION}-{zone}">{override_css}</style>
<style id="news-feed-panel-v{NEWS_FEED_PANEL_VERSION}">{panel_css}</style>
</head>
<body class="page-full-feed page-article-feed page-article-feed-iframe page-news-hub site-experience page-inner--rich lane-{lane}{body_etp}" data-news-lane="{lane}">
{back_link}
{zone_html}
<script>
window.__NEWS_FEED_PAYLOADS = {payloads_json};
</script>
<script>
{js_deps}
</script>
<script>
window.loadJson = function (name) {{
  var key = String(name || "").split("/").pop();
  if (window.__NEWS_FEED_PAYLOADS && Object.prototype.hasOwnProperty.call(window.__NEWS_FEED_PAYLOADS, key)) {{
    return Promise.resolve(window.__NEWS_FEED_PAYLOADS[key]);
  }}
  return Promise.reject(new Error("Unknown news payload: " + name));
}};
</script>
<script>
{js_boot}
</script>
<script>
{_NEWS_MEASURE_HEIGHT_JS}
(function () {{
  function sendHeight() {{
    if (typeof window.parent.postMessage !== "function") return;
    var h = measureNewsFeedContentHeight();
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
      "#js-article-feed-list",
      "#js-article-feed-nav",
      "#js-news-hub-feature",
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
  [100, 400, 1000, 2500, 5000, 8000, 12000].forEach(function (ms) {{
    setTimeout(sendHeight, ms);
  }});
}})();
</script>
{news_iframe_canvas_override_js(zone=zone)}
{iframe_internal_link_script()}
</body>
</html>"""


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_news_hub_iframe_html(
    payloads_json: str,
    initial_lane: str,
    back_href: str,
    back_label: str,
    *,
    _css_version: str = _NEWS_IFRAME_CSS_VERSION,
) -> str:
    payloads = json.loads(payloads_json)
    return build_news_hub_iframe_html(
        payloads=payloads,
        initial_lane=initial_lane,
        back_href=back_href,
        back_label=back_label,
    )


def render_news_hub_body_iframe(
    *,
    payloads: dict[str, Any],
    initial_lane: str = "digital",
    back_href: str = "/?jd_scroll=news",
    back_label: str = "← Back to home · News Hub",
) -> None:
    from streamlit_site_parity import render_subpage_body_iframe

    payloads_json = _json_for_script(payloads)
    render_subpage_body_iframe(
        _cached_news_hub_iframe_html(
            payloads_json,
            initial_lane,
            back_href,
            back_label,
        ),
        height=1400,
    )
    inject_news_host_canvas_override()


@st.cache_data(show_spinner=False, ttl=300)
def _cached_news_feed_iframe_payloads(kind: str) -> dict[str, Any]:
    return load_news_feed_iframe_payloads(kind)


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_news_server_iframe_html(
    kind: str,
    payloads_json: str,
    related_chips: str,
    back_href: str,
    back_label: str,
    *,
    _css_version: str = _NEWS_IFRAME_CSS_VERSION,
) -> str:
    payloads = json.loads(payloads_json)
    return build_news_server_iframe_html(
        kind=kind,
        payloads=payloads,
        related_chips=related_chips,
        back_href=back_href,
        back_label=back_label,
    )


def render_news_feed_body_iframe(
    *,
    kind: str,
    payloads: dict[str, Any],
    related_chips: str = "",
    back_href: str | None = None,
    back_label: str | None = None,
) -> None:
    """Render a news-feed page inside a Streamlit iframe (deep-page parity)."""
    from streamlit_site_parity import render_subpage_body_iframe

    spec = NEWS_FEED_SPECS[kind]
    payloads_json = _json_for_script(payloads)
    render_subpage_body_iframe(
        _cached_news_server_iframe_html(
            kind,
            payloads_json,
            related_chips,
            back_href or spec.default_back_href,
            back_label or spec.default_back_label,
        ),
        height=1200,
    )
    inject_news_host_canvas_override()
