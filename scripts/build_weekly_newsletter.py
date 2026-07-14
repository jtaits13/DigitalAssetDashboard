#!/usr/bin/env python3
"""
Build a weekly digest HTML email from committed static_home/data JSON (KPIs + Key observations).

Usage:
  python scripts/build_weekly_newsletter.py
  python scripts/build_weekly_newsletter.py --out static_home/mockups/weekly-newsletter-email.html

Env:
  SITE_BASE_URL — absolute site root for CTA links (no trailing slash).
  NEWSLETTER_WEEKLY_TAKEAWAYS — set to 0 to revert section takeaways to page KO bullets.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATA = ROOT / "static_home" / "data"
DEFAULT_OUT = ROOT / "static_home" / "mockups" / "weekly-newsletter-email.html"
DEFAULT_EXEC_OUT = ROOT / "static_home" / "mockups" / "weekly-newsletter-email-executive-mock.html"
NEWSLETTER_MAX_WIDTH = "1100px"

DEFAULT_SITE_BASE = os.environ.get(
    "SITE_BASE_URL",
    "https://jtaits13.github.io/DigitalAssetDashboard",
).rstrip("/")

_LI_RE = re.compile(r"<li>(.*?)</li>", re.DOTALL | re.IGNORECASE)
_STRONG_RE = re.compile(r"<strong[^>]*>(.*?)</strong>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_LINK_RE = re.compile(r"<a[^>]*>(.*?)</a>", re.DOTALL | re.IGNORECASE)
_INDUSTRY_LEAD_RE = re.compile(r"^Industry headlines emphasize\s+", re.IGNORECASE)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _fmt_pct(raw: object, *, decimals: int = 1) -> str:
    if raw is None:
        return "—"
    try:
        n = float(raw)
    except (TypeError, ValueError):
        return "—"
    if abs(n) <= 1.5 and n != 0:
        n *= 100.0
    sign = "+" if n >= 0 else ""
    return f"{sign}{n:.{decimals}f}%"


def _parse_iso_dt(raw: object) -> datetime | None:
    if not raw:
        return None
    try:
        s = str(raw).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _strip_tags(html: str) -> str:
    from html import unescape

    return unescape(_TAG_RE.sub("", html).replace("&nbsp;", " ")).strip()


_COLOR_INK = "#1a3d5c"
_COLOR_BRAND = _COLOR_INK
_COLOR_BRAND_BORDER = "#b8ccd9"
_COLOR_BODY = "#334155"
_COLOR_MUTED = "#5c6b7a"
_COLOR_LABEL = "#4a5f6b"
_COLOR_LINE = "#e2e8f0"
_COLOR_LINE_SOFT = "#eef2f6"
_COLOR_WASH = "#f8fafc"
_COLOR_INSET = "#f1f5f9"
_COLOR_LINK = _COLOR_BRAND
_COLOR_POS = "#0b5a30"
_COLOR_NEG = "#b42318"
_COLOR_NEUTRAL = "#4a5f73"

_LI_STYLE = f"margin:0 0 0.8rem;color:{_COLOR_BODY};font-size:14px;line-height:1.65;"
_LI_STYLE_LAST = f"margin:0;color:{_COLOR_BODY};font-size:14px;line-height:1.65;"
_STRONG_STYLE = f"display:block;margin:0 0 0.25rem;color:{_COLOR_INK};font-weight:600;font-size:14px;line-height:1.45;"
_BODY_STYLE = f"display:block;margin:0;color:{_COLOR_BODY};"
_UL_STYLE = "margin:0;padding:0 0 0 1.15rem;list-style:disc;list-style-position:outside;"


def _accent_border(accent: str) -> str:
    return _COLOR_BRAND_BORDER


def _related_style(accent: str) -> str:
    border = _accent_border(accent)
    return (
        f"display:block;font-size:12px;color:{_COLOR_MUTED};margin-top:0.4rem;"
        f"padding:0.28rem 0.55rem 0.28rem 0.65rem;border-left:3px solid {border};line-height:1.5;"
        f"background:{_COLOR_INSET};border-radius:0 5px 5px 0;"
    )


_OUTLOOK_FONT = "Segoe UI, Arial, sans-serif"
_OUTLOOK_WIDTH = 1100
# Spacing scale (px)
_OL_PAD = "24px"
_OL_GAP = "32px"
_OL_GAP_LG = "40px"
_OL_GAP_SM = "16px"
_OL_GAP_XS = "12px"
# Surfaces & borders — neutral grays everywhere except synthesis highlight
_OL_CARD_BG = "#f8fafc"
_OL_CARD_BORDER = "#d5dde6"
_OL_SURFACE = "#eef2f6"
_OL_CELL = "#ffffff"
_OL_BORDER = "#d5dde6"
_OL_DIVIDER = "#d5dde6"
_OL_SYNTHESIS_BG = "#eef6fb"
_OL_SYNTHESIS_BORDER = _COLOR_BRAND
_OL_ACCENT = _COLOR_BRAND
# Type scale
_OL_TEXT_WIB = "14px"
_OL_TEXT_HEADLINE = "14px"
_OL_TEXT_SECTION = "13px"
_OL_TEXT_BODY = "14px"
_OL_TEXT_META = "12px"
_OL_TEXT_META_SM = "11px"
_OL_TEXT_EYEBROW = "11px"
_OL_TEXT_CAPTION = "10px"
_OL_TEXT_H2 = "16px"
_OL_TEXT_KPI = "19px"
_OL_KPI_OUTER_PAD = "6px"
_OL_KPI_PAD = "10px 14px"
_OL_KPI_VALUE_GAP = "4px"
_OL_KPI_DELTA_GAP = "3px"
_OL_KPI_LABEL_LH = "12px"
_OL_KPI_VALUE_LH = "22px"
_OL_KPI_DELTA_LH = "15px"
_OL_KPI_VALUE_FONT = "Arial, Helvetica, sans-serif"
_OL_LINE = "1.6"
_OL_LINE_HEADLINE = "1.55"
_OL_LINE_SECTION = "1.6"
_OL_HEADLINE_INNER_GAP = "6px"
_OL_HEADLINE_ITEM_GAP = "16px"
_OL_INSET_PAD = "8px 10px"
_OL_INSET_LABEL_MB = "6px"
_OL_INSET_BODY_LH = "1.6"
_OL_INSET_EXTERNAL_GAP = "8px"
_OL_ACTION_LINK_VPAD = "14px"
_OL_ACTION_LINK_WEIGHT = "700"
_OL_SECTION_AFTER_LINK_GAP = "32px"
_OL_RELATED_PAD = "4px 9px 4px 10px"


def _ol_spacer_row(height: str) -> str:
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;"><tr><td height="{height}" '
        f'style="height:{height};line-height:{height};font-size:1px;'
        f'mso-line-height-rule:exactly;">&nbsp;</td></tr></table>'
    )


def _ol_inset_box_html(
    label: str,
    body_html: str,
    *,
    border_color: str,
    gap_before: str = "0",
    gap_after: str = "0",
    pad: str | None = None,
    label_mb: str | None = None,
) -> str:
    inset_pad = pad or _OL_INSET_PAD
    inset_label_mb = label_mb or _OL_INSET_LABEL_MB
    before = _ol_spacer_row(gap_before) if gap_before != "0" else ""
    after = _ol_spacer_row(gap_after) if gap_after != "0" else ""
    box = (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;">'
        f'<tr><td style="padding:{inset_pad};background:{_COLOR_INSET};'
        f'border-left:3px solid {border_color};">'
        f'<p style="margin:0 0 {inset_label_mb};font-size:{_OL_TEXT_CAPTION};font-weight:700;letter-spacing:0.06em;'
        f'text-transform:uppercase;color:{_COLOR_LABEL};{_ol_font()}">{escape(label)}</p>'
        f"{body_html}"
        f"</td></tr></table>"
    )
    return f"{before}{box}{after}"


def _ol_related_reading_html(
    title_html: str,
    source_html: str,
    *,
    border_color: str,
) -> str:
    """Single-line related reading callout — matches full-newsletter inset style."""
    before = _ol_spacer_row(_OL_INSET_EXTERNAL_GAP)
    after = _ol_spacer_row(_OL_INSET_EXTERNAL_GAP)
    line = (
        f'<p style="margin:0;font-size:{_OL_TEXT_SECTION};line-height:1.5;mso-line-height-rule:exactly;'
        f'color:{_COLOR_MUTED};{_ol_font()}">'
        f'<span style="font-weight:700;color:{_COLOR_LABEL};font-size:{_OL_TEXT_CAPTION};letter-spacing:0.06em;'
        f'text-transform:uppercase;">Related reading</span> · {title_html}{source_html}</p>'
    )
    box = (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;">'
        f'<tr><td style="padding:{_OL_RELATED_PAD};background:{_COLOR_INSET};'
        f'border-left:3px solid {border_color};border-radius:0 5px 5px 0;">'
        f"{line}"
        f"</td></tr></table>"
    )
    return f"{before}{box}{after}"


def _ol_font(extra: str = "") -> str:
    return f"font-family:{_OUTLOOK_FONT};{extra}"


def _centered_action_link_html(
    href: str,
    label: str,
    *,
    margin_bottom: str = "0",
    sandwich: bool = False,
    outlook: bool = False,
) -> str:
    vpad = _OL_ACTION_LINK_VPAD
    border_color = _OL_DIVIDER
    if sandwich:
        borders = f"border-bottom:1px solid {border_color};"
    else:
        borders = f"border-top:1px solid {border_color};"
    font = _ol_font() if outlook else "font-family:'Segoe UI',system-ui,-apple-system,sans-serif;"
    link_size = _OL_TEXT_WIB if outlook else "14px"
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="margin:0 0 {margin_bottom};border-collapse:collapse;{borders}">'
        f'<tr><td align="center" style="padding:{vpad} 0 {vpad};text-align:center;{font}">'
        f'<a href="{escape(href)}" style="color:{_COLOR_LINK};font-weight:{_OL_ACTION_LINK_WEIGHT};'
        f'text-decoration:none;font-size:{link_size};{font}">{escape(label)}</a>'
        f"</td></tr></table>"
    )


def _ol_centered_action_link_html(
    href: str,
    label: str,
    *,
    margin_bottom: str = "0",
    sandwich: bool = False,
) -> str:
    return _centered_action_link_html(
        href, label, margin_bottom=margin_bottom, sandwich=sandwich, outlook=True
    )


def _ol_eyebrow(label: str, *, margin: str = f"0 0 {_OL_GAP_XS}") -> str:
    return (
        f'<p style="margin:{margin};font-size:{_OL_TEXT_EYEBROW};font-weight:700;'
        f"letter-spacing:0.08em;text-transform:uppercase;color:{_COLOR_LABEL};"
        f'{_ol_font()}">{escape(label)}</p>'
    )


def _li_style(*, outlook: bool, is_last: bool, section: bool = False) -> str:
    if outlook:
        margin = "0" if is_last else f"0 0 {10 if section else 14}px"
        size = _OL_TEXT_SECTION if section else _OL_TEXT_BODY
        lh = _OL_LINE_SECTION if section else _OL_LINE
        return f"margin:{margin};color:{_COLOR_BODY};font-size:{size};line-height:{lh};{_ol_font()}"
    return _LI_STYLE_LAST if is_last else _LI_STYLE


def _strong_style(*, outlook: bool, section: bool = False) -> str:
    if outlook:
        size = _OL_TEXT_SECTION if section else _OL_TEXT_BODY
        return (
            f"display:block;margin:0 0 {4 if section else 6}px;color:{_COLOR_INK};font-weight:700;"
            f"font-size:{size};line-height:1.45;{_ol_font()}"
        )
    return _STRONG_STYLE


def _body_style(*, outlook: bool, section: bool = False) -> str:
    if outlook:
        size = _OL_TEXT_SECTION if section else _OL_TEXT_BODY
        lh = _OL_LINE_SECTION if section else _OL_LINE
        return f"display:block;margin:0;color:{_COLOR_BODY};font-size:{size};line-height:{lh};{_ol_font()}"
    return _BODY_STYLE


def _section_eyebrow(label: str, *, margin: str = "0 0 0.55rem", outlook: bool = False) -> str:
    if outlook:
        return _ol_eyebrow(label, margin=margin if margin != "0 0 0.55rem" else f"0 0 {_OL_GAP_XS}")
    size = "11px"
    return (
        f'<p style="margin:{margin};font-size:{size};font-weight:700;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:{_COLOR_LABEL};font-family:inherit;">'
        f"{escape(label)}</p>"
    )


def _prose(text: str, *, margin: str = "0", color: str = _COLOR_INK) -> str:
    return f'<p style="margin:{margin};font-size:14px;line-height:1.7;color:{color};">{text}</p>'


def _callout_card(
    inner_html: str,
    *,
    margin_bottom: str | None = None,
    outlook: bool = False,
    outlook_pad: str | None = None,
) -> str:
    if outlook:
        pad = outlook_pad or _OL_PAD
        mb = margin_bottom if margin_bottom is not None else _OL_GAP
        return (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="margin:0 0 {mb};border-collapse:collapse;background:{_OL_CARD_BG};'
            f'border:1px solid {_OL_CARD_BORDER};">'
            f'<tr><td style="padding:{pad};">{inner_html}</td></tr></table>'
        )
    mb = margin_bottom if margin_bottom is not None else "1.45rem"
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 {mb};border-collapse:collapse;background:{_COLOR_WASH};border:1px solid #dde4ec;border-radius:10px;">
  <tr>
    <td style="padding:1.05rem 1.15rem;">
      {inner_html}
    </td>
  </tr>
</table>
"""


