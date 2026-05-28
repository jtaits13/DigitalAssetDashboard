"""Topic-specific news themes for Key observations."""

from __future__ import annotations

from key_observations.models import TopicTheme

TOPIC_THEMES: dict[str, tuple[TopicTheme, ...]] = {
    "tokenized_mmf": (
        TopicTheme(
            "institutional_settlement",
            "Institutional settlement & cash rails",
            (
                "money market fund",
                "liquidity fund",
                "cash management",
                "collateral",
                "settlement",
                "buidl",
                "blackrock",
                "tokenized fund",
            ),
            (
                "tokenized money market fund",
                "BlackRock BUIDL tokenized fund",
                "on-chain cash management fund",
            ),
        ),
        TopicTheme(
            "regulation",
            "Regulation & compliance",
            (
                "sec",
                "regulation",
                "compliance",
                "ucits",
                "mica",
                "hong kong",
                "professional investor",
                "reg d",
                "reg s",
            ),
            ("tokenized fund regulation SEC", "UCITS tokenized fund"),
        ),
        TopicTheme(
            "chain_efficiency",
            "Chain efficiency & migration",
            (
                "solana",
                "avalanche",
                "layer 2",
                "throughput",
                "low fee",
                "network migration",
                "settlement efficiency",
            ),
            ("tokenized treasury Solana", "RWA blockchain fees"),
        ),
        TopicTheme(
            "issuer_models",
            "Issuer strategy split",
            (
                "institutional",
                "retail",
                "ucits",
                "asset manager",
                "distribution",
                "yield product",
            ),
            ("tokenized money market fund institutional", "UCITS tokenized MMF"),
        ),
        TopicTheme(
            "rates_yields",
            "Rates, yields & Fed policy",
            (
                "fed",
                "interest rate",
                "yield",
                "apy",
                "treasury yield",
                "money market rate",
            ),
            ("money market fund yield Fed", "tokenized treasury yield"),
        ),
        TopicTheme(
            "multichain",
            "Multi-chain distribution",
            ("multi-chain", "multichain", "cross-chain", "deployment", "chain expansion"),
            ("tokenized fund multi-chain", "RWA cross-chain"),
        ),
    ),
    "us_treasuries": (
        TopicTheme(
            "tokenized_treasuries",
            "Tokenized U.S. Treasuries",
            (
                "tokenized treasury",
                "tokenized treasuries",
                "t-bill",
                "treasury token",
                "buidl",
                "ondo",
            ),
            ("tokenized US treasury RWA", "on-chain treasuries"),
        ),
        TopicTheme(
            "regulation",
            "Regulation",
            ("sec", "regulation", "compliance", "mica", "cftc"),
            ("tokenized treasury SEC",),
        ),
        TopicTheme(
            "institutional_adoption",
            "Institutional adoption",
            ("blackrock", "institutional", "wall street", "bank", "custody"),
            ("BlackRock tokenized treasury",),
        ),
    ),
    "stablecoins": (
        TopicTheme(
            "stablecoin_policy",
            "Stablecoin policy & reserves",
            ("stablecoin", "usdc", "usdt", "reserves", "genius act", "payment stablecoin"),
            ("stablecoin regulation US",),
        ),
        TopicTheme(
            "bank_integration",
            "Bank & payments integration",
            ("bank", "payments", "visa", "mastercard", "stripe", "circle"),
            ("stablecoin bank integration",),
        ),
    ),
    "tokenized_stocks": (
        TopicTheme(
            "tokenized_equities",
            "Tokenized equities",
            ("tokenized stock", "tokenized equity", "tokenized shares", "24/7 trading"),
            ("tokenized stocks blockchain",),
        ),
        TopicTheme(
            "regulation",
            "Securities regulation",
            ("sec", "securities", "broker", "retail", "compliance"),
            ("tokenized stocks SEC",),
        ),
    ),
    "crypto": (
        TopicTheme(
            "market_structure",
            "Crypto market structure",
            ("bitcoin", "ethereum", "market cap", "etf", "dominance", "altcoin"),
            ("bitcoin ethereum market",),
        ),
        TopicTheme(
            "regulation",
            "Crypto regulation",
            ("sec", "regulation", "enforcement", "legislation", "stablecoin"),
            ("crypto regulation SEC",),
        ),
        TopicTheme(
            "etf_flows",
            "ETF & institutional flows",
            ("etf", "inflow", "outflow", "blackrock", "fidelity", "spot bitcoin"),
            ("bitcoin ETF flow",),
        ),
    ),
    "etp": (
        TopicTheme(
            "etf_flows",
            "ETF flows & inflows",
            (
                "etf flow",
                "inflow",
                "outflow",
                "spot bitcoin etf",
                "spot ether etf",
                "ibit",
                "farside",
            ),
            ("bitcoin ETF inflow", "spot bitcoin ETF flow"),
        ),
        TopicTheme(
            "market_sizing",
            "ETF AUM & market-size scenarios",
            (
                "etf aum",
                "assets under management",
                "180 billion",
                "220 billion",
                "bitcoin etf assets",
                "market size",
            ),
            ("bitcoin ETF AUM forecast 2026",),
        ),
        TopicTheme(
            "launch_pipeline",
            "ETP filings & product pipeline",
            (
                "etf filing",
                "s-1",
                "spot etf",
                "crypto etf filing",
                "new etf",
                "etf application",
            ),
            ("crypto ETF filing SEC", "spot bitcoin ETF filing"),
        ),
        TopicTheme(
            "regulation",
            "SEC & exchange approvals",
            ("sec", "approval", "nyse", "cboe", "listing", "exchange-traded"),
            ("spot bitcoin ETF SEC approval",),
        ),
        TopicTheme(
            "concentration",
            "Fund concentration & share",
            ("ibit", "blackrock", "dominance", "concentration", "market share"),
            ("bitcoin ETF market share IBIT",),
        ),
    ),
    "rwa_global": (
        TopicTheme(
            "tokenization_growth",
            "RWA tokenization",
            ("tokenization", "real world asset", "rwa", "on-chain credit", "private credit"),
            ("real world asset tokenization",),
        ),
        TopicTheme(
            "macro_rates",
            "Macro & rates",
            ("fed", "interest rate", "yield", "inflation", "treasury"),
            ("tokenization interest rates",),
        ),
    ),
    "participants": (
        TopicTheme(
            "infrastructure",
            "RWA infrastructure",
            ("tokenization platform", "custody", "network", "ethereum", "layer 2"),
            ("RWA tokenization platform",),
        ),
    ),
}
