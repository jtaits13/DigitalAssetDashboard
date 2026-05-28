"""Dynamic Key observations: on-page data + industry headlines."""

from key_observations.compose import build_key_observations_html
from key_observations.models import ObservationCandidate, TopicTheme

__all__ = [
    "ObservationCandidate",
    "TopicTheme",
    "build_key_observations_html",
]