def _kpi_strip_html(cells: str, *, outlook: bool = False, section: bool = False) -> str:
    if outlook:
        bottom = "20px" if section else _OL_GAP_SM
        return (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-collapse:collapse;margin:0 0 {bottom};background:{_OL_SURFACE};'
            f'border:1px solid {_OL_BORDER};">'
            f'<tr><td style="padding:{_OL_KPI_OUTER_PAD};">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-collapse:collapse;background:{_OL_CELL};">'
            f"<tr>{cells}</tr></table>"
            f"</td></tr></table>"
        )
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:0 0 1rem;background:{_COLOR_WASH};border:1px solid #e8edf2;border-radius:8px;">
  <tr>
    <td style="padding:0.4rem;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;background:#ffffff;border-radius:6px;overflow:hidden;">
        <tr>{cells}</tr>
      </table>
    </td>
  </tr>
</table>
"""

# Newsletter zone guardrails — keep takeaways on-topic per section.
_SECTION_KO: dict[str, dict[str, Any]] = {
    "tmmf": {
        "topic_keys": ("tokenized_mmf",),
        "must_match": re.compile(
            r"mmf|money market|tmmf|settlement|tokenized fund|issuer|network share|"
            r"flight to efficiency|cash rail|holder count|buidl|multichain",
            re.IGNORECASE,
        ),
        "reject": re.compile(
            r"stablecoin market structure|top-50 alts|launch pipeline|forward market-size",
            re.IGNORECASE,
        ),
        "boost": re.compile(r"settlement|holder|network share|issuer", re.IGNORECASE),
    },
    "stablecoins": {
        "topic_keys": ("stablecoins",),
        "must_match": re.compile(
            r"stablecoin|usdc|usdt|issuer|reserves|payments|bank integration|concentration-led",
            re.IGNORECASE,
        ),
        "reject": re.compile(
            r"tokenized u\.s\. treasur|top-50 alts|launch pipeline|money market fund",
            re.IGNORECASE,
        ),
        "boost": re.compile(r"stablecoin|reserves|payments|bank", re.IGNORECASE),
    },
    "rwa": {
        "topic_keys": ("rwa_global", "us_treasuries", "tokenized_stocks"),
        "must_match": re.compile(
            r"tokeniz|\brwa\b|real-?world|on-?chain credit|private credit|securitiz|"
            r"distribution|distributed value|collateral|market plumbing|broker",
            re.IGNORECASE,
        ),
        "reject": re.compile(
            r"in the news · macro & rates|macro & rates|top-50 alts|"
            r"forward market-size|stablecoin market structure|etf flows",
            re.IGNORECASE,
        ),
        "boost": re.compile(
            r"rwa tokenization|tokeniz|real-?world|private credit|securitiz|on-?chain credit",
            re.IGNORECASE,
        ),
    },
    "etp": {
        "topic_keys": ("etp",),
        "must_match": re.compile(
            r"\betp\b|\betf\b|aum|filing|ibit|inflow|outflow|launch pipeline|market-size|product pipeline",
            re.IGNORECASE,
        ),
        "reject": re.compile(
            r"stablecoin market structure|tokenized u\.s\. treasur|top-50 alts|money market fund",
            re.IGNORECASE,
        ),
        "boost": re.compile(r"etf|etp|aum|filing|pipeline", re.IGNORECASE),
    },
    "crypto": {
        "topic_keys": ("crypto",),
        "must_match": re.compile(
            r"top-50|alt|market cap|btc|dominance|defi|layer 1|stablecoin share|category tab",
            re.IGNORECASE,
        ),
        "reject": re.compile(
            r"tokenized u\.s\. treasur|launch pipeline|stablecoin market structure|money market fund",
            re.IGNORECASE,
        ),
        "boost": re.compile(r"top-50|alt|dominance|defi|category", re.IGNORECASE),
    },
}


def _ko_lead_text(chunk: str) -> str:
    sm = _STRONG_RE.search(chunk)
    if sm:
        return _polish_newsletter_lead(_strip_tags(sm.group(1)))[0].lower()
    return plain.split(".", 1)[0].lower() if (plain := _bullet_plain_text(chunk)) else ""


def _is_news_ko_chunk(chunk: str) -> bool:
    plain = _bullet_plain_text(chunk)
    if _INDUSTRY_LEAD_RE.search(plain):
        return True
    return _ko_lead_text(chunk).startswith("in the news")


def _section_bullet_score(plain: str, section_id: str) -> float:
    profile = _SECTION_KO[section_id]
    score = 1.0
    if profile["must_match"].search(plain):
        score += 2.0
    if profile["boost"].search(plain):
        score += 2.5
    if plain.lower().startswith("in the news"):
        score += 0.5
    return score


def _select_section_ko_chunks(
    *html_sources: str,
    section_id: str,
    max_items: int,
    executive_news_only: bool = False,
) -> list[str]:
    profile = _SECTION_KO[section_id]
    seen: set[str] = set()
    ranked_analytical: list[tuple[float, str]] = []
    ranked_news: list[tuple[float, str]] = []
    for html in html_sources:
        for match in _LI_RE.finditer(html or ""):
            chunk = match.group(1).strip()
            plain = _bullet_plain_text(chunk)
            key = plain.lower()
            if not plain or key in seen:
                continue
            if profile["reject"].search(plain):
                continue
            if executive_news_only and _is_news_ko_chunk(chunk):
                from key_observations.week_headlines import executive_news_text_allowed

                if not executive_news_text_allowed(plain):
                    continue
            if section_id == "rwa":
                lead = _ko_lead_text(chunk)
                if re.search(r"in the news · (regulation|macro)", lead):
                    if not re.search(r"tokeniz|\brwa\b", lead):
                        continue
            if not profile["must_match"].search(plain):
                continue
            seen.add(key)
            scored = (_section_bullet_score(plain, section_id), chunk)
            if _is_news_ko_chunk(chunk):
                ranked_news.append(scored)
            else:
                ranked_analytical.append(scored)
    ranked_analytical.sort(key=lambda row: row[0], reverse=True)
    ranked_news.sort(key=lambda row: row[0], reverse=True)
    # RWA: pick top-scoring tokenization notes only — no cap of one bullet per asset lane
    # (Treasuries, tokenized stocks, private credit, etc.).
    news_slots = 1 if max_items >= 3 and ranked_news else 0
    analytical_slots = max_items - news_slots
    selected = [chunk for _, chunk in ranked_analytical[:analytical_slots]]
    if news_slots:
        selected.extend(chunk for _, chunk in ranked_news[:news_slots])
    if len(selected) < max_items:
        used = set(selected)
        for _, chunk in ranked_news + ranked_analytical:
            if chunk in used:
                continue
            selected.append(chunk)
            used.add(chunk)
            if len(selected) >= max_items:
                break
    return selected


def _split_long_lead(lead: str) -> tuple[str, str]:
    lead = re.sub(r"\s+", " ", lead).strip().rstrip(":")
    if len(lead) <= 90:
        return lead, ""
    if lead.startswith("Others (") and "outpaced" in lead:
        return "Others outpaced DeFi tokens over 1M", (
            "Among top-50 coins outside Layer 1, stablecoins, CEX, DeFi, meme, and RWA tabs "
            "(e.g. HYPE, LAB, MNT, WLD, WLFI)."
        )
    if ":" in lead:
        head, tail = lead.split(":", 1)
        if len(head) <= 90:
            return head.strip(), tail.strip()
    return lead, ""


def _format_display_lead(lead: str) -> str:
    lead = re.sub(r"\s+", " ", lead).strip().rstrip(":")
    if not lead:
        return lead
    low = lead.lower()
    if low.startswith("in the news"):
        if " · " in lead:
            prefix, topic = lead.split(" · ", 1)
            topic = topic.strip()
            if topic:
                topic = topic[0].upper() + topic[1:]
            return f"In the news · {topic}"
        return "In the news" + lead[9:]
    if low.startswith("tmmfs"):
        return "TMMFs" + lead[5:]
    return lead[0].upper() + lead[1:]


def _polish_newsletter_lead(lead: str) -> tuple[str, str]:
    lead = re.sub(r"\s+", " ", lead).strip().rstrip(":")
    overflow = ""
    if re.search(r'flight to efficiency', lead, re.IGNORECASE) and not re.search(
        r"\btmmf\b|money market", lead, re.IGNORECASE
    ):
        lead = 'Early "flight to efficiency" shows up in TMMF 30D network share'
    if _INDUSTRY_LEAD_RE.match(lead):
        topic = _INDUSTRY_LEAD_RE.sub("", lead).strip()
        return _format_display_lead(f"In the news · {topic}"), ""
    if len(lead) > 90:
        lead, overflow = _split_long_lead(lead)
    return _format_display_lead(lead), overflow


def _truncate_headline_item(item: str, *, max_len: int = 88) -> str:
    item = re.sub(r"\s+", " ", item).strip()
    if len(item) <= max_len:
        return item
    m = re.search(r"\s[\-–]\s(?:CoinDesk|CoinTelegraph|The Block|Google News|AMBCrypto|The Defiant|FinTech Weekly).*$", item)
    if m:
        source = item[m.start() :].strip()
        title = item[: m.start()].strip()
        budget = max(24, max_len - len(source) - 1)
        if len(title) > budget:
            title = title[: budget - 1].rsplit(" ", 1)[0] + "…"
        return f"{title} {source}"
    m = re.search(r"\(([^)]+)\)\s*$", item)
    if m:
        source = m.group(0)
        title = item[: m.start()].strip()
        budget = max(24, max_len - len(source) - 1)
        if len(title) > budget:
            title = title[: budget - 1].rsplit(" ", 1)[0] + "…"
        return f"{title}{source}"
    return item[: max_len - 1].rsplit(" ", 1)[0] + "…"


def _split_headline_and_implication(part: str) -> tuple[str, str]:
    m = re.search(
        r"^(.+?\((?:CoinDesk|CoinTelegraph|The Block|Google News|AMBCrypto|The Defiant|FinTech Weekly)\))\s*\.?\s*(.*)$",
        part,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = re.search(
        r"^(.+?\s[\-–]\s(?:CoinDesk|CoinTelegraph|The Block|Google News|AMBCrypto|The Defiant|FinTech Weekly))\s*\.?\s*(.*)$",
        part,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return part, ""


def _compact_headline_coverage(rest: str) -> str:
    if not rest.lower().startswith("recent coverage includes"):
        return rest
    body = rest[len("Recent coverage includes") :].strip()
    parts = [p.strip() for p in body.split(";") if p.strip()]
    if not parts:
        return rest
    headlines: list[str] = []
    tail: list[str] = []
    for part in parts:
        headline, implication = _split_headline_and_implication(part)
        if re.search(
            r"\((?:CoinDesk|CoinTelegraph|The Block|Google News|AMBCrypto|The Defiant|FinTech Weekly)\)",
            headline,
            re.IGNORECASE,
        ):
            headlines.append(_truncate_headline_item(headline))
            if implication:
                tail.append(implication)
        elif " - " in headline and len(headline) > 40:
            headlines.append(_truncate_headline_item(headline))
            if implication:
                tail.append(implication)
        else:
            tail.append(part)
    short = "; ".join(headlines[:2])
    if len(headlines) > 2:
        short += f"; +{len(headlines) - 2} more"
    out = f"Notable: {short}" if short else ""
    if tail:
        implication = " ".join(tail).strip()
        implication = re.sub(r"\.{2,}$", ".", implication)
        if implication:
            out = f"{out} {implication}".strip()
    out = re.sub(r"(\))\s*(?=[A-Z])", r"\1. ", out)
    out = re.sub(r"\.{2,}", ".", out)
    return out or rest


def _capitalize_rest(rest: str) -> str:
    rest = rest.strip()
    if not rest:
        return rest
    rest = rest[0].upper() + rest[1:]
    return re.sub(
        r"([.!?])\s+([a-z])",
        lambda m: f"{m.group(1)} {m.group(2).upper()}",
        rest,
    )


def _polish_newsletter_rest(lead: str, rest: str, *, lead_overflow: str = "") -> str:
    rest = re.sub(r"\s+", " ", rest).strip().lstrip(": ").strip()
    if lead_overflow:
        lo = lead_overflow.rstrip(". ").strip()
        rest = f"{lo}. {rest}".strip() if lo else rest
    if lead.startswith("In the news"):
        rest = _compact_headline_coverage(rest)
    rest = re.sub(
        r"e\.g\. USYC \(44 holders, \$2\.96B; ~\$67M/holder\), iBENJI \(28 holders, \$1\.59B; ~\$57M/holder\), "
        r"JTRSY \(19 holders, \$871M; ~\$46M/holder\)",
        "e.g. USYC, iBENJI, and JTRSY at roughly $46–67M per holder",
        rest,
        flags=re.IGNORECASE,
    )
    rest = re.sub(r"\bon this page today\b", "today", rest, flags=re.IGNORECASE)
    rest = re.sub(r"\bon this page\b", "", rest, flags=re.IGNORECASE)
    rest = re.sub(
        r"Flow headlines can front-run AUM changes in the KPI strip and aggregate chart—compare cited inflow/outflow themes with the 30-day Farside net-flow figure and fund-table AUM\.?",
        "Flow stories often move before AUM — see the net-flow and fund KPIs above.",
        rest,
        flags=re.IGNORECASE,
    )
    rest = re.sub(
        r"Spot ETF flow stories often move Bitcoin first—compare headline flow narratives with the 30-day net-flow KPI and IBIT/ETHA AUM(?: on this page)?\.?",
        "Spot ETF flow narratives often move Bitcoin first — see ETP and crypto KPIs above.",
        rest,
        flags=re.IGNORECASE,
    )
    rest = re.sub(
        r"Issuer strategy coverage can clarify whether the market is bifurcating into institutional rails vs retail yield products—holder counts and AUM per holder in the funds table help validate that split\.?",
        "Coverage points to a possible split between institutional rails and retail yield products.",
        rest,
        flags=re.IGNORECASE,
    )
    rest = re.sub(
        r"platform concentration on this page may shift before aggregate stablecoin market cap does\.?",
        "issuer/platform concentration can shift before aggregate market cap moves.",
        rest,
        flags=re.IGNORECASE,
    )
    rest = re.sub(
        r"network rank and share on this overview often shift as new issuers choose distribution rails\.?",
        "network share often shifts as issuers choose distribution rails.",
        rest,
        flags=re.IGNORECASE,
    )
    rest = re.sub(
        r"This page lists (\d+)",
        r"The dashboard tracks \1",
        rest,
        flags=re.IGNORECASE,
    )
    rest = re.sub(
        r"That pattern is consistent with liquidity migrating toward higher-throughput, lower-fee chains—"
        r"though Ethereum still dominates levels in most snapshots\.?",
        (
            "That pattern is consistent with TMMF issuers routing more distributed value toward "
            "higher-throughput, lower-fee chains—though Ethereum still dominates TMMF share levels in most snapshots."
        ),
        rest,
        flags=re.IGNORECASE,
    )
    rest = re.sub(
        r"gainers include ([^;]+); losers include ([^.]+)\.",
        lambda m: (
            f"Among tokenized money market funds, gainers include {m.group(1)}; losers include {m.group(2)}."
            if "tmmf" not in m.group(0).lower() and "money market" not in m.group(0).lower()
            else m.group(0)
        ),
        rest,
        flags=re.IGNORECASE,
    )
    rest = re.sub(r"([+\-]?\d+(?:\.\d+)?)\s+pp\b", r"\1%", rest)
    rest = re.sub(r"30D share\)", "30D TMMF network share)", rest, flags=re.IGNORECASE)
    rest = re.sub(r"\s{2,}", " ", rest).strip()
    rest = re.sub(r"\.{2,}", ".", rest)
    rest = re.sub(r"\s+\.$", ".", rest)
    return _capitalize_rest(rest)


def _bullet_plain_text(chunk: str) -> str:
    chunk = _LINK_RE.sub(r"\1", chunk)
    return re.sub(r"\s+", " ", _strip_tags(chunk)).strip()


def _related_article_html(
    article: dict[str, Any] | None,
    *,
    accent: str,
    outlook: bool = False,
) -> str:
    if not article:
        return ""
    title = str(article.get("title") or "").strip()
    link = str(article.get("link") or "").strip()
    source = str(article.get("source") or "").strip()
    if not title:
        return ""
    if len(title) > 78:
        title = title[:76].rsplit(" ", 1)[0] + "…"
    if link:
        link_weight = "" if outlook else "font-weight:600;"
        title_html = (
            f'<a href="{escape(link, quote=True)}" style="color:{_COLOR_LINK};text-decoration:none;'
            f'{link_weight}">{escape(title)}</a>'
        )
    else:
        title_html = escape(title)
    source_html = f" · {escape(source)}" if source else ""
    if outlook:
        border = _accent_border(accent)
        return _ol_related_reading_html(title_html, source_html, border_color=border)
    return (
        f'<span style="{_related_style(accent)}">'
        f'<span style="font-weight:700;color:{_COLOR_LABEL};font-size:10px;letter-spacing:0.06em;text-transform:uppercase;">'
        f"Related reading</span> · {title_html}{source_html}</span>"
    )


def _ko_li_email_html(
    chunk: str,
    *,
    is_last: bool = False,
    related_article: dict[str, Any] | None = None,
    accent: str = _COLOR_BRAND,
    outlook: bool = False,
    section: bool = False,
) -> str:
    chunk = _LINK_RE.sub(r"\1", chunk)
    chunk = re.sub(r"</?em>", "", chunk, flags=re.IGNORECASE)
    sm = _STRONG_RE.search(chunk)
    body_parts: list[str] = []
    if outlook:
        size = _OL_TEXT_SECTION if section else _OL_TEXT_BODY
        lh = _OL_LINE_SECTION if section else _OL_LINE
        lead_gap = 4 if section else 6
        if sm:
            lead, lead_overflow = _polish_newsletter_lead(_strip_tags(sm.group(1)))
            body_parts.append(
                f'<p style="margin:0 0 {lead_gap}px;font-size:{size};line-height:1.45;mso-line-height-rule:exactly;{_ol_font()}">'
                f'<strong style="color:{_COLOR_INK};font-weight:700;">{escape(lead)}.</strong></p>'
            )
            rest = _polish_newsletter_rest(lead, _strip_tags(chunk[sm.end() :]), lead_overflow=lead_overflow)
        else:
            rest = _polish_newsletter_rest("", _strip_tags(chunk))
        if rest:
            body_parts.append(
                f'<p style="margin:0;font-size:{size};line-height:{lh};mso-line-height-rule:exactly;'
                f'color:{_COLOR_BODY};{_ol_font()}">'
                f"{escape(rest)}</p>"
            )
    else:
        strong = _strong_style(outlook=outlook, section=section)
        body_span = _body_style(outlook=outlook, section=section)
        if sm:
            lead, lead_overflow = _polish_newsletter_lead(_strip_tags(sm.group(1)))
            body_parts.append(f'<strong style="{strong}">{escape(lead)}.</strong>')
            rest = _polish_newsletter_rest(lead, _strip_tags(chunk[sm.end() :]), lead_overflow=lead_overflow)
        else:
            rest = _polish_newsletter_rest("", _strip_tags(chunk))
        if rest:
            body_parts.append(f'<span style="{body_span}">{escape(rest)}</span>')
    related = _related_article_html(related_article, accent=accent, outlook=outlook)
    li_style = _li_style(outlook=outlook, is_last=is_last, section=section)
    return f'<li style="{li_style}">{"".join(body_parts)}{related}</li>'


def _fund_launch_bullet_html(
    launch: Any,
    *,
    accent: str,
    is_last: bool = False,
    outlook: bool = False,
    section: bool = False,
) -> str:
    from key_observations.week_headlines import FundLaunch, launch_section_copy

    if not isinstance(launch, FundLaunch):
        return ""
    lead, body = launch_section_copy(launch)
    article = {
        "title": launch.title,
        "link": launch.link,
        "source": launch.source,
    }
    li_style = _li_style(outlook=outlook, is_last=is_last, section=section)
    related = _related_article_html(article, accent=accent, outlook=outlook)
    if outlook:
        size = _OL_TEXT_SECTION if section else _OL_TEXT_BODY
        lh = _OL_LINE_SECTION if section else _OL_LINE
        lead_gap = 4 if section else 6
        return (
            f'<li style="{li_style}">'
            f'<p style="margin:0 0 {lead_gap}px;font-size:{size};line-height:1.45;mso-line-height-rule:exactly;{_ol_font()}">'
            f'<strong style="color:{_COLOR_INK};font-weight:700;">{escape(lead)}</strong></p>'
            f'<p style="margin:0;font-size:{size};line-height:{lh};mso-line-height-rule:exactly;color:{_COLOR_BODY};{_ol_font()}">'
            f"{escape(body)}</p>"
            f"{related}</li>"
        )
    return (
        f'<li style="{li_style}">'
        f'<strong style="{_strong_style(outlook=outlook, section=section)}">{escape(lead)}</strong>'
        f'<span style="{_body_style(outlook=outlook, section=section)}">{escape(body)}</span>'
        f"{related}</li>"
    )


def _weekly_takeaways_active() -> bool:
    try:
        from key_observations.newsletter_week import weekly_takeaways_enabled

        return weekly_takeaways_enabled()
    except Exception:
        return False


def _ko_bullets_html(
    html_sources: tuple[str, ...],
    *,
    section_id: str,
    max_items: int = 3,
    articles: list[dict[str, Any]] | None = None,
    used_links: set[str] | None = None,
    accent: str = _COLOR_BRAND,
    fund_launch: Any | None = None,
    outlook: bool = False,
    section: bool = False,
    executive_news_only: bool = False,
    explore: dict[str, dict[str, Any]] | None = None,
    etp: dict[str, Any] | None = None,
    crypto: dict[str, Any] | None = None,
    week_headlines: list[Any] | None = None,
    shipped_leads: dict[str, list[str]] | None = None,
    force_legacy_takeaways: bool = False,
) -> str:
    profile = _SECTION_KO[section_id]
    topic_keys: tuple[str, ...] = profile["topic_keys"]
    links = used_links if used_links is not None else set()
    ul_style = (
        f"margin:0;padding:0 0 0 18px;list-style:disc;list-style-position:outside;{_ol_font()}"
        if outlook
        else _UL_STYLE
    )

    use_weekly = (
        not force_legacy_takeaways
        and _weekly_takeaways_active()
        and section_id in {"tmmf", "stablecoins", "rwa", "etp", "crypto"}
    )
    if use_weekly:
        try:
            from key_observations.newsletter_week import select_weekly_section_takeaways

            weekly = select_weekly_section_takeaways(
                section_id,
                explore=explore or {},
                etp=etp,
                crypto=crypto,
                articles=articles,
                week_headlines=week_headlines or [],
                used_links=links,
                max_items=max_items,
                skip_fund_launch_slot=bool(fund_launch),
                topic_keys=topic_keys,
            )
        except Exception:
            weekly = []
        items: list[str] = []
        if fund_launch:
            link = str(getattr(fund_launch, "link", "") or "").strip()
            if link:
                links.add(link)
            items.append(
                _fund_launch_bullet_html(
                    fund_launch,
                    accent=accent,
                    is_last=(not weekly),
                    outlook=outlook,
                    section=section,
                )
            )
        if shipped_leads is not None:
            shipped_leads.setdefault(section_id, [])
        try:
            from key_observations.week_headlines import match_article_for_takeaway
        except Exception:
            match_article_for_takeaway = None  # type: ignore[assignment,misc]
        for i, tw in enumerate(weekly):
            if shipped_leads is not None and tw.lead and tw.kind != "flat":
                shipped_leads[section_id].append(tw.lead)
            chunk = f"<strong>{escape(tw.lead)}</strong> {escape(tw.body)}"
            related = tw.article
            # Data takeaways still get a Related article when the matcher finds one.
            if (
                related is None
                and match_article_for_takeaway
                and topic_keys
                and tw.kind in {"wow", "flat"}
            ):
                related = match_article_for_takeaway(
                    f"{tw.lead} {tw.body}",
                    bullet_lead=tw.lead,
                    bullet_html=chunk,
                    topic_keys=topic_keys,
                    articles=articles,
                    used_links=links,
                )
            if related and related.get("link"):
                links.add(str(related.get("link") or "").strip())
            items.append(
                _ko_li_email_html(
                    chunk,
                    is_last=(i == len(weekly) - 1),
                    related_article=related,
                    accent=accent,
                    outlook=outlook,
                    section=section,
                )
            )
        if items:
            return f'<ul style="{ul_style}">{"".join(items)}</ul>'
        # Fall through to legacy page-KO path if weekly returned nothing.

    chunks = _select_section_ko_chunks(
        *html_sources,
        section_id=section_id,
        max_items=max_items,
        executive_news_only=executive_news_only,
    )
    if fund_launch:
        max_items = max(0, max_items - 1)
        chunks = chunks[:max_items]
    if not chunks and not fund_launch:
        return ""
    try:
        from key_observations.week_headlines import match_article_for_takeaway
    except Exception:
        match_article_for_takeaway = None  # type: ignore[assignment,misc]

    items = []
    if fund_launch:
        link = str(getattr(fund_launch, "link", "") or "").strip()
        if link:
            links.add(link)
        items.append(
            _fund_launch_bullet_html(
                fund_launch,
                accent=accent,
                is_last=(not chunks),
                outlook=outlook,
                section=section,
            )
        )
    for i, chunk in enumerate(chunks):
        related: dict[str, Any] | None = None
        if match_article_for_takeaway and topic_keys:
            related = match_article_for_takeaway(
                _bullet_plain_text(chunk),
                bullet_lead=_ko_lead_text(chunk),
                bullet_html=chunk,
                topic_keys=topic_keys,
                articles=articles,
                used_links=links,
            )
        items.append(
            _ko_li_email_html(
                chunk,
                is_last=(i == len(chunks) - 1),
                related_article=related,
                accent=accent,
                outlook=outlook,
                section=section,
            )
        )
    return f'<ul style="{ul_style}">{"".join(items)}</ul>'


def _kpi_row(
    label: str,
    value: str,
    delta: str,
    *,
    delta_color: str | None = None,
    is_last: bool = False,
    outlook: bool = False,
) -> str:
    dc = delta_color or (
        _COLOR_POS if delta.startswith("+") else _COLOR_NEG if delta.startswith("-") else _COLOR_NEUTRAL
    )
    divider = "" if is_last else f"border-right:1px solid {_OL_BORDER};"
    if outlook:
        return (
            f'<td width="33%" style="padding:{_OL_KPI_PAD};{divider}background:{_OL_CELL};vertical-align:top;">'
            f'<p style="margin:0;font-size:{_OL_TEXT_CAPTION};line-height:{_OL_KPI_LABEL_LH};mso-line-height-rule:exactly;'
            f'color:{_COLOR_MUTED};text-transform:uppercase;letter-spacing:0.06em;{_ol_font()}">'
            f"{escape(label)}</p>"
            f'<p style="margin:{_OL_KPI_VALUE_GAP} 0 0;font-size:{_OL_TEXT_KPI};line-height:{_OL_KPI_VALUE_LH};'
            f'mso-line-height-rule:exactly;font-weight:400;color:{_COLOR_INK};letter-spacing:-0.01em;'
            f'text-shadow:0.4px 0 0 {_COLOR_INK};font-family:{_OL_KPI_VALUE_FONT};">'
            f"{escape(value)}</p>"
            f'<p style="margin:{_OL_KPI_DELTA_GAP} 0 0;font-size:{_OL_TEXT_META};line-height:{_OL_KPI_DELTA_LH};'
            f'mso-line-height-rule:exactly;font-weight:400;color:{dc};font-family:{_OL_KPI_VALUE_FONT};">'
            f'<span style="font-weight:700;">{escape(delta)}</span> '
            f'<span style="font-weight:400;color:{_COLOR_MUTED};{_ol_font()}">30D</span></p>'
            f"</td>"
        )
    return (
        f'<td style="padding:0.65rem 0.85rem;{divider}background:#fff;vertical-align:top;width:33%;">'
        f'<div style="font-size:10px;color:{_COLOR_MUTED};text-transform:uppercase;letter-spacing:0.06em;">'
        f"{escape(label)}</div>"
        f'<div style="font-size:19px;font-weight:600;color:{_COLOR_INK};margin-top:0.25rem;letter-spacing:-0.01em;">'
        f"{escape(value)}</div>"
        f'<div style="font-size:12px;color:{dc};margin-top:0.2rem;font-weight:600;">'
        f'{escape(delta)} <span style="font-weight:400;color:{_COLOR_MUTED};">30D</span></div>'
        f"</td>"
    )


_HEADLINE_SO_WHAT_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"state street|stablecoin reserves? money market|genius act.*money market", re.I),
        "A major custodian launched a dedicated stablecoin reserve fund",
        "reserve infrastructure is being productized—not just banked—ahead of scaled issuance",
    ),
    (
        re.compile(r"bita|covered-call bitcoin|premium income etf|debuts.*bitcoin etf", re.I),
        "BlackRock broadened listed Bitcoin access with an income-oriented ETF",
        "product innovation is expanding beyond spot beta into yield and options overlays",
    ),
    (
        re.compile(r"stablecoin|bitlicense", re.I),
        "Bank-led stablecoin plans are shifting from pilot to scaled issuance",
        "regulated issuers are treating stablecoins as payments infrastructure, not trading collateral",
    ),
    (
        re.compile(r"prediction market|kalshi|insider|market manipulation", re.I),
        "Prediction-market venues face tighter conduct and disclosure rules",
        "oversight is scaling with new trading venues—a governance story more than a token bet",
    ),
    (
        re.compile(r"shut down|shutdown|didn.t care|post-mortem", re.I),
        "An on-chain product cycle ended without durable user demand",
        "distribution and use-case fit still matter more than token design alone",
    ),
    (
        re.compile(r"tokeniz|\brwa\b|private credit|securitize|treasur", re.I),
        "Tokenization coverage points to TradFi assets moving on-chain",
        "distribution and collateral plumbing are still the bottleneck, not issuer intent",
    ),
    (
        re.compile(r"money market|mmf|settlement|buidl|benji", re.I),
        "Tokenized cash and settlement rails keep attracting institutional attention",
        "on-chain money-market funds are being framed as workflow infrastructure, not yield products",
    ),
    (
        re.compile(r"\betf\b|\betp\b|inflow|outflow|ibit", re.I),
        "Listed crypto ETF access remains a primary institutional on-ramp",
        "flows and product filings still front-run how allocators gain exposure",
    ),
    (
        re.compile(r"sec\b|cftc|regulat|legislation|genius act", re.I),
        "Regulatory headlines are shaping what institutions can launch and hold",
        "policy clarity matters more than weekly price moves for durable adoption",
    ),
)

_FAMILY_SO_WHAT: dict[str, tuple[str, str]] = {
    "stablecoins": (
        "Stablecoin infrastructure stayed in the news",
        "payments and reserve rails remain the institutional entry point",
    ),
    "tokenization": (
        "Tokenization remained a lead institutional theme",
        "TradFi distribution is still catching up to on-chain issuance",
    ),
    "tmmf": (
        "Tokenized cash rails drew fresh coverage",
        "settlement and treasury workflow adoption matter more than headline yield",
    ),
    "etp": (
        "U.S. crypto ETF access stayed in focus",
        "listed products still mediate how traditional capital enters the asset class",
    ),
    "etp_flows": (
        "ETF flow dynamics stayed in focus",
        "allocators are adjusting listed exposure faster than on-chain rails are repricing",
    ),
    "regulation": (
        "Policy and oversight headlines continued to build",
        "compliance capacity is becoming part of market structure, not a side story",
    ),
}


def _headline_so_what_line(pick: Any) -> str:
    """Per-headline takeaway: story read, then market meaning."""
    title = str(pick.title or "")
    for pattern, interpretation, meaning in _HEADLINE_SO_WHAT_RULES:
        if pattern.search(title):
            return f"{interpretation}—{meaning}."
    family = str(getattr(pick, "theme_family", "") or "")
    if family in _FAMILY_SO_WHAT:
        interpretation, meaning = _FAMILY_SO_WHAT[family]
        return f"{interpretation}—{meaning}."
    return (
        "This headline adds to the week's infrastructure narrative—"
        "structural buildout is still running ahead of short-term spot noise."
    )


def _so_what_inset_html(line: str, *, outlook: bool = False, margin_top: str | None = None) -> str:
    if outlook:
        body = (
            f'<p style="margin:0;font-size:{_OL_TEXT_SECTION};line-height:{_OL_INSET_BODY_LH};'
            f'mso-line-height-rule:exactly;color:{_COLOR_BODY};{_ol_font()}">{escape(line)}</p>'
        )
        return _ol_inset_box_html("So what", body, border_color=_COLOR_BRAND)
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="margin:0.5rem 0 0 0;border-collapse:collapse;">'
        f"<tr><td style=\"padding:0.55rem 0.7rem;background:{_COLOR_INSET};"
        f"border-left:3px solid {_COLOR_BRAND};border-radius:0 6px 6px 0;\">"
        f'<span style="display:block;font-size:10px;font-weight:700;letter-spacing:0.06em;'
        f'text-transform:uppercase;color:{_COLOR_LABEL};margin:0 0 0.3rem;">So what</span>'
        f'<span style="display:block;font-size:13px;line-height:1.6;color:{_COLOR_BODY};">'
        f"{escape(line)}</span></td></tr></table>"
    )


def _ol_headline_separator_html() -> str:
    """Spacer + rule between headline items — table rows render reliably in Outlook."""
    return (
        _ol_spacer_row(_OL_HEADLINE_ITEM_GAP)
        + f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;"><tr><td style="border-bottom:1px solid {_OL_BORDER};'
        f'font-size:1px;line-height:1px;mso-line-height-rule:exactly;">&nbsp;</td></tr></table>'
    )


def _headline_so_what_html(pick: Any, *, outlook: bool = False, margin_top: str | None = None) -> str:
    return _so_what_inset_html(_headline_so_what_line(pick), outlook=outlook, margin_top=margin_top)


def _headline_item_html(pick: Any, index: int, *, is_last: bool = False, outlook: bool = False) -> str:
    title = escape(str(pick.title))
    link = str(pick.link or "").strip()
    if link:
        title = (
            f'<a href="{escape(link, quote=True)}" style="color:{_COLOR_LINK};text-decoration:none;'
            f'font-weight:600;">{title}</a>'
        )
    meta = escape(str(pick.source or "Industry"))
    if int(pick.outlet_count) > 1:
        meta += f" · {int(pick.outlet_count)} sources"
    if outlook:
        gap = _OL_HEADLINE_INNER_GAP
        separator = "" if is_last else _ol_headline_separator_html()
        return (
            f'<div style="margin:0;padding:0;">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-collapse:collapse;">'
            f"<tr>"
            f'<td style="width:22px;vertical-align:top;padding:0 6px 0 0;white-space:nowrap;{_ol_font()}">'
            f'<strong style="color:{_OL_ACCENT};">{index}.</strong></td>'
            f'<td style="vertical-align:top;">'
            f'<p style="margin:0;font-size:{_OL_TEXT_HEADLINE};line-height:{_OL_LINE_HEADLINE};'
            f'mso-line-height-rule:exactly;color:{_COLOR_INK};{_ol_font()}">{title}</p>'
            f"</td></tr>"
            f"<tr><td></td>"
            f'<td style="padding-top:{gap};">'
            f'<p style="margin:0;font-size:{_OL_TEXT_META};line-height:{_OL_LINE};mso-line-height-rule:exactly;'
            f'color:{_COLOR_MUTED};{_ol_font()}">{meta}</p>'
            f"</td></tr>"
            f"<tr><td></td>"
            f'<td style="padding-top:{gap};">'
            f"{_headline_so_what_html(pick, outlook=True, margin_top='0')}"
            f"</td></tr>"
            f"</table>{separator}</div>"
        )
    item_pad = "0" if is_last else "0 0 1.1rem"
    item_border = "" if is_last else f"border-bottom:1px solid {_COLOR_LINE_SOFT};"
    return (
        f'<li style="margin:0;padding:{item_pad};list-style:none;{item_border}">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">'
        f"<tr><td style=\"width:1.65rem;vertical-align:top;padding:0.1rem 0.45rem 0 0;\">"
        f'<span style="display:inline-block;min-width:1.35rem;font-size:13px;font-weight:700;'
        f'color:#ffffff;background:{_COLOR_BRAND};border-radius:999px;text-align:center;'
        f'line-height:1.35rem;">{index}</span></td>'
        f'<td style="vertical-align:top;">'
        f'<div style="font-size:14px;line-height:1.55;color:{_COLOR_INK};">{title}</div>'
        f'<div style="font-size:12px;color:{_COLOR_MUTED};margin:0.3rem 0 0;">{meta}</div>'
        f"{_headline_so_what_html(pick)}"
        f"</td></tr></table></li>"
    )


def _week_headlines_html(picks: list[Any], *, outlook: bool = False) -> str:
    if not picks:
        return ""
    items = [
        _headline_item_html(pick, i, is_last=(i == len(picks)), outlook=outlook)
        for i, pick in enumerate(picks, start=1)
    ]
    if outlook:
        inner = f'{_section_eyebrow("Headlines of the week", outlook=True)}{"".join(items)}'
    else:
        inner = (
            f'{_section_eyebrow("Headlines of the week", outlook=False)}'
            f'<ul style="margin:0;padding:0;list-style:none;">{"".join(items)}</ul>'
        )
    # Flush to dashboard link — spacing lives in link padding + section gap below.
    return _callout_card(inner, outlook=outlook, margin_bottom="0")


def _dashboard_link_html(site: str, *, outlook: bool = False) -> str:
    href = f"{site}/index.html"
    label = "Open live dashboard →"
    if outlook:
        return _ol_centered_action_link_html(href, label, sandwich=True)
    return _centered_action_link_html(href, label, sandwich=True)


def _section_block(
    title: str,
    page_href: str,
    kpi_cells: str,
    ko_html: str,
    *,
    accent: str,
    ko_body_html: str | None = None,
    takeaways_label: str = "Key takeaways",
    max_bullets: int = 3,
    section_id: str = "",
    articles: list[dict[str, Any]] | None = None,
    used_links: set[str] | None = None,
    reserved_headline_links: set[str] | None = None,
    ko_html_sources: tuple[str, ...] | None = None,
    section_divider: bool = False,
    fund_launch: Any | None = None,
    outlook: bool = False,
    executive_news_only: bool = False,
    scope_note: str = "",
    explore: dict[str, dict[str, Any]] | None = None,
    etp: dict[str, Any] | None = None,
    crypto: dict[str, Any] | None = None,
    week_headlines: list[Any] | None = None,
    shipped_leads: dict[str, list[str]] | None = None,
    force_legacy_takeaways: bool = False,
) -> str:
    section_links = used_links if used_links is not None else set(reserved_headline_links or set())
    if ko_body_html is None:
        sources = ko_html_sources if ko_html_sources is not None else (ko_html,)
        bullets = _ko_bullets_html(
            sources,
            section_id=section_id,
            max_items=max_bullets,
            articles=articles,
            used_links=section_links,
            accent=accent,
            fund_launch=fund_launch,
            outlook=outlook,
            section=outlook,
            executive_news_only=executive_news_only,
            explore=explore,
            etp=etp,
            crypto=crypto,
            week_headlines=week_headlines,
            shipped_leads=shipped_leads,
            force_legacy_takeaways=force_legacy_takeaways,
        )
    else:
        bullets = ko_body_html
    body = bullets or (
        f'<p style="margin:0;color:{_COLOR_MUTED};font-size:{_OL_TEXT_SECTION if outlook else "13"}px;'
        f'line-height:{_OL_LINE_SECTION if outlook else "1.6"};'
        f'{"mso-line-height-rule:exactly;" if outlook else ""}'
        f'{(_ol_font() if outlook else "font-family:inherit;")}">'
        f"No key observations exported for this section.</p>"
    )
    takeaways_margin = f"{_OL_GAP_SM} 0 {_OL_GAP_XS}" if outlook else "0 0 0.55rem"
    takeaways = f'{_section_eyebrow(takeaways_label, margin=takeaways_margin, outlook=outlook)}{body}'
    scope_html = _scope_note_html(scope_note, outlook=outlook)
    if outlook:
        top_pad = _OL_SECTION_AFTER_LINK_GAP if section_divider else _OL_GAP_XS
        title_pad = f"{_OL_GAP_SM} 0 {_OL_GAP_XS}" if section_divider else f"0 0 {_OL_GAP_XS}"
        section_border = "" if section_divider else f"border-top:1px solid {_OL_DIVIDER};"
        return (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="margin:{top_pad} 0 0;border-collapse:collapse;{section_border}">'
            f'<tr><td style="padding:{title_pad};border-bottom:3px solid {accent};">'
            f'<h2 style="margin:0;font-size:{_OL_TEXT_H2};font-weight:700;color:{_COLOR_INK};'
            f'{_ol_font()}">{escape(title)}</h2></td></tr>'
            f'<tr><td style="padding:{_OL_GAP_SM} 0 0;">'
            f"{_kpi_strip_html(kpi_cells, outlook=True, section=True)}"
            f"{scope_html}"
            f"{takeaways}"
            f'{_ol_centered_action_link_html(page_href, "Open full page →", sandwich=True)}'
            f"</td></tr></table>"
        )
    divider_row = ""
    top_margin = _OL_SECTION_AFTER_LINK_GAP if section_divider else "0"
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:{top_margin} 0 1.3rem;border-collapse:collapse;">
  {divider_row}
  <tr>
    <td style="padding:0 0 0.6rem;border-bottom:3px solid {accent};">
      <h2 style="margin:0;font-size:17px;font-weight:700;color:{_COLOR_INK};letter-spacing:-0.02em;">{escape(title)}</h2>
    </td>
  </tr>
  <tr><td style="height:0.9rem;font-size:0;line-height:0;">&nbsp;</td></tr>
  <tr>
    <td>
      {_kpi_strip_html(kpi_cells)}
      {scope_html}
      {takeaways}
      {_centered_action_link_html(page_href, "Open full page →", sandwich=True)}
    </td>
  </tr>
</table>
"""


