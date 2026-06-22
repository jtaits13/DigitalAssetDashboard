"""Streamlit TMMF full page — home-preview zone card (one white panel, nested KPI/table boxes)."""

from __future__ import annotations

from html import escape

_CARD_KEY = "tmmf_zone_card"
# Bordered Streamlit container that wraps header + widget blocks.
_PANEL = ",\n".join(
    (
        f'.stApp [data-testid="stVerticalBlockBorderWrapper"]:has(.tmmf-streamlit-zone-marker)',
        f'.stApp [data-testid="stVerticalBlockBorderWrapper"].st-key-{_CARD_KEY}',
        f'.stApp .st-key-{_CARD_KEY}',
    )
)
# Parent element container — drop side padding so the card spans the content column.
_PANEL_EC = (
    f'.stApp [data-testid="stElementContainer"]:has(.tmmf-streamlit-zone-marker), '
    f'.stApp [data-testid="stElementContainer"]:has(.st-key-{_CARD_KEY})'
)


def tmmf_single_block_header_html(
    *,
    section_id: str,
    badge: str,
    title: str,
    subtitle_html: str,
    subtitle_class: str = "section-dek section-dek--wide page-intro__dek",
) -> str:
    """Zone header markup inside the unified Streamlit card (home TMMF preview parity)."""
    dek_tag = "div" if "section-dek" in subtitle_class else "p"
    return (
        '<span class="tmmf-streamlit-zone-marker" hidden aria-hidden="true"></span>'
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
    )


