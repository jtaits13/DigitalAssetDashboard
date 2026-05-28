"""Data-driven Key observations for the Tokenized MMF page."""

from __future__ import annotations

from collections import defaultdict
from html import escape
from typing import Any

from rwa_league.client import RwaTreasuryDistributedNetworkRow
from rwa_league.mmf import asset_distributed_value_usd

_INSTITUTIONAL_TICKERS: frozenset[str] = frozenset(
    {"BUIDL", "USYC", "iBENJI", "IBENJI", "BENJI", "OUSG", "uMINT", "USTBL", "CUMIU"}
)
_YIELD_TICKERS: frozenset[str] = frozenset(
    {"USDY", "EUTBL", "WTGXX", "CASH+", "UKTBL", "XFTB"}
)


def _holder_count(asset: dict[str, Any]) -> int | None:
    raw = asset.get("holding_addresses_count")
    if isinstance(raw, dict):
        v = raw.get("val")
        if isinstance(v, (int, float)) and v >= 0:
            return int(v)
    return None


def _investor_text(asset: dict[str, Any]) -> str:
    raw = asset.get("primary_market__investor_types")
    if isinstance(raw, list):
        parts = [str(x).strip() for x in raw if str(x).strip()]
        return ", ".join(parts)
    return str(raw or "").strip()


def _network_count(asset: dict[str, Any]) -> int:
    slugs: set[str] = set()
    for tok in asset.get("tokens") or []:
        if not isinstance(tok, dict):
            continue
        net = tok.get("network") or {}
        if isinstance(net, dict):
            slug = str(net.get("slug") or net.get("name") or "").strip()
            if slug:
                slugs.add(slug)
    return len(slugs)


def _fmt_usd_compact(n: float) -> str:
    x = float(n)
    if x >= 1e9:
        return f"${x / 1e9:.2f}B"
    if x >= 1e6:
        return f"${x / 1e6:.0f}M"
    if x >= 1e3:
        return f"${x / 1e3:.0f}K"
    return f"${x:,.0f}"


def _fmt_pp(delta: float | None) -> str:
    if delta is None:
        return "—"
    return f"{delta * 100:+.2f} pp"


def _bullet(lead: str, body: str) -> str:
    return f"<li><strong>{escape(lead)}</strong> {body}</li>"


def _regulatory_cluster(framework: str) -> str | None:
    fw = (framework or "").lower()
    if "reg. s" in fw or "reg s" in fw:
        return "U.S. Reg S"
    if "reg. d" in fw or "reg d" in fw:
        return "U.S. Reg D"
    if "ucits" in fw:
        return "UCITS"
    if "hong kong" in fw or "professional investor" in fw:
        return "Hong Kong PI"
    if "form n-1a" in fw or "mutual fund" in fw:
        return "U.S. mutual fund (N-1A)"
    return None


def _settlement_bullet(mmfs: list[dict[str, Any]], net_rows: list[RwaTreasuryDistributedNetworkRow]) -> str:
    candidates: list[tuple[float, str, int, float]] = []
    for asset in mmfs:
        aum = asset_distributed_value_usd(asset)
        holders = _holder_count(asset)
        if aum < 400e6 or not holders or holders < 10 or holders > 250:
            continue
        tick = str(asset.get("ticker") or "—").strip()
        candidates.append((aum / holders, tick, holders, aum))
    candidates.sort(reverse=True)
    eth_share = next(
        (r.market_share_raw for r in net_rows if "ethereum" in (r.network or "").lower()),
        None,
    )
    if not candidates:
        return _bullet(
            "TMMFs look like institutional cash rails:",
            "the largest funds in this population still show relatively concentrated on-chain holder bases versus broad retail distribution.",
        )
    examples = ", ".join(
        f"{escape(tick)} ({holders:,} holders, {_fmt_usd_compact(aum)}; ~{_fmt_usd_compact(ppu)}/holder)"
        for ppu, tick, holders, aum in [(c[0], c[1], c[2], c[3]) for c in candidates[:3]]
    )
    eth_bit = ""
    if eth_share is not None and eth_share >= 0.25:
        eth_bit = (
            f" Ethereum still carries ~{eth_share * 100:.0f}% of aggregated MMF network share, "
            "alongside selective deployment on chains used for institutional workflows."
        )
    return _bullet(
        "TMMFs are becoming a de facto settlement layer for institutions:",
        f"several of the largest funds combine very high AUM with small holder counts—e.g. {examples}—"
        f"suggesting on-chain cash and collateral rails rather than broad retail savings products.{eth_bit}",
    )


