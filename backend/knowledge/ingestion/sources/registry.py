"""Authoritative source registry for the state law ingestion pipeline.

Loads `state_sources.yaml`, which maps each supported state to its official
statute source and any court-procedure sources for `kb-court-procedures`.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

_SOURCES_FILE = Path(__file__).parent / "state_sources.yaml"


@dataclass(frozen=True)
class CourtProcedureSource:
    county: str
    url: str
    description: str


@dataclass(frozen=True)
class StateSource:
    state: str
    dispute_type: str
    statute_url: str
    statute_description: str
    review_frequency_days: int
    court_procedures: list[CourtProcedureSource] = field(default_factory=list)

    def as_source_urls_dict(self) -> dict:
        """Shape stored in `law_freshness.source_urls`."""
        return {
            "statute": self.statute_url,
            "court_procedures": [{"county": cp.county, "url": cp.url} for cp in self.court_procedures],
        }


@lru_cache
def _load_raw() -> dict:
    with _SOURCES_FILE.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_states() -> list[str]:
    """Return all state abbreviations registered in the source list."""
    return list(_load_raw().keys())


def get_state_source(state: str) -> StateSource | None:
    """Return the registered source info for a state, or None if not registered."""
    raw = _load_raw().get(state.upper())
    if raw is None:
        return None

    return StateSource(
        state=state.upper(),
        dispute_type=raw["dispute_type"],
        statute_url=raw["statute"]["url"],
        statute_description=raw["statute"]["description"],
        review_frequency_days=raw["review_frequency_days"],
        court_procedures=[
            CourtProcedureSource(county=cp["county"], url=cp["url"], description=cp["description"])
            for cp in raw.get("court_procedures", [])
        ],
    )
