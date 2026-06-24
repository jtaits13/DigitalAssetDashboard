"""Streamlit full news-feed pages — static HTML iframes (parity with static_home/*.html)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from streamlit_tmmf_static import _json_for_script, _read_js_files

_REPO = Path(__file__).resolve().parent
_STATIC = _REPO / "static_home"
_DATA = _STATIC / "data"

_NEWS_JS_DEPS = ("static-base.js", "kpi-hints.js")
_NEWS_JS_FULL_FEED = ("full-article-feed-page.js",)
_NEWS_JS_ETF = ("etf-news-page.js",)

_NEWS_MEASURE_HEIGHT_JS = """
function measureNewsFeedContentHeight() {
  if (window.__TMMF_MODAL_OPEN) return null;
  var scrollY = window.scrollY || document.documentElement.scrollTop || 0;
  var navEl =
    document.getElementById("js-article-feed-nav") ||
    document.getElementById("js-etf-news-nav");
  var nodes = [
    document.querySelector(".page-back-below-header"),
    document.querySelector("main.page-shell"),
    navEl,
    document.querySelector("main.page-shell > .back-link"),
  ];
  var maxBottom = 0;
  nodes.forEach(function (el) {
    if (!el) return;
    var rect = el.getBoundingClientRect();
    maxBottom = Math.max(maxBottom, rect.bottom + scrollY);
  });
  if (!maxBottom) {
    var main = document.querySelector("main.page-shell");
    if (main) {
      maxBottom = main.getBoundingClientRect().bottom + scrollY;
    }
  }
  if (!maxBottom) return null;
  return Math.ceil(maxBottom + 6);
}
"""

_NEWS_IFRAME_BACK_LINK = """
<div class="page-back-below-header">
  <p class="back-link back-link--below-header">
    <a href="{back_href}">{back_label_html}</a>
  </p>
</div>
"""

_FULL_ARTICLE_ZONE = """
<main class="page-shell">
  <article class="hub-section hub-section--panel inner-rich-zone {zone_classes}">
    <div class="home-zone__stripe" aria-hidden="true"></div>
    <header class="home-zone__head">
      <span class="home-zone__badge" aria-hidden="true">{badge}</span>
      <div class="home-zone__titles">
        <h1 class="page-intro__title">{title}</h1>
        <p class="page-intro__dek">{dek_html}</p>
      </div>
    </header>
    <div class="home-zone__body inner-rich-zone__body">
      <div class="data-banner" id="js-data-banner" role="status" hidden></div>
      <div class="article-feed-toolbar">
        <label class="search-field">
          <span class="search-field__label">Search headlines</span>
          <input
            type="search"
            class="search-field__input"
            id="js-article-feed-search"
            placeholder="{search_placeholder}"
          />
        </label>
        <p class="toolbar-note" id="js-article-feed-meta">Loading&hellip;</p>
      </div>
      <div class="article-feed-stream" id="js-article-feed-list"></div>
      <div class="etf-news-nav" id="js-article-feed-nav"></div>
    </div>
  </article>
  <p class="back-link">
    <a href="{back_href}">{back_label_html}</a>
  </p>
</main>
"""

_ETF_NEWS_ZONE = """
<main class="page-shell">
  <article class="hub-section hub-section--panel inner-rich-zone zone--etp home-zone home-zone--etp">
    <div class="home-zone__stripe" aria-hidden="true"></div>
    <header class="home-zone__head">
      <span class="home-zone__badge" aria-hidden="true">ETP</span>
      <div class="home-zone__titles">
        <h1 class="page-intro__title">ETF/ETP News</h1>
        <p class="page-intro__dek">
          ETF and ETP-related headlines from crypto and finance news sources. Up to
          <strong>five</strong> ranked stories per <strong>UTC day</strong> with search and pagination.
        </p>
      </div>
    </header>
    <div class="home-zone__body inner-rich-zone__body">
      <div class="data-banner" id="js-data-banner" role="status" hidden></div>
      <div class="article-feed-toolbar">
        <label class="search-field">
          <span class="search-field__label">Search headlines</span>
          <input
            type="search"
            class="search-field__input"
            id="js-etf-news-search"
            placeholder="Keyword in title or summary&hellip;"
          />
        </label>
        <p class="toolbar-note" id="js-etf-news-meta">Loading&hellip;</p>
      </div>
      <div class="article-feed-stream" id="js-etf-news-list"></div>
      <div class="etf-news-nav" id="js-etf-news-nav"></div>
    </div>
  </article>
  <p class="back-link">
    <a href="{back_href}">{back_label_html}</a>
  </p>
