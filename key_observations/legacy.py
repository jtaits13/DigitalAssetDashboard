"""Baseline observation candidates (editorial fallbacks when data/news scores are low)."""

from __future__ import annotations

from key_observations.models import ObservationCandidate

_LEGACY: dict[str, list[tuple[str, str, str, float, tuple[str, ...]]]] = {
    "us_treasuries": [
        (
            "legacy_treasuries_bridge",
            "Tokenized U.S. Treasuries remain the institutional bridge into RWAs:",
            "adoption is strongest where products plug into cash management, collateral, and liquidity workflows.",
            40.0,
            ("tokenized_treasuries", "institutional_adoption"),
        ),
        (
            "legacy_treasuries_distribution",
            "Distribution still drives outcomes:",
            "network/platform leadership generally follows issuer reach, treasury utility, and integration quality more than feature novelty.",
            38.0,
            ("tokenized_treasuries",),
        ),
    ],
    "stablecoins": [
        (
            "legacy_sc_concentration",
            "Stablecoin market structure remains concentration-led:",
            "leadership is still defined by a small set of large issuers/platforms; share shifts matter as much as aggregate market-cap growth.",
            40.0,
            ("stablecoin_policy",),
        ),
        (
            "legacy_sc_institutional",
            "Institutional relevance continues to rise:",
            "policy and bank-integration pathways increasingly frame stablecoins as payment and treasury infrastructure—not only crypto trading liquidity.",
            39.0,
            ("bank_integration", "stablecoin_policy"),
        ),
    ],
    "tokenized_stocks": [
        (
            "legacy_stocks_early",
            "Tokenized stocks remain an early-stage lane:",
            "liquidity and scale are still concentrated in a small set of platforms/networks.",
            39.0,
            ("tokenized_equities",),
        ),
        (
            "legacy_stocks_plumbing",
            "Near-term progress depends on market plumbing:",
            "broader growth is likely to hinge on broker distribution, custody confidence, and venue interoperability rather than listing count alone.",
            38.0,
            ("tokenized_equities", "regulation"),
        ),
    ],
    "participants_networks": [
        (
            "legacy_pnet_concentration",
            "RWA value remains network-concentrated:",
            "the top chains continue to capture the majority of distributed issuance and often set near-term market direction.",
            40.0,
            ("infrastructure",),
        ),
        (
            "legacy_pnet_staged",
            "Institutional expansion is likely staged:",
            "large-scale adoption typically lands on proven networks first, then broadens as compliance, interoperability, and liquidity deepen.",
            38.0,
            ("infrastructure", "institutional_adoption"),
        ),
    ],
    "participants_platforms": [
        (
            "legacy_pplat_distribution",
            "Platform competition is increasingly distribution-led:",
            "partnership depth and channel reach are becoming stronger share drivers than technical differentiation alone.",
            40.0,
            ("infrastructure",),
        ),
        (
            "legacy_pplat_scale",
            "Scale tends to reinforce itself:",
            "once platforms establish issuer and liquidity depth, they often capture a disproportionate share of incremental distributed value.",
            38.0,
            ("infrastructure",),
        ),
    ],
    "participants_asset_managers": [
        (
            "legacy_pam_topheavy",
            "Asset-manager participation remains top-heavy:",
            "a smaller set of large managers still accounts for most distributed value and often anchors category momentum.",
            40.0,
            ("infrastructure", "institutional_adoption"),
        ),
        (
            "legacy_pam_distribution",
            "Share shifts are usually distribution-sensitive:",
            "advisor access, custody confidence, and repeat issuance cadence are key drivers of manager-level position changes.",
            38.0,
            ("infrastructure",),
        ),
    ],
}


def legacy_candidates_for_topic(topic: str) -> list[ObservationCandidate]:
    rows = _LEGACY.get(topic, ())
    return [
        ObservationCandidate(
            id=row_id,
            lead=lead,
            body=body,
            score=score,
            themes=themes,
            source="data",
        )
        for row_id, lead, body, score, themes in rows
    ]
