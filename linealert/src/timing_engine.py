"""Calculate event timing observations.

This module turns normalized event evidence into timing evidence. It calculates
what happened and when, but does not decide whether a value is bad. Drift and
rules are evaluated in later stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from event_loader import Event


@dataclass(frozen=True)
class LagObservation:
    """Measured lag between two adjacent events."""

    observation_key: str
    previous_event: str
    current_event: str
    lag_seconds: float
    previous_row: int
    current_row: int


@dataclass(frozen=True)
class CycleObservation:
    """Measured cycle duration between repeated occurrences of one event."""

    observation_key: str
    event_name: str
    cycle_seconds: float
    previous_row: int
    current_row: int


@dataclass(frozen=True)
class TimingMetric:
    """Aggregated timing evidence used for baseline comparison."""

    observation_key: str
    metric_type: str
    event_path: str
    value_seconds: float
    sample_count: int


@dataclass(frozen=True)
class TimingObservations:
    """All timing evidence produced by the timing engine."""

    lags: list[LagObservation]
    cycles: list[CycleObservation]
    metrics: list[TimingMetric]


def calculate_timing_observations(events: list[Event]) -> TimingObservations:
    """Calculate adjacent event lags, repeated-event cycles, and aggregates."""

    if len(events) < 2:
        return TimingObservations(lags=[], cycles=[], metrics=[])

    lags = _calculate_adjacent_lags(events)
    cycles = _calculate_cycles(events)
    metrics = _aggregate_metrics(lags, cycles)

    return TimingObservations(lags=lags, cycles=cycles, metrics=metrics)


def _calculate_adjacent_lags(events: list[Event]) -> list[LagObservation]:
    observations: list[LagObservation] = []
    for previous, current in zip(events, events[1:]):
        lag_seconds = (current.timestamp - previous.timestamp).total_seconds()
        key = f"lag:{previous.event_name}->{current.event_name}"
        observations.append(
            LagObservation(
                observation_key=key,
                previous_event=previous.event_name,
                current_event=current.event_name,
                lag_seconds=lag_seconds,
                previous_row=previous.source_row,
                current_row=current.source_row,
            )
        )
    return observations


def _calculate_cycles(events: list[Event]) -> list[CycleObservation]:
    observations: list[CycleObservation] = []
    previous_by_event: dict[str, Event] = {}

    for current in events:
        previous = previous_by_event.get(current.event_name)
        if previous is not None:
            cycle_seconds = (current.timestamp - previous.timestamp).total_seconds()
            key = f"cycle:{current.event_name}"
            observations.append(
                CycleObservation(
                    observation_key=key,
                    event_name=current.event_name,
                    cycle_seconds=cycle_seconds,
                    previous_row=previous.source_row,
                    current_row=current.source_row,
                )
            )
        previous_by_event[current.event_name] = current

    return observations


def _aggregate_metrics(
    lags: list[LagObservation], cycles: list[CycleObservation]
) -> list[TimingMetric]:
    grouped_values: dict[str, list[float]] = {}
    event_paths: dict[str, str] = {}
    metric_types: dict[str, str] = {}

    for lag in lags:
        grouped_values.setdefault(lag.observation_key, []).append(lag.lag_seconds)
        event_paths[lag.observation_key] = f"{lag.previous_event}->{lag.current_event}"
        metric_types[lag.observation_key] = "lag"

    for cycle in cycles:
        grouped_values.setdefault(cycle.observation_key, []).append(cycle.cycle_seconds)
        event_paths[cycle.observation_key] = cycle.event_name
        metric_types[cycle.observation_key] = "cycle"

    return [
        TimingMetric(
            observation_key=key,
            metric_type=metric_types[key],
            event_path=event_paths[key],
            value_seconds=mean(values),
            sample_count=len(values),
        )
        for key, values in sorted(grouped_values.items())
    ]