def _load_explore_sections() -> dict[str, dict[str, Any]]:
    explore = _read_json(DATA / "rwa_explore_asset_type.json") or {}
    out: dict[str, dict[str, Any]] = {}
    for sec in explore.get("sections") or []:
        sid = sec.get("id")
        if sid:
            out[str(sid)] = sec
    return out


def _explore_kpi_cells(explore: dict[str, dict[str, Any]], section_id: str, *, outlook: bool = False) -> str:
    sec = explore.get(section_id) or {}
    kpis = (sec.get("kpis") or [])[:3]
    if not kpis:
        return _kpi_row("—", "—", "—", is_last=True, outlook=outlook)
    cells = ""
    for i, k in enumerate(kpis):
        cells += _kpi_row(
            str(k.get("label") or "—"),
            str(k.get("value_display") or "—"),
            _fmt_pct(k.get("delta_30d_pct")),
            is_last=(i == len(kpis) - 1),
            outlook=outlook,
        )
    return cells


def _scope_note_html(text: str, *, outlook: bool = False) -> str:
    body = str(text or "").strip()
    if not body:
        return ""
    if body.lower().startswith("scope:"):
        rest = body[6:].strip()
        inner = (
            f'<strong style="color:#4a5f6b;font-weight:700;">Scope:</strong> {escape(rest)}'
        )
    else:
        inner = escape(body)
    if outlook:
        return (
            f'<p style="margin:0 0 12px;font-size:12px;line-height:1.55;mso-line-height-rule:exactly;'
            f'color:#5c6b7a;{_ol_font()}">{inner}</p>'
        )
    return (
        f'<p style="margin:0 0 0.75rem;padding:0.35rem 0.55rem 0.35rem 0.65rem;font-size:12px;'
        f"line-height:1.5;color:#5c6b7a;background:#f1f5f9;border-left:3px solid #b8ccd9;"
        f'border-radius:0 5px 5px 0;font-family:inherit;">{inner}</p>'
    )