STREAMLIT_TMMF_SUBPAGE_CSS = f"""
<style>
/* TMMF Streamlit — home preview zone: one white hub-section--panel, nested KPI + table boxes. */

.stApp:has(.tmmf-streamlit-zone-marker) {{
  --hx-tmmf: #3e5c74;
  --hx-tmmf-bright: #507188;
  --hx-tmmf-dark: #31485c;
  --hx-tmmf-soft: #eef2f6;
  --hx-tmmf-rgb: 62 92 116;
  --hx-tmmf-bright-rgb: 80 113 136;
}}

/* Card spans full content column (subpage layout adds 1.25rem side padding by default). */
{_PANEL_EC} {{
  padding-left: 0 !important;
  padding-right: 0 !important;
  max-width: var(--content-max, var(--max, 72rem)) !important;
}}

/* —— Outer zone card (matches .stApp .home-zone.hub-section--panel on home) —— */
{_PANEL} {{
  display: block !important;
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 auto 1.35rem !important;
  padding: 0 !important;
  border: 1px solid rgba(199, 216, 232, 0.9) !important;
  border-radius: 14px !important;
  overflow: hidden !important;
  background: #ffffff !important;
  box-shadow:
    0 1px 2px rgba(2, 29, 65, 0.04),
    0 8px 26px rgba(2, 29, 65, 0.06) !important;
  box-sizing: border-box !important;
}}

{_PANEL} > [data-testid="stVerticalBlock"] {{
  gap: 0 !important;
  background: #ffffff !important;
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
  padding-top: 0 !important;
}}

{_PANEL} [data-testid="stElementContainer"]:nth-child(2) {{
  padding-top: 1rem !important;
}}

{_PANEL} [data-testid="stElementContainer"]:last-child {{
  padding-bottom: 1.35rem !important;
}}

/* —— Zone header —— */
{_PANEL} .home-zone__stripe {{
  display: block;
  height: 4px;
  margin: 0;
  padding: 0;
  border: none;
  background: linear-gradient(90deg, var(--hx-tmmf-bright, #507188) 0%, transparent 88%);
}}

{_PANEL} .home-zone__head {{
  display: block;
  padding: 1rem 1.25rem 0.85rem;
  margin: 0;
  border-bottom: 1px solid rgba(199, 216, 232, 0.75);
  background: #ffffff;
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
  color: var(--hx-tmmf-dark, #31485c) !important;
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
  background: linear-gradient(145deg, var(--hx-tmmf-bright, #507188), var(--hx-tmmf-dark, #31485c));
  box-shadow: 0 2px 8px rgb(var(--hx-tmmf-rgb, 62 92 116) / 0.18);
}}

{_PANEL} .page-intro__dek.section-dek--wide {{
  margin: 0;
  max-width: 52rem;
  font-size: 0.92rem !important;
  line-height: 1.5 !important;
  color: var(--ink-muted, #4a5f73) !important;
}}

{_PANEL} .page-intro__dek.section-dek--wide strong {{
  color: var(--hx-tmmf-dark, #31485c);
}}

{_PANEL} .home-related-chips {{
  display: flex !important;
  flex-wrap: wrap !important;
  align-items: center !important;
  gap: 0.35rem 0.45rem !important;
  margin: 0 0 0.85rem !important;
  padding: 0.55rem 0.7rem !important;
  border-radius: 8px !important;
  background: var(--hx-tmmf-soft, #eef2f6) !important;
  border: 1px solid rgb(var(--hx-tmmf-bright-rgb, 80 113 136) / 0.18) !important;
}}

{_PANEL} .home-related-chips__label {{
  font-size: 0.68rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: var(--hx-tmmf, #3e5c74) !important;
}}

{_PANEL} .home-related-chips .home-chip {{
  display: inline-flex !important;
  padding: 0.22rem 0.58rem !important;
  border-radius: 999px !important;
  font-size: 0.76rem !important;
  font-weight: 600 !important;
  color: var(--hx-tmmf-dark, #31485c) !important;
  background: #fff !important;
  border: 1px solid rgb(var(--hx-tmmf-bright-rgb, 80 113 136) / 0.22) !important;
  text-decoration: none !important;
}}

/* —— KPI row: home preview — individual cells in their own boxes —— */
{_PANEL} .jd-kpi-window-note,
{_PANEL} .rwa-onchain-kpi-legend {{
  margin: 0 0 0.55rem;
  font-size: 0.78rem;
  line-height: 1.45;
  color: var(--muted, #5a7084);
}}

{_PANEL} .rwa-kpi-panel-static {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 0 0.75rem !important;
}}

{_PANEL} .rwa-kpi-row--home-grid {{
  display: grid !important;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)) !important;
  gap: 0.55rem !important;
}}

{_PANEL} .rwa-kpi-row--home-grid .rwa-kpi-cell {{
  border: 1px solid rgba(62, 92, 116, 0.18) !important;
  border-left: 3px solid var(--hx-tmmf, #3e5c74) !important;
  background: linear-gradient(145deg, var(--hx-tmmf-soft, #eef2f6) 0%, rgba(255, 255, 255, 0.9) 68%) !important;
  border-radius: 8px !important;
  padding: 0.55rem 0.65rem !important;
  box-shadow: 0 1px 3px rgb(var(--hx-tmmf-rgb, 62 92 116) / 0.06) !important;
}}

{_PANEL} .rwa-kpi-row--home-grid .rwa-kpi-val {{
  color: var(--hx-tmmf, #3e5c74) !important;
}}

{_PANEL} .methodology-panel {{
  margin: 0.4rem 0 0.85rem !important;
  border: 1px solid rgb(var(--hx-tmmf-bright-rgb, 80 113 136) / 0.2);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 1px 3px rgb(var(--hx-tmmf-rgb, 62 92 116) / 0.06);
}}

{_PANEL} .methodology-panel summary {{
  padding: 0.65rem 0.9rem;
  font-size: 0.85rem;
  font-weight: 650;
  color: var(--hx-tmmf, #3e5c74);
  cursor: pointer;
}}

{_PANEL} .methodology-panel__body {{
  padding: 0 0.9rem 0.85rem;
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--ink-muted, #4a5f73);
}}

{_PANEL} .inner-rich-block {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin-bottom: 0 !important;
}}

{_PANEL} .etp-mock-key-obs-block {{
  margin-bottom: 0.85rem !important;
}}

{_PANEL} .crypto-story-callout {{
  display: block !important;
  margin: 0;
  padding: 1rem 1.1rem 0.9rem;
  border: 1px solid rgb(var(--hx-tmmf-bright-rgb, 80 113 136) / 0.22);
  border-left: 4px solid var(--hx-tmmf-bright, #507188);
  border-radius: 10px;
  background: linear-gradient(160deg, rgb(var(--hx-tmmf-rgb, 62 92 116) / 0.07) 0%, #fff 55%);
  box-shadow: 0 1px 4px rgb(var(--hx-tmmf-rgb, 62 92 116) / 0.08);
}}

{_PANEL} .crypto-story-callout__title {{
  display: block;
  margin: 0 0 0.55rem !important;
  padding: 0 0 0.45rem !important;
  border-bottom: 1px solid rgb(var(--hx-tmmf-bright-rgb, 80 113 136) / 0.14);
  font-size: 0.72rem !important;
  font-weight: 800 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  line-height: 1.3 !important;
  color: var(--hx-tmmf-dark, #31485c) !important;
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
  color: var(--hx-tmmf-bright, #507188) !important;
  font-weight: 600;
}}

{_PANEL} .review-note.ko-disclaimer {{
  margin: 0.55rem 0 0 !important;
  font-size: 0.72rem !important;
  line-height: 1.45 !important;
  color: var(--muted, #5a7084) !important;
}}

/* —— Nested table blocks (Streamlit bordered sub-containers) —— */
{_PANEL} [data-testid="stVerticalBlockBorderWrapper"]:has(.tmmf-streamlit-table-block) {{
  margin: 0 0 1rem !important;
  padding: 0.85rem 0.95rem 0.95rem !important;
  border: 1px solid rgba(199, 216, 232, 0.9) !important;
  border-radius: 10px !important;
  background: #ffffff !important;
  box-shadow: 0 1px 3px rgb(var(--hx-tmmf-rgb, 62 92 116) / 0.06) !important;
}}

{_PANEL} [data-testid="stVerticalBlockBorderWrapper"]:has(.tmmf-streamlit-table-block) > [data-testid="stVerticalBlock"] {{
  gap: 0.35rem !important;
}}

{_PANEL} [data-testid="stVerticalBlockBorderWrapper"]:has(.tmmf-streamlit-table-block) [data-testid="stElementContainer"] {{
  padding: 0 !important;
}}

{_PANEL} [data-testid="stVerticalBlockBorderWrapper"]:has(.tmmf-streamlit-table-block) div[data-testid="stDataFrame"] {{
  border: 1px solid rgba(199, 216, 232, 0.75) !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}}

/* —— Table blocks: static HTML section fallback —— */
{_PANEL} .etp-mock-table-block.tmmf-mock-league-block {{
  margin: 0 0 1rem !important;
  padding: 0.85rem 0.95rem 0.95rem !important;
  border: 1px solid rgba(199, 216, 232, 0.9) !important;
  border-radius: 10px !important;
  background: #ffffff !important;
  box-shadow: 0 1px 3px rgb(var(--hx-tmmf-rgb, 62 92 116) / 0.06) !important;
}}

{_PANEL} .inner-table-head,
{_PANEL} .jd-hub-subsection-head {{
  margin-top: 0.15rem;
}}

{_PANEL} .tmmf-mock-league-intro {{
  margin: 0 0 0.65rem;
  font-size: 0.84rem;
  line-height: 1.5;
  color: var(--ink-muted, #4a5f73);
}}

{_PANEL} hr.jd-divider {{
  border: none;
  border-top: 1px solid rgba(199, 216, 232, 0.75);
  margin: 0.15rem 0 0.85rem;
}}

{_PANEL} p.jd-subpage-toolbar-note {{
  font-size: 0.78rem;
  color: var(--muted, #5a7084);
  margin: 0.35rem 0 0.65rem;
}}

{_PANEL} [data-testid="stTextInput"] label p {{
  font-size: 0.78rem !important;
  font-weight: 600 !important;
  color: var(--hx-tmmf-dark, #31485c) !important;
}}

{_PANEL} [data-testid="stTextInput"] input {{
  max-width: 32rem;
  font-size: 0.875rem !important;
  border-color: rgb(var(--hx-tmmf-bright-rgb, 80 113 136) / 0.22) !important;
}}

{_PANEL} [data-testid="stCaptionContainer"] {{
  font-size: 0.72rem !important;
  color: var(--muted, #5a7084) !important;
  margin: 0.5rem 0 0.65rem !important;
}}

{_PANEL} .etp-mock-snapshot {{
  margin-bottom: 0.85rem;
}}

{_PANEL} div[data-testid="stDataFrame"] {{
  font-size: 0.78rem;
  width: 100%;
  border: 1px solid rgba(199, 216, 232, 0.85);
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 1px 2px rgb(var(--hx-tmmf-rgb, 62 92 116) / 0.04);
}}

{_PANEL} .source-cap.timestamp-foot {{
  margin: 0.5rem 0 0;
  font-size: 0.72rem;
  color: var(--muted, #5a7084);
}}

{_PANEL} [data-testid="stLinkButton"] {{
  margin-top: 0.85rem;
}}

{_PANEL} [data-testid="stLinkButton"] a {{
  background: var(--hx-tmmf-bright, #507188) !important;
  border-color: rgb(var(--hx-tmmf-bright-rgb, 80 113 136) / 0.35) !important;
  color: #fff !important;
  font-size: 0.82rem !important;
  font-weight: 600 !important;
  max-width: 20rem;
}}
</style>
"""

TMMF_ZONE_CARD_KEY = _CARD_KEY
