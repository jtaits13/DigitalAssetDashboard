"""Layout helpers and shared CSS for the Streamlit home page."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Final, Literal, Optional

import streamlit as st

RWA_EXPLORE_TOP_NAV_SESSION_KEY: Final[str] = "_rwa_explore_top_nav"
RwaExploreTopNavTarget = Literal["home", "global_market"]


def rwa_xyz_mirror_footer_text() -> str:
    """Timestamp + cache/refresh hint for pages that mirror RWA.xyz (single wording everywhere)."""
    return (
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC · "
        "RWA.xyz data · Cached up to one hour · Use **Refresh all data** on the home page to reload."
    )


KEY_OBSERVATIONS_DISCLAIMER = (
    "Key observations are AI generated and should be reviewed for accuracy."
)


def key_observations_disclaimer_html() -> str:
    """Footnote under Key observations blocks (static + Streamlit)."""
    return f'<p class="review-note ko-disclaimer">{escape(KEY_OBSERVATIONS_DISCLAIMER)}</p>'


def monthly_review_note_html(*, year: int = 2026, month: int = 4) -> str:
    """Alias for :func:`key_observations_disclaimer_html` (legacy call sites)."""
    del year, month
    return key_observations_disclaimer_html()


def monthly_review_note_class_html(*, year: int = 2026, month: int = 4) -> str:
    """Alias for :func:`key_observations_disclaimer_html` (legacy call sites)."""
    del year, month
    return key_observations_disclaimer_html()


# Section rhythm: soft labels, ticker spacing, teal accent aligned with primaryColor.
# Streamlit st.dataframe: unify header/body font + color (sortable tables on home).
# KPI tile legends (RWA + ETP): one size/color everywhere.
KPI_WINDOW_NOTE_CSS = """
<style>
.jd-kpi-window-note {
    font-size: 0.64rem;
    font-weight: 400;
    color: #3E6A7A;
    margin: 0 0 0.5rem 0;
    line-height: 1.32;
}
</style>
"""

STREAMLIT_TABLE_UNIFY_CSS = """
<style>
div[data-testid="stDataFrame"] {
  font-size: 0.875rem;
  color: #021D41;
}
div[data-testid="stDataFrame"] [data-testid="stHeaderCell"],
div[data-testid="stDataFrame"] [role="columnheader"] {
  color: #021D41 !important;
  font-weight: 600;
  font-size: 0.875rem;
}
div[data-testid="stDataFrame"] [role="gridcell"] {
  color: #021D41;
  font-size: 0.875rem;
}
</style>
"""

ETP_FULLPAGE_AUM_LINE_CSS = """
<style>
.etp-fullpage-aum-line {
  font-size: 0.95rem;
  font-weight: 700;
  color: #021D41;
  margin: 0.35rem 0 0.85rem 0;
}
</style>
"""

STREAMLIT_TMMF_SUBPAGE_CSS = """
<style>
/* Streamlit TMMF inner page — parity with static_home/rwa-tokenized-mmf.html */

.stApp:has(.mock-tmmf-inner) {
  background:
    radial-gradient(ellipse 88% 52% at 6% -6%, rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.1), transparent 55%),
    radial-gradient(ellipse 70% 42% at 98% 2%, rgb(var(--hx-etp-rgb, 62 92 116) / 0.12), transparent 50%),
    var(--wash, #eef2f6);
}

.stApp:has(.mock-tmmf-inner) .inner-rich-zone.etp-mock-zone {
  margin-bottom: 0;
  border-bottom: none;
  border-radius: 14px 14px 0 0;
  max-width: 100%;
}

.stApp:has(.mock-tmmf-inner) .tmmf-streamlit-zone-body {
  margin: 0 0 1.25rem;
  padding: 0.2rem 1.25rem 1.35rem;
  border: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.2);
  border-top: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.12);
  border-radius: 0 0 14px 14px;
  background: linear-gradient(
    180deg,
    rgb(var(--hx-etp-rgb, 62 92 116) / 0.06) 0%,
    rgba(255, 255, 255, 0.98) 100%
  );
  box-shadow:
    0 1px 2px rgb(var(--hx-etp-rgb, 62 92 116) / 0.05),
    0 10px 28px rgb(var(--hx-etp-rgb, 62 92 116) / 0.07);
  max-width: 100%;
  box-sizing: border-box;
}

