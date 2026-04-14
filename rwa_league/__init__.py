"""RWA.xyz league table widget (scraped from embedded Next.js data)."""

from rwa_league.client import (
    RwaGlobalKpi,
    RwaNetworkLeagueRow,
    RwaStablecoinPlatformRow,
    RwaTreasuryDistributedNetworkRow,
    fetch_rwa_home_data,
    fetch_rwa_network_league,
    fetch_rwa_stablecoins_data,
    fetch_rwa_treasuries_data,
)
from rwa_league.widgets import (
    clear_rwa_league_cache,
    show_rwa_league_widget,
    show_rwa_stablecoins_widget,
    show_rwa_treasuries_widget,
)

__all__ = [
    "RwaGlobalKpi",
    "RwaNetworkLeagueRow",
    "RwaStablecoinPlatformRow",
    "RwaTreasuryDistributedNetworkRow",
    "clear_rwa_league_cache",
    "fetch_rwa_home_data",
    "fetch_rwa_network_league",
    "fetch_rwa_stablecoins_data",
    "fetch_rwa_treasuries_data",
    "show_rwa_league_widget",
    "show_rwa_stablecoins_widget",
    "show_rwa_treasuries_widget",
]
