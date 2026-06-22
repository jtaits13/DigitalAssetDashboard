"""Streamlit TMMF full page — single etp-mock-zone card (matches GitHub Pages)."""

from __future__ import annotations

from html import escape

_CARD_KEY = "tmmf_zone_card"
# Streamlit adds ``st-key-{key}`` on bordered containers; keep fallbacks for marker class.
_PANEL = ",\n".join(
    (
        f'.stApp [data-testid="stVerticalBlockBorderWrapper"].st-key-{_CARD_KEY}',
        f'.stApp:has(.st-key-{_CARD_KEY}) [data-testid="stVerticalBlockBorderWrapper"]',
        f'.stApp:has(.tmmf-single-block) [data-testid="stVerticalBlockBorderWrapper"]:has(.tmmf-single-block)',
    )
)


def tmmf_single_block_header_html(
    *,
    section_id: str,
    badge: str,
    title: str,
    subtitle_html: str,
    subtitle_class: str = "section-dek section-dek--wide page-intro__dek",
) -> str:
    """Zone header markup inside the unified Streamlit card."""
    dek_tag = "div" if "section-dek" in subtitle_class else "p"
    return (
        '<div class="tmmf-single-block tmmf-single-block__shell etp-mock-zone zone--tmmf '
        'home-zone home-zone--tmmf inner-rich-zone">'
        '<div class="home-zone__stripe" aria-hidden="true"></div>'
        '<header class="home-zone__head home-zone__head--title-row">'
        '<div class="home-zone__titles">'
        '<div class="home-zone__title-row">'
        f'<span class="home-zone__badge" aria-hidden="true">{escape(badge)}</span>'
        f'<p class="page-intro__title" role="heading" aria-level="1" id="{escape(section_id)}-heading">'
        f"{escape(title)}</p>"
        "</div>"
        f'<{dek_tag} class="{escape(subtitle_class)}">{subtitle_html}</{dek_tag}>'
        "</div>"
        "</header>"
        "</div>"
    )


