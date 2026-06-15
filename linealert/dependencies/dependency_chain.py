"""Dependency chain configuration models."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DependencyChain:
    """Expected ordered chain of dependent events."""

    chain_id: str
    events: list[str]

    @property
    def direct_edges(self) -> list[tuple[str, str]]:
        return list(zip(self.events, self.events[1:]))

    def as_dict(self) -> dict[str, object]:
        return {
            "chain_id": self.chain_id,
            "events": list(self.events),
            "direct_edges": [
                {"source": source, "target": target}
                for source, target in self.direct_edges
            ],
        }


def load_dependency_chains(config_path: str | Path) -> list[DependencyChain]:
    """Load dependency chains from JSON configuration."""

    path = Path(config_path)
    with path.open("r", encoding="utf-8") as config_file:
        raw_config = json.load(config_file)
    if not isinstance(raw_config, dict):
        raise ValueError(f"Dependency chain config must be an object: {path}")

    raw_chains = raw_config.get("chains")
    if not isinstance(raw_chains, list):
        raise ValueError("Dependency chain config requires a chains list")

    return [
        _parse_chain(raw_chain=raw_chain, index=index)
        for index, raw_chain in enumerate(raw_chains, start=1)
    ]


def _parse_chain(raw_chain: object, index: int) -> DependencyChain:
    if isinstance(raw_chain, list):
        events = _parse_events(raw_chain, index)
        return DependencyChain(chain_id=f"chain_{index}", events=events)

    if not isinstance(raw_chain, dict):
        raise ValueError(f"Dependency chain {index} must be a list or object")

    raw_events = raw_chain.get("events")
    if not isinstance(raw_events, list):
        raise ValueError(f"Dependency chain {index} requires an events list")
    events = _parse_events(raw_events, index)
    chain_id = str(raw_chain.get("chain_id") or f"chain_{index}")
    return DependencyChain(chain_id=chain_id, events=events)


def _parse_events(raw_events: list[object], index: int) -> list[str]:
    events = [str(event).strip() for event in raw_events]
    if len(events) < 2:
        raise ValueError(f"Dependency chain {index} requires at least two events")
    if any(not event for event in events):
        raise ValueError(f"Dependency chain {index} contains an empty event name")
    if len(set(events)) != len(events):
        raise ValueError(f"Dependency chain {index} contains duplicate events")
    return events
