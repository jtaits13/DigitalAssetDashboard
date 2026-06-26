"""Static JSON fallback helpers for Streamlit iframe subpages (no rerun)."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

T = TypeVar("T")


def clear_stale_first_state() -> None:
    """No-op — kept for home refresh compatibility after removing stale-first reruns."""


def maybe_rerun_after_stale_first() -> None:
    """No-op — stale-first reruns removed; subpages load live data once per run."""


def load_live_with_static_fallback(
    *,
    load_live_cached: Callable[[], T],
    load_stale: Callable[[], T | None],
    mark_stale: Callable[[T, str], T] | None = None,
) -> T:
    """Load live ``@st.cache_data`` payloads; fall back to committed static JSON on failure."""
    try:
        return load_live_cached()
    except Exception as exc:
        stale = load_stale()
        if stale is not None:
            if mark_stale is not None:
                return mark_stale(stale, str(exc))
            return stale
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
