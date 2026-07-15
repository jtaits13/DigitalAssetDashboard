"""Page-specific analysis linking headline themes back to each deep page."""

from __future__ import annotations

# Map Streamlit / export topic ids to the theme registry key when they differ.
TOPIC_THEME_KEY: dict[str, str] = {
    "participants_networks": "participants",
    "participants_platforms": "participants",
    "participants_asset_managers": "participants",
}

# (topic_key, theme_id) -> market takeaway that extends the declarative lead
# (no "watch/compare" instructions; no restatement of the lead).
PAGE_THEME_INTERPRETATIONS: dict[tuple[str, str], str] = {
    # US Treasuries
    ("us_treasuries", "tokenized_treasuries"): (
        "That usually shows up first as new issuer and product supply, then as higher distributed value "
        "and denser collateral-style use across networks and platforms."
    ),
    ("us_treasuries", "regulation"): (
        "Clearer rules tend to unlock balance-sheet participation and collateral workflows even when "
        "aggregate on-chain totals reprice slowly."
    ),
    ("us_treasuries", "institutional_adoption"): (
        "Bank and asset-manager distribution deals often shift platform and network leadership before "
        "headline RWA totals fully catch up."
    ),
    # Tokenized MMF
    ("tokenized_mmf", "institutional_settlement"): (
        "Funds that combine large AUM with small holder bases usually look more like on-chain "
        "operating cash than retail savings products."
    ),
    ("tokenized_mmf", "regulation"): (
        "Similar funds can sit under different investor-eligibility and jurisdiction labels, so "
        "compliance framing still decides who can hold and distribute them."
    ),
    ("tokenized_mmf", "chain_efficiency"): (
        "Fee and throughput advantages can pull 30D network-share toward the chains that keep "
        "settlement cheaper and more operationally reliable."
    ),
    ("tokenized_mmf", "issuer_models"): (
        "The market is still bifurcating: institutional settlement wrappers concentrate AUM in "
        "few holders, while retail-leaning yield products stay more holder-dispersed."
    ),
    ("tokenized_mmf", "rates_yields"): (
        "Rate and money-market moves can reshape fund-level inflows as quickly as any chain "
        "or product launch story."
    ),
    ("tokenized_mmf", "multichain"): (
        "Funds listing many networks with thin holder counts usually signal jurisdictional or "
        "distribution reach, not deep secondary liquidity on every chain."
    ),
    # Stablecoins
    ("stablecoins", "stablecoin_policy"): (
        "Issuer and platform share can shift before aggregate market cap does, because policy "
        "and reserve quality determine which names institutions will hold."
    ),
    ("stablecoins", "bank_integration"): (
        "That pushes demand toward treasury and settlement use cases, not only exchange trading "
        "liquidity."
    ),
    # Tokenized stocks
    ("tokenized_stocks", "tokenized_equities"): (
        "Liquidity and scale stay concentrated until broker distribution and custody plumbing "
        "can support broader trading."
    ),
    ("tokenized_stocks", "regulation"): (
        "Securities and broker-rule constraints often set the pace more than listing count, "
        "so near-term share stays tied to venues that can actually distribute products."
    ),
    # Crypto prices
    ("crypto", "market_structure"): (
        "Bitcoin-led tapes usually concentrate gains in majors, while alt-led breadth shows up "
        "as wider category participation across the top-50."
    ),
    ("crypto", "regulation"): (
        "Enforcement and legislation shocks tend to pull risk into majors first, while higher-beta "
        "categories retrace until policy clarity returns."
    ),
    ("crypto", "etf_flows"): (
        "Listed-product demand usually hits Bitcoin first, then filters into broader market beta "
        "if primary-market creations stay firm."
    ),
    # U.S. ETPs
    ("etp", "etf_flows"): (
        "Net flow prints often lead AUM changes, so listed-channel demand shows up in the KPI "
        "strip before long-run fund-table balances fully reset."
    ),
    ("etp", "market_sizing"): (
        "Analyst brackets are useful for planning ranges; live spot Bitcoin ETP AUM and the "
        "aggregate trend show whether those scenarios are still on path."
    ),
    ("etp", "launch_pipeline"): (
        "Most filings will not scale, but active pipelines still foreshadow which issuers and "
        "custodians will compete hardest for the next wave of listings."
    ),
    ("etp", "regulation"): (
        "Approval and listing decisions set the feasible product set on U.S. exchanges, so "
        "issuers already in the fund table have a structural advantage when new access opens."
    ),
    ("etp", "concentration"): (
        "Mega-fund share still drives distribution economics; attention on the largest wrappers "
        "usually matters more than incremental niche listings."
    ),
    # RWA global
    ("rwa_global", "tokenization_growth"): (
        "Network rank and share often shift first as new issuers pick distribution rails, before "
        "headline RWA totals fully reprice."
    ),
    ("rwa_global", "macro_rates"): (
        "Higher yield and collateral demand usually favor Treasury- and cash-like RWAs relative "
        "to more speculative tokenized categories."
    ),
    # Participants (networks / platforms / asset managers share themes)
    ("participants", "infrastructure"): (
        "Issuer and custody integrations named in coverage often show up in participant rankings "
        "before category-level RWA totals move."
    ),
}

# Extra nuance when participant sub-pages reuse the shared ``participants`` themes.
PARTICIPANT_PAGE_INTERPRETATIONS: dict[tuple[str, str], str] = {
    ("participants_networks", "infrastructure"): (
        "Chains that win custody and issuance integrations usually pull distributed value share "
        "before the broader RWA market total catches up."
    ),
    ("participants_platforms", "infrastructure"): (
        "Stacks that win issuer workflow and distribution partnerships tend to climb platform "
        "rank ahead of category-level RWA totals."
    ),
    ("participants_asset_managers", "infrastructure"): (
        "Large-manager launches and migrations move slowly but often re-anchor category momentum "
        "in this table before the broader market reprices."
    ),
}

# Shared theme fallbacks when a page-specific line is missing.
_THEME_FALLBACKS: dict[str, str] = {
    "regulation": (
        "Clearer permissioning can unlock who may hold and distribute products, while ambiguity "
        "keeps more institutional capital on the sidelines."
    ),
    "institutional_adoption": (
        "Named bank and asset-manager commitments often show up as share and ranking shifts "
        "before aggregate category totals fully reprice."
    ),
    "infrastructure": (
        "Custody and issuance integrations usually move network and platform rankings first, "
        "with category-level AUM following later."
    ),
}


def resolve_topic_key(topic: str) -> str:
    return TOPIC_THEME_KEY.get(topic, topic)


def page_theme_interpretation(topic: str, theme_id: str) -> str:
    """Market takeaway that extends a declarative news lead for this page."""
    if (topic, theme_id) in PARTICIPANT_PAGE_INTERPRETATIONS:
        return PARTICIPANT_PAGE_INTERPRETATIONS[(topic, theme_id)]
    topic_key = resolve_topic_key(topic)
    if (topic_key, theme_id) in PAGE_THEME_INTERPRETATIONS:
        return PAGE_THEME_INTERPRETATIONS[(topic_key, theme_id)]
    if theme_id in _THEME_FALLBACKS:
        return _THEME_FALLBACKS[theme_id]
    return (
        "That kind of coverage can still shift rank, share, and concentration on this page "
        "before aggregate totals fully reprice."
    )
