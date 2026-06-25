"""Stale-first payload loading for Streamlit iframe subpages."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

import streamlit as st

T = TypeVar("T")

_PHASE_PREFIX = "_stale_first_phase_"
_RERUN_KEY = "_stale_first_rerun"


def clear_stale_first_state() -> None:
    """Reset stale-first session flags (e.g. after home refresh)."""
    drop = [k for k in st.session_state if k.startswith(_PHASE_PREFIX) or k == _RERUN_KEY]
    for key in drop:
        del st.session_state[key]


def maybe_rerun_after_stale_first() -> None:
    """Trigger a second run to fetch live payloads after showing static data."""
    if st.session_state.pop(_RERUN_KEY, None):
        st.rerun()


def resolve_payload_stale_first(
    *,
    page_key: str,
    load_stale: Callable[[], T | None],
    load_live_cached: Callable[[], T],
    mark_stale: Callable[[T, str], T] | None = None,
) -> T:
    """
    On a cold visit, return committed static/cache JSON immediately, then live data after one rerun.

    Subsequent visits use ``load_live_cached`` (``@st.cache_data``) until TTL expires.
    """
    phase_key = f"{_PHASE_PREFIX}{page_key}"
    phase = st.session_state.get(phase_key, "init")

    def _with_stale_error(stale: T, exc: Exception) -> T:
        if mark_stale is not None:
            return mark_stale(stale, str(exc))
        return stale

    if phase == "init":
        stale = load_stale()
        if stale is not None:
            st.session_state[phase_key] = "stale_shown"
            st.session_state[_RERUN_KEY] = page_key
            return stale
        st.session_state[phase_key] = "live"

    if phase == "stale_shown":
        st.session_state[phase_key] = "live"
        try:
            return load_live_cached()
        except Exception as exc:
            stale = load_stale()
            if stale is not None:
                return _with_stale_error(stale, exc)
            raise

    try:
        return load_live_cached()
    except Exception as exc:
        stale = load_stale()
        if stale is not None:
            return _with_stale_error(stale, exc)
        raise


def mark_dict_stale(payload: dict[str, Any], error: str) -> dict[str, Any]:
    merged = dict(payload)
    merged["stale"] = True
    prev = str(merged.get("error") or "").strip()
    merged["error"] = f"{prev} {error}".strip() if prev else error
    return merged


def mark_payload_map_stale(payloads: dict[str, Any], error: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in payloads.items():
        if isinstance(value, dict):
            out[key] = mark_dict_stale(value, error)
        else:
            out[key] = value
    return out
