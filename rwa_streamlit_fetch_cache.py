"""Shared ``@st.cache_data`` wrappers for RWA.xyz scrapes (Streamlit only)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import streamlit as st

_RWA_CACHE_TTL = 3600
_RWA_SCHEMA = 1


def clear_rwa_streamlit_fetch_cache() -> None:
    """Clear all RWA Streamlit fetch caches (home refresh)."""
    cached_rwa_home_data.clear()
    cached_rwa_stablecoins_data.clear()
    cached_rwa_treasuries_data.clear()
    cached_rwa_tokenized_stocks_data.clear()
    cached_rwa_tokenized_mmf_data.clear()
    cached_rwa_networks_page_data.clear()
    cached_rwa_platforms_page_data.clear()
    cached_rwa_asset_managers_page_data.clear()


@st.cache_data(ttl=_RWA_CACHE_TTL, show_spinner=False)
def cached_rwa_home_data(*, _schema: int = _RWA_SCHEMA) -> tuple[list[Any], list[Any], str | None]:
    from rwa_league.client import fetch_rwa_home_data

    return fetch_rwa_home_data()


@st.cache_data(ttl=_RWA_CACHE_TTL, show_spinner=False)
def cached_rwa_stablecoins_data(*, _schema: int = _RWA_SCHEMA) -> tuple[Any, Any, Any, Any]:
    from rwa_league.client import fetch_rwa_stablecoins_data

    return fetch_rwa_stablecoins_data()


@st.cache_data(ttl=_RWA_CACHE_TTL, show_spinner=False)
def cached_rwa_treasuries_data(*, _schema: int = _RWA_SCHEMA) -> tuple[Any, Any, Any, Any]:
    from rwa_league.client import fetch_rwa_treasuries_data

    return fetch_rwa_treasuries_data()


@st.cache_data(ttl=_RWA_CACHE_TTL, show_spinner=False)
def cached_rwa_tokenized_stocks_data(*, _schema: int = _RWA_SCHEMA) -> tuple[Any, Any, Any, Any]:
    from rwa_league.client import fetch_rwa_tokenized_stocks_data

    return fetch_rwa_tokenized_stocks_data()


@st.cache_data(ttl=_RWA_CACHE_TTL, show_spinner=False)
def cached_rwa_tokenized_mmf_data(*, _schema: int = _RWA_SCHEMA) -> tuple[Any, Any, Any, Any]:
    from rwa_league.client import fetch_rwa_tokenized_mmf_data

    return fetch_rwa_tokenized_mmf_data()


@st.cache_data(ttl=_RWA_CACHE_TTL, show_spinner=False)
def cached_rwa_networks_page_data(*, _schema: int = _RWA_SCHEMA) -> tuple[list[Any], list[Any], Any]:
    from rwa_league.client import fetch_rwa_networks_page_data

    return fetch_rwa_networks_page_data()


@st.cache_data(ttl=_RWA_CACHE_TTL, show_spinner=False)
def cached_rwa_platforms_page_data(*, _schema: int = _RWA_SCHEMA) -> tuple[list[Any], list[Any], Any]:
    from rwa_league.client import fetch_rwa_platforms_page_data

    return fetch_rwa_platforms_page_data()


@st.cache_data(ttl=_RWA_CACHE_TTL, show_spinner=False)
def cached_rwa_asset_managers_page_data(*, _schema: int = _RWA_SCHEMA) -> tuple[list[Any], list[Any], Any]:
    from rwa_league.client import fetch_rwa_asset_managers_page_data

    return fetch_rwa_asset_managers_page_data()


def _stablecoins_pack_safe() -> tuple[Any, Any, Any, Any]:
    try:
        return cached_rwa_stablecoins_data()
    except Exception as exc:
        return ([], [], [], str(exc))


def _treasuries_pack_safe() -> tuple[Any, Any, Any, Any]:
    try:
        return cached_rwa_treasuries_data()
    except Exception as exc:
        return ([], [], [], str(exc))


def _stocks_pack_safe() -> tuple[Any, Any, Any, Any]:
    try:
        return cached_rwa_tokenized_stocks_data()
    except Exception as exc:
        return ([], [], [], str(exc))


def _mmf_pack_safe() -> tuple[Any, Any, Any, Any]:
    try:
        return cached_rwa_tokenized_mmf_data()
    except Exception as exc:
        return ([], [], [], str(exc))


def _networks_pack_safe() -> tuple[list[Any], list[Any], Any]:
    try:
        return cached_rwa_networks_page_data()
    except Exception as exc:
        return ([], [], str(exc))


def _platforms_pack_safe() -> tuple[list[Any], list[Any], Any]:
    try:
        return cached_rwa_platforms_page_data()
    except Exception as exc:
        return ([], [], str(exc))


def _asset_managers_pack_safe() -> tuple[list[Any], list[Any], Any]:
    try:
        return cached_rwa_asset_managers_page_data()
    except Exception as exc:
        return ([], [], str(exc))


def fetch_explore_asset_type_packs_parallel() -> tuple[Any, Any, Any, Any]:
    """Parallel cached RWA fetches for Explore by Asset Type."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_sc = pool.submit(_stablecoins_pack_safe)
        f_tr = pool.submit(_treasuries_pack_safe)
        f_st = pool.submit(_stocks_pack_safe)
        f_mmf = pool.submit(_mmf_pack_safe)
    return f_sc.result(), f_tr.result(), f_st.result(), f_mmf.result()


def fetch_explore_participant_packs_parallel() -> tuple[Any, Any, Any]:
    """Parallel cached RWA fetches for Explore by Market Participant."""
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_net = pool.submit(_networks_pack_safe)
        f_plat = pool.submit(_platforms_pack_safe)
        f_am = pool.submit(_asset_managers_pack_safe)
    return f_net.result(), f_plat.result(), f_am.result()