def _load_rwa_global_kpi_cells(*, outlook: bool = False) -> str:
    from rwa_global_page_payloads import RWA_GLOBAL_NEWSLETTER_KPI_LABELS

    payload = _read_json(DATA / "rwa_global_market.json") or {}
    by_label = {str(k.get("label") or ""): k for k in (payload.get("kpis") or [])}
    cells = ""
    labels = list(RWA_GLOBAL_NEWSLETTER_KPI_LABELS)
    for i, label in enumerate(labels):
        k = by_label.get(label) or {}
        cells += _kpi_row(
            label if k else "—",
            str(k.get("value_display") or "—"),
            _fmt_pct(k.get("delta_30d_pct")),
            is_last=(i == len(labels) - 1),
            outlook=outlook,
        )
    return cells


def _load_tmmf_ko(articles: list[dict[str, Any]] | None) -> str:
    deep = _read_json(DATA / "rwa_tokenized_mmf.json")
    if deep and str(deep.get("key_observations_html") or "").strip():
        return str(deep["key_observations_html"])
    try:
        from rwa_league.mmf import build_curated_mmf_dashboard_data
        from rwa_league.mmf_takeaways import build_mmf_key_observations_html

        fund_assets, net_rows, _, _, _ = build_curated_mmf_dashboard_data()
        if fund_assets:
            return build_mmf_key_observations_html(fund_assets, list(net_rows), articles)
    except Exception:
        pass
    return ""


