"""Data-driven Key observations for the U.S. ETP page."""

from __future__ import annotations

from html import escape
from typing import Any

from crypto_etps.client import CryptoEtpRow, format_usd_compact, has_listed_aum_usd
from key_observations import build_key_observations_html
from key_observations.models import ObservationCandidate

_SEC_SPOT_BTC_ETPS_ORDER_URL = "https://www.sec.gov/files/rules/sro/nysearca/2024/34-99306.pdf"
_SEC_OPTIONS_APPROVAL_URL = "https://www.sec.gov/files/rules/sro/cboebzx/2024/34-101224.pdf"
_DL_NEWS_BTC_ETF_AUM_SCENARIO_URL = (
    "https://www.dlnews.com/articles/markets/bitcoin-etfs-to-top-180-billion-usd-in-2026-say-analysts/"
)
_CF_BENCHMARKS_FILINGS_WAVE_URL = (
    "https://www.cfbenchmarks.com/blog/what-a-huge-wall-of-filings-tells-us-about-the-next-wave-of-us-crypto-etfs"
)

_SPOT_BTC_SYMBOLS: frozenset[str] = frozenset(
    {
        "IBIT",
        "FBTC",
        "GBTC",
        "ARKB",
        "BITB",
        "HODL",
        "BRRR",
        "EZBC",
        "BTCO",
        "BTCW",
        "DEFI",
    }
)

_ETP_CONTEXT_NOTE = (
    "Context for strategy only (not investment advice). Bullets rank listed fund data, Farside flow KPIs, "
    "and recent ETF/ETP headlines on this page."
)


def _listed_aum_rows(rows: list[CryptoEtpRow]) -> list[tuple[float, str, str]]:
    out: list[tuple[float, str, str]] = []
    for row in rows:
        if not has_listed_aum_usd(row.assets_usd):
            continue
        sym = str(row.symbol or "").strip().upper()
        if not sym:
            continue
        out.append((float(row.assets_usd), sym, str(row.name or sym).strip()))
    return out


def _spot_btc_aum(rows: list[CryptoEtpRow]) -> float:
    total = 0.0
    for row in rows:
        sym = str(row.symbol or "").strip().upper()
        if sym not in _SPOT_BTC_SYMBOLS or not has_listed_aum_usd(row.assets_usd):
            continue
        total += float(row.assets_usd)
    return total


def _market_sizing_candidate(rows: list[CryptoEtpRow]) -> ObservationCandidate:
    btc_aum = _spot_btc_aum(rows)
    today_bit = (
        f"about <strong>{escape(format_usd_compact(btc_aum))}</strong> across U.S. spot Bitcoin ETPs on this page today"
        if btc_aum > 0
        else "today’s listed spot Bitcoin ETP AUM on this page"
    )
    return ObservationCandidate(
        id="etp_market_sizing",
        lead="Forward market-size scenarios are large, but still assumptions-driven:",
        body=(
            "Public analyst commentary continues to frame the next few years in a broad range—for example, one "
            "widely cited 2026 scenario set points to roughly <strong>$180B–$220B</strong> for Bitcoin ETF assets, "
            f"compared with {today_bit} (see "
            f'<a href="{escape(_DL_NEWS_BTC_ETF_AUM_SCENARIO_URL, quote=True)}" target="_blank" '
            'rel="noopener noreferrer">DL News summary of analyst estimates</a>). '
            "Treat these as directional planning ranges, not a base-case forecast."
        ),
        score=78.0,
        themes=("market_sizing", "etf_flows"),
        source="data",
    )


def _launch_pipeline_candidate(rows: list[CryptoEtpRow]) -> ObservationCandidate:
    listed = len(rows)
    listed_bit = (
        f"This page lists <strong>{listed}</strong> U.S. crypto ETPs; "
        if listed
        else ""
    )
    return ObservationCandidate(
        id="etp_launch_pipeline",
        lead="The launch pipeline is crowded:",
        body=(
            f"{listed_bit}industry filing trackers and analyst snapshots still cite "
            "<strong>120+ crypto ETP filings</strong> in the U.S. queue (example: "
            f'<a href="{escape(_CF_BENCHMARKS_FILINGS_WAVE_URL, quote=True)}" target="_blank" '
            'rel="noopener noreferrer">CF Benchmarks, citing Bloomberg analysts</a>). '
            "Filing volume does <strong>not</strong> mean all products launch or scale, but it does point to a "
            "heavier near-term slate of spot and spot-adjacent product attempts."
        ),
        score=76.0,
        themes=("launch_pipeline",),
        source="data",
    )


