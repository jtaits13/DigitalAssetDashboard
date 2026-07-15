"""Page-specific analysis linking headline themes back to each deep page."""

from __future__ import annotations

# Map Streamlit / export topic ids to the theme registry key when they differ.
TOPIC_THEME_KEY: dict[str, str] = {
    "participants_networks": "participants",
    "participants_platforms": "participants",
    "participants_asset_managers": "participants",
}

# (topic_key, theme_id) -> interpretive sentence(s) for the bullet body.
PAGE_THEME_INTERPRETATIONS: dict[tuple[str, str], str] = {
    # US Treasuries
    ("us_treasuries", "tokenized_treasuries"): (
        "New issuance and product headlines often mark where tokenized T-bill supply is expanding—"
        "watch whether that shows up in distributed value, network share, and collateral-oriented use on this page."
    ),
    ("us_treasuries", "regulation"): (
        "Increased regulatory clarity for tokenized Treasuries could accelerate institutional adoption "
        "and collateral workflows, even when aggregate on-chain totals move gradually."
    ),
    ("us_treasuries", "institutional_adoption"): (
        "Major-bank and asset-manager coverage usually precedes distribution wins—"
        "platform and network leadership here may shift as those integrations scale."
    ),
    # Tokenized MMF
    ("tokenized_mmf", "institutional_settlement"): (
        "Settlement and cash-rail headlines align with funds that combine large AUM with small holder bases—"
        "compare with the funds table and whether issuers are positioning products as on-chain liquidity, not retail savings."
    ),
    ("tokenized_mmf", "regulation"): (
        "Cross-border compliance stories often explain why similar funds sit under different regulatory labels—"
        "jurisdiction and investor-eligibility columns on this page are the practical read-through."
    ),
    ("tokenized_mmf", "chain_efficiency"): (
        "Fee and throughput narratives frequently foreshadow 30D network-share migration among tokenized funds—"
        "check whether gainers in the By network table match the chains named in coverage."
    ),
    ("tokenized_mmf", "issuer_models"): (
        "Issuer strategy coverage can clarify whether the market is bifurcating into institutional rails vs retail yield products—"
        "holder counts and AUM per holder in the funds table help validate that split."
    ),
    ("tokenized_mmf", "rates_yields"): (
        "Fed and money-market yield stories can reshape inflows across tokenized MMFs—"
        "rate moves may matter as much as chain choice for near-term fund-level AUM."
    ),
    ("tokenized_mmf", "multichain"): (
        "Multi-chain deployment headlines often reflect compliance and distribution requirements rather than deep liquidity on every chain—"
        "compare with funds that list many networks but very few holders."
    ),
    # Stablecoins
    ("stablecoins", "stablecoin_policy"): (
        "Reserve and policy headlines can reprice which stablecoins issuers prioritize—"
        "platform concentration on this page may shift before aggregate stablecoin market cap does."
    ),
    ("stablecoins", "bank_integration"): (
        "Bank and payments integration stories usually frame stablecoins as treasury and settlement infrastructure—"
        "relevant for institutional use cases beyond exchange trading liquidity."
    ),
    # Tokenized stocks
    ("tokenized_stocks", "tokenized_equities"): (
        "Equity-tokenization headlines still center on access and settlement experiments—"
        "liquidity and scale on this page remain concentrated until broker and custody plumbing matures."
    ),
    ("tokenized_stocks", "regulation"): (
        "Securities-law and broker-rule coverage often caps how fast tokenized equities scale—"
        "regulatory framing may matter more than additional listings for near-term network/platform share."
    ),
    # Crypto prices
    ("crypto", "market_structure"): (
        "Breadth and dominance narratives help explain whether moves are Bitcoin-led or alt-led—"
        "compare with BTC/ETH 1M % and the category mix in the top-50 table."
    ),
    ("crypto", "regulation"): (
        "Enforcement and legislation headlines can shift risk appetite across the top-50—"
        "watch whether beta concentrates in majors or spreads into higher-beta categories."
    ),
    ("crypto", "etf_flows"): (
        "Spot ETF flow stories often move Bitcoin first—"
        "compare headline flow narratives with the 30-day net-flow KPI and IBIT/ETHA AUM on this page."
    ),
    # U.S. ETPs
    ("etp", "etf_flows"): (
        "Flow headlines can front-run AUM changes in the KPI strip and aggregate chart—"
        "compare cited inflow/outflow themes with the 30-day Farside net-flow figure and fund-table AUM."
    ),
    ("etp", "market_sizing"): (
        "AUM scenario coverage is useful for planning ranges, not point forecasts—"
        "anchor analyst brackets against live spot Bitcoin ETP AUM on this page and the aggregate trend chart."
    ),
    ("etp", "launch_pipeline"): (
        "Filing-wave headlines signal product attempts ahead of launches—"
        "most filings will not scale, but they can foreshadow issuer and custodian competition in the table below."
    ),
    ("etp", "regulation"): (
        "Approval and listing headlines shape which products can scale on U.S. exchanges—"
        "watch whether coverage names issuers or structures already listed in the fund table."
    ),
    ("etp", "concentration"): (
        "Concentration narratives matter for distribution economics—"
        "compare headline focus on mega-funds with top-fund AUM share in the KPI row and concentration chart."
    ),
    # RWA global
    ("rwa_global", "tokenization_growth"): (
        "Tokenization growth headlines usually lead headline RWA totals—"
        "network rank and share on this overview often shift as new issuers choose distribution rails."
    ),
    ("rwa_global", "macro_rates"): (
        "Rates and inflation coverage shapes which RWA categories attract inflows—"
        "Treasury- and cash-like RWAs often benefit when yield and collateral demand rise."
    ),
    # Participants (networks / platforms / asset managers share themes)
    ("participants", "infrastructure"): (
        "Infrastructure and custody headlines often map to platform and network rank changes—"
        "issuer integrations named in coverage may show up in participant tables before headline totals move."
    ),
}