def _explore_kpi(
    explore: dict[str, dict[str, Any]],
    section_id: str,
    *,
    label_match: str = "",
    index: int = 0,
) -> dict[str, Any]:
    sec = explore.get(section_id) or {}
    kpis = sec.get("kpis") or []
    if label_match:
        needle = label_match.lower()
        for kpi in kpis:
            if needle in str(kpi.get("label") or "").lower():
                return kpi
    if 0 <= index < len(kpis):
        return kpis[index]
    return {}


_RAIL_FLAT_THRESHOLD = 2.0


def _pct_value(pct: str) -> float | None:
    if pct == "—":
        return None
    try:
        return float(pct.replace("%", "").replace("+", ""))
    except (TypeError, ValueError):
        return None


def _is_flat_move(pct: str, *, threshold: float = _RAIL_FLAT_THRESHOLD) -> bool:
    n = _pct_value(pct)
    if n is None:
        return True
    return abs(n) < threshold


def _delta_tone(pct: str, *, threshold: float = _RAIL_FLAT_THRESHOLD) -> str:
    if _is_flat_move(pct, threshold=threshold):
        return "held steady"
    n = _pct_value(pct)
    if n is None:
        return "held steady"
    if n < 0:
        return "softened"
    if n > 0:
        return "firmed"
    return "held steady"


def _market_move_verb(pct: str) -> str:
    if pct.startswith("-"):
        return "pulled back"
    if pct.startswith("+"):
        return "advanced"
    return "moved sideways"


def _pct_color(pct: str) -> str:
    if pct.startswith("-"):
        return _COLOR_NEG
    if pct.startswith("+"):
        return _COLOR_POS
    return _COLOR_NEUTRAL


