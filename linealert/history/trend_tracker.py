"""Observation-only trend tracking for historical context."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from linealert.history.observation_history import ObservationHistory


@dataclass(frozen=True)
class EvidenceDensityTrend:
    """Evidence density trend across observed cycles."""

    density_by_cycle: dict[int, int]
    direction: str
    average_step_change: float

    def as_dict(self) -> dict[str, object]:
        return {
            "density_by_cycle": dict(self.density_by_cycle),
            "direction": self.direction,
            "average_step_change": round(self.average_step_change, 3),
        }


@dataclass(frozen=True)
class ClusterHistory:
    """Cluster appearance, persistence, and recurrence."""

    cluster: str
    cycles_observed: list[int]
    occurrence_count: int
    persistence_cycles: int
    recurrence_count: int

    def as_dict(self) -> dict[str, object]:
        return {
            "cluster": self.cluster,
            "cycles_observed": list(self.cycles_observed),
            "occurrence_count": self.occurrence_count,
            "persistence_cycles": self.persistence_cycles,
            "recurrence_count": self.recurrence_count,
        }


def track_evidence_density(history: ObservationHistory) -> EvidenceDensityTrend:
    density = history.evidence_density_by_cycle
    values = list(density.values())
    step_change = _average_step_change(values)
    return EvidenceDensityTrend(
        density_by_cycle=density,
        direction=_direction(step_change),
        average_step_change=step_change,
    )


def track_cluster_history(
    history: ObservationHistory,
    cluster: str,
    last_n_cycles: int | None = None,
) -> ClusterHistory:
    cycles = history.cluster_cycles(cluster)
    return ClusterHistory(
        cluster=cluster,
        cycles_observed=cycles,
        occurrence_count=len(
            [
                observation
                for observation in history.observations
                if observation.evidence_cluster == cluster
            ]
        ),
        persistence_cycles=history.cluster_persistence(cluster),
        recurrence_count=history.cluster_recurrence(
            cluster,
            last_n_cycles or max(1, len(history.cycles_observed)),
        ),
    )


def _average_step_change(values: list[int]) -> float:
    if len(values) < 2:
        return 0.0
    return mean(current - previous for previous, current in zip(values, values[1:]))


def _direction(step_change: float) -> str:
    if step_change > 0:
        return "Increasing"
    if step_change < 0:
        return "Decreasing"
    return "Flat"
