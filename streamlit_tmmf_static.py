"""Streamlit TMMF full page — static HTML iframe (parity with ``rwa-tokenized-mmf.html``)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

_REPO = Path(__file__).resolve().parent
_STATIC = _REPO / "static_home"

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


def load_tmmf_deep_payload() -> dict[str, Any]:
    """Live TMMF deep-page JSON (same shape as ``static_home/data/rwa_tokenized_mmf.json``)."""
    from key_observations.feeds import load_takeaway_articles
    from rwa_league.client import fetch_rwa_tokenized_mmf_data
    from scripts.export_static_site_data import _build_rwa_tokenized_mmf_deep_payload

    mmf_pack = fetch_rwa_tokenized_mmf_data()
    manifest: dict[str, Any] = {"errors": []}
    payload = _build_rwa_tokenized_mmf_deep_payload(
        mmf_pack,
        manifest,
        load_takeaway_articles(),
    )
    payload["back_href"] = "/?jd_scroll=tmmf"
    return payload


def _json_for_script(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, default=str)
    return raw.replace("</", "<\\/")


@st.cache_resource(show_spinner=False)
def _cached_iframe_tmmf_stylesheet() -> str:
    """Same CSS stack as ``static_home/rwa-tokenized-mmf.html``."""
    from streamlit_site_parity import _patch_inner_page_css_for_streamlit

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
            chunks.append(_patch_inner_page_css_for_streamlit(path.read_text(encoding="utf-8")))
    for rel in ("mockups/etp-inner-page-mock.css", "mockups/tmmf-inner-page-mock.css"):
        path = _STATIC / rel
        if path.is_file():
            chunks.append(_patch_inner_page_css_for_streamlit(path.read_text(encoding="utf-8")))
    chunks.append(
        """
html, body.page-rwa-deep-mmf.site-experience {
  margin: 0;
  padding: 0;
  background: var(--wash, #f3f7fb);
  overflow: visible;
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
"""
    )
    return "\n".join(chunks)


def _read_js_files(names: tuple[str, ...]) -> str:
    parts: list[str] = []
    for name in names:
        path = _STATIC / "js" / name
        if path.is_file():
            parts.append(f"/* ---- {name} ---- */\n")
            parts.append(path.read_text(encoding="utf-8"))
            parts.append("\n")
    return "\n".join(parts)


def build_tmmf_body_iframe_html(*, payload: dict[str, Any], related_chips: str) -> str:
    """Self-contained iframe document — hydrates via ``rwa-asset-deep-page.js``."""
    from streamlit_site_parity import iframe_auto_height_script, iframe_internal_link_script

    css = _cached_iframe_tmmf_stylesheet()
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
{js_boot}
</script>
{iframe_auto_height_script(root_selector=".etp-mock-zone__body", extra_pad=48)}
{iframe_internal_link_script()}
</body>
</html>"""


def render_tmmf_body_iframe(*, payload: dict[str, Any], related_chips: str) -> None:
    """Render the GitHub Pages TMMF zone inside a Streamlit iframe."""
    st.markdown(
        '<span class="tmmf-body-iframe-marker" hidden aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    components.html(
        build_tmmf_body_iframe_html(payload=payload, related_chips=related_chips),
        height=3200,
        scrolling=False,
    )
