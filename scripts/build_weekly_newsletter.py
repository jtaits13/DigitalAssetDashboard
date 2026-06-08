#!/usr/bin/env python3
"""
Build a weekly digest HTML email from committed static_home/data JSON (KPIs + Key observations).

Usage:
  python scripts/build_weekly_newsletter.py
  python scripts/build_weekly_newsletter.py --out static_home/mockups/weekly-newsletter-email.html

Env:
  SITE_BASE_URL — absolute site root for CTA links (no trailing slash).
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
_STRONG_RE = re.compile(r"<strong>(.*?)</strong>", re.DOTALL | re.IGNORECASE)
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


_LI_STYLE = "margin:0 0 0.7rem;color:#243447;font-size:14px;line-height:1.6;"
_LI_STYLE_LAST = "margin:0;color:#243447;font-size:14px;line-height:1.6;"
_STRONG_STYLE = "color:#1a3d5c;"


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


def _polish_newsletter_lead(lead: str) -> tuple[str, str]:
    lead = re.sub(r"\s+", " ", lead).strip().rstrip(":")
    overflow = ""
    if _INDUSTRY_LEAD_RE.match(lead):
        topic = _INDUSTRY_LEAD_RE.sub("", lead).strip()
        return f"In the news · {topic}", ""
    if len(lead) > 90:
        lead, overflow = _split_long_lead(lead)
    return lead, overflow


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
    rest = re.sub(r"\s{2,}", " ", rest).strip()
    rest = re.sub(r"\.{2,}", ".", rest)
    rest = re.sub(r"\s+\.$", ".", rest)
    return _capitalize_rest(rest)


def _ko_li_email_html(chunk: str, *, is_last: bool = False) -> str:
    chunk = _LINK_RE.sub(r"\1", chunk)
    chunk = re.sub(r"</?em>", "", chunk, flags=re.IGNORECASE)
    sm = _STRONG_RE.search(chunk)
    body_parts: list[str] = []
    if sm:
        lead, lead_overflow = _polish_newsletter_lead(_strip_tags(sm.group(1)))
        body_parts.append(f'<strong style="{_STRONG_STYLE}">{escape(lead)}.</strong>')
        rest = _polish_newsletter_rest(lead, _strip_tags(chunk[sm.end() :]), lead_overflow=lead_overflow)
    else:
        rest = _polish_newsletter_rest("", _strip_tags(chunk))
    if rest:
        body_parts.append(escape(rest))
    li_style = _LI_STYLE_LAST if is_last else _LI_STYLE
    return f'<li style="{li_style}">{" ".join(body_parts)}</li>'


def _ko_bullets_html(html: str, *, max_items: int = 3) -> str:
    if not html or not str(html).strip():
        return ""
    chunks = [m.group(1).strip() for m in _LI_RE.finditer(html)][:max_items]
    if not chunks:
        return ""
    items = "".join(
        _ko_li_email_html(chunk, is_last=(i == len(chunks) - 1))
        for i, chunk in enumerate(chunks)
    )
    return f'<ul style="margin:0;padding:0 0 0 1.15rem;">{items}</ul>'


def _merged_ko_bullets_html(*html_sources: str, max_items: int = 3) -> str:
    seen: set[str] = set()
    chunks: list[str] = []
    for html in html_sources:
        for m in _LI_RE.finditer(html or ""):
            chunk = m.group(1).strip()
            key = re.sub(r"\s+", " ", _strip_tags(chunk)).strip().lower()
            if key and key not in seen:
                seen.add(key)
                chunks.append(chunk)
            if len(chunks) >= max_items:
                break
        if len(chunks) >= max_items:
            break
    if not chunks:
        return ""
    items = "".join(
        _ko_li_email_html(chunk, is_last=(i == len(chunks) - 1))
        for i, chunk in enumerate(chunks[:max_items])
    )
    return f'<ul style="margin:0;padding:0 0 0 1.15rem;">{items}</ul>'


def _kpi_row(label: str, value: str, delta: str, *, delta_color: str | None = None) -> str:
    dc = delta_color or ("#0d6b3a" if delta.startswith("+") else "#b42318" if delta.startswith("-") else "#4a5f73")
    return (
        f'<td style="padding:0.45rem 0.65rem;border:1px solid #e2e8f0;background:#fff;vertical-align:top;width:33%;">'
        f'<div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;">{escape(label)}</div>'
        f'<div style="font-size:17px;font-weight:600;color:#1a3d5c;margin-top:0.15rem;">{escape(value)}</div>'
        f'<div style="font-size:12px;color:{dc};margin-top:0.1rem;font-weight:600;">{escape(delta)} <span style="font-weight:400;color:#64748b;">30D</span></div>'
        f"</td>"
    )


def _week_headlines_html(picks: list[Any]) -> str:
    if not picks:
        return ""
    items: list[str] = []
    for i, pick in enumerate(picks, start=1):
        title = escape(str(pick.title))
        link = str(pick.link or "").strip()
        if link:
            title = (
                f'<a href="{escape(link, quote=True)}" style="color:#2a5f82;text-decoration:none;'
                f'font-weight:600;">{title}</a>'
            )
        meta = escape(str(pick.source or "Industry"))
        if int(pick.outlet_count) > 1:
            meta += f" · {int(pick.outlet_count)} sources"
        margin = "0" if i == len(picks) else "0 0 0.7rem"
        items.append(
            f'<li style="margin:{margin};color:#243447;font-size:14px;line-height:1.6;">'
            f'<span style="font-weight:700;color:#1a3d5c;">{i}.</span> {title}'
            f'<span style="display:block;font-size:12px;color:#64748b;margin-top:0.2rem;">{meta}</span>'
            f"</li>"
        )
    joined = "".join(items)
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 1.25rem;border-collapse:collapse;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;">
  <tr>
    <td style="padding:0.85rem 1rem;">
      <p style="margin:0 0 0.5rem;font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#64748b;">Headlines of the week</p>
      <ul style="margin:0;padding:0 0 0 1.15rem;">{joined}</ul>
    </td>
  </tr>
</table>
"""


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
) -> str:
    if ko_body_html is None:
        bullets = _ko_bullets_html(ko_html, max_items=max_bullets)
    else:
        bullets = ko_body_html
    body = bullets or '<p style="margin:0;color:#64748b;font-size:13px;">No key observations exported for this section.</p>'
    takeaways = (
        f'<p style="margin:0.85rem 0 0.5rem;font-size:11px;font-weight:700;letter-spacing:0.06em;'
        f'text-transform:uppercase;color:#64748b;">{escape(takeaways_label)}</p>{body}'
    )
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 1.35rem;border-collapse:collapse;">
  <tr>
    <td style="padding:0 0 0.45rem;border-bottom:3px solid {accent};">
      <h2 style="margin:0;font-size:16px;font-weight:700;color:#1a3d5c;">{escape(title)}</h2>
    </td>
  </tr>
  <tr><td style="height:0.65rem;font-size:0;line-height:0;">&nbsp;</td></tr>
  <tr>
    <td>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:0 0 0.75rem;">
        <tr>{kpi_cells}</tr>
      </table>
      {takeaways}
      <p style="margin:0.75rem 0 0;">
        <a href="{escape(page_href)}" style="color:{accent};font-weight:600;text-decoration:none;font-size:13px;">Open full page →</a>
      </p>
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