STREAMLIT_TMMF_SUBPAGE_CSS = f"""
<style>
/* TMMF Streamlit — one visible etp-mock-zone card (yellow-box parity on GitHub Pages). */

.stApp:has(.tmmf-single-block) {{
  background:
    radial-gradient(ellipse 88% 52% at 6% -6%, rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.1), transparent 55%),
    radial-gradient(ellipse 70% 42% at 98% 2%, rgb(var(--hx-etp-rgb, 62 92 116) / 0.12), transparent 50%),
    var(--wash, #eef2f6);
}}

/* —— Unified zone card outline —— */
{_PANEL} {{
  margin: 0 auto 1.25rem !important;
  padding: 0 !important;
  max-width: 100% !important;
  width: 100% !important;
  border: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.38) !important;
  border-radius: 14px !important;
  overflow: hidden !important;
  background: var(--hx-etp-soft, #eef2f6) !important;
  box-shadow:
    0 1px 2px rgb(var(--hx-etp-rgb, 62 92 116) / 0.06),
    0 10px 28px rgb(var(--hx-etp-rgb, 62 92 116) / 0.12) !important;
  box-sizing: border-box !important;
}}

.stApp:has(.tmmf-single-block) [data-testid="stElementContainer"]:has(.st-key-{_CARD_KEY}),
.stApp:has(.tmmf-single-block) [data-testid="stElementContainer"]:has([data-testid="stVerticalBlockBorderWrapper"].st-key-{_CARD_KEY}) {{
  margin: 0 !important;
  padding: 0 !important;
}}

{_PANEL} > [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
  background: linear-gradient(
    180deg,
    rgb(var(--hx-etp-rgb, 62 92 116) / 0.06) 0%,
    rgba(255, 255, 255, 0.98) 100%
  ) !important;
}}

{_PANEL} [data-testid="stElementContainer"] {{
  margin: 0 !important;
  padding: 0 1.25rem !important;
  max-width: 100% !important;
  width: 100% !important;
  background: transparent !important;
}}

{_PANEL} [data-testid="stElementContainer"]:first-child {{
  padding: 0 !important;
}}

{_PANEL} [data-testid="stElementContainer"]:not(:first-child) {{
  padding-top: 1rem !important;
}}

{_PANEL} [data-testid="stElementContainer"]:last-child {{
  padding-bottom: 1.35rem !important;
}}

/* No nested white cards from patched inner-rich-block rules */
{_PANEL} .inner-rich-block {{
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin-bottom: 0 !important;
}}

/* —— Header —— */
{_PANEL} .tmmf-single-block__shell {{
  margin: 0 !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  background: transparent !important;
}}

{_PANEL} .home-zone__stripe {{
  display: block;
  height: 4px;
  margin: 0;
  padding: 0;
  border: none;
  background: linear-gradient(90deg, var(--hx-etp-bright, #507188) 0%, transparent 88%);
}}

{_PANEL} .home-zone__head {{
  display: block;
  padding: 1.15rem 1.25rem 1rem;
  margin: 0;
  border-bottom: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.2);
  background: var(--hx-etp-head, linear-gradient(180deg, #f0f4f9 0%, #ffffff 100%));
}}

{_PANEL} .home-zone__title-row {{
  display: flex;
  align-items: flex-start;
  gap: 0.85rem;
  margin-bottom: 0.4rem;
}}

{_PANEL} .home-zone__title-row .page-intro__title {{
  flex: 1;
  min-width: 0;
  margin: 0 !important;
  padding: 0 !important;
  color: var(--hx-etp-dark, #31485c) !important;
  font-size: clamp(1.35rem, 2.8vw, 1.75rem) !important;
  font-weight: 780 !important;
  letter-spacing: -0.02em !important;
  line-height: 1.2 !important;
}}

{_PANEL} .home-zone__badge {{
  flex-shrink: 0;
  width: 2.4rem;
  height: 2.4rem;
  display: grid;
  place-items: center;
  margin: 0;
  border-radius: 10px;
  font-size: 0.58rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  color: #ffffff;
  background: var(--hx-etp-dark, #31485c);
  box-shadow: 0 2px 8px rgb(var(--hx-etp-rgb, 62 92 116) / 0.18);
}}

{_PANEL} .page-intro__dek.section-dek--wide {{
  margin: 0;
  max-width: 52rem;
  font-size: 0.92rem !important;
  line-height: 1.5 !important;
  color: var(--ink-muted, #4a5f73) !important;
}}

{_PANEL} .page-intro__dek.section-dek--wide strong {{
  color: var(--hx-etp-dark, #31485c);
}}

{_PANEL} .home-related-chips {{
  display: flex !important;
  flex-wrap: wrap !important;
  align-items: center !important;
  gap: 0.35rem 0.45rem !important;
  margin: 0 0 var(--etp-mock-gap, 1rem) !important;
  padding: 0.55rem 0.7rem !important;
  border-radius: 8px !important;
  background: var(--hx-etp-soft, #eef2f6) !important;
  border: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.18) !important;
}}

{_PANEL} .home-related-chips__label {{
  font-size: 0.68rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: var(--hx-etp, #3e5c74) !important;
}}

{_PANEL} .home-related-chips .home-chip {{
  display: inline-flex !important;
  padding: 0.22rem 0.58rem !important;
  border-radius: 999px !important;
  font-size: 0.76rem !important;
  font-weight: 600 !important;
  color: var(--hx-etp-dark, #31485c) !important;
  background: #fff !important;
  border: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.22) !important;
  text-decoration: none !important;
}}

{_PANEL} .jd-kpi-window-note,
{_PANEL} .rwa-onchain-kpi-legend {{
  margin: 0 0 0.55rem;
  font-size: 0.78rem;
  line-height: 1.45;
  color: var(--muted, #5a7084);
}}

{_PANEL} .rwa-kpi-panel-static {{
  margin-bottom: 0.65rem !important;
}}

{_PANEL} .methodology-panel {{
  margin: 0.4rem 0 0.85rem !important;
  border: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.2);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 1px 3px rgb(var(--hx-etp-rgb, 62 92 116) / 0.06);
}}

{_PANEL} .methodology-panel summary {{
  padding: 0.65rem 0.9rem;
  font-size: 0.85rem;
  font-weight: 650;
  color: var(--hx-etp, #3e5c74);
  cursor: pointer;
}}

{_PANEL} .methodology-panel__body {{
  padding: 0 0.9rem 0.85rem;
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--ink-muted, #4a5f73);
}}

{_PANEL} .etp-mock-key-obs-block {{
  margin-bottom: var(--etp-mock-gap-lg, 1.2rem) !important;
}}

{_PANEL} .crypto-story-callout {{
  display: block !important;
  margin: 0;
  padding: 1rem 1.1rem 0.9rem;
  border: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.22);
  border-left: 4px solid var(--hx-etp-bright, #507188);
  border-radius: 10px;
  background: linear-gradient(160deg, rgb(var(--hx-etp-rgb, 62 92 116) / 0.07) 0%, #fff 55%);
  box-shadow: 0 1px 4px rgb(var(--hx-etp-rgb, 62 92 116) / 0.08);
}}

{_PANEL} .crypto-story-callout__title {{
  display: block;
  margin: 0 0 0.55rem !important;
  padding: 0 0 0.45rem !important;
  border-bottom: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.14);
  font-size: 0.72rem !important;
  font-weight: 800 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  line-height: 1.3 !important;
  color: var(--hx-etp-dark, #31485c) !important;
}}

{_PANEL} .crypto-story-callout__dek {{
  margin: 0 0 0.65rem !important;
  font-size: 0.84rem !important;
  line-height: 1.5 !important;
  color: var(--ink-muted, #4a5f73) !important;
}}

{_PANEL} .crypto-story-callout__list {{
  margin: 0 !important;
  padding-left: 1.15rem !important;
  font-size: 0.84rem !important;
  line-height: 1.52 !important;
}}

{_PANEL} .crypto-story-callout__list li + li {{
  margin-top: 0.55rem !important;
}}

{_PANEL} .crypto-story-callout__list a {{
  color: var(--hx-etp-bright, #507188) !important;
  font-weight: 600;
}}

{_PANEL} .review-note.ko-disclaimer {{
  margin: 0.55rem 0 0 !important;
  font-size: 0.72rem !important;
  line-height: 1.45 !important;
  color: var(--muted, #5a7084) !important;
}}

{_PANEL} .inner-table-head,
{_PANEL} .jd-hub-subsection-head {{
  margin-top: 0.35rem;
}}

{_PANEL} .tmmf-mock-league-intro {{
  margin: 0 0 0.65rem;
  font-size: 0.84rem;
  line-height: 1.5;
  color: var(--ink-muted, #4a5f73);
}}

{_PANEL} hr.jd-divider {{
  border: none;
  border-top: 1px solid rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.14);
  margin: 0.35rem 0 var(--etp-mock-gap-lg, 1.2rem);
}}

{_PANEL} p.jd-subpage-toolbar-note {{
  font-size: 0.78rem;
  color: var(--muted, #5a7084);
  margin: 0.35rem 0 0.65rem;
}}

{_PANEL} [data-testid="stTextInput"] label p {{
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  color: var(--hx-etp-dark, #31485c) !important;
}}

{_PANEL} [data-testid="stTextInput"] input {{
  max-width: 32rem;
  font-size: 0.875rem !important;
  border-color: rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.22) !important;
}}

{_PANEL} [data-testid="stCaptionContainer"] {{
  font-size: 0.72rem !important;
  color: var(--muted, #5a7084) !important;
  margin: 0.5rem 0 0.65rem !important;
}}

{_PANEL} div[data-testid="stDataFrame"] {{
  font-size: 0.78rem;
  width: 100%;
}}

{_PANEL} [data-testid="stLinkButton"] {{
  margin-top: var(--etp-mock-gap-lg, 1.2rem);
}}

{_PANEL} [data-testid="stLinkButton"] a {{
  background: var(--hx-etp-bright, #507188) !important;
  border-color: rgb(var(--hx-etp-bright-rgb, 80 113 136) / 0.35) !important;
  color: #fff !important;
  font-size: 0.82rem !important;
  font-weight: 600 !important;
  max-width: 20rem;
}}
</style>
"""

TMMF_ZONE_CARD_KEY = _CARD_KEY
