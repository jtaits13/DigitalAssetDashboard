"""Infer spot vs. futures exposure from StockAnalysis ETF About + Index Tracked text.

Heuristics only (not legal advice). Tuned on live copy: e.g. IBIT ``track the spot price``,
BITO ``front-month CME bitcoin futures``. Index names like ``CME CF Bitcoin Reference Rate``
do **not** imply futures exposure.
"""

from __future__ import annotations

# Substrings in About / Index Tracked (lowercased).
_FUTURES_NEEDLES: tuple[str, ...] = (
    "bitcoin futures",
    "ethereum futures",
    "ether futures",
    "micro bitcoin futures",
    "micro ether futures",
    "micro ethereum futures",
    "cme bitcoin futures",
    "cme ether futures",
    "cme ethereum futures",
    "futures contracts",
    "front-month cme",
    "portfolio of front-month",
    "invests primarily in futures",
    "invests in bitcoin futures",
    "invests in ether futures",
    "invests in ethereum futures",
    "managed portfolio of futures",
    "basket of bitcoin futures",
    "basket of ether futures",
    "bitcoin futures subindex",
    "ether futures subindex",
)

_SPOT_NEEDLES: tuple[str, ...] = (
    "track the spot price",
    "tracks the spot price",
    "spot price of bitcoin",
    "spot price of ether",
    "spot price of ethereum",
    "physically backed",
    "physical bitcoin",
    "physical ether",
    "holds bitcoin",
    "holds ether",
    "custody of bitcoin",
    "custody of ether",
)


def infer_spot_futures_exposure(about: str, index_tracked: str) -> str:
    """Return ``Spot``, ``Futures``, or ``—``."""
    blob = f"{about or ''} {index_tracked or ''}".lower()
    if not blob.strip():
        return "—"

    f_hit = any(n in blob for n in _FUTURES_NEEDLES)
    s_hit = any(n in blob for n in _SPOT_NEEDLES)

    if f_hit and not s_hit:
        return "Futures"
    if s_hit and not f_hit:
        return "Spot"
    if f_hit and s_hit:
        # Rare mixed wording; prefer explicit futures contract language.
        strong_f = any(
            n in blob
            for n in (
                "bitcoin futures",
                "ethereum futures",
                "ether futures",
                "futures contracts",
                "front-month cme",
            )
        )
        return "Futures" if strong_f else "Spot"
    return "—"
