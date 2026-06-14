"""Dependency path health summaries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyPathHealth:
    """Observed health of one dependency chain path."""

    chain_id: str
    events: list[str]
    cycles_observed: int
    healthy_cycles: int
    disrupted_cycles: int
    percent_healthy: float
    status: str

    def as_dict(self) -> dict[str, object]:
        return {
            "chain_id": self.chain_id,
            "events": list(self.events),
            "cycles_observed": self.cycles_observed,
            "healthy_cycles": self.healthy_cycles,
            "disrupted_cycles": self.disrupted_cycles,
            "percent_healthy": round(self.percent_healthy, 3),
            "status": self.status,
        }


def calculate_path_health(
    chain_id: str,
    events: list[str],
    cycles_observed: int,
    disrupted_cycle_ids: set[int],
) -> DependencyPathHealth:
    disrupted_cycles = len(disrupted_cycle_ids)
    healthy_cycles = max(0, cycles_observed - disrupted_cycles)
    percent_healthy = (
        (healthy_cycles / cycles_observed) * 100 if cycles_observed else 0.0
    )
    return DependencyPathHealth(
        chain_id=chain_id,
        events=list(events),
        cycles_observed=cycles_observed,
        healthy_cycles=healthy_cycles,
        disrupted_cycles=disrupted_cycles,
        percent_healthy=percent_healthy,
        status="Healthy" if disrupted_cycles == 0 else "Disrupted",
    )