def _explore_kpi_cells(explore: dict[str, dict[str, Any]], section_id: str) -> str:
    sec = explore.get(section_id) or {}
    cells = ""
    for k in (sec.get("kpis") or [])[:3]:
        cells += _kpi_row(
            str(k.get("label") or "—"),
            str(k.get("value_display") or "—"),
            _fmt_pct(k.get("delta_30d_pct")),
        )
    return cells or _kpi_row("—", "—", "—")


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


def _week_in_brief_html(crypto: dict[str, Any], etp: dict[str, Any]) -> str:
    crypto_pct = _fmt_pct((crypto.get("primary") or {}).get("delta", {}).get("pct"))
    etp_pct = _fmt_pct(etp.get("aggregate_pct"))
    crypto_color = "#b42318" if crypto_pct.startswith("-") else "#0d6b3a" if crypto_pct.startswith("+") else "#4a5f73"
    etp_color = "#b42318" if etp_pct.startswith("-") else "#0d6b3a" if etp_pct.startswith("+") else "#4a5f73"
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 1.15rem;border-collapse:collapse;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;">
  <tr>
    <td style="padding:0.85rem 1rem;">
      <p style="margin:0 0 0.35rem;font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#64748b;">Week in brief</p>
      <p style="margin:0;font-size:14px;line-height:1.6;color:#1a3d5c;">
        Markets softened over the past month (crypto market cap <strong style="color:{crypto_color};">{escape(crypto_pct)}</strong>,
        U.S. crypto ETP AUM <strong style="color:{etp_color};">{escape(etp_pct)}</strong>) while institutional infrastructure kept advancing.
        Tokenized cash and Treasuries remain the durable growth story; this week&apos;s top headlines skew toward
        <strong>regulation, tokenization, and institutional infrastructure</strong> rather than daily price moves.
      </p>
    </td>
  </tr>
