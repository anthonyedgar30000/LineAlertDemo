"""History utilities for collections of machine cycles."""

from __future__ import annotations

from statistics import mean

from linealert.cycles.cycle import Cycle


class CycleHistory:
    """Query aggregate measurements across cycle context objects."""

    def __init__(self, cycles: list[Cycle]) -> None:
        self.cycles = list(cycles)

    def last(self, count: int) -> list[Cycle]:
        if count < 1:
            raise ValueError("count must be at least 1")
        return self.cycles[-count:]

    def average_cycle_duration_ms(self) -> float:
        if not self.cycles:
            return 0.0
        return mean(cycle.duration_ms for cycle in self.cycles)

    def average_lag_ms(self, relationship: str) -> float:
        values = [
            measurement.observed_ms
            for cycle in self.cycles
            for measurement in cycle.measurements
            if measurement.relationship == relationship
            and measurement.observed_ms is not None
        ]
        if not values:
            return 0.0
        return mean(values)

    def trend_over_cycles(self, relationship: str | None = None) -> dict[str, float | str]:
        values = (
            self._relationship_values(relationship)
            if relationship is not None
            else [cycle.duration_ms for cycle in self.cycles]
        )
        if len(values) < 2:
            return {
                "metric": relationship or "cycle_duration_ms",
                "slope_ms_per_cycle": 0.0,
                "direction": "flat",
            }

        slope = _average_step_change(values)
        return {
            "metric": relationship or "cycle_duration_ms",
            "slope_ms_per_cycle": round(slope, 3),
            "direction": _trend_direction(slope),
        }

    def _relationship_values(self, relationship: str) -> list[float]:
        return [
            measurement.observed_ms
            for cycle in self.cycles
            for measurement in cycle.measurements
            if measurement.relationship == relationship
            and measurement.observed_ms is not None
        ]


def _average_step_change(values: list[float]) -> float:
    step_changes = [
        current - previous for previous, current in zip(values, values[1:])
    ]
    return mean(step_changes)


def _trend_direction(slope: float) -> str:
    if slope > 0:
        return "increasing"
    if slope < 0:
        return "decreasing"
    return "flat"
