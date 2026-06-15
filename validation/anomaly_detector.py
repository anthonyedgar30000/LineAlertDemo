"""Detect measurable event-timeline anomalies against a known-good baseline."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev

try:
    from event_loader import Event
except ImportError:  # pragma: no cover - used when imported from repository root.
    from linealert.src.event_loader import Event

from simulator.plc_simulator import MACHINE_SEQUENCE
from validation.baseline import (
    EventRelationship,
    ValidationBaseline,
    group_events_by_cycle,
)


@dataclass(frozen=True)
class EvidenceRecord:
    """A single measurable observation supporting an anomaly record."""

    issue_type: str
    cycle_id: int | None
    timestamp: str
    relationship: str | None = None
    event_name: str | None = None
    expected_ms: float | None = None
    observed_ms: float | None = None
    deviation_percent: float | None = None
    details: str = ""

    def as_dict(self) -> dict[str, object]:
        output: dict[str, object] = {
            "issue_type": self.issue_type,
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp,
        }
        optional_values = {
            "relationship": self.relationship,
            "event_name": self.event_name,
            "expected_ms": _round_optional(self.expected_ms),
            "observed_ms": _round_optional(self.observed_ms),
            "deviation_percent": _round_optional(self.deviation_percent),
            "details": self.details or None,
        }
        output.update(
            {
                key: value
                for key, value in optional_values.items()
                if value is not None
            }
        )
        return output


@dataclass(frozen=True)
class Anomaly:
    """Observation-only anomaly detected from event measurements."""

    issue_type: str
    confidence: float
    evidence: list[EvidenceRecord]

    def as_dict(self) -> dict[str, object]:
        return {
            "issue_type": self.issue_type,
            "confidence": round(self.confidence, 3),
            "evidence": [record.as_dict() for record in self.evidence],
        }


def detect_anomalies(
    events: list[Event],
    baseline: ValidationBaseline,
    relationships: list[EventRelationship],
) -> list[Anomaly]:
    """Compare observed event behavior with baseline measurements."""

    cycles = group_events_by_cycle(events)
    anomalies = [
        _detect_missing_events(cycles=cycles, baseline=baseline),
        _detect_sequence_violations(cycles=cycles),
        _detect_excessive_lag(
            cycles=cycles,
            baseline=baseline,
            relationships=relationships,
        ),
        _detect_increasing_drift(
            cycles=cycles,
            baseline=baseline,
            relationships=relationships,
        ),
        _detect_rhythm_instability(cycles=cycles, baseline=baseline),
    ]
    return [anomaly for anomaly in anomalies if anomaly is not None]


def _detect_missing_events(
    cycles: list[list[Event]], baseline: ValidationBaseline
) -> Anomaly | None:
    evidence: list[EvidenceRecord] = []
    expected_events = {
        event_name
        for event_name, expected_count in baseline.event_frequencies.items()
        if expected_count > 0
    }

    for cycle_id, cycle in enumerate(cycles, start=1):
        events_by_name = {event.event_name: event for event in cycle}
        timestamp = _cycle_timestamp(cycle)
        for event_name in sorted(expected_events):
            if event_name not in events_by_name:
                evidence.append(
                    EvidenceRecord(
                        issue_type="MissingEvent",
                        cycle_id=cycle_id,
                        timestamp=timestamp,
                        event_name=event_name,
                        details=f"Expected event {event_name} was absent from cycle.",
                    )
                )

    if not evidence:
        return None
    return Anomaly(
        issue_type="MissingEvent",
        confidence=_confidence_from_count(len(evidence)),
        evidence=evidence,
    )


def _detect_sequence_violations(cycles: list[list[Event]]) -> Anomaly | None:
    evidence: list[EvidenceRecord] = []
    expected_positions = {
        event_name: index for index, event_name in enumerate(MACHINE_SEQUENCE)
    }

    for cycle_id, cycle in enumerate(cycles, start=1):
        observed_sequence = [event.event_name for event in cycle]
        previous_position = -1
        for event_name in observed_sequence:
            position = expected_positions.get(event_name)
            if position is None:
                continue
            if position < previous_position:
                evidence.append(
                    EvidenceRecord(
                        issue_type="SequenceViolation",
                        cycle_id=cycle_id,
                        timestamp=_cycle_timestamp(cycle),
                        event_name=event_name,
                        details=f"Event {event_name} arrived outside expected sequence.",
                    )
                )
            previous_position = max(previous_position, position)

        missing_sequence_events = [
            event_name for event_name in MACHINE_SEQUENCE if event_name not in observed_sequence
        ]
        if missing_sequence_events:
            evidence.append(
                EvidenceRecord(
                    issue_type="SequenceViolation",
                    cycle_id=cycle_id,
                    timestamp=_cycle_timestamp(cycle),
                    event_name=missing_sequence_events[0],
                    details=(
                        "Expected sequence incomplete; missing "
                        + ", ".join(missing_sequence_events)
                        + "."
                    ),
                )
            )

    if not evidence:
        return None
    return Anomaly(
        issue_type="SequenceViolation",
        confidence=_confidence_from_count(len(evidence)),
        evidence=evidence,
    )


def _detect_excessive_lag(
    cycles: list[list[Event]],
    baseline: ValidationBaseline,
    relationships: list[EventRelationship],
) -> Anomaly | None:
    evidence: list[EvidenceRecord] = []

    for relationship in relationships:
        baseline_stats = baseline.relationships.get(relationship.key)
        if baseline_stats is None or baseline_stats.sample_count == 0:
            continue

        threshold_ms = max(100.0, baseline_stats.stddev_ms * 3.0)
        for cycle_id, cycle in enumerate(cycles, start=1):
            observed_ms = _relationship_lag_ms(cycle, relationship)
            if observed_ms is None:
                continue
            delta_ms = observed_ms - baseline_stats.avg_ms
            deviation_percent = _deviation_percent(observed_ms, baseline_stats.avg_ms)
            if delta_ms > threshold_ms and deviation_percent > 20.0:
                evidence.append(
                    EvidenceRecord(
                        issue_type="ExcessiveLag",
                        relationship=relationship.name,
                        cycle_id=cycle_id,
                        timestamp=_cycle_timestamp(cycle),
                        expected_ms=baseline_stats.avg_ms,
                        observed_ms=observed_ms,
                        deviation_percent=deviation_percent,
                        details=f"{relationship.key} exceeded baseline lag.",
                    )
                )

    if not evidence:
        return None
    return Anomaly(
        issue_type="ExcessiveLag",
        confidence=_confidence_from_count(len(evidence)),
        evidence=evidence,
    )


def _detect_increasing_drift(
    cycles: list[list[Event]],
    baseline: ValidationBaseline,
    relationships: list[EventRelationship],
) -> Anomaly | None:
    evidence: list[EvidenceRecord] = []

    for relationship in relationships:
        baseline_stats = baseline.relationships.get(relationship.key)
        if baseline_stats is None or baseline_stats.sample_count == 0:
            continue
        observed_values = [
            lag_ms
            for cycle in cycles
            if (lag_ms := _relationship_lag_ms(cycle, relationship)) is not None
        ]
        if len(observed_values) < 3:
            continue

        slope_ms = _average_step_change(observed_values)
        total_change_ms = observed_values[-1] - observed_values[0]
        min_total_change_ms = max(50.0, baseline_stats.avg_ms * 0.10)
        if slope_ms > 5.0 and total_change_ms > min_total_change_ms:
            evidence.append(
                EvidenceRecord(
                    issue_type="IncreasingDrift",
                    relationship=relationship.name,
                    cycle_id=len(observed_values),
                    timestamp=_last_cycle_timestamp(cycles),
                    expected_ms=baseline_stats.avg_ms,
                    observed_ms=observed_values[-1],
                    deviation_percent=_deviation_percent(
                        observed_values[-1], baseline_stats.avg_ms
                    ),
                    details=(
                        f"{relationship.key} increased by "
                        f"{total_change_ms:.1f} ms across observed cycles."
                    ),
                )
            )

    if not evidence:
        return None
    return Anomaly(
        issue_type="IncreasingDrift",
        confidence=_confidence_from_count(len(evidence), base=0.78),
        evidence=evidence,
    )


def _detect_rhythm_instability(
    cycles: list[list[Event]], baseline: ValidationBaseline
) -> Anomaly | None:
    durations = [
        duration_ms
        for cycle in cycles
        if (duration_ms := _cycle_duration_ms(cycle)) is not None
    ]
    if len(durations) < 3:
        return None

    observed_stddev_ms = pstdev(durations)
    threshold_ms = baseline.cycle_duration.stddev_ms + max(
        25.0, baseline.cycle_duration.avg_ms * 0.005
    )
    if observed_stddev_ms <= threshold_ms:
        return None

    evidence = [
        EvidenceRecord(
            issue_type="RhythmInstability",
            cycle_id=None,
            timestamp=_last_cycle_timestamp(cycles),
            expected_ms=baseline.cycle_duration.stddev_ms,
            observed_ms=observed_stddev_ms,
            deviation_percent=_deviation_percent(
                observed_stddev_ms,
                baseline.cycle_duration.stddev_ms or threshold_ms,
            ),
            details="Cycle-duration variance exceeded baseline rhythm variance.",
        )
    ]
    return Anomaly(
        issue_type="RhythmInstability",
        confidence=_confidence_from_ratio(observed_stddev_ms, threshold_ms),
        evidence=evidence,
    )


def _relationship_lag_ms(
    cycle: list[Event], relationship: EventRelationship
) -> float | None:
    events_by_name = {event.event_name: event for event in cycle}
    from_event = events_by_name.get(relationship.from_event)
    to_event = events_by_name.get(relationship.to_event)
    if from_event is None or to_event is None:
        return None
    return (to_event.timestamp - from_event.timestamp).total_seconds() * 1000


def _cycle_duration_ms(cycle: list[Event]) -> float | None:
    events_by_name = {event.event_name: event for event in cycle}
    start_event = events_by_name.get("CycleStart")
    complete_event = events_by_name.get("CycleComplete")
    if start_event is None or complete_event is None:
        return None
    return (complete_event.timestamp - start_event.timestamp).total_seconds() * 1000


def _average_step_change(values: list[float]) -> float:
    step_changes = [
        current - previous for previous, current in zip(values, values[1:])
    ]
    return mean(step_changes)


def _cycle_timestamp(cycle: list[Event]) -> str:
    if not cycle:
        return ""
    return cycle[0].timestamp.isoformat()


def _last_cycle_timestamp(cycles: list[list[Event]]) -> str:
    if not cycles:
        return ""
    return _cycle_timestamp(cycles[-1])


def _deviation_percent(observed: float, expected: float) -> float:
    if expected == 0:
        return 0.0
    return ((observed - expected) / expected) * 100.0


def _confidence_from_count(count: int, base: float = 0.72) -> float:
    return min(0.99, base + (count * 0.03))


def _confidence_from_ratio(observed: float, threshold: float) -> float:
    if threshold <= 0:
        return 0.99
    return min(0.99, 0.70 + min(0.25, (observed / threshold - 1.0) * 0.10))


def _round_optional(value: float | None) -> float | None:
    return round(value, 3) if value is not None else None