# Extra nuance when participant sub-pages reuse the shared ``participants`` themes.
PARTICIPANT_PAGE_INTERPRETATIONS: dict[tuple[str, str], str] = {
    ("participants_networks", "infrastructure"): (
        "Network and custody headlines often explain near-term shifts in distributed value by chain—"
        "chains named in coverage are worth comparing with rank and share in the Networks table."
    ),
    ("participants_platforms", "infrastructure"): (
        "Platform and issuance-workflow headlines usually signal which stacks win issuer integrations—"
        "platform rank here may respond before category-level RWA totals change."
    ),
    ("participants_asset_managers", "infrastructure"): (
        "Asset-manager and franchise headlines typically move slowly but anchor category momentum—"
        "large-manager launches or migrations often show up in this table before the broader market reprices."
    ),
}

# Shared theme fallbacks when a page-specific line is missing.
_THEME_FALLBACKS: dict[str, str] = {
    "regulation": (
        "Regulatory headlines can reshape eligible investors and distribution paths—"
        "compare coverage with compliance labels and concentration on this page."
    ),
    "institutional_adoption": (
        "Institutional adoption stories often precede measurable on-chain share shifts—"
        "watch whether named issuers or banks appear in this page's league tables."
    ),
    "infrastructure": (
        "Infrastructure headlines often foreshadow rank changes among networks and platforms—"
        "compare named projects with the tables on this page."
    ),
}


def resolve_topic_key(topic: str) -> str:
    return TOPIC_THEME_KEY.get(topic, topic)


def page_theme_interpretation(topic: str, theme_id: str) -> str:
    """Interpretive sentence linking headline theme to the page subject."""
    if (topic, theme_id) in PARTICIPANT_PAGE_INTERPRETATIONS:
        return PARTICIPANT_PAGE_INTERPRETATIONS[(topic, theme_id)]
    topic_key = resolve_topic_key(topic)
    if (topic_key, theme_id) in PAGE_THEME_INTERPRETATIONS:
        return PAGE_THEME_INTERPRETATIONS[(topic_key, theme_id)]
    if theme_id in _THEME_FALLBACKS:
        return _THEME_FALLBACKS[theme_id]
    return (
        "Named themes in recent coverage can still lead rank, share, and concentration "
        "shifts on this page before totals fully reprice."
    )