.stApp:has(.mock-tmmf-inner) .etp-mock-snapshot {
  margin-bottom: var(--etp-mock-gap, 1rem);
}

.stApp:has(.mock-tmmf-inner) .rwa-kpi-panel-static {
  background: rgb(var(--hx-etp-rgb, 62 92 116) / 0.05);
  border: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.14);
  border-radius: 10px;
  padding: 0.65rem 0.7rem;
  margin-bottom: 0;
}

.stApp:has(.mock-tmmf-inner) .rwa-kpi-row--home-grid {
  display: grid !important;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)) !important;
  gap: 0.55rem !important;
  justify-content: stretch !important;
  padding: 0 !important;
  border-bottom: none !important;
}

.stApp:has(.mock-tmmf-inner) .rwa-kpi-row--home-grid .rwa-kpi-cell {
  flex: none !important;
  min-width: 0 !important;
  max-width: none !important;
  text-align: left !important;
  border: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.18);
  border-left: 3px solid var(--hx-etp-bright, #507188);
  background: linear-gradient(145deg, var(--hx-etp-soft, #eef2f6) 0%, rgba(255, 255, 255, 0.92) 70%);
  border-radius: 8px;
  padding: 0.55rem 0.65rem;
}

.stApp:has(.mock-tmmf-inner) .rwa-kpi-row--home-grid .rwa-kpi-label {
  display: block;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--ink-soft, #1f4c67);
  margin-bottom: 0.32rem;
  line-height: 1.28;
}

.stApp:has(.mock-tmmf-inner) .rwa-kpi-row--home-grid .rwa-kpi-val {
  display: block;
  font-size: 1rem;
  font-weight: 700;
  color: var(--hx-etp, #3e5c74) !important;
  line-height: 1.2;
  margin-bottom: 0.18rem;
}

.stApp:has(.mock-tmmf-inner) .rwa-kpi-row--home-grid .rwa-kpi-delta {
  display: block;
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1.2;
  min-height: 1.15em;
  margin-top: 0;
}

.stApp:has(.mock-tmmf-inner) .rwa-kpi-row--home-grid .rwa-kpi-delta.up {
  color: #0d6b3a !important;
}

.stApp:has(.mock-tmmf-inner) .rwa-kpi-row--home-grid .rwa-kpi-delta.down {
  color: #b42318 !important;
}

.stApp:has(.mock-tmmf-inner) .jd-kpi-window-note,
.stApp:has(.mock-tmmf-inner) .rwa-onchain-kpi-legend {
  display: block;
  margin: 0 0 0.65rem;
  font-size: 0.72rem;
  line-height: 1.45;
  color: var(--muted, #5a7084);
  font-weight: 400;
}

.stApp:has(.mock-tmmf-inner) .jd-kpi-window-note strong {
  color: inherit;
  font-weight: inherit;
}

.stApp:has(.mock-tmmf-inner) .tmmf-streamlit-zone-body .jd-hub-subsection-head {
  display: none;
}

.stApp:has(.mock-tmmf-inner) .tmmf-streamlit-zone-body .inner-table-head {
  margin-bottom: 0.35rem;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.14);
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body .subsection-head {
  margin: 0;
  color: var(--hx-etp-dark, #31485c);
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body .tmmf-mock-league-intro {
  margin: 0 0 0.75rem;
  max-width: 52rem;
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--ink-muted, #4a5f73);
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body .tmmf-mock-league-intro strong {
  color: var(--hx-etp-dark, #31485c);
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body .etp-mock-table-block {
  margin-top: 0.15rem;
  padding-top: var(--etp-mock-gap-lg, 1.2rem);
  border-top: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.12);
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body .etp-mock-table-block.tmmf-mock-league-block {
  margin-top: 0;
  padding: 0.95rem 1rem 1rem;
  border: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.16);
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 1px 4px rgb(var(--hx-etp-rgb, 62 92 116) / 0.06);
  margin-bottom: var(--etp-mock-gap-lg, 1.2rem);
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body hr.jd-divider {
  border: none;
  border-top: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.14);
  margin: 0.35rem 0 var(--etp-mock-gap-lg, 1.2rem);
}

.stApp:has(.mock-tmmf-inner) [data-testid="stElementContainer"]:has(.etp-mock-key-obs-block) [data-testid="stMarkdownContainer"],
.stApp:has(.mock-tmmf-inner) [data-testid="stElementContainer"]:has(.etp-mock-key-obs-block) [data-testid="stMarkdownContainer"] > div {
  width: 100% !important;
  max-width: 100% !important;
}

.stApp:has(.mock-tmmf-inner) [data-testid="stElementContainer"]:has(.etp-mock-key-obs-block) .etp-mock-key-obs-block,
.stApp:has(.mock-tmmf-inner) .tmmf-streamlit-zone-body .etp-mock-key-obs-block {
  margin-bottom: var(--etp-mock-gap-lg, 1.2rem);
}

.stApp:has(.mock-tmmf-inner) [data-testid="stElementContainer"]:has(.etp-mock-key-obs-block) .crypto-story-callout,
.stApp:has(.mock-tmmf-inner) .tmmf-streamlit-zone-body .etp-mock-key-obs-block .crypto-story-callout {
  display: block;
  margin: 0;
  padding: 1rem 1.1rem 0.9rem;
  border: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.22);
  border-left: 4px solid var(--hx-etp-bright, #507188);
  border-radius: 10px;
  background: linear-gradient(160deg, rgb(var(--hx-etp-rgb, 62 92 116) / 0.07) 0%, #fff 55%);
  box-shadow: 0 1px 4px rgb(var(--hx-etp-rgb, 62 92 116) / 0.08);
}

.stApp:has(.mock-tmmf-inner) [data-testid="stElementContainer"]:has(.etp-mock-key-obs-block) .crypto-story-callout__title,
.stApp:has(.mock-tmmf-inner) .tmmf-streamlit-zone-body .etp-mock-key-obs-block .crypto-story-callout__title {
  margin: 0 0 0.55rem;
  padding-bottom: 0.45rem;
  border-bottom: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.14);
  font-size: 0.9rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--hx-etp-dark, #31485c) !important;
  line-height: 1.3 !important;
}

.stApp:has(.mock-tmmf-inner) [data-testid="stElementContainer"]:has(.etp-mock-key-obs-block) .crypto-story-callout__dek,
.stApp:has(.mock-tmmf-inner) .tmmf-streamlit-zone-body .etp-mock-key-obs-block .crypto-story-callout__dek {
  margin: 0 0 0.55rem;
  font-size: 0.78rem !important;
  line-height: 1.45 !important;
  color: var(--muted, #5a7084) !important;
}

.stApp:has(.mock-tmmf-inner) [data-testid="stElementContainer"]:has(.etp-mock-key-obs-block) .crypto-story-callout__list,
.stApp:has(.mock-tmmf-inner) .tmmf-streamlit-zone-body .etp-mock-key-obs-block .crypto-story-callout__list {
  margin: 0;
  padding-left: 1.05rem;
  font-size: 0.79rem !important;
  line-height: 1.48 !important;
  color: var(--ink-soft, #1f4c67) !important;
}

.stApp:has(.mock-tmmf-inner) [data-testid="stElementContainer"]:has(.etp-mock-key-obs-block) .crypto-story-callout__list li,
.stApp:has(.mock-tmmf-inner) .tmmf-streamlit-zone-body .etp-mock-key-obs-block .crypto-story-callout__list li {
  font-size: 0.79rem !important;
  line-height: 1.48 !important;
  color: var(--ink-soft, #1f4c67) !important;
}

.stApp:has(.mock-tmmf-inner) [data-testid="stElementContainer"]:has(.etp-mock-key-obs-block) .crypto-story-callout__list li + li,
.stApp:has(.mock-tmmf-inner) .tmmf-streamlit-zone-body .etp-mock-key-obs-block .crypto-story-callout__list li + li {
  margin-top: 0.4rem;
}

.stApp:has(.mock-tmmf-inner) [data-testid="stElementContainer"]:has(.etp-mock-key-obs-block) .crypto-story-callout__list a,
.stApp:has(.mock-tmmf-inner) .tmmf-streamlit-zone-body .etp-mock-key-obs-block .crypto-story-callout__list a {
  color: var(--hx-etp-bright, #507188);
  font-weight: 600;
  text-decoration: none;
}

.stApp:has(.mock-tmmf-inner) [data-testid="stElementContainer"]:has(.etp-mock-key-obs-block) .crypto-story-callout__list a:hover,
.stApp:has(.mock-tmmf-inner) .tmmf-streamlit-zone-body .etp-mock-key-obs-block .crypto-story-callout__list a:hover {
  color: var(--hx-etp, #3e5c74);
  text-decoration: underline;
  text-underline-offset: 0.12em;
}

.stApp:has(.mock-tmmf-inner) [data-testid="stElementContainer"]:has(.etp-mock-key-obs-block) .crypto-story-callout__note,
.stApp:has(.mock-tmmf-inner) .tmmf-streamlit-zone-body .etp-mock-key-obs-block .crypto-story-callout__note {
  margin: 0.55rem 0 0;
  padding: 0.55rem 0.65rem;
  border-top: none;
  border-radius: 8px;
  background: rgb(var(--hx-etp-rgb, 62 92 116) / 0.06);
  font-size: 0.73rem !important;
  line-height: 1.45 !important;
  color: var(--muted, #5a7084) !important;
}

.stApp:has(.mock-tmmf-inner) [data-testid="stElementContainer"]:has(.etp-mock-key-obs-block) .review-note.ko-disclaimer,
.stApp:has(.mock-tmmf-inner) .tmmf-streamlit-zone-body .etp-mock-key-obs-block .review-note.ko-disclaimer {
  margin: 0.5rem 0 0;
  padding: 0.38rem 0.55rem;
  border: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.16);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.85);
  font-size: 0.71rem;
  line-height: 1.4;
  color: var(--muted, #5a7084);
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body .jd-kpi-window-note,
.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body .etp-mock-snapshot__note {
  margin: 0.5rem 0 0;
  font-size: 0.72rem;
  line-height: 1.45;
  color: var(--muted, #5a7084);
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body [data-testid="stTextInput"] label p {
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  color: var(--hx-etp-dark, #31485c) !important;
  margin-bottom: 0.3rem !important;
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body [data-testid="stTextInput"] input {
  max-width: 32rem;
  font-size: 0.875rem !important;
  border-color: rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.22) !important;
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body [data-testid="stTextInput"] input:focus {
  border-color: var(--hx-etp-bright, #507188) !important;
  box-shadow: 0 0 0 3px rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.14) !important;
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body p.jd-subpage-toolbar-note {
  font-size: 0.78rem;
  color: var(--muted, #5a7084);
  margin: 0.35rem 0 0.65rem;
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body [data-testid="stCaptionContainer"] {
  font-size: 0.72rem !important;
  color: var(--muted, #5a7084) !important;
  line-height: 1.45 !important;
  max-width: 52rem;
  margin: 0.5rem 0 0.65rem !important;
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body div[data-testid="stDataFrame"] {
  font-size: 0.78rem;
  width: 100%;
  max-width: 100%;
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body div[data-testid="stDataFrame"] [role="columnheader"],
.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body div[data-testid="stDataFrame"] [role="gridcell"] {
  font-size: 0.78rem !important;
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body [data-testid="stLinkButton"] a {
  background: var(--hx-etp-bright, #507188) !important;
  border-color: rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.35) !important;
  color: #fff !important;
  font-size: 0.82rem !important;
  font-weight: 600 !important;
  max-width: 20rem;
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body [data-testid="stLinkButton"] {
  margin-top: var(--etp-mock-gap-lg, 1.2rem);
}

.stApp .mock-tmmf-inner .tmmf-streamlit-zone-body [data-testid="stVerticalBlock"] > div {
  max-width: 100%;
}

.stApp .mock-tmmf-inner .page-intro__dek.section-dek--wide {
  margin: 0;
  max-width: 52rem;
  font-size: 0.92rem;
  line-height: 1.5;
  color: var(--ink-muted, #4a5f73);
}

.stApp .mock-tmmf-inner .etp-mock-zone .page-intro__title {
  margin: 0 0 0.4rem;
  color: var(--hx-etp-dark, #31485c);
  font-size: clamp(1.35rem, 2.8vw, 1.75rem);
  font-weight: 780;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.stApp .mock-tmmf-inner .page-intro__dek.section-dek--wide strong {
  color: var(--hx-etp-dark, #31485c);
}
</style>
"""

HOME_PAGE_LAYOUT_CSS = """
<style>
/* Hub hierarchy: h1 → major section band (largest body heading) → lane/widget (smaller) → dek (smallest) */
h1.home-main-heading {
    font-size: clamp(1.45rem, 2.8vw, 1.85rem);
    font-weight: 750;
    letter-spacing: -0.03em;
    line-height: 1.2;
    color: #021D41;
    margin: 0.15rem 0 0.65rem 0;
}
h1.home-main-heading#jd-page-top {
    scroll-margin-top: 5.5rem;
}
/* In-page jump targets (nav); zero layout height */
.jd-hub-section-anchor {
    scroll-margin-top: 5.5rem;
    height: 0;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden;
    width: 100%;
    border: none;
}
/* Inside News columns + Markets teasers — always smaller than .home-band-label */
h2.home-lane-heading {
    font-size: 0.97rem;
    font-weight: 600;
    color: #021D41;
    margin: 0 0 0.5rem 0;
    letter-spacing: -0.015em;
    line-height: 1.35;
}
h2.home-widget-heading {
    font-size: 1.02rem;
    font-weight: 650;
    color: #021D41;
    margin: 0 0 0.4rem 0;
    letter-spacing: -0.018em;
    line-height: 1.3;
}
/* CoinDesk-style hub: section band + short dek + teaser content */
.jd-hub-band {
    margin-top: 0.25rem;
    margin-bottom: 0.35rem;
}
.jd-hub-dek {
    font-size: 0.76rem;
    font-weight: 400;
    color: #3E6A7A;
    line-height: 1.5;
    margin: 0 0 1rem 0;
    max-width: min(44rem, 100%);
}
[data-testid="stMarkdownContainer"] p.jd-hub-dek {
    font-size: 0.76rem !important;
}
/* Lead hub intros (see ``HOME_LEAD_DEK_OVERRIDE_LAST_CSS`` in news_feeds — appended last for cascade). */
.jd-hub-dek.jd-hub-dek--large {
    font-size: 0.9375rem;
}
[data-testid="stMarkdownContainer"] p.jd-hub-dek.jd-hub-dek--large {
    font-size: 0.9375rem !important;
}
.jd-hub-cta-note {
    font-size: 0.68rem;
    font-weight: 400;
    color: #3E6A7A;
    margin: 0.4rem 0 0.15rem 0;
    line-height: 1.38;
}
[data-testid="stMarkdownContainer"] p.jd-hub-cta-note {
    font-size: 0.68rem !important;
    line-height: 1.38 !important;
}
/* Multipage: result counts / filters under search (matches hub note color, clearer than raw caption) */
p.jd-subpage-toolbar-note {
    font-size: 0.78rem;
    color: #3E6A7A;
    margin: 0.35rem 0 0.85rem 0;
    line-height: 1.45;
    max-width: min(44rem, 100%);
}
p.jd-subpage-footer-heading {
    font-size: 0.82rem;
    font-weight: 650;
    color: #1F4C67;
    margin: 0.25rem 0 0.45rem 0;
    letter-spacing: -0.01em;
}
.cd-ticker-shell {
    margin-bottom: 1.25rem !important;
}
.home-band-label {
    font-size: 1.28rem;
    font-weight: 800;
    letter-spacing: -0.024em;
    line-height: 1.22;
    text-transform: none;
    color: #021D41;
    margin: 0 0 0.2rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #C7D8E8;
}
.home-band-label.teal {
    color: #25809C;
    border-bottom-color: #8CB9C9;
    /* Slightly larger optical size so teal reads at parity with navy headings */
    font-size: 1.3rem;
}
p.home-band-label.teal.jd-home-band-first {
    margin-top: 0.2rem;
}
p.home-band-label.teal.jd-home-band-after-rule {
    margin-top: 0.3rem;
}
/* Landing title + intro: spacing + reading width only (no card chrome) */
.jd-home-hero {
    margin: 0 0 0.75rem 0;
    padding: 0;
}
.jd-home-hero h1.home-main-heading#jd-page-top {
    margin: 0.12rem 0 0.4rem 0;
}
.jd-home-hero .jd-hub-dek {
    max-width: min(42rem, 100%);
}
[data-testid="stMarkdownContainer"] .jd-home-hero p.jd-hub-dek {
    margin: 0 0 0.42rem 0 !important;
}
[data-testid="stMarkdownContainer"] .jd-home-hero p.jd-hub-dek:last-child:not(.jd-home-hero__internal-callout) {
    margin-bottom: 0.15rem !important;
}
/* Confluence / internal callout: same blurb band, slightly stronger type + slim left rule (no box) */
.jd-home-hero p.jd-home-hero__internal-callout {
    margin-top: 0.35rem !important;
    padding-left: 0.7rem;
    border-left: 3px solid #25809c;
    font-weight: 600;
    color: #25809c;
    letter-spacing: 0.015em;
    box-sizing: border-box;
}
.jd-home-hero p.jd-home-hero__internal-callout strong {
    font-weight: 700;
    color: #25809c;
}
.jd-home-hero p.jd-home-hero__internal-callout a {
    color: #25809c;
    font-weight: 650;
    text-decoration: underline;
    text-underline-offset: 2px;
}
.jd-home-hero p.jd-home-hero__internal-callout a:hover {
    color: #1a6b7e;
}
[data-testid="stMarkdownContainer"] .jd-home-hero p.jd-home-hero__internal-callout.jd-hub-dek {
    font-size: 1rem !important;
    line-height: 1.48 !important;
    font-weight: 600 !important;
    color: #25809c !important;
    margin-bottom: 0.15rem !important;
    padding-left: 0.7rem !important;
    border-left: 3px solid #25809c !important;
    margin-top: 0.35rem !important;
}
[data-testid="stMarkdownContainer"] .jd-home-hero p.jd-home-hero__internal-callout strong {
    color: #25809c !important;
}
[data-testid="stMarkdownContainer"] .jd-home-hero p.jd-home-hero__internal-callout a {
    color: #25809c !important;
}
[data-testid="stMarkdownContainer"] .jd-home-hero p.jd-home-hero__internal-callout a:hover {
    color: #1a6b7e !important;
}

/* Full-bleed dividers between major hub blocks */
[data-testid="stAppViewContainer"] hr {
    margin: 1.25rem 0 !important;
    border: none;
    border-top: 1px solid #dce7f0;
}
/* Main-area captions: same tier as ``jd-hub-cta-note`` (sources, timestamps, section footnotes). */
section[data-testid="stMain"] [data-testid="stCaptionContainer"] {
    font-size: 0.68rem;
    line-height: 1.38;
    color: #3e6a7a;
}
section[data-testid="stMain"] [data-testid="stCaptionContainer"] p {
    font-size: inherit !important;
    line-height: inherit;
}
/* Wide layout stretches past the fixed nav + price ticker; cap main column to the same 1200px as .jd-site-nav-inner */
section[data-testid="stMain"] > div[data-testid="stMainBlockContainer"] {
    max-width: min(1200px, 100%) !important;
    margin-left: auto !important;
    margin-right: auto !important;
}
/* Older Streamlit: block-container on main wrapper */
section[data-testid="stMain"] > div.block-container {
    max-width: min(1200px, 100%) !important;
    margin-left: auto !important;
    margin-right: auto !important;
}
</style>
"""


def section_label_teal(text: str, *, placement: str = "default") -> str:
    """
    HTML for a major hub section title (teal accent, bottom rule).

    ``placement``: ``\"first\"`` — first band below the hero/ticker; ``\"after_divider\"`` —
    band following a full-width ``st.divider()`` (tighter top margin).
    """
    extra = ""
    if placement == "first":
        extra = " jd-home-band-first"
    elif placement == "after_divider":
        extra = " jd-home-band-after-rule"
    return f'<p class="home-band-label teal{extra}">{text}</p>'


def section_label_neutral(text: str) -> str:
    return f'<p class="home-band-label">{text}</p>'


def subpage_toolbar_note_html(text: str) -> str:
    """Muted line for filter/result counts on multipage feeds (pairs with ``.jd-hub-dek`` rhythm)."""
    return f'<p class="jd-subpage-toolbar-note">{escape(text)}</p>'


def subpage_footer_heading_html(text: str) -> str:
    """Small label above pagination controls (aligned with hub subsection color hierarchy)."""
    return f'<p class="jd-subpage-footer-heading">{escape(text)}</p>'


def subpage_footnote_html(text: str) -> str:
    """Bottom-of-page or bottom-of-section footnote (``jd-hub-cta-note``); plain text only (escaped)."""
    return f'<p class="jd-hub-cta-note">{escape(text)}</p>'


def subpage_footnote_markup_html(inner_html: str) -> str:
    """
    Same visual tier as :func:`subpage_footnote_html` for **trusted** inline markup only
    (e.g. ``<strong>`` / ``<a href="...">`` from static copy in repo code).
    """
    return f'<p class="jd-hub-cta-note">{inner_html}</p>'


def hub_subsection_heading_html(text: str, *, element_id: Optional[str] = None) -> str:
    """
    HTML for an in-section title matching **RWA Global Market Overview** / **U.S. Digital Asset ETPs** on the hub:
    ``jd-hub-subsection-head`` + ``h2.home-main-heading`` (slim rule, navy text — not the teal major band).
    """
    id_attr = f' id="{escape(element_id, quote=True)}"' if element_id else ""
    return (
        f'<div class="jd-hub-subsection-head"{id_attr}>'
        f'<h2 class="home-main-heading">{escape(text)}</h2></div>'
    )


def inner_subsection_heading_html(
    text: str,
    *,
    element_id: Optional[str] = None,
    heading_level: int = 2,
) -> str:
    """GitHub Pages inner-table heading (``subsection-head`` inside ``inner-table-head``)."""
    tag = f"h{max(2, min(4, heading_level))}"
    id_attr = f' id="{escape(element_id, quote=True)}"' if element_id else ""
    return (
        f'<div class="inner-table-head">'
        f'<{tag} class="subsection-head rwa-split-table-head__title"{id_attr}>{escape(text)}</{tag}>'
        f"</div>"
    )


def hub_section_anchor(element_id: str) -> str:
    """Zero-height scroll target for hub nav / fragment links (IDs must be URL-safe)."""
    safe = "".join(c for c in element_id if c.isalnum() or c in "-_")
    if not safe or safe != element_id.strip():
        raise ValueError("hub_section_anchor: invalid element_id")
    return f'<div id="{safe}" class="jd-hub-section-anchor" aria-hidden="true"></div>'


def set_rwa_explore_top_nav_target(target: RwaExploreTopNavTarget) -> None:
    """Set before ``st.switch_page`` to an Explore index so that page can render the correct top control."""
    st.session_state[RWA_EXPLORE_TOP_NAV_SESSION_KEY] = target


def render_rwa_explore_top_nav_button(*, key: str) -> None:
    """Top-left control on Explore index pages: always return to RWA Global Market Overview."""
    if st.button("← RWA Global Market Overview", key=key):
        st.switch_page("pages/RWA_Global_Market_Overview.py")
