"""Streamlit Crypto Prices full page — static HTML iframe (parity with ``crypto-prices.html``)."""

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

_CRYPTO_JS_DEPS = (
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
_CRYPTO_JS_BOOT = ("crypto-page.js",)

_CRYPTO_PATCH_LOAD_JSON_JS = """
(function () {
  var load = window.loadJson;
  if (typeof load !== "function") return;
  function loadJsonWithTimeout(name, ms) {
    var timeoutMs = ms == null ? 14000 : ms;
    return new Promise(function (resolve, reject) {
      var done = false;
      var timer = setTimeout(function () {
        if (done) return;
        done = true;
        reject(new Error("Timed out loading " + name));
      }, timeoutMs);
      load(name)
        .then(function (data) {
          if (done) return;
          done = true;
          clearTimeout(timer);
          resolve(data);
        })
        .catch(function (err) {
          if (done) return;
          done = true;
          clearTimeout(timer);
          reject(err);
        });
    });
  }
  if (window.__DATA_FRESHNESS) {
    window.__DATA_FRESHNESS.loadJsonWithTimeout = loadJsonWithTimeout;
  }
  window.loadJsonWithTimeout = loadJsonWithTimeout;
})();
"""

_CRYPTO_MEASURE_HEIGHT_JS = """
function measureCryptoContentHeight() {
  if (window.__TMMF_MODAL_OPEN) return null;
  var scrollY = window.scrollY || document.documentElement.scrollTop || 0;
  var nodes = [
    document.querySelector(".page-back-below-header"),
    document.querySelector("main.page-shell.etp-mock-shell"),
    document.getElementById("js-crypto-generated"),
  ];
  var maxBottom = 0;
  nodes.forEach(function (el) {
    if (!el) return;
    var rect = el.getBoundingClientRect();
    if (rect.height <= 0 && el.id === "js-crypto-generated" && !(el.textContent || "").trim()) {
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

_CRYPTO_IFRAME_BACK_LINK = """
<div class="page-back-below-header">
  <p class="back-link back-link--below-header">
    <a href="{back_href}">{back_label_html}</a>
  </p>
</div>
"""

_CRYPTO_ZONE_BODY = """
<main class="page-shell etp-mock-shell">
  <article class="hub-section hub-section--panel inner-rich-zone zone--crypto home-zone home-zone--crypto etp-mock-zone">
    <div class="home-zone__stripe" aria-hidden="true"></div>
    <header class="home-zone__head">
      <span class="home-zone__badge" aria-hidden="true">CRY</span>
      <div class="home-zone__titles">
        <h1 class="page-intro__title">Crypto Prices &mdash; Top 50 Snapshot</h1>
        <p class="section-dek section-dek--wide">
          Top-line crypto market snapshot with a KPI strip, a 12-month total market-cap trend chart, category
          filters, and a searchable <strong>top 50</strong> spot-price table. Sources:
          <a href="https://coinpaprika.com/" target="_blank" rel="noopener noreferrer">CoinPaprika</a>
          (total cap),
          <a href="https://www.coingecko.com/" target="_blank" rel="noopener noreferrer">CoinGecko</a>
          (top 50; CoinCap fallback), and
          <a href="https://www.tradingview.com/symbols/TOTAL/" target="_blank" rel="noopener noreferrer"
            >TradingView TOTAL</a
          >
          (chart).
        </p>
      </div>
    </header>
    <div class="home-zone__body inner-rich-zone__body etp-mock-zone__body">
      {related_chips}
      <div class="data-banner" id="js-data-banner" role="status" hidden></div>
      <section class="etp-mock-snapshot" aria-labelledby="crypto-snapshot-heading">
        <h2 class="subsection-head u-vh" id="crypto-snapshot-heading">Top-line snapshot</h2>
        <p class="data-freshness etp-mock-freshness" id="js-crypto-snapshot-as-of" hidden></p>
        <div id="js-crypto-kpi" aria-label="Crypto KPI strip"></div>
      </section>
      <div class="inner-rich-block etp-mock-key-obs-block" aria-labelledby="crypto-ko-heading">
        <h2 class="subsection-head u-vh" id="crypto-ko-heading">Key observations</h2>
        <div id="js-crypto-key-obs" hidden></div>
      </div>
      <section class="etp-mock-insights etp-mock-insights--crypto-full" aria-labelledby="insights-heading">
        <h2 class="u-vh" id="insights-heading">Market structure</h2>
        <div class="etp-mock-insights__panel etp-mock-insights__panel--conc">
          <h3 class="etp-mock-insights__head">Top-50 market cap mix</h3>
          <p class="etp-mock-conc__dek">Share of top-50 market cap by category (CoinGecko snapshot).</p>
          <div
            id="js-crypto-cap-mix"
            class="etp-mock-conc__rows etp-mock-conc__rows--grid"
            role="img"
            aria-label="Top-50 market cap mix by category"
          ></div>
        </div>
      </section>
      <section class="etp-mock-dashboard etp-mock-dashboard--full-width" aria-labelledby="dashboard-heading">
        <h2 class="u-vh" id="dashboard-heading">Chart and context</h2>
        <div class="etp-mock-dash__panel etp-mock-dash__panel--chart">
          <h3 class="etp-mock-dash__head" id="js-crypto-chart-heading">Crypto total market cap</h3>
          <div id="crypto-market-cap-chart" class="aum-chart-host" role="img" aria-label="Crypto market cap chart"></div>
          <p class="etp-mock-chart__cap" id="js-crypto-chart-caption">
            TradingView TOTAL represents crypto market capitalization using the top 125 coins.
          </p>
          <p class="method-note etp-mock-chart__method" id="js-crypto-chart-method">
            The chart is powered by TradingView's TOTAL index so it does not rely on rate-limited local historical
            exports.
          </p>
          <p class="cta-note etp-mock-chart__method">
            <a
              id="js-crypto-chart-link"
              href="https://www.tradingview.com/symbols/TOTAL/"
              target="_blank"
              rel="noopener noreferrer"
              >Open the full TradingView TOTAL chart &rarr;</a
            >
          </p>
        </div>
      </section>
      <section class="etp-mock-table-block" aria-labelledby="crypto-table-heading">
        <div class="rwa-split-table-head inner-table-head">
          <h2 class="subsection-head rwa-split-table-head__title" id="crypto-table-heading">Prices table</h2>
          <div class="rwa-split-table-head__actions" id="js-crypto-table-actions"></div>
        </div>
        <div class="crypto-cat-tabs crypto-mock-cat-tabs" id="js-crypto-category-tabs"></div>
        <label class="search-field etp-mock-table-search">
          <span class="search-field__label">Search by coin name or ticker</span>
          <input
            type="search"
            class="search-field__input"
            id="js-crypto-search"
            placeholder="Filter by name or ticker&hellip;"
          />
        </label>
        <div class="etp-mock-table-meta crypto-mock-table-actions" aria-live="polite">
          <p class="etp-mock-table-meta__count toolbar-note" id="js-crypto-toolbar">Loading market table&hellip;</p>
          <p class="kpi-footnote kpi-footnote--block">
            Hover a <strong>Ticker</strong> or <strong>Coin</strong> name for a short summary from CoinGecko&rsquo;s
            About copy (mainstream adoption and uses, plus a brief lead).
          </p>
          <div class="rwa-table-actions" id="js-crypto-table-fullscreen"></div>
        </div>
        <div class="table-wrap table-wrap--scroll">
          <table class="data-table data-table--dense data-table--sortable" aria-label="Top 50 cryptocurrencies">
            <thead id="js-crypto-thead">
              <tr>
                <th class="th-sortable" data-sort="rank">Rank</th>
                <th class="th-sortable" data-sort="symbol">Ticker</th>
                <th class="th-sortable" data-sort="name">Coin</th>
                <th class="th-sortable" data-sort="category">Category</th>
                <th class="num th-sortable" data-sort="price_usd">Price</th>
                <th class="num th-sortable" data-sort="pct_30d">1M %</th>
                <th class="num th-sortable" data-sort="market_cap_usd">Market Cap</th>
                <th>Market Page</th>
              </tr>
            </thead>
            <tbody id="js-crypto-tbody">
              <tr>
                <td colspan="8">Loading&hellip;</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="rwa-table-footnote-row">
          <p class="source-cap rwa-table-footnote-row__cap">
            Top-line market-cap source: CoinPaprika. Spot market source: CoinGecko with CoinCap fallback. Market-cap
            chart source: TradingView TOTAL.
          </p>
        </div>
      </section>
      <p class="timestamp-foot" id="js-crypto-generated">&mdash;</p>
    </div>
  </article>
</main>
"""


def _static_crypto_payload_fallback(*, error: str = "") -> dict[str, Any]:
    """Last-resort payloads from runtime cache or committed static JSON exports."""
    from crypto_live_cache import bundle_from_static_exports, load_crypto_live_cache

    cached = load_crypto_live_cache(_DATA / "crypto_live_cache.json", static_dir=_DATA)
    if cached:
        out = {
            "crypto_kpis.json": dict(cached.get("kpis") or {}),
            "crypto_prices.json": dict(cached.get("prices") or {}),
            "crypto_market_cap_series.json": dict(cached.get("chart") or {}),
        }
    else:
        out = {}
        for name in ("crypto_kpis.json", "crypto_prices.json", "crypto_market_cap_series.json"):
            path = _DATA / name
            if path.is_file():
                out[name] = json.loads(path.read_text(encoding="utf-8"))
    if not out:
        seeded = bundle_from_static_exports(_DATA)
        if seeded:
            out = {
                "crypto_kpis.json": seeded.get("kpis") or {},
                "crypto_prices.json": seeded.get("prices") or {},
                "crypto_market_cap_series.json": seeded.get("chart") or {},
            }
    if error:
        for key in list(out):
            merged = dict(out[key])
            merged["error"] = error
            merged["stale"] = True
            out[key] = merged
    return out


def load_crypto_prices_iframe_payloads() -> dict[str, Any]:
    """Live crypto page JSON (kpis, prices, chart) matching static export shape."""
    from scripts.export_static_site_data import build_crypto_prices_page_payloads

    pack = build_crypto_prices_page_payloads(
        news_articles=None,
        blurb_cache_path=_DATA / "crypto_about_blurbs_cache.json",
        skip_about_blurbs=True,
        live_cache_path=_DATA / "crypto_live_cache.json",
    )
    return {
        "crypto_kpis.json": pack["kpis"],
        "crypto_prices.json": pack["prices"],
        "crypto_market_cap_series.json": pack["chart"],
    }


def get_crypto_iframe_payloads() -> dict[str, Any]:
    """Static JSON first; live fetch only when committed exports are missing."""
    from streamlit_payload_stale_first import load_static_first_with_live_fallback, mark_payload_map_stale

    return load_static_first_with_live_fallback(
        load_stale=lambda: _static_crypto_payload_fallback() or None,
        load_live_cached=_cached_crypto_prices_iframe_payloads,
        mark_stale=mark_payload_map_stale,
    )


@st.cache_resource(show_spinner=False)
def _cached_iframe_crypto_stylesheet_v1() -> str:
    """Same CSS stack as ``static_home/crypto-prices.html`` (iframe-safe, no mock banners)."""
    from streamlit_site_parity import _iframe_crypto_mock_css

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
    for rel in ("mockups/etp-inner-page-mock.css", "mockups/crypto-inner-page-mock.css"):
        path = _STATIC / rel
        if path.is_file():
            chunks.append(_iframe_crypto_mock_css(path.read_text(encoding="utf-8")))
    chunks.append(
        """
html, body.page-crypto-iframe.site-experience {
  margin: 0;
  padding: 0;
  background: var(--wash, #f3f7fb);
  overflow: hidden;
}
html::before,
html::after,
body.page-crypto-iframe::before,
body.page-crypto-iframe::after {
  display: none !important;
  content: none !important;
  height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
}
body.page-crypto-iframe .page-back-below-header {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0.35rem 1.25rem 0;
  box-sizing: border-box;
}
body.page-crypto-iframe p.back-link.back-link--below-header {
  margin: 0.2rem 0 0.85rem;
}
body.page-crypto-iframe .back-link--below-header a {
  display: inline-block;
  font-weight: 650;
  font-size: 0.84rem;
  line-height: 1.35;
  color: var(--ink-soft, #1f4c67);
  text-decoration: none;
}
body.page-crypto-iframe .back-link--below-header a:hover {
  color: var(--hx-crypto-bright, #507188);
}
body.page-crypto-iframe .page-shell.etp-mock-shell {
  max-width: var(--content-max, 72rem);
  margin: 0 auto;
  padding: 0 1.25rem 1.5rem;
  box-sizing: border-box;
}
body.page-crypto-iframe .home-reveal {
  opacity: 1 !important;
  transform: none !important;
}
body.page-crypto-iframe .rwa-table-modal--streamlit-fallback:not([hidden]) {
  display: grid !important;
  place-items: center !important;
  padding: 1.25rem !important;
  box-sizing: border-box !important;
}
body.page-crypto-iframe .rwa-table-modal--streamlit-fallback .rwa-table-modal__dialog {
  max-height: min(92vh, 980px);
  width: min(96%, 1400px);
}
"""
    )
    return "\n".join(chunks)


def _crypto_back_link_html(*, href: str, label: str) -> str:
    label_html = (
        escape(label)
        .replace("\u2190", "&larr;")
        .replace("\u00b7", "&middot;")
    )
    return _CRYPTO_IFRAME_BACK_LINK.format(back_href=escape(href), back_label_html=label_html)


def build_crypto_prices_body_iframe_html(
    *,
    payloads: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=crypto",
    back_label: str = "← Back to home · Crypto preview",
) -> str:
    """Self-contained iframe document — hydrates via ``crypto-page.js``."""
    from streamlit_site_parity import iframe_internal_link_script

    css = _cached_iframe_crypto_stylesheet_v1()
    back_link = _crypto_back_link_html(href=back_href, label=back_label)
    zone = _CRYPTO_ZONE_BODY.format(related_chips=related_chips.strip())
    payloads_json = _json_for_script(payloads)
    js_deps = _read_js_files(_CRYPTO_JS_DEPS)
    js_boot = _read_js_files(_CRYPTO_JS_BOOT)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>{css}</style>
</head>
<body
  class="page-crypto page-crypto-iframe site-experience page-inner--rich mock-crypto-inner"
  data-methodology="crypto"
>
{back_link}
{zone}
<script>
window.__CRYPTO_PAGE_PAYLOADS = {payloads_json};
</script>
<script>
{js_deps}
</script>
<script>
window.loadJson = function (name) {{
  var key = String(name || "").split("/").pop();
  if (window.__CRYPTO_PAGE_PAYLOADS && Object.prototype.hasOwnProperty.call(window.__CRYPTO_PAGE_PAYLOADS, key)) {{
    return Promise.resolve(window.__CRYPTO_PAGE_PAYLOADS[key]);
  }}
  return Promise.reject(new Error("Unknown crypto payload: " + name));
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
{_CRYPTO_MEASURE_HEIGHT_JS}
(function () {{
  function sendHeight() {{
    if (typeof window.parent.postMessage !== "function") return;
    var h = measureCryptoContentHeight();
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
      "#js-crypto-cap-mix",
      "#crypto-market-cap-chart",
      "#js-crypto-tbody",
      "#js-crypto-generated",
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
      "#js-crypto-key-obs",
      "#js-crypto-cap-mix",
      "#crypto-market-cap-chart",
      "#js-crypto-tbody",
    ].forEach(function (sel) {{
      var el = document.querySelector(sel);
      if (el) mo.observe(el, {{ childList: true, subtree: true, attributes: true }});
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
def _cached_crypto_prices_iframe_payloads() -> dict[str, Any]:
    return load_crypto_prices_iframe_payloads()


def render_crypto_prices_body_iframe(
    *,
    payloads: dict[str, Any],
    related_chips: str,
    back_href: str = "/?jd_scroll=crypto",
    back_label: str = "← Back to home · Crypto preview",
) -> None:
    """Render the GitHub Pages Crypto Prices zone inside a Streamlit iframe."""
    from streamlit_site_parity import render_subpage_body_iframe

    render_subpage_body_iframe(
        build_crypto_prices_body_iframe_html(
            payloads=payloads,
            related_chips=related_chips,
            back_href=back_href,
            back_label=back_label,
        ),
        height=1400,
    )