def _brief_move_verb(pct: str, *, flat_threshold: float = _RAIL_FLAT_THRESHOLD) -> str:
    n = _pct_value(pct)
    if n is None:
        return "held steady"
    if abs(n) < flat_threshold:
        return "held steady" if abs(n) < 0.05 else "was little changed"
    return _delta_tone(pct, threshold=flat_threshold)


def _week_in_brief_bullet(
    lead: str,
    raw_pct: object,
    metric: str,
    watch: str,
    *,
    flat_threshold: float = _RAIL_FLAT_THRESHOLD,
) -> str:
    pct = _fmt_pct(raw_pct)
    verb = _brief_move_verb(pct, flat_threshold=flat_threshold)
    data_html = f'<strong style="color:{_pct_color(pct)};">{escape(pct)}</strong>'
    return f"{lead} {verb} ({data_html} {metric}, 30D); {watch}."


def _week_in_brief_crypto_bullet(crypto_pct: str, watch: str) -> str:
    color = _pct_color(crypto_pct)
    verb = _market_move_verb(crypto_pct)
    return (
        f"Crypto markets {verb} "
        f'(<strong style="color:{color};">{escape(crypto_pct)}</strong> total market cap, 30D); {watch}.'
    )


def _headlines_by_family(week_headlines: list[Any]) -> dict[str, list[Any]]:
    out: dict[str, list[Any]] = {}
    for pick in week_headlines:
        family = str(getattr(pick, "theme_family", "") or "")
        if family:
            out.setdefault(family, []).append(pick)
    return out


_BRIEF_HOOK_PREFIX_RE = re.compile(
    r"^(?:breaking:|update:|report:|analysis:)\s*",
    re.IGNORECASE,
)
_BRIEF_HOOK_ATTRIBUTION_RE = re.compile(
    r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?:says|said|reports?|warns?|claims?)\s+",
)
_BRIEF_HOOK_CLAUSE_SPLIT_RE = re.compile(
    r"\s+(?:as|while|after|amid|when|where|before)\s+",
    re.IGNORECASE,
)
_BRIEF_HOOK_TRUNC_STOPWORDS = frozenset({
    "a", "an", "the", "as", "for", "to", "on", "in", "at", "with", "and", "or", "of",
    "that", "while", "after", "before", "into", "from", "over", "under", "its", "their",
    "aim", "aims", "aiming", "won", "says", "said", "by",
})


def _brief_headline_hook(title_or_pick: Any, *, max_len: int = 60) -> str:
    if isinstance(title_or_pick, str):
        title = title_or_pick.strip()
    else:
        title = str(getattr(title_or_pick, "title", "") or "").strip()
    title = _BRIEF_HOOK_PREFIX_RE.sub("", title).strip()
    title = _BRIEF_HOOK_ATTRIBUTION_RE.sub("", title).strip()
    clause_parts = _BRIEF_HOOK_CLAUSE_SPLIT_RE.split(title, maxsplit=1)
    if len(clause_parts) > 1 and len(clause_parts[0]) >= 18:
        title = clause_parts[0].strip()
    if len(title) <= max_len:
        return title
    words = title[: max_len - 1].rsplit(" ", 1)[0].split()
    while len(words) > 5 and words[-1].lower().rstrip(".,;:") in _BRIEF_HOOK_TRUNC_STOPWORDS:
        words.pop()
    trimmed = " ".join(words)
    if len(trimmed) <= max_len:
        return trimmed
    return trimmed + "…"


def _tmmf_network_anchor(explore: dict[str, dict[str, Any]]) -> str:
    kpi = _explore_kpi(explore, "tokenized_mmf", label_match="network share")
    disp = str(kpi.get("value_display") or "").strip()
    if not disp:
        return ""
    if "·" in disp:
        share_raw, network = [p.strip() for p in disp.split("·", 1)]
        share_raw = share_raw.replace("%", "").strip()
        try:
            share_n = float(share_raw)
            share_txt = f"~{share_n:.0f}%"
        except (TypeError, ValueError):
            share_txt = share_raw
        return f"{network} still anchors {share_txt} of TMMF distributed value"
    return f"top-network share held at {disp}"


def _tmmf_watch_hook(
    articles: list[dict[str, Any]] | None,
    week_headlines: list[Any],
) -> str | None:
    """Plain-language TMMF context for Week in brief watch clauses."""
    if not articles:
        return None
    from key_observations.week_headlines import pick_brief_tmmf_article, plain_language_tmmf_hook

    exclude = {str(getattr(p, "link", "") or "").strip() for p in week_headlines}
    art = pick_brief_tmmf_article(articles, exclude_links=exclude)
    if not art:
        return None
    return plain_language_tmmf_hook(
        str(art.get("title") or ""),
        summary=str(art.get("summary") or ""),
    )


def _tmmf_hook_from_pick(pick: Any) -> str:
    from key_observations.week_headlines import plain_language_tmmf_hook

    return plain_language_tmmf_hook(str(getattr(pick, "title", "") or ""))


# Watch clauses add weekly context only — never repeat the KPI % or move verb from the first clause.


def _week_in_brief_watch_tmmf(
    tmmf_pct: str,
    by_family: dict[str, list[Any]],
    explore: dict[str, dict[str, Any]],
    articles: list[dict[str, Any]] | None,
    week_headlines: list[Any],
    fund_launch: Any | None = None,
) -> str:
    from key_observations.week_headlines import FundLaunch, plain_language_launch_brief

    if isinstance(fund_launch, FundLaunch):
        hook = plain_language_launch_brief(fund_launch)
        if _is_flat_move(tmmf_pct):
            return (
                f"issuer headlines stayed active ({hook}); "
                "settlement and routing still look like the bottleneck—not fund yields"
            )
        tmmf_n = _pct_value(tmmf_pct) or 0
        if tmmf_n < 0:
            return (
                f"supply softened while issuer headlines kept building ({hook}); "
                "watch whether issuers pause expansion or lean harder into settlement workflows"
            )
        return (
            f"issuers added supply as headlines built ({hook}); "
            "track which networks capture incremental settlement demand"
        )

    extra_hook = _tmmf_watch_hook(articles, week_headlines)
    net_delta = _explore_kpi(explore, "tokenized_mmf", label_match="network share").get(
        "delta_30d_pct"
    )
    net_mix_flat = _is_flat_move(_fmt_pct(net_delta), threshold=1.0)
    network_anchor = _tmmf_network_anchor(explore)

    if picks := by_family.get("tmmf"):
        hook = _tmmf_hook_from_pick(picks[0])
        return (
            f"tokenized-cash headlines centered on {hook}, "
            "with issuer settlement and routing still the bottleneck—not fund yields"
        )
    if _is_flat_move(tmmf_pct):
        if extra_hook and network_anchor and net_mix_flat:
            return (
                f"issuer headlines stayed active ({extra_hook}); "
                f"{network_anchor}, and the network mix barely shifted"
            )
        if extra_hook:
            return (
                f"issuer headlines stayed active ({extra_hook}), "
                "suggesting settlement workflows mattered more than the flat supply read"
            )
        if network_anchor and net_mix_flat:
            return (
                f"{network_anchor}, and the network mix barely shifted—"
                "routing share, not yield repricing, explains the flat supply read"
            )
        return (
            "issuer settlement and multichain routing still look like the bottleneck—"
            "not a meaningful yield repricing in tokenized funds"
        )
    tmmf_n = _pct_value(tmmf_pct) or 0
    if tmmf_n < 0:
        if extra_hook:
            return (
                f"supply softened while issuer headlines kept building ({extra_hook}); "
                "watch whether issuers pause expansion or lean harder into settlement workflows"
            )
        return (
            "watch whether issuers pause expansion or lean further into settlement workflows"
        )
    if extra_hook:
        return (
            f"issuers added supply as headlines built ({extra_hook}); "
            "track which networks capture incremental settlement demand"
        )
    return (
        "issuers added supply this month—"
        "track multichain routing and which networks capture incremental settlement demand"
    )


def _week_in_brief_watch_stablecoins(
    sc_pct: str,
    by_family: dict[str, list[Any]],
    fund_launch: Any | None = None,
) -> str:
    from key_observations.week_headlines import FundLaunch, plain_language_launch_brief

    if isinstance(fund_launch, FundLaunch):
        hook = plain_language_launch_brief(fund_launch)
        if _is_flat_move(sc_pct):
            return (
                f"a major reserve-fund launch led the week ({hook}), "
                "suggesting reserve infrastructure is running ahead of the flat market-cap read"
            )
        sc_n = _pct_value(sc_pct) or 0
        if sc_n < 0:
            return (
                f"reserve-fund launches kept building ({hook})—"
                "watch whether dedicated products offset the softer market-cap print"
            )
        return (
            f"reserve-fund launches accelerated ({hook})—"
            "track which bank-led programs move from pilot to scale"
        )

    if picks := by_family.get("stablecoins"):
        hook = _brief_headline_hook(picks[0])
        return (
            f"bank-led issuance led the week ({hook}), "
            "suggesting issuance is running ahead of the flat market-cap read"
        )
    if _is_flat_move(sc_pct):
        return (
            "issuer and bank-integration headlines outweighed the flat market-cap read this week"
        )
    sc_n = _pct_value(sc_pct) or 0
    if sc_n < 0:
        return (
            "watch whether bank and fintech rails keep expanding issuance despite the softer market-cap print"
        )
    return (
        "supply continued to build—"
        "track reserve transparency and which bank-led programs move from pilot to scale"
    )


def _week_in_brief_watch_rwa(
    tre_pct: str,
    crypto_pct: str,
    by_family: dict[str, list[Any]],
) -> str:
    if picks := by_family.get("tokenization"):
        hook = _brief_headline_hook(picks[0])
        return (
            f"tokenization stayed in the news ({hook}), "
            "with TradFi distribution and collateral plumbing still the bottleneck"
        )
    crypto_n = _pct_value(crypto_pct) or 0
    if _is_flat_move(tre_pct) and crypto_n < -5:
        return (
            "private-credit and distribution headlines drove the narrative "
            "(not a move in on-chain Treasury supply), even as crypto spot sold off"
        )
    if _is_flat_move(tre_pct):
        return (
            "watch securitization and broker-dealer distribution deals for the next leg of scale"
        )
    tre_n = _pct_value(tre_pct) or 0
    if tre_n < 0:
        return (
            "monitor whether issuers keep launching collateral and liquidity products despite broader risk"
        )
    return (
        "tokenized Treasuries continued to build—"
        "watch private-credit and broker workflows for signs distribution is catching up"
    )


def _week_in_brief_watch_etp(
    etp: dict[str, Any],
    etp_pct: str,
    by_family: dict[str, list[Any]],
    fund_launch: Any | None = None,
) -> str:
    from key_observations.week_headlines import FundLaunch, plain_language_launch_brief

    if isinstance(fund_launch, FundLaunch):
        hook = plain_language_launch_brief(fund_launch)
        aum_n = _pct_value(etp_pct)
        if aum_n is not None and aum_n < -10:
            return (
                f"crypto spot weakness hit AUM marks while a new listed product launched "
                f"({hook})—watch whether allocators rotate into income-oriented ETFs on the dip"
            )
        return (
            f"listed-access innovation led the week ({hook})—"
            "product pipeline still front-runs AUM marks"
        )

    for family in ("etp", "etp_flows"):
        if picks := by_family.get(family):
            hook = _brief_headline_hook(picks[0])
            return (
                f"listed-access headlines drove the week ({hook}), "
                "with product pipeline and flows still front-running AUM marks"
            )
    flow_disp = str(etp.get("net_flow_1m_display") or "").strip()
    flow_pct = _fmt_pct(etp.get("net_flow_1m_pct"))
    aum_n = _pct_value(etp_pct)
    flow_n = _pct_value(flow_pct)
    flow_usd_raw = etp.get("net_flow_1m_usd")
    try:
        flow_usd_n = float(flow_usd_raw) if flow_usd_raw is not None else None
    except (TypeError, ValueError):
        flow_usd_n = None
    if aum_n is not None and aum_n < -10 and flow_usd_n is not None and flow_usd_n > 0:
        flow_ref = flow_disp or flow_pct
        return (
            f"crypto spot weakness hit AUM marks while 30-day net flows turned positive "
            f"({flow_ref})—watch whether allocators keep adding on the dip"
        )
    if aum_n is not None and aum_n < -5:
        return (
            "crypto spot weakness dragged AUM lower—"
            "monitor flow and filing data to see if exposure is stabilizing"
        )
    if flow_n is not None and flow_n < 0:
        return (
            f"30-day net flows stayed negative ({flow_disp or flow_pct})—"
            "track whether outflows broaden beyond bitcoin-only products"
        )
    return (
        "flows and filings stayed active—"
        "monitor whether new product approvals translate into sustained AUM rebuild"
    )


