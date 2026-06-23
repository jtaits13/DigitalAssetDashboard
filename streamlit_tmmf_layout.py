"""Streamlit TMMF full page — GitHub Pages ``etp-mock-zone`` envelope via bordered container."""

from __future__ import annotations

from html import escape

TMMF_ZONE_CARD_KEY = "tmmf_zone_card"
_CARD = f'[data-testid="stVerticalBlockBorderWrapper"].st-key-{TMMF_ZONE_CARD_KEY}'
_BODY = f'.stApp {_CARD} > [data-testid="stVerticalBlock"]'
_TABLE = f'.stApp {_CARD} [data-testid="stVerticalBlockBorderWrapper"]:has(.tmmf-streamlit-table-block)'


def tmmf_github_zone_header_html(
    *,
    section_id: str,
    badge: str,
    title: str,
    subtitle_html: str,
    subtitle_class: str = "section-dek section-dek--wide page-intro__dek",
) -> str:
    """Header markup from ``static_home/rwa-tokenized-mmf.html`` (inside the zone card)."""
    dek_tag = "div" if "section-dek" in subtitle_class else "p"
    return (
        '<span class="tmmf-streamlit-zone-marker" hidden aria-hidden="true"></span>'
        '<div class="home-zone__stripe" aria-hidden="true"></div>'
        '<header class="home-zone__head">'
        f'<span class="home-zone__badge" aria-hidden="true">{escape(badge)}</span>'
        '<div class="home-zone__titles">'
        f'<p class="page-intro__title" role="heading" aria-level="1" id="{escape(section_id)}-heading">'
        f"{escape(title)}</p>"
        f'<{dek_tag} class="{escape(subtitle_class)}">{subtitle_html}</{dek_tag}>'
        "</div>"
        "</header>"
    )


# Copied from static_home/mockups/etp-inner-page-mock.css — applied to the Streamlit bordered
# wrapper that replaces ``<article class="etp-mock-zone">`` (widgets cannot live inside HTML).
STREAMLIT_TMMF_SUBPAGE_CSS = f"""
<style>
.stApp [data-testid="stElementContainer"]:has(.st-key-{TMMF_ZONE_CARD_KEY}) {{
  padding-left: 0 !important;
  padding-right: 0 !important;
  max-width: var(--content-max, var(--max, 72rem)) !important;
}}

/* —— etp-mock-zone shell (rwa-tokenized-mmf.html) —— */
.stApp {_CARD} {{
  display: block !important;
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 auto 1.35rem !important;
  padding: 0 !important;
  overflow: hidden !important;
  box-sizing: border-box !important;
  --hx-stripe: var(--hx-etp-bright, #507188);
  border: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.2) !important;
  border-radius: 14px !important;
  background: var(--hx-etp-soft, #eef2f6) !important;
  box-shadow:
    0 1px 2px rgb(var(--hx-etp-rgb, 62 92 116) / 0.05),
    0 10px 28px rgb(var(--hx-etp-rgb, 62 92 116) / 0.07) !important;
}}

/* —— etp-mock-zone__body / inner-rich-zone__body gradient —— */
.stApp {_BODY} {{
  gap: 0 !important;
  background: linear-gradient(
    180deg,
    rgb(var(--hx-etp-rgb, 62 92 116) / 0.06) 0%,
    rgba(255, 255, 255, 0.98) 100%
  ) !important;
}}

.stApp {_CARD} .home-zone__stripe {{
  height: 4px;
  background: linear-gradient(90deg, var(--hx-etp-bright, #507188) 0%, transparent 88%);
}}

.stApp {_CARD} .home-zone__head {{
  display: flex;
  align-items: flex-start;
  gap: 0.85rem;
  padding: 1.15rem 1.25rem 1rem;
  border-bottom: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.2);
  background: var(--hx-etp-head, linear-gradient(180deg, #f0f4f9 0%, #ffffff 100%));
}}

.stApp {_CARD} .home-zone__titles .page-intro__title {{
  margin: 0 0 0.4rem;
  color: var(--hx-etp-dark, #31485c);
  font-size: clamp(1.35rem, 2.8vw, 1.75rem);
  font-weight: 780;
  letter-spacing: -0.02em;
  line-height: 1.2;
}}

.stApp {_CARD} .home-zone__titles .section-dek--wide {{
  margin: 0;
  max-width: 52rem;
  font-size: 0.92rem;
  line-height: 1.5;
  color: var(--ink-muted, #4a5f73);
}}

.stApp {_CARD} .home-zone__titles .section-dek--wide a {{
  color: var(--hx-etp-bright, #507188);
}}

.stApp {_CARD} [data-testid="stElementContainer"] {{
  margin: 0 !important;
  max-width: 100% !important;
  width: 100% !important;
  background: transparent !important;
}}

.stApp {_CARD} [data-testid="stElementContainer"]:first-child {{
  padding: 0 !important;
}}

.stApp {_CARD} [data-testid="stElementContainer"]:not(:first-child) {{
  padding-top: 0 !important;
  padding-left: 1.25rem !important;
  padding-right: 1.25rem !important;
}}

.stApp {_CARD} [data-testid="stElementContainer"]:last-child {{
  padding-bottom: 1.35rem !important;
}}

/* Nested league table boxes (tmmf-inner-page-mock.css) */
.stApp {_TABLE} {{
  margin: 0 0 var(--etp-mock-gap-lg, 1.2rem) !important;
  padding: 0.95rem 1rem 1rem !important;
  border: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.16) !important;
  border-radius: 10px !important;
  background: #fff !important;
  box-shadow: 0 1px 4px rgb(var(--hx-etp-rgb, 62 92 116) / 0.06) !important;
}}

.stApp {_TABLE} > [data-testid="stVerticalBlock"] {{
  gap: 0.35rem !important;
}}

.stApp {_TABLE} [data-testid="stElementContainer"] {{
  padding-left: 0 !important;
  padding-right: 0 !important;
}}
</style>
"""

tmmf_single_block_header_html = tmmf_github_zone_header_html
