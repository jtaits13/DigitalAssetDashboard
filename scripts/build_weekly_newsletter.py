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
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "static_home" / "data"
DEFAULT_OUT = ROOT / "static_home" / "mockups" / "weekly-newsletter-email.html"

DEFAULT_SITE_BASE = os.environ.get(
    "SITE_BASE_URL",
    "https://jtaits13.github.io/DigitalAssetDashboard",
).rstrip("/")

_LI_RE = re.compile(r"<li>(.*?)</li>", re.DOTALL | re.IGNORECASE)
_STRONG_RE = re.compile(r"<strong>(.*?)</strong>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


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


def _ko_bullets(html: str, *, max_items: int = 3) -> list[str]:
    if not html or not str(html).strip():
        return []
    out: list[str] = []
    for m in _LI_RE.finditer(html):
        chunk = m.group(1).strip()
        sm = _STRONG_RE.search(chunk)
        if sm:
            lead = _strip_tags(sm.group(1)).rstrip(":").strip()
            rest = _strip_tags(chunk[sm.end() :]).strip()
            text = f"{lead}: {rest}" if rest else lead
        else:
            text = _strip_tags(chunk)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append(text)
        if len(out) >= max_items:
            break
    return out


def _ko_bullets_html(html: str, *, max_items: int = 3) -> str:
    bullets = _ko_bullets(html, max_items=max_items)
    if not bullets:
        return ""
    items = "".join(
        f'<li style="margin:0 0 0.55rem;color:#243447;font-size:14px;line-height:1.5;">{escape(b)}</li>'
        for b in bullets
    )
    return f'<ul style="margin:0;padding:0 0 0 1.1rem;">{items}</ul>'


def _kpi_row(label: str, value: str, delta: str, *, delta_color: str | None = None) -> str:
    dc = delta_color or ("#0d6b3a" if delta.startswith("+") else "#b42318" if delta.startswith("-") else "#4a5f73")
    return (
        f'<td style="padding:0.45rem 0.65rem;border:1px solid #e2e8f0;background:#fff;vertical-align:top;width:33%;">'
        f'<div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;">{escape(label)}</div>'
        f'<div style="font-size:17px;font-weight:600;color:#1a3d5c;margin-top:0.15rem;">{escape(value)}</div>'
        f'<div style="font-size:12px;color:{dc};margin-top:0.1rem;font-weight:600;">{escape(delta)} <span style="font-weight:400;color:#64748b;">30D</span></div>'
        f"</td>"
    )


def _section_block(
    title: str,
    page_href: str,
    kpi_cells: str,
    ko_html: str,
    *,
    accent: str,
) -> str:
    bullets = _ko_bullets_html(ko_html, max_items=3)
    body = bullets or '<p style="margin:0;color:#64748b;font-size:13px;">No key observations exported for this section.</p>'
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
      {body}
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


def build_newsletter_html(*, site_base: str = DEFAULT_SITE_BASE) -> tuple[str, datetime]:
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

    # --- Crypto ---
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
    )

    # --- ETP ---
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
    )

    # --- Stablecoins ---
    sc = explore.get("stablecoins") or {}
    sc_kpis = sc.get("kpis") or []
    sc_cells = ""
    for k in sc_kpis[:3]:
        sc_cells += _kpi_row(
            str(k.get("label") or "—"),
            str(k.get("value_display") or "—"),
            _fmt_pct(k.get("delta_30d_pct")),
        )
    if not sc_cells:
        sc_cells = _kpi_row("Market cap", "—", "—")

    try:
        from key_observations.page_ko import build_legacy_page_ko
        from key_observations.feeds import load_takeaway_articles

        sc_ko = build_legacy_page_ko("stablecoins", load_takeaway_articles(max_items=80))
    except Exception:
        sc_ko = ""

    stable_section = _section_block(
        "Stablecoins",
        f"{site}/rwa-stablecoins.html",
        sc_cells,
        sc_ko,
        accent="#3d78a0",
    )

    # --- RWA bundle (treasuries + stocks + TMMF KPIs, treasuries KO) ---
    def _explore_kpi_cells(section_id: str) -> str:
        sec = explore.get(section_id) or {}
        cells = ""
        for k in (sec.get("kpis") or [])[:3]:
            cells += _kpi_row(
                str(k.get("label") or "—"),
                str(k.get("value_display") or "—"),
                _fmt_pct(k.get("delta_30d_pct")),
            )
        return cells or _kpi_row("—", "—", "—")

    try:
        from key_observations.page_ko import build_legacy_page_ko
        from key_observations.feeds import load_takeaway_articles

        arts = load_takeaway_articles(max_items=80)
        tre_ko = build_legacy_page_ko("us_treasuries", arts)
        stocks_ko = build_legacy_page_ko("tokenized_stocks", arts)
    except Exception:
        tre_ko = stocks_ko = ""

    tre_cells = _explore_kpi_cells("treasuries")
    rwa_ko = tre_ko + stocks_ko
    tre_section = _section_block(
        "RWA — U.S. Treasuries & tokenized stocks",
        f"{site}/rwa-global.html",
        tre_cells,
        rwa_ko,
        accent="#2a5f82",
    )

    tmmf = explore.get("tokenized_mmf") or {}
    tmmf_kpis = tmmf.get("kpis") or []
    tmmf_cells = ""
    for k in tmmf_kpis[:3]:
        tmmf_cells += _kpi_row(
            str(k.get("label") or "—"),
            str(k.get("value_display") or "—"),
            _fmt_pct(k.get("delta_30d_pct")),
        )
    tmmf_section = _section_block(
        "Tokenized money market funds",
        f"{site}/rwa-tokenized-mmf.html",
        tmmf_cells or _kpi_row("Distributed value", "—", "—"),
        "",
        accent="#2a5f82",
    )

    exec_summary = (
        f"Snapshot as of {week_label} (UTC). Crypto total market cap is "
        f"{crypto.get('primary', {}).get('value_display', '—')} "
        f"({_fmt_pct((crypto.get('primary') or {}).get('delta', {}).get('pct'))} over ~30D). "
        f"Listed U.S. crypto ETP aggregate AUM is {etp.get('total_aum_display', '—')} "
        f"({_fmt_pct(etp.get('aggregate_pct'))}). "
        f"On-chain stablecoin market cap is {(sc_kpis[0].get('value_display') if sc_kpis else '—')}."
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <title>Digital Assets Dashboard — Weekly snapshot</title>
</head>
<body style="margin:0;padding:0;background:#eef2f6;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;color:#243447;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">
    Weekly themes from the Digital Assets Dashboard — crypto, ETPs, stablecoins, and RWA.
  </div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2f6;padding:24px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;background:#ffffff;border:1px solid #d8e2ec;border-radius:12px;overflow:hidden;">
          <tr>
            <td style="padding:1.25rem 1.35rem;background:linear-gradient(135deg,#1a3d5c 0%,#2a5f82 100%);color:#ffffff;">
              <p style="margin:0 0 0.35rem;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;opacity:0.85;">Weekly snapshot</p>
              <h1 style="margin:0;font-size:22px;font-weight:700;line-height:1.25;">Digital Assets Dashboard</h1>
              <p style="margin:0.55rem 0 0;font-size:13px;line-height:1.45;opacity:0.92;">Week ending {escape(week_label)} (UTC)</p>
            </td>
          </tr>
          <tr>
            <td style="padding:1.15rem 1.35rem 0.5rem;">
              <p style="margin:0 0 1rem;font-size:14px;line-height:1.55;color:#334155;">{escape(exec_summary)}</p>
              <p style="margin:0 0 1.25rem;">
                <a href="{escape(site)}/index.html" style="display:inline-block;background:#2a5f82;color:#ffffff;text-decoration:none;font-weight:600;font-size:13px;padding:0.55rem 1rem;border-radius:8px;">Open live dashboard</a>
              </p>
              {crypto_section}
              {etp_section}
              {stable_section}
              {tre_section}
              {tmmf_section}
            </td>
          </tr>
          <tr>
            <td style="padding:0.85rem 1.35rem 1.25rem;border-top:1px solid #e2e8f0;background:#f8fafc;">
              <p style="margin:0 0 0.45rem;font-size:11px;line-height:1.45;color:#64748b;">
                <strong>Disclaimer:</strong> Context only — not investment advice. Key observation bullets are AI-generated from on-page data and recent industry headlines; review for accuracy before sharing externally.
              </p>
              <p style="margin:0;font-size:11px;line-height:1.45;color:#64748b;">
                Generated by <code style="font-size:10px;">scripts/build_weekly_newsletter.py</code> from committed dashboard JSON. Data sources match the live site (CoinPaprika, CoinGecko, StockAnalysis, Farside, RWA.xyz, RSS).
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
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output HTML path")
    parser.add_argument("--site-base", default=DEFAULT_SITE_BASE, help="Absolute site URL for links")
    args = parser.parse_args()

    html, week_end = build_newsletter_html(site_base=args.site_base)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"Wrote {args.out} (week ending {week_end.date().isoformat()})")


if __name__ == "__main__":
    main()