def _week_in_brief_watch_crypto(
    crypto_pct: str,
    rail_pcts: list[str],
    by_family: dict[str, list[Any]],
) -> str:
    crypto_n = _pct_value(crypto_pct) or 0
    rails_flat = bool(rail_pcts) and all(_is_flat_move(p) for p in rail_pcts)
    if crypto_n < -10 and rails_flat:
        return (
            "on-chain rails were largely unchanged—"
            "suggesting macro and ETF flows, not rail fundamentals, drove the selloff"
        )
    if crypto_n < -5:
        return (
            "the move looks macro- and flow-driven rather than a repricing of on-chain rails"
        )
    if crypto_n > 5:
        return (
            "risk assets rallied—"
            "watch whether flows rotate back into rails or concentrate in listed beta"
        )
    if picks := by_family.get("regulation"):
        hook = _brief_headline_hook(picks[0])
        return (
            f"oversight headlines shared attention with prices ({hook}), "
            "but policy noise was not the main market driver"
        )
    return (
        "macro and ETF-flow data matter more than daily price noise for this week's read"
    )


def _synthesis_takeaway(
    week_headlines: list[Any],
    *,
    rails_resilient: bool,
) -> str:
    """Second clause: what the data read means in a news/market context."""
    by_family: dict[str, Any] = {}
    for pick in week_headlines:
        family = str(getattr(pick, "theme_family", "") or "")
        if family and family not in by_family:
            by_family[family] = pick

    if rails_resilient:
        if "stablecoins" in by_family:
            return (
                "bank-led stablecoin and payments-rail headlines kept advancing in the news flow."
            )
        if "tokenization" in by_family:
            return (
                "TradFi-bridge and tokenization coverage kept building momentum in the headlines."
            )
        if "tmmf" in by_family:
            return (
                "settlement and tokenized-cash adoption look durable in this week's coverage."
            )
        return (
            "headlines stayed focused on institutional infrastructure—not a broad repricing of on-chain rail metrics."
        )

    if "etp" in by_family or "etp_flows" in by_family:
        return (
            "listed ETF access and on-chain rails are diverging—flows and AUM matter, "
            "but tokenized cash and settlement still look like the longer-duration bet."
        )
    return (
        "the market move is concentrated in crypto spot and ETF trading exposure, while tokenized cash, "
        "stablecoins, and tokenization remain the structural through-line."
    )


def _week_in_brief_synthesis(
    crypto_pct: str,
    rail_pcts: list[str],
    etp_pct: str,
    week_headlines: list[Any],
) -> str:
    """Two-part executive takeaway: data interpretation, then market meaning."""
    crypto_n = _pct_value(crypto_pct)
    if crypto_n is None:
        return ""
    rail_vals = [v for p in rail_pcts if (v := _pct_value(p)) is not None]
    rails_flatish = bool(rail_vals) and all(abs(v) < _RAIL_FLAT_THRESHOLD for v in rail_vals)
    if crypto_n < -5 and rails_flatish:
        meaning = _synthesis_takeaway(week_headlines, rails_resilient=True)
        return f"On balance, on-chain rail metrics held steadier than crypto spot markets—{meaning}"
    if crypto_n < -5:
        meaning = _synthesis_takeaway(week_headlines, rails_resilient=False)
        return f"Crypto spot markets led the weekly move—{meaning}"
    return ""


def _week_in_brief_priority_row(
    label: str,
    body: str,
    *,
    is_last: bool = False,
    is_first: bool = False,
    outlook: bool = False,
) -> str:
    if outlook:
        if is_first:
            pad = "6px 0 10px"
            bullet_pad = "6px 0 10px"
        else:
            pad = "0" if is_last else "0 0 10px"
            bullet_pad = pad
        return (
            f"<tr>"
            f'<td style="padding:{bullet_pad};vertical-align:top;width:16px;color:{_OL_ACCENT};font-weight:700;'
            f'font-size:{_OL_TEXT_WIB};line-height:{_OL_LINE_HEADLINE};{_ol_font()}">•</td>'
            f'<td style="padding:{pad};vertical-align:top;font-size:{_OL_TEXT_WIB};line-height:{_OL_LINE};'
            f'mso-line-height-rule:exactly;color:{_COLOR_BODY};{_ol_font()}">'
            f'<strong style="color:{_COLOR_INK};font-weight:700;">{escape(label)}</strong> — {body}</td>'
            f"</tr>"
        )
    pad = "0" if is_last else "0 0 0.6rem"
    return (
        f"<tr>"
        f'<td style="padding:{pad};vertical-align:top;width:1rem;color:{_COLOR_BRAND};font-weight:700;'
        f'font-size:13px;line-height:1.55;">•</td>'
        f'<td style="padding:{pad};vertical-align:top;font-size:14px;line-height:1.65;color:{_COLOR_BODY};">'
        f'<strong style="color:{_COLOR_INK};">{escape(label)}</strong> — {body}</td>'
        f"</tr>"
    )


def _week_in_brief_html(
    crypto: dict[str, Any],
    etp: dict[str, Any],
    explore: dict[str, dict[str, Any]],
    week_headlines: list[Any],
    articles: list[dict[str, Any]] | None = None,
    fund_launches: dict[str, Any] | None = None,
    *,
    outlook: bool = False,
) -> str:
    crypto_pct = _fmt_pct((crypto.get("primary") or {}).get("delta", {}).get("pct"))
    etp_pct = _fmt_pct(etp.get("aggregate_pct"))
    tmmf_pct = _fmt_pct(_explore_kpi(explore, "tokenized_mmf", label_match="distributed").get("delta_30d_pct"))
    sc_pct = _fmt_pct(_explore_kpi(explore, "stablecoins", label_match="market cap").get("delta_30d_pct"))
    tre_pct = _fmt_pct(_explore_kpi(explore, "treasuries", label_match="distributed").get("delta_30d_pct"))

    tmmf_raw = _explore_kpi(explore, "tokenized_mmf", label_match="distributed").get("delta_30d_pct")
    sc_raw = _explore_kpi(explore, "stablecoins", label_match="market cap").get("delta_30d_pct")
    tre_raw = _explore_kpi(explore, "treasuries", label_match="distributed").get("delta_30d_pct")
    by_family = _headlines_by_family(week_headlines)
    launches = fund_launches or {}

    priorities: list[tuple[str, str]] = [
        (
            "Tokenized MMFs",
            _week_in_brief_bullet(
                "Institutional cash and settlement rail",
                tmmf_raw,
                "distributed value",
                _week_in_brief_watch_tmmf(
                    tmmf_pct,
                    by_family,
                    explore,
                    articles,
                    week_headlines,
                    fund_launch=launches.get("tmmf"),
                ),
            ),
        ),
        (
            "Stablecoins",
            _week_in_brief_bullet(
                "Payments and reserve infrastructure",
                sc_raw,
                "market cap",
                _week_in_brief_watch_stablecoins(
                    sc_pct, by_family, fund_launch=launches.get("stablecoin_reserve")
                ),
            ),
        ),
        (
            "RWA tokenization",
            _week_in_brief_bullet(
                "TradFi-to-on-chain bridge",
                tre_raw,
                "tokenized Treasuries",
                _week_in_brief_watch_rwa(tre_pct, crypto_pct, by_family),
            ),
        ),
        (
            "U.S. crypto ETFs",
            _week_in_brief_bullet(
                "Spot ETF AUM",
                etp.get("aggregate_pct"),
                "aggregate AUM",
                _week_in_brief_watch_etp(
                    etp, etp_pct, by_family, fund_launch=launches.get("crypto_etf")
                ),
                flat_threshold=1.0,
            ),
        ),
        (
            "Crypto prices",
            _week_in_brief_crypto_bullet(
                crypto_pct,
                _week_in_brief_watch_crypto(crypto_pct, [tmmf_pct, sc_pct, tre_pct], by_family),
            ),
        ),
    ]
    rows_html = "".join(
        _week_in_brief_priority_row(
            label, body, is_last=(i == len(priorities) - 1), is_first=(i == 0), outlook=outlook
        )
        for i, (label, body) in enumerate(priorities)
    )
    synthesis = _week_in_brief_synthesis(
        crypto_pct, [tmmf_pct, sc_pct, tre_pct], etp_pct, week_headlines
    )
    if outlook:
        synthesis_html = (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="margin:0;border-collapse:collapse;">'
            f'<tr><td style="padding:10px 13px;background:{_OL_SYNTHESIS_BG};'
            f'border-left:3px solid {_OL_SYNTHESIS_BORDER};">'
            f'<p style="margin:0;font-size:{_OL_TEXT_WIB};line-height:{_OL_LINE};mso-line-height-rule:exactly;'
            f'color:{_COLOR_BODY};{_ol_font()}">'
            f"{escape(synthesis)}</p></td></tr></table>"
            if synthesis
            else ""
        )
        synthesis_gap = (
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="border-collapse:collapse;"><tr><td height="10" style="height:10px;'
            'line-height:10px;font-size:1px;mso-line-height-rule:exactly;">&nbsp;</td></tr></table>'
            if synthesis
            else ""
        )
    else:
        synthesis_html = (
            f'<p style="margin:0 0 0.95rem;padding:0.65rem 0.8rem;background:#eef6fb;'
            f"border-left:3px solid {_COLOR_BRAND};border-radius:0 8px 8px 0;"
            f'font-size:14px;line-height:1.65;color:{_COLOR_BODY};">{escape(synthesis)}</p>'
            if synthesis
            else ""
        )
        synthesis_gap = ""
    inner = (
        f'{_ol_eyebrow("Week in brief", margin="0 0 9px") if outlook else _section_eyebrow("Week in brief", outlook=False)}'
        f"{synthesis_html}"
        f"{synthesis_gap if outlook else ''}"
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;">{rows_html}</table>'
    )
    return _callout_card(inner, outlook=outlook, outlook_pad="17px 18px" if outlook else None)


