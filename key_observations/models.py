"""Shared types for dynamic Key observations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ObservationCandidate:
    """One selectable Key observation bullet."""

    id: str
    lead: str
    body: str
    score: float
    themes: tuple[str, ...] = ()
    source: str = "data"  # data | news | blend


@dataclass(frozen=True)
class TopicTheme:
    """News theme used to score headlines and align data bullets."""

    id: str
    label: str
    keywords: tuple[str, ...]
    google_queries: tuple[str, ...] = ()
