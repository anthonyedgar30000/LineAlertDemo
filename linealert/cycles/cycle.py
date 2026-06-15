"""First-class machine cycle context for LineAlert evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

try:
    from event_loader import Event
except ImportError:  # pragma: no cover - used when imported from repository root.
    from linealert.src.event_loader import Event


class CycleStatus(str, Enum):
    """Measurement-only cycle status."""

    HEALTHY = "Healthy"
    MONITOR = "Monitor"
    OUT_OF_BASELINE = "OutOfBaseline"


@dataclass(frozen=True)
class CycleMeasurement:
    """A measured value inside a machine cycle."""

    name: str
    metric: str
    observed_ms: float | None
    relationship: str | None = None
    relationship_key: str | None = None
    baseline_ms: float | None = None
    deviation_ms: float | None = None
    deviation_percent: float | None = None
    status: CycleStatus = CycleStatus.HEALTHY

    def as_dict(self) -> dict[str, object]:
        output: dict[str, object] = {
            "name": self.name,
            "metric": self.metric,
            "status": self.status.value,
        }
        optional_values = {
            "relationship": self.relationship,
            "relationship_key": self.relationship_key,
            "observed_ms": _round_optional(self.observed_ms),
            "baseline_ms": _round_optional(self.baseline_ms),
            "deviation_ms": _round_optional(self.deviation_ms),
            "deviation_percent": _round_optional(self.deviation_percent),
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
class CycleEvidence:
    """Measurement evidence attached to a specific cycle."""

    cycle_id: int
    relationship: str
    measurement: str
    observed_ms: float | None
    baseline_ms: float | None
    deviation_percent: float | None
    status: CycleStatus

    def as_dict(self) -> dict[str, object]:
        output: dict[str, object] = {
            "cycle_id": self.cycle_id,
            "relationship": self.relationship,
            "measurement": self.measurement,
            "status": self.status.value,
        }
        optional_values = {
            "observed_ms": _round_optional(self.observed_ms),
            "baseline_ms": _round_optional(self.baseline_ms),
            "deviation_percent": _round_optional(self.deviation_percent),
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
class Cycle:
    """Operational context for one machine cycle."""

    cycle_id: int
    start_timestamp: datetime
    end_timestamp: datetime
    duration_ms: float
    events: list[Event]
    measurements: list[CycleMeasurement]
    evidence: list[CycleEvidence]
    status: CycleStatus

    def as_dict(self) -> dict[str, object]:
        return {
            "cycle_id": self.cycle_id,
            "start_timestamp": self.start_timestamp.isoformat(),
            "end_timestamp": self.end_timestamp.isoformat(),
            "duration_ms": round(self.duration_ms, 3),
            "status": self.status.value,
            "events": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "event_name": event.event_name,
                    "source_row": event.source_row,
                }
                for event in self.events
            ],
            "measurements": [
                measurement.as_dict() for measurement in self.measurements
            ],
            "evidence": [evidence.as_dict() for evidence in self.evidence],
        }


def _round_optional(value: float | None) -> float | None:
    return round(value, 3) if value is not None else None