def _regulatory_bullet(mmfs: list[dict[str, Any]]) -> str:
    total = sum(asset_distributed_value_usd(a) for a in mmfs) or 1.0
    by_cluster: dict[str, float] = defaultdict(float)
    examples: dict[str, list[str]] = defaultdict(list)
    for asset in mmfs:
        cluster = _regulatory_cluster(str(asset.get("regulatory_framework") or ""))
        if not cluster:
            continue
        aum = asset_distributed_value_usd(asset)
        by_cluster[cluster] += aum
        tick = str(asset.get("ticker") or "").strip()
        if tick and len(examples[cluster]) < 3:
            examples[cluster].append(tick)
    if not by_cluster:
        return _bullet(
            "A global regulatory map is still forming:",
            "regulatory framework labels are sparse in this export; treat jurisdiction and investor-eligibility columns as the primary compliance signals.",
        )
    ranked = sorted(by_cluster.items(), key=lambda kv: -kv[1])[:3]
    parts: list[str] = []
    for cluster, aum in ranked:
        pct = aum / total * 100
        ex = ", ".join(escape(t) for t in examples.get(cluster, [])[:2])
        ex_bit = f" (e.g. {ex})" if ex else ""
        parts.append(f"<strong>{escape(cluster)}</strong> ~{pct:.0f}% of population AUM{ex_bit}")
    return _bullet(
        "A global regulatory arbitrage map is emerging:",
        "distributed value clusters into distinct compliance regimes—" + "; ".join(parts) + ". "
        "Issuers appear to anchor products in familiar safe harbors rather than one global standard.",
    )


def _network_shift_bullet(net_rows: list[RwaTreasuryDistributedNetworkRow]) -> str:
    with_delta = [r for r in net_rows if r.market_share_change_30d_raw is not None]
    if len(with_delta) < 3:
        return _bullet(
            "Network share is concentrated, with limited 30D shift data:",
            "use the By network table for current share levels; 30-day share change fields were not available for enough chains in this snapshot.",
        )
    gainers = sorted(with_delta, key=lambda r: r.market_share_change_30d_raw or 0, reverse=True)[:2]
    losers = sorted(with_delta, key=lambda r: r.market_share_change_30d_raw or 0)[:2]
    gain_txt = ", ".join(
        f"{escape(r.network)} ({_fmt_pp(r.market_share_change_30d_raw)} 30D share)"
        for r in gainers
    )
    loss_txt = ", ".join(
        f"{escape(r.network)} ({_fmt_pp(r.market_share_change_30d_raw)} 30D share)"
        for r in losers
    )
    return _bullet(
        "Early “flight to efficiency” shows up in 30D network share:",
        f"gainers include {gain_txt}; losers include {loss_txt}. "
        "That pattern is consistent with liquidity migrating toward higher-throughput, lower-fee chains—"
        "though Ethereum still dominates levels in most snapshots.",
    )


