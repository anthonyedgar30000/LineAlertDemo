"""Observation-only historical drift tracking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DriftMeasurement:
    """Measured value for a metric at a cycle."""

    metric_name: str
    cycle_id: int
    timestamp: str
    value: float
    unit: str = "ms"

    def as_dict(self) -> dict[str, object]:
        return {
            "metric_name": self.metric_name,
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp,
            "value": self.value,
            "unit": self.unit,
        }


@dataclass(frozen=True)
class HistoricalDriftIndicator:
    """Observed historical value movement for one metric."""

    metric_name: str
    start_cycle: int
    end_cycle: int
    start_value: float
    end_value: float
    change: float
    unit: str
    direction: str
    status: str

    def as_dict(self) -> dict[str, object]:
        return {
            "metric_name": self.metric_name,
            "start_cycle": self.start_cycle,
            "end_cycle": self.end_cycle,
            "start_value": self.start_value,
            "end_value": self.end_value,
            "change": round(self.change, 3),
            "unit": self.unit,
            "direction": self.direction,
            "status": self.status,
        }


def track_historical_drift(
    measurements: list[DriftMeasurement],
    metric_name: str,
) -> HistoricalDriftIndicator:
    metric_measurements = sorted(
        [
            measurement
            for measurement in measurements
            if measurement.metric_name == metric_name
        ],
        key=lambda measurement: (measurement.cycle_id, measurement.timestamp),
    )
    if not metric_measurements:
        raise ValueError(f"No drift measurements found for metric: {metric_name}")

    start = metric_measurements[0]
    end = metric_measurements[-1]
    change = end.value - start.value
    direction = _direction(change)
    return HistoricalDriftIndicator(
        metric_name=metric_name,
        start_cycle=start.cycle_id,
        end_cycle=end.cycle_id,
        start_value=start.value,
        end_value=end.value,
        change=change,
        unit=end.unit,
        direction=direction,
        status=_status(direction),
    )


def _direction(change: float) -> str:
    if change > 0:
        return "Increasing"
    if change < 0:
        return "Decreasing"
    return "Flat"


def _status(direction: str) -> str:
    if direction == "Increasing":
        return "Historical Increase Detected"
    if direction == "Decreasing":
        return "Historical Decrease Detected"
    return "No Historical Change Detected"