</main>
"""


@dataclass(frozen=True)
class NewsFeedPageSpec:
    kind: str
    feed_key: str
    use_full_article_feed_js: bool
    body_extra_class: str
    body_data_attrs: str
    zone_classes: str
    badge: str
    title: str
    dek_html: str
    search_placeholder: str
    default_back_href: str
    default_back_label: str


NEWS_FEED_SPECS: dict[str, NewsFeedPageSpec] = {
    "all_articles": NewsFeedPageSpec(
        kind="all_articles",
        feed_key="all_articles.json",
        use_full_article_feed_js=True,
        body_extra_class="",
        body_data_attrs='data-article-feed="all_articles.json" data-article-feed-page-size="20"',
        zone_classes="zone--news",
        badge="NEWS",
        title="All digital asset headlines",
        dek_html=(
            "Digital-asset-related headlines from CoinDesk, CoinTelegraph, Decrypt, The Block, and The Defiant. "
            "Stories from the <strong>last seven days</strong> (UTC); <strong>20</strong> per page with search."
        ),
        search_placeholder="Keyword in title, summary, or source&hellip;",
        default_back_href="/?jd_scroll=news",
        default_back_label="← Back to home · News Hub",
    ),
    "regulatory": NewsFeedPageSpec(
        kind="regulatory",
        feed_key="all_regulatory.json",
        use_full_article_feed_js=True,
        body_extra_class="",
        body_data_attrs='data-article-feed="all_regulatory.json" data-article-feed-country="1"',
        zone_classes="zone--news",
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
    ),
    "custodian": NewsFeedPageSpec(
        kind="custodian",
        feed_key="all_custodian_news.json",
        use_full_article_feed_js=True,
        body_extra_class="",
        body_data_attrs='data-article-feed="all_custodian_news.json" data-article-feed-access="1"',
        zone_classes="zone--news",
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
    ),
    "etf_news": NewsFeedPageSpec(
        kind="etf_news",
        feed_key="etf_news.json",
        use_full_article_feed_js=False,
        body_extra_class="page-etp",
        body_data_attrs="",
        zone_classes="zone--etp home-zone home-zone--etp",
        badge="ETP",
        title="ETF/ETP News",
        dek_html="",
        search_placeholder="",
        default_back_href="/US_Crypto_ETPs",
        default_back_label="← Back to U.S. ETP Overview",
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
    feed_key = NEWS_FEED_SPECS[kind].feed_key
    try:
        return load_news_feed_iframe_payloads(kind)
    except Exception as exc:
        fallback = _static_news_feed_fallback(feed_key=feed_key, error=str(exc))
        if fallback:
            return fallback
        raise


@st.cache_resource(show_spinner=False)
def _cached_iframe_news_stylesheet_v1() -> str:
    chunks: list[str] = [
        "@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;780&display=swap');",
    ]
    for rel in ("styles.css", "css/site-experience.css", "css/inner-page-experience.css"):
        path = _STATIC / rel
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))
    chunks.append(
        """
html, body.page-article-feed-iframe.site-experience {
  margin: 0;
  padding: 0;
  background: var(--wash, #f3f7fb);
  overflow: hidden;
}
html::before,
html::after,
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
body.page-article-feed-iframe main.page-shell {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0 1.25rem 1.5rem;
  box-sizing: border-box;
}
body.page-article-feed-iframe .home-reveal {
  opacity: 1 !important;
  transform: none !important;
}
"""
    )
    return "\n".join(chunks)


def _news_back_label_html(label: str) -> str:
    return (
        escape(label)
        .replace("\u2190", "&larr;")
        .replace("\u2192", "&rarr;")
        .replace("\u00b7", "&middot;")
    )


def build_news_feed_body_iframe_html(
    *,
    kind: str,
    payloads: dict[str, Any],
    back_href: str | None = None,
    back_label: str | None = None,
) -> str:
    from streamlit_site_parity import iframe_internal_link_script

    spec = NEWS_FEED_SPECS[kind]
    css = _cached_iframe_news_stylesheet_v1()
    href = back_href or spec.default_back_href
    label = back_label or spec.default_back_label
    label_html = _news_back_label_html(label)

    if spec.use_full_article_feed_js:
        zone = _FULL_ARTICLE_ZONE.format(
            zone_classes=spec.zone_classes,
            badge=escape(spec.badge),
            title=escape(spec.title),
            dek_html=spec.dek_html,
            search_placeholder=spec.search_placeholder,
            back_href=escape(href),
            back_label_html=label_html,
        )
        js_boot = _read_js_files(_NEWS_JS_FULL_FEED)
    else:
        zone = _ETF_NEWS_ZONE.format(
            back_href=escape(href),
            back_label_html=label_html,
        )
        js_boot = _read_js_files(_NEWS_JS_ETF)

    back_link = _NEWS_IFRAME_BACK_LINK.format(back_href=escape(href), back_label_html=label_html)
    payloads_json = _json_for_script(payloads)
    js_deps = _read_js_files(_NEWS_JS_DEPS)
    body_classes = (
        "page-full-feed page-article-feed page-article-feed-iframe site-experience page-inner--rich "
        + spec.body_extra_class
    ).strip()

    feed_errors = []
    feed_data = payloads.get(spec.feed_key) if isinstance(payloads.get(spec.feed_key), dict) else {}
    if isinstance(feed_data.get("feed_errors"), list):
        feed_errors = feed_data["feed_errors"]

    banner_init = ""
    if feed_errors:
        banner_text = escape("; ".join(str(e) for e in feed_errors[:4]))
        banner_init = f"""
(function () {{
  var b = document.getElementById("js-data-banner");
  if (b) {{
    b.hidden = false;
    b.textContent = "Partial feed warnings: {banner_text}";
  }}
}})();
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
</head>
<body class="{body_classes}" {spec.body_data_attrs}>
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
      "main.page-shell",
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
    {banner_init}
  }});
  if (typeof MutationObserver !== "undefined") {{
    var mo = new MutationObserver(function () {{
      sendHeight();
      bindObservers();
    }});
    [
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
{iframe_internal_link_script()}
</body>
</html>"""


@st.cache_data(show_spinner=False, ttl=300)
def _cached_news_feed_iframe_payloads(kind: str) -> dict[str, Any]:
    return get_news_feed_iframe_payloads(kind)


def render_news_feed_body_iframe(
    *,
    kind: str,
    payloads: dict[str, Any],
    back_href: str | None = None,
    back_label: str | None = None,
) -> None:
    components.html(
        build_news_feed_body_iframe_html(
            kind=kind,
            payloads=payloads,
            back_href=back_href,
            back_label=back_label,
        ),
        height=1200,
        scrolling=False,
    )