def _issuer_model_bullet(mmfs: list[dict[str, Any]]) -> str:
    rails: list[tuple[float, str]] = []
    yield_products: list[tuple[float, str]] = []
    for asset in mmfs:
        aum = asset_distributed_value_usd(asset)
        tick = str(asset.get("ticker") or "").strip()
        holders = _holder_count(asset)
        inv = _investor_text(asset).lower()
        if not tick or aum <= 0:
            continue
        is_rail = tick in _INSTITUTIONAL_TICKERS or (
            holders is not None and holders < 300 and aum >= 400e6
        )
        is_yield = tick in _YIELD_TICKERS or (
            holders is not None and holders >= 800
        ) or "retail" in inv or "ucits" in inv
        if is_rail and not is_yield:
            rails.append((aum, tick))
        elif is_yield:
            yield_products.append((aum, tick))
    rails.sort(reverse=True)
    yield_products.sort(reverse=True)
    if not rails and not yield_products:
        return _bullet(
            "Issuer strategies are diverging:",
            "concentration among a few large franchises remains, but labels in this export do not separate institutional rails vs retail-oriented products cleanly.",
        )
    rail_ex = ", ".join(escape(t) for _, t in rails[:4]) or "—"
    yield_ex = ", ".join(escape(t) for _, t in yield_products[:4]) or "—"
    return _bullet(
        "Issuer strategies are splitting into two models:",
        f"<em>Institutional cash rail</em> programs (low holder counts, large AUM per holder—e.g. {rail_ex}) "
        f"vs <em>global yield / distribution</em> products (broader holder bases, retail- or UCITS-friendly framing—e.g. {yield_ex}). "
        "These behave like different businesses under the same “tokenized MMF” label.",
    )


def _multichain_compliance_bullet(mmfs: list[dict[str, Any]]) -> str:
    odd: list[tuple[str, int, int, float]] = []
    for asset in mmfs:
        nets = _network_count(asset)
        holders = _holder_count(asset)
        aum = asset_distributed_value_usd(asset)
        tick = str(asset.get("ticker") or "").strip()
        if nets >= 3 and holders is not None and holders <= 12 and aum > 0:
            odd.append((tick, nets, holders, aum))
    odd.sort(key=lambda x: -x[3])
    if not odd:
        return _bullet(
            "Multi-chain deployment is selective:",
            "most AUM is not spread evenly across many chains; large funds tend to concentrate value on one or two networks.",
        )
    examples = ", ".join(
        f"{escape(t)} ({n} chains, {h} holders, {_fmt_usd_compact(a)})" for t, n, h, a in odd[:3]
    )
    return _bullet(
        "Multi-chain footprints often track compliance, not liquidity:",
        f"several funds list multiple networks while holder counts stay tiny—e.g. {examples}—"
        "which is more consistent with distribution or jurisdictional requirements than deep secondary-market liquidity on every chain.",
    )


def build_mmf_key_observations_html(
    mmfs: list[dict[str, Any]],
    net_rows: list[RwaTreasuryDistributedNetworkRow] | None = None,
) -> str:
    """
    Key observations HTML (inner ``div`` + ``ul`` + context note) from the current MMF population.
    Append ``monthly_review_note_class_html()`` for the review footnote on static pages.
    """
    if not mmfs:
        return ""

    nets = list(net_rows or [])
    bullets = [
        _settlement_bullet(mmfs, nets),
        _regulatory_bullet(mmfs),
        _network_shift_bullet(nets),
        _issuer_model_bullet(mmfs),
        _multichain_compliance_bullet(mmfs),
    ]
    items = "".join(bullets)
    return (
        '<div style="border:1px solid #C7D8E8;border-radius:10px;padding:0.75rem 0.95rem;'
        'margin:0.1rem 0 0.55rem;background:#ffffff;box-shadow:0 1px 3px rgba(15,23,42,0.06);">'
        f'<ul style="margin:0.1rem 0 0 1.05rem;padding:0;color:#1F4C67;font-size:0.9rem;line-height:1.45;">'
        f"{items}</ul>"
        '<p class="takeaways__note">Context only—not investment advice. Bullets are generated from the '
        "fund population and network aggregates on this page (RWA.xyz US Treasuries and Non-U.S. Government Debt lists).</p>"
        "</div>"
    )
