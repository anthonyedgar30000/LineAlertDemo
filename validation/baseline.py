"""Generate known-good timing baselines from normal event timelines."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Iterable

try:
    from event_loader import Event
except ImportError:  # pragma: no cover - used when imported from repository root.
    from linealert.src.event_loader import Event


@dataclass(frozen=True)
class EventRelationship:
    """A measurable relationship between two timeline events."""

    name: str
    from_event: str
    to_event: str
    relationship_type: str = "lag"

    @property
    def key(self) -> str:
        return f"{self.from_event}->{self.to_event}"


@dataclass(frozen=True)
class TimingStats:
    """Observed timing distribution for a relationship or cycle rhythm."""

    avg_ms: float
    stddev_ms: float
    sample_count: int

    def as_dict(self) -> dict[str, float | int]:
        return {
            "avg_ms": round(self.avg_ms, 3),
            "stddev_ms": round(self.stddev_ms, 3),
            "sample_count": self.sample_count,
        }


@dataclass(frozen=True)
class ValidationBaseline:
    """Known-good baseline measurements used for validation comparisons."""

    relationships: dict[str, TimingStats]
    cycle_duration: TimingStats
    event_frequencies: dict[str, int]

    def as_dict(self) -> dict[str, object]:
        return {
            "relationships": {
                relationship: stats.as_dict()
                for relationship, stats in sorted(self.relationships.items())
            },
            "cycle_duration_ms": self.cycle_duration.as_dict(),
            "event_frequencies": dict(sorted(self.event_frequencies.items())),
        }


def load_relationships(config_path: str | Path) -> list[EventRelationship]:
    """Load first-class timing relationship definitions from JSON."""

    path = Path(config_path)
    with path.open("r", encoding="utf-8") as relationships_file:
        raw_config = json.load(relationships_file)

    raw_relationships = raw_config.get("relationships") if isinstance(raw_config, dict) else None
    if not isinstance(raw_relationships, list):
        raise ValueError(f"Relationship config must contain a relationships list: {path}")

    relationships: list[EventRelationship] = []
    for index, raw_relationship in enumerate(raw_relationships, start=1):
        if not isinstance(raw_relationship, dict):
            raise ValueError(f"Relationship {index} must be an object")
        relationships.append(
            EventRelationship(
                name=str(raw_relationship.get("name") or _default_relationship_name(raw_relationship)),
                from_event=_required_str(raw_relationship, "from", index),
                to_event=_required_str(raw_relationship, "to", index),
                relationship_type=str(raw_relationship.get("type") or raw_relationship.get("metric") or "lag"),
            )
        )

    return relationships


def generate_baseline(
    events: list[Event], relationships: Iterable[EventRelationship]
) -> ValidationBaseline:
    """Generate known-good timing and rhythm values from normal cycles."""

    cycles = group_events_by_cycle(events)
    if not cycles:
        raise ValueError("Cannot generate baseline without complete cycles")

    relationship_stats = {
        relationship.key: _stats_for_values(
            _relationship_lags_ms(cycles=cycles, relationship=relationship)
        )
        for relationship in relationships
    }
    cycle_duration = _stats_for_values(_cycle_durations_ms(cycles))
    event_frequencies = _event_frequencies(cycles)

    return ValidationBaseline(
        relationships=relationship_stats,
        cycle_duration=cycle_duration,
        event_frequencies=event_frequencies,
    )


def group_events_by_cycle(events: list[Event]) -> list[list[Event]]:
    """Split a sorted event timeline into cycles delimited by CycleStart."""

    cycles: list[list[Event]] = []
    current_cycle: list[Event] = []

    for event in sorted(events, key=lambda item: (item.timestamp, item.source_row)):
        if event.event_name == "CycleStart":
            if current_cycle:
                cycles.append(current_cycle)
            current_cycle = [event]
        elif current_cycle:
            current_cycle.append(event)

    if current_cycle:
        cycles.append(current_cycle)

    return cycles


def _relationship_lags_ms(
    cycles: list[list[Event]], relationship: EventRelationship
) -> list[float]:
    lags: list[float] = []
    for cycle in cycles:
        events_by_name = {event.event_name: event for event in cycle}
        from_event = events_by_name.get(relationship.from_event)
        to_event = events_by_name.get(relationship.to_event)
        if from_event is None or to_event is None:
            continue
        lags.append((to_event.timestamp - from_event.timestamp).total_seconds() * 1000)
    return lags


def _cycle_durations_ms(cycles: list[list[Event]]) -> list[float]:
    durations: list[float] = []
    for cycle in cycles:
        events_by_name = {event.event_name: event for event in cycle}
        start_event = events_by_name.get("CycleStart")
        complete_event = events_by_name.get("CycleComplete")
        if start_event is None or complete_event is None:
            continue
        durations.append(
            (complete_event.timestamp - start_event.timestamp).total_seconds() * 1000
        )
    return durations


def _event_frequencies(cycles: list[list[Event]]) -> dict[str, int]:
    frequencies: dict[str, list[int]] = {}
    for cycle in cycles:
        counts: dict[str, int] = {}
        for event in cycle:
            counts[event.event_name] = counts.get(event.event_name, 0) + 1
        for event_name in counts:
            frequencies.setdefault(event_name, []).append(counts[event_name])

    return {
        event_name: round(mean(counts))
        for event_name, counts in frequencies.items()
    }


def _stats_for_values(values: list[float]) -> TimingStats:
    if not values:
        return TimingStats(avg_ms=0.0, stddev_ms=0.0, sample_count=0)
    return TimingStats(
        avg_ms=mean(values),
        stddev_ms=pstdev(values) if len(values) > 1 else 0.0,
        sample_count=len(values),
    )


def _default_relationship_name(raw_relationship: dict[str, object]) -> str:
    from_event = str(raw_relationship.get("from", "unknown"))
    to_event = str(raw_relationship.get("to", "unknown"))
    return f"{from_event}->{to_event}"


def _required_str(
    raw_relationship: dict[str, object], field_name: str, index: int
) -> str:
    value = raw_relationship.get(field_name)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Relationship {index} missing required field: {field_name}")
    return str(value)