def build_newsletter_html(
    *,
    site_base: str = DEFAULT_SITE_BASE,
    variant: str = "standard",
    outlook_body: bool = False,
    force_legacy_takeaways: bool = False,
) -> tuple[str, datetime]:
    site = site_base.rstrip("/")
    generated: list[datetime] = []

    crypto = _read_json(DATA / "crypto_kpis.json") or {}
    etp = _read_json(DATA / "etp_kpis.json") or {}
    explore = _load_explore_sections()

    for payload in (crypto, etp):
        dt = _parse_iso_dt(payload.get("generated_at"))
        if dt:
            generated.append(dt)

    week_end = max(generated) if generated else datetime.now(timezone.utc)
    week_label = week_end.strftime("%-d %b %Y") if os.name != "nt" else week_end.strftime("%d %b %Y")

    try:
        from key_observations.feeds import load_takeaway_articles
        from key_observations.page_ko import build_legacy_page_ko
        from key_observations.week_headlines import (
            pick_executive_week_headlines_with_launches,
            pick_week_headlines_with_launches,
        )

        articles = load_takeaway_articles(max_items=200)
        is_executive = variant == "executive"
        if is_executive:
            week_headlines, fund_launches = pick_executive_week_headlines_with_launches(
                articles, n=3
            )
        else:
            week_headlines, fund_launches = pick_week_headlines_with_launches(articles, n=3)
        sc_ko = build_legacy_page_ko("stablecoins", articles)
        tre_ko = build_legacy_page_ko("us_treasuries", articles)
        stocks_ko = build_legacy_page_ko("tokenized_stocks", articles)
        rwa_global_ko = build_legacy_page_ko("rwa_global", articles)
    except Exception:
        articles = None
        week_headlines = []
        fund_launches = {}
        sc_ko = tre_ko = stocks_ko = rwa_global_ko = ""
        is_executive = variant == "executive"

    tmmf_ko = _load_tmmf_ko(articles)
    ol = bool(outlook_body and is_executive)
    max_bullets = 2 if is_executive else 3
    newsletter_used_links: set[str] = set()
    for pick in week_headlines:
        if pick.link:
            newsletter_used_links.add(str(pick.link).strip())
    shipped_leads: dict[str, list[str]] = {}
    section_base_kw = {
        "takeaways_label": "Key takeaways",
        "max_bullets": max_bullets,
        "articles": articles,
        "used_links": newsletter_used_links,
        "executive_news_only": is_executive,
        "explore": explore,
        "etp": etp,
        "crypto": crypto,
        "week_headlines": week_headlines,
        "shipped_leads": shipped_leads,
        "force_legacy_takeaways": force_legacy_takeaways,
    }
    headlines_block = _week_headlines_html(week_headlines, outlook=ol)

    # --- 1. TMMFs (matches home page order) ---
    tmmf_section = _section_block(
        "Tokenized money market funds",
        f"{site}/rwa-tokenized-mmf.html",
        _explore_kpi_cells(explore, "tokenized_mmf", outlook=ol),
        tmmf_ko,
        accent=_COLOR_BRAND,
        section_id="tmmf",
        section_divider=True,
        fund_launch=fund_launches.get("tmmf"),
        outlook=ol,
        **section_base_kw,
    )

    # --- 2. Stablecoins ---
    stable_section = _section_block(
        "Stablecoins",
        f"{site}/rwa-stablecoins.html",
        _explore_kpi_cells(explore, "stablecoins", outlook=ol),
        sc_ko,
        accent=_COLOR_BRAND,
        section_id="stablecoins",
        section_divider=True,
        fund_launch=fund_launches.get("stablecoin_reserve"),
        outlook=ol,
        **section_base_kw,
    )

    # --- 3. RWA on-chain (tokenization-focused takeaways) ---
    from rwa_global_page_payloads import RWA_GLOBAL_SCOPE_NOTE

    rwa_section = _section_block(
        "RWA — On-chain data",
        f"{site}/rwa-global.html",
        _load_rwa_global_kpi_cells(outlook=ol),
        "",
        accent=_COLOR_BRAND,
        section_id="rwa",
        ko_html_sources=(rwa_global_ko, tre_ko, stocks_ko),
        section_divider=True,
        outlook=ol,
        scope_note=RWA_GLOBAL_SCOPE_NOTE,
        **section_base_kw,
    )

    # --- 4. U.S. crypto ETPs ---
    etp_cells = "".join(
        [
            _kpi_row("Aggregate AUM", str(etp.get("total_aum_display") or "—"), _fmt_pct(etp.get("aggregate_pct")), outlook=ol),
            _kpi_row("30D net flow", str(etp.get("net_flow_1m_display") or "—"), _fmt_pct(etp.get("net_flow_1m_pct")), outlook=ol),
            _kpi_row(
                "IBIT AUM",
                str((etp.get("ibit") or {}).get("aum_display") or "—"),
                _fmt_pct((etp.get("ibit") or {}).get("delta", {}).get("pct")),
                is_last=True,
                outlook=ol,
            ),
        ]
    )
    etp_section = _section_block(
        "U.S. crypto ETPs",
        f"{site}/etps.html",
        etp_cells,
        str(etp.get("key_observations_html") or ""),
        accent=_COLOR_BRAND,
        section_id="etp",
        section_divider=True,
        fund_launch=fund_launches.get("crypto_etf"),
        outlook=ol,
        **section_base_kw,
    )

    # --- 5. Crypto prices ---
    crypto_cells = "".join(
        [
            _kpi_row(
                str(crypto.get("primary", {}).get("label") or "Total market cap"),
                str(crypto.get("primary", {}).get("value_display") or "—"),
                _fmt_pct((crypto.get("primary") or {}).get("delta", {}).get("pct")),
                outlook=ol,
            ),
            _kpi_row(
                str(crypto.get("btc_dominance", {}).get("label") or "BTC dominance"),
                str(crypto.get("btc_dominance", {}).get("value_display") or "—"),
                _fmt_pct((crypto.get("btc_dominance") or {}).get("delta", {}).get("pct")),
                outlook=ol,
            ),
            _kpi_row(
                str(crypto.get("stablecoin_share", {}).get("label") or "Stablecoin share"),
                str(crypto.get("stablecoin_share", {}).get("value_display") or "—"),
                _fmt_pct((crypto.get("stablecoin_share") or {}).get("delta", {}).get("pct")),
                is_last=True,
                outlook=ol,
            ),
        ]
    )
    crypto_section = _section_block(
        "Crypto prices",
        f"{site}/crypto-prices.html",
        crypto_cells,
        str(crypto.get("key_observations_html") or ""),
        accent=_COLOR_BRAND,
        section_id="crypto",
        section_divider=True,
        outlook=ol,
        **section_base_kw,
    )

    if is_executive:
        intro = ""
        intro_block = _week_in_brief_html(
            crypto, etp, explore, week_headlines, articles, fund_launches, outlook=ol
        )
        header_kicker = "Executive weekly brief"
        page_title = "Digital Assets Dashboard — Executive weekly brief"
        preview_text = "Executive weekly brief — tokenized cash, stablecoins, RWAs, ETPs, and crypto market context."
        mock_banner = ""
        footer_extra = ""
        footer_generation_html = ""
        disclaimer = (
            "Context only — not investment advice. Brief prepared from dashboard data and industry coverage; "
            "figures as of the week-ending date shown."
        )
    else:
        intro = (
            "KPIs and key takeaways from the live dashboard, grouped by asset class. "
            f"Figures reflect the latest export as of {week_label} (UTC)."
        )
        intro_block = _callout_card(
            _prose(escape(intro), margin="0", color=_COLOR_BODY),
            margin_bottom="1.4rem",
        )
        header_kicker = "Weekly snapshot"
        page_title = "Digital Assets Dashboard — Weekly snapshot"
        preview_text = "Weekly themes from the Digital Assets Dashboard — TMMFs, stablecoins, RWA, ETPs, and crypto."
        mock_banner = ""
        footer_extra = ""
        footer_generation_html = (
            f'<p style="margin:0;font-size:11px;line-height:1.6;color:#6b7c8f;">'
            f'Generated by <code style="font-size:10px;background:{_COLOR_INSET};padding:0.12rem 0.35rem;'
            f'border-radius:3px;color:{_COLOR_LABEL};">scripts/build_weekly_newsletter.py</code> from '
            f"committed dashboard JSON. Data sources match the live site (CoinPaprika, CoinGecko, "
            f"StockAnalysis, Farside, RWA.xyz, RSS).</p>"
        )
        disclaimer = (
            "Context only — not investment advice. Key observation bullets are AI-generated from on-page data "
            "and recent industry headlines; review for accuracy before sharing externally."
        )

    if ol:
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{escape(page_title)}</title>
</head>
<body style="margin:0;padding:16px;background:{_OL_SURFACE};{_ol_font()}color:{_COLOR_BODY};">
  <table role="presentation" width="{_OUTLOOK_WIDTH}" align="center" cellpadding="0" cellspacing="0" style="border-collapse:collapse;background:#ffffff;border:1px solid {_OL_CARD_BORDER};">
    <tr>
      <td style="padding:{_OL_PAD};background:{_COLOR_BRAND};color:#ffffff;">
        <p style="margin:0 0 6px;font-size:{_OL_TEXT_EYEBROW};letter-spacing:0.1em;text-transform:uppercase;color:#e2eef5;{_ol_font()}">{escape(header_kicker)}</p>
        <h1 style="margin:0;font-size:22px;font-weight:700;line-height:1.25;color:#ffffff;{_ol_font()}">Digital Assets Dashboard</h1>
        <p style="margin:8px 0 0;font-size:{_OL_TEXT_META};line-height:1.5;color:#e2eef5;{_ol_font()}">Week ending {escape(week_label)}</p>
      </td>
    </tr>
    <tr>
      <td style="padding:12px {_OL_PAD};background:{_OL_SURFACE};border-bottom:1px solid {_OL_BORDER};font-size:{_OL_TEXT_META};line-height:1.5;color:{_COLOR_MUTED};{_ol_font()}">
        Full formatted version is attached to this email.
      </td>
    </tr>
    <tr>
      <td style="padding:{_OL_PAD} {_OL_PAD} {_OL_GAP};">
        {intro_block}
        {headlines_block}
        {_dashboard_link_html(site, outlook=True)}
        {tmmf_section}
        {stable_section}
        {rwa_section}
        {etp_section}
        {crypto_section}
      </td>
    </tr>
    <tr>
      <td style="padding:{_OL_GAP_SM} {_OL_PAD};border-top:1px solid {_OL_DIVIDER};background:{_OL_SURFACE};font-size:{_OL_TEXT_META};line-height:1.55;color:{_COLOR_MUTED};{_ol_font()}">
        <strong style="color:{_COLOR_LABEL};">Disclaimer:</strong> {escape(disclaimer)}
      </td>
    </tr>
  </table>
</body>
</html>
"""
    else:
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <title>{escape(page_title)}</title>
</head>
<body style="margin:0;padding:0;background:#e9eef3;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;color:{_COLOR_BODY};">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
    {escape(preview_text)}
  </div>
  {mock_banner}
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#e9eef3;padding:30px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:{NEWSLETTER_MAX_WIDTH};background:#ffffff;border:1px solid #d0dae4;border-radius:12px;overflow:hidden;box-shadow:0 3px 10px rgba(26,61,92,0.07);">
          <tr>
            <td style="padding:1.4rem 1.45rem;background:{_COLOR_BRAND};color:#ffffff;">
              <p style="margin:0 0 0.45rem;font-size:11px;letter-spacing:0.13em;text-transform:uppercase;color:#e2eef5;">{escape(header_kicker)}</p>
              <h1 style="margin:0;font-size:23px;font-weight:700;line-height:1.2;letter-spacing:-0.02em;color:#ffffff;">Digital Assets Dashboard</h1>
              <p style="margin:0.65rem 0 0;font-size:13px;line-height:1.5;color:#e2eef5;">Week ending {escape(week_label)}</p>
            </td>
          </tr>
          <tr>
            <td style="padding:1.3rem 1.45rem 0.85rem;">
              {intro_block}
              {headlines_block}
              {_dashboard_link_html(site, outlook=False)}
              {tmmf_section}
              {stable_section}
              {rwa_section}
              {etp_section}
              {crypto_section}
            </td>
          </tr>
          <tr>
            <td style="padding:1.05rem 1.45rem 1.4rem;border-top:1px solid {_COLOR_LINE};background:{_COLOR_WASH};">
              <p style="margin:0 0 0.5rem;font-size:11px;line-height:1.6;color:{_COLOR_MUTED};">
                <strong style="color:{_COLOR_LABEL};">Disclaimer:</strong> {escape(disclaimer)}
              </p>
              {footer_extra}{footer_generation_html}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    if (
        not force_legacy_takeaways
        and _weekly_takeaways_active()
        and shipped_leads
    ):
        try:
            from key_observations.newsletter_week import record_shipped_leads

            record_shipped_leads(week_label=week_label, leads_by_section=shipped_leads)
        except Exception:
            pass
    return html, week_end


def main() -> None:
    parser = argparse.ArgumentParser(description="Build weekly newsletter HTML from static site data.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Standard newsletter output path")
    parser.add_argument(
        "--exec-out",
        type=Path,
        default=DEFAULT_EXEC_OUT,
        help="Executive newsletter output path",
    )
    parser.add_argument("--site-base", default=DEFAULT_SITE_BASE, help="Absolute site URL for links")
    parser.add_argument("--standard-only", action="store_true", help="Skip executive variant output")
    parser.add_argument(
        "--legacy-takeaways",
        action="store_true",
        help="Revert section Key takeaways to page KO scraping (disable weekly first-cut path).",
    )
    args = parser.parse_args()

    html, week_end = build_newsletter_html(
        site_base=args.site_base,
        variant="standard",
        force_legacy_takeaways=args.legacy_takeaways,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"Wrote {args.out} (week ending {week_end.date().isoformat()})")

    if not args.standard_only:
        exec_html, _ = build_newsletter_html(
            site_base=args.site_base,
            variant="executive",
            force_legacy_takeaways=args.legacy_takeaways,
        )
        args.exec_out.parent.mkdir(parents=True, exist_ok=True)
        args.exec_out.write_text(exec_html, encoding="utf-8")
        print(f"Wrote {args.exec_out} (executive variant)")


if __name__ == "__main__":
    main()