def _concentration_candidate(rows: list[CryptoEtpRow]) -> ObservationCandidate:
    aum_rows = _listed_aum_rows(rows)
    total = sum(a for a, _, _ in aum_rows) or 1.0
    top = sorted(aum_rows, key=lambda x: -x[0])[:3]
    top_share = sum(a for a, _, _ in top) / total * 100.0
    examples = ", ".join(
        f"{escape(sym)} ({escape(format_usd_compact(aum))})" for aum, sym, _ in top
    )
    return ObservationCandidate(
        id="etp_concentration",
        lead="Product access expanded quickly, then concentrated:",
        body=(
            f"U.S. spot Bitcoin ETP approvals in 2024 (see "
            f'<a href="{escape(_SEC_SPOT_BTC_ETPS_ORDER_URL, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">SEC order</a>) widened listed access fast—yet the top three funds '
            f"still carry about <strong>{top_share:.0f}%</strong> of listed AUM here ({examples}). "
            "For allocators and service providers, scale and distribution economics now matter at least as much "
            "as first-mover timing."
        ),
        score=64.0 + min(10.0, top_share / 8.0),
        themes=("concentration", "regulation"),
        source="data",
    )


def _flow_candidate(
    *,
    net_flow_1m_display: str,
    net_flow_1m_pct: float | None,
) -> ObservationCandidate | None:
    if not net_flow_1m_display or net_flow_1m_display.strip() in ("—", "-", ""):
        return None
    pct_bit = ""
    if net_flow_1m_pct is not None:
        pct_bit = f" (<strong>{net_flow_1m_pct:+.1f}%</strong> vs the prior 30-day window on Farside BTC/ETH spot ETFs)"
    return ObservationCandidate(
        id="etp_flows",
        lead="Recent spot ETF flows are visible in the KPI strip:",
        body=(
            f"Aggregate <strong>30-day net flow</strong> for listed BTC/ETH spot products is "
            f"<strong>{escape(net_flow_1m_display.strip())}</strong>{pct_bit}. "
            "Flow momentum often shows up in IBIT/ETHA AUM and the aggregate chart before the full table reprices."
        ),
        score=58.0,
        themes=("etf_flows",),
        source="data",
    )


def _market_structure_candidate() -> ObservationCandidate:
    return ObservationCandidate(
        id="etp_market_structure",
        lead="Market structure is maturing around liquidity tools:",
        body=(
            "U.S. exchange-listed spot Bitcoin options ("
            f'<a href="{escape(_SEC_OPTIONS_APPROVAL_URL, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">SEC approval order</a>) improve hedging and risk transfer around spot ETPs, '
            "which can influence advisor suitability frameworks, institutional implementation, and trading-desk "
            "workflow design."
        ),
        score=52.0,
        themes=("regulation",),
        source="data",
    )


def etp_data_candidates(
    rows: list[CryptoEtpRow],
    *,
    net_flow_1m_display: str = "—",
    net_flow_1m_pct: float | None = None,
) -> list[ObservationCandidate]:
    pool: list[ObservationCandidate] = [
        _market_sizing_candidate(rows),
        _launch_pipeline_candidate(rows),
        _concentration_candidate(rows),
        _market_structure_candidate(),
    ]
    flow = _flow_candidate(
        net_flow_1m_display=net_flow_1m_display,
        net_flow_1m_pct=net_flow_1m_pct,
    )
    if flow:
        pool.append(flow)
    return pool


def build_etp_key_observations_html(
    rows: list[CryptoEtpRow],
    *,
    net_flow_1m_display: str = "—",
    net_flow_1m_pct: float | None = None,
    aggregate_pct: float | None = None,
    total_aum_display: str = "—",
    articles: list[dict[str, Any]] | None = None,
) -> str:
    if not rows:
        return ""
    from key_observations.page_blend import blend_page_ko_candidates

    framing = etp_data_candidates(
        rows,
        net_flow_1m_display=net_flow_1m_display,
        net_flow_1m_pct=net_flow_1m_pct,
    )
    etp_ctx = {
        "net_flow_1m_display": net_flow_1m_display,
        "net_flow_1m_pct": net_flow_1m_pct,
        "aggregate_pct": aggregate_pct,
        "total_aum_display": total_aum_display,
    }
    data, pins = blend_page_ko_candidates("etp", framing, etp=etp_ctx)
    # Keep one structural framing pin behind the WoW read when no WoW pin landed.
    if not pins:
        pins = ("etp_market_sizing", "etp_launch_pipeline")
    elif "etp_market_sizing" not in pins:
        pins = pins + ("etp_market_sizing",)
    return build_key_observations_html(
        "etp",
        data,
        articles,
        context_note=_ETP_CONTEXT_NOTE,
        min_bullets=3,
        max_bullets=5,
        pin_candidate_ids=pins,
    )
