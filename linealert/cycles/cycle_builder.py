"""Build first-class cycle objects from event timelines."""

from __future__ import annotations

try:
    from event_loader import Event
except ImportError:  # pragma: no cover - used when imported from repository root.
    from linealert.src.event_loader import Event

from linealert.cycles.cycle import (
    Cycle,
    CycleEvidence,
    CycleMeasurement,
    CycleStatus,
)
from validation.baseline import EventRelationship, TimingStats, ValidationBaseline


MONITOR_DEVIATION_PERCENT = 10.0
OUT_OF_BASELINE_DEVIATION_PERCENT = 20.0
MONITOR_MIN_DELTA_MS = 50.0
OUT_OF_BASELINE_MIN_DELTA_MS = 100.0


def build_cycles(
    events: list[Event],
    relationships: list[EventRelationship] | None = None,
    baseline: ValidationBaseline | None = None,
) -> list[Cycle]:
    """Group CycleStart/CycleComplete windows into cycle context objects."""

    cycles: list[Cycle] = []
    current_events: list[Event] = []

    for event in sorted(events, key=lambda item: (item.timestamp, item.source_row)):
        if event.event_name == "CycleStart":
            current_events = [event]
            continue

        if not current_events:
            continue

        current_events.append(event)
        if event.event_name == "CycleComplete":
            cycle_id = len(cycles) + 1
            cycles.append(
                _build_cycle(
                    cycle_id=cycle_id,
                    events=list(current_events),
                    relationships=relationships or [],
                    baseline=baseline,
                )
            )
            current_events = []

    return cycles


def _build_cycle(
    cycle_id: int,
    events: list[Event],
    relationships: list[EventRelationship],
    baseline: ValidationBaseline | None,
) -> Cycle:
    start_event = events[0]
    end_event = events[-1]
    duration_ms = (end_event.timestamp - start_event.timestamp).total_seconds() * 1000
    measurements = _cycle_measurements(
        events=events,
        duration_ms=duration_ms,
        relationships=relationships,
        baseline=baseline,
    )
    evidence = _cycle_evidence(cycle_id=cycle_id, measurements=measurements)
    status = _cycle_status(measurements)

    return Cycle(
        cycle_id=cycle_id,
        start_timestamp=start_event.timestamp,
        end_timestamp=end_event.timestamp,
        duration_ms=duration_ms,
        events=events,
        measurements=measurements,
        evidence=evidence,
        status=status,
    )


def _cycle_measurements(
    events: list[Event],
    duration_ms: float,
    relationships: list[EventRelationship],
    baseline: ValidationBaseline | None,
) -> list[CycleMeasurement]:
    measurements = [
        _measurement_from_value(
            name="Cycle Duration",
            metric="duration_ms",
            observed_ms=duration_ms,
            baseline_stats=baseline.cycle_duration if baseline is not None else None,
        )
    ]

    events_by_name = {event.event_name: event for event in events}
    for relationship in relationships:
        from_event = events_by_name.get(relationship.from_event)
        to_event = events_by_name.get(relationship.to_event)
        baseline_stats = (
            baseline.relationships.get(relationship.key)
            if baseline is not None
            else None
        )
        observed_ms = (
            (to_event.timestamp - from_event.timestamp).total_seconds() * 1000
            if from_event is not None and to_event is not None
            else None
        )
        measurements.append(
            _measurement_from_value(
                name=relationship.name,
                metric="lag_ms",
                observed_ms=observed_ms,
                relationship=relationship.name,
                relationship_key=relationship.key,
                baseline_stats=baseline_stats,
            )
        )

    return measurements


def _measurement_from_value(
    name: str,
    metric: str,
    observed_ms: float | None,
    baseline_stats: TimingStats | None,
    relationship: str | None = None,
    relationship_key: str | None = None,
) -> CycleMeasurement:
    baseline_ms = baseline_stats.avg_ms if baseline_stats is not None else None
    deviation_ms = (
        observed_ms - baseline_ms
        if observed_ms is not None and baseline_ms is not None
        else None
    )
    deviation_percent = (
        (deviation_ms / baseline_ms) * 100
        if deviation_ms is not None and baseline_ms not in (None, 0)
        else None
    )
    status = _measurement_status(
        observed_ms=observed_ms,
        baseline_ms=baseline_ms,
        deviation_ms=deviation_ms,
        deviation_percent=deviation_percent,
    )

    return CycleMeasurement(
        name=name,
        metric=metric,
        observed_ms=observed_ms,
        relationship=relationship,
        relationship_key=relationship_key,
        baseline_ms=baseline_ms,
        deviation_ms=deviation_ms,
        deviation_percent=deviation_percent,
        status=status,
    )


def _measurement_status(
    observed_ms: float | None,
    baseline_ms: float | None,
    deviation_ms: float | None,
    deviation_percent: float | None,
) -> CycleStatus:
    if baseline_ms is None:
        return CycleStatus.HEALTHY
    if observed_ms is None:
        return CycleStatus.OUT_OF_BASELINE
    if deviation_ms is None or deviation_percent is None:
        return CycleStatus.HEALTHY

    abs_deviation_ms = abs(deviation_ms)
    abs_deviation_percent = abs(deviation_percent)
    if (
        abs_deviation_percent > OUT_OF_BASELINE_DEVIATION_PERCENT
        and abs_deviation_ms > OUT_OF_BASELINE_MIN_DELTA_MS
    ):
        return CycleStatus.OUT_OF_BASELINE
    if (
        abs_deviation_percent > MONITOR_DEVIATION_PERCENT
        and abs_deviation_ms > MONITOR_MIN_DELTA_MS
    ):
        return CycleStatus.MONITOR
    return CycleStatus.HEALTHY


def _cycle_evidence(
    cycle_id: int, measurements: list[CycleMeasurement]
) -> list[CycleEvidence]:
    return [
        CycleEvidence(
            cycle_id=cycle_id,
            relationship=measurement.relationship,
            measurement=measurement.metric,
            observed_ms=measurement.observed_ms,
            baseline_ms=measurement.baseline_ms,
            deviation_percent=measurement.deviation_percent,
            status=measurement.status,
        )
        for measurement in measurements
        if measurement.relationship is not None
        and measurement.status is not CycleStatus.HEALTHY
    ]


def _cycle_status(measurements: list[CycleMeasurement]) -> CycleStatus:
    statuses = {measurement.status for measurement in measurements}
    if CycleStatus.OUT_OF_BASELINE in statuses:
        return CycleStatus.OUT_OF_BASELINE
    if CycleStatus.MONITOR in statuses:
        return CycleStatus.MONITOR
    return CycleStatus.HEALTHY