</table>
"""


def build_newsletter_html(
    *,
    site_base: str = DEFAULT_SITE_BASE,
    variant: str = "standard",
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
        from key_observations.week_headlines import pick_week_headlines

        articles = load_takeaway_articles(max_items=200)
        week_headlines = pick_week_headlines(articles, n=3)
        sc_ko = build_legacy_page_ko("stablecoins", articles)
        tre_ko = build_legacy_page_ko("us_treasuries", articles)
        stocks_ko = build_legacy_page_ko("tokenized_stocks", articles)
        rwa_global_ko = build_legacy_page_ko("rwa_global", articles)
    except Exception:
        articles = None
        week_headlines = []
        sc_ko = tre_ko = stocks_ko = rwa_global_ko = ""

    tmmf_ko = _load_tmmf_ko(articles)
    is_executive = variant == "executive"
    takeaways_label = "What this means" if is_executive else "Key takeaways"
    max_bullets = 2 if is_executive else 3
    section_kw = {"takeaways_label": takeaways_label, "max_bullets": max_bullets}
    headlines_block = _week_headlines_html(week_headlines)

    # --- 1. TMMFs (matches home page order) ---
    tmmf_section = _section_block(
        "Tokenized money market funds",
        f"{site}/rwa-tokenized-mmf.html",
        _explore_kpi_cells(explore, "tokenized_mmf"),
        tmmf_ko,
        accent="#2a5f82",
        **section_kw,
    )

    # --- 2. Stablecoins ---
    stable_section = _section_block(
        "Stablecoins",
        f"{site}/rwa-stablecoins.html",
        _explore_kpi_cells(explore, "stablecoins"),
        sc_ko,
        accent="#3d78a0",
        **section_kw,
    )

    # --- 3. RWA on-chain ---
    rwa_ko_body = _merged_ko_bullets_html(rwa_global_ko, tre_ko, stocks_ko, max_items=max_bullets)
    rwa_section = _section_block(
        "RWA — On-chain data",
        f"{site}/rwa-global.html",
        _explore_kpi_cells(explore, "treasuries"),
        "",
        accent="#2a5f82",
        ko_body_html=rwa_ko_body,
        **section_kw,
    )

    # --- 4. U.S. crypto ETPs ---
    etp_cells = "".join(
        [
            _kpi_row("Aggregate AUM", str(etp.get("total_aum_display") or "—"), _fmt_pct(etp.get("aggregate_pct"))),
            _kpi_row("30D net flow", str(etp.get("net_flow_1m_display") or "—"), _fmt_pct(etp.get("net_flow_1m_pct"))),
            _kpi_row(
                "IBIT AUM",
                str((etp.get("ibit") or {}).get("aum_display") or "—"),
                _fmt_pct((etp.get("ibit") or {}).get("delta", {}).get("pct")),
            ),
        ]
    )
    etp_section = _section_block(
        "U.S. crypto ETPs",
        f"{site}/etps.html",
        etp_cells,
        str(etp.get("key_observations_html") or ""),
        accent="#3d78a0",
        **section_kw,
    )

    # --- 5. Crypto prices ---
    crypto_cells = "".join(
        [
            _kpi_row(
                str(crypto.get("primary", {}).get("label") or "Total market cap"),
                str(crypto.get("primary", {}).get("value_display") or "—"),
                _fmt_pct((crypto.get("primary") or {}).get("delta", {}).get("pct")),
            ),
            _kpi_row(
                str(crypto.get("btc_dominance", {}).get("label") or "BTC dominance"),
                str(crypto.get("btc_dominance", {}).get("value_display") or "—"),
                _fmt_pct((crypto.get("btc_dominance") or {}).get("delta", {}).get("pct")),
            ),
            _kpi_row(
                str(crypto.get("stablecoin_share", {}).get("label") or "Stablecoin share"),
                str(crypto.get("stablecoin_share", {}).get("value_display") or "—"),
                _fmt_pct((crypto.get("stablecoin_share") or {}).get("delta", {}).get("pct")),
            ),
        ]
    )
    crypto_section = _section_block(
        "Crypto prices",
        f"{site}/crypto-prices.html",
        crypto_cells,
        str(crypto.get("key_observations_html") or ""),
        accent="#6e869e",
        **section_kw,
    )

    if is_executive:
        intro = ""
        intro_block = _week_in_brief_html(crypto, etp)
        header_kicker = "Executive weekly brief"
        page_title = "Digital Assets Dashboard — Executive weekly brief"
        preview_text = "Executive weekly brief — tokenized cash, stablecoins, RWAs, ETPs, and crypto market context."
        mock_banner = """
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#fef3c7;border-bottom:1px solid #fcd34d;">
    <tr>
      <td style="padding:0.45rem 1rem;font-size:12px;line-height:1.4;color:#92400e;text-align:center;">
        Design mock — Executive newsletter variant · mockups/weekly-newsletter-email-executive-mock.html
      </td>
    </tr>
  </table>"""
        footer_extra = (
            'Design mock — executive variant. Compare with '
            '<a href="weekly-newsletter-email.html" style="color:#2a5f82;">standard newsletter mock</a>. '
        )
        disclaimer = (
            "Context only — not investment advice. Brief prepared from dashboard data and industry coverage; "
            "figures as of the week-ending date shown."
        )
    else:
        intro = (
            "KPIs and key takeaways from the live dashboard, grouped by asset class. "
            f"Figures reflect the latest export as of {week_label} (UTC)."
        )
        intro_block = f'<p style="margin:0 0 1rem;font-size:14px;line-height:1.6;color:#334155;">{escape(intro)}</p>'
        header_kicker = "Weekly snapshot"
        page_title = "Digital Assets Dashboard — Weekly snapshot"
        preview_text = "Weekly themes from the Digital Assets Dashboard — TMMFs, stablecoins, RWA, ETPs, and crypto."
        mock_banner = ""
        footer_extra = ""
        disclaimer = (
            "Context only — not investment advice. Key observation bullets are AI-generated from on-page data "
            "and recent industry headlines; review for accuracy before sharing externally."
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <title>{escape(page_title)}</title>
</head>
<body style="margin:0;padding:0;background:#eef2f6;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;color:#243447;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
    {escape(preview_text)}
  </div>
  {mock_banner}
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2f6;padding:24px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:{NEWSLETTER_MAX_WIDTH};background:#ffffff;border:1px solid #d8e2ec;border-radius:12px;overflow:hidden;">
          <tr>
            <td style="padding:1.25rem 1.35rem;background:linear-gradient(135deg,#1a3d5c 0%,#2a5f82 100%);color:#ffffff;">
              <p style="margin:0 0 0.35rem;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;opacity:0.85;">{escape(header_kicker)}</p>
              <h1 style="margin:0;font-size:22px;font-weight:700;line-height:1.25;">Digital Assets Dashboard</h1>
              <p style="margin:0.55rem 0 0;font-size:13px;line-height:1.45;opacity:0.92;">Week ending {escape(week_label)} (UTC)</p>
            </td>
          </tr>
          <tr>
            <td style="padding:1.15rem 1.35rem 0.5rem;">
              {intro_block}
              {headlines_block}
              <p style="margin:0 0 1.25rem;">
                <a href="{escape(site)}/index.html" style="display:inline-block;background:#2a5f82;color:#ffffff;text-decoration:none;font-weight:600;font-size:13px;padding:0.55rem 1rem;border-radius:8px;">Open live dashboard</a>
              </p>
              {tmmf_section}
              {stable_section}
              {rwa_section}
              {etp_section}
              {crypto_section}
            </td>
          </tr>
          <tr>
            <td style="padding:0.85rem 1.35rem 1.25rem;border-top:1px solid #e2e8f0;background:#f8fafc;">
              <p style="margin:0 0 0.45rem;font-size:11px;line-height:1.45;color:#64748b;">
                <strong>Disclaimer:</strong> {escape(disclaimer)}
              </p>
              <p style="margin:0;font-size:11px;line-height:1.45;color:#64748b;">
                {footer_extra}Generated by <code style="font-size:10px;">scripts/build_weekly_newsletter.py</code> from committed dashboard JSON. Data sources match the live site (CoinPaprika, CoinGecko, StockAnalysis, Farside, RWA.xyz, RSS).
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
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
    args = parser.parse_args()

    html, week_end = build_newsletter_html(site_base=args.site_base, variant="standard")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"Wrote {args.out} (week ending {week_end.date().isoformat()})")

    if not args.standard_only:
        exec_html, _ = build_newsletter_html(site_base=args.site_base, variant="executive")
        args.exec_out.parent.mkdir(parents=True, exist_ok=True)
        args.exec_out.write_text(exec_html, encoding="utf-8")
        print(f"Wrote {args.exec_out} (executive variant)")


if __name__ == "__main__":
    main()
