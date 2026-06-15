"""Validate observed cycles against configured dependency chains."""

from __future__ import annotations

from dataclasses import dataclass

from linealert.cycles.cycle import Cycle
from linealert.dependencies.dependency_chain import DependencyChain
from linealert.dependencies.path_health import (
    DependencyPathHealth,
    calculate_path_health,
)


@dataclass(frozen=True)
class DependencyChainObservation:
    """Observation-only dependency chain disruption."""

    observation_type: str
    chain_id: str
    cycle_id: int
    event_name: str | None
    source: str | None
    target: str | None
    details: str

    def as_dict(self) -> dict[str, object]:
        output: dict[str, object] = {
            "observation_type": self.observation_type,
            "chain_id": self.chain_id,
            "cycle_id": self.cycle_id,
            "details": self.details,
        }
        if self.event_name is not None:
            output["event_name"] = self.event_name
        if self.source is not None:
            output["source"] = self.source
        if self.target is not None:
            output["target"] = self.target
        return output


@dataclass(frozen=True)
class DependencyChainValidationReport:
    """Dependency chain validation result with observations only."""

    chain_count: int
    observed_cycle_count: int
    path_health: list[DependencyPathHealth]
    observations: list[DependencyChainObservation]

    @property
    def observation_count(self) -> int:
        return len(self.observations)

    @property
    def integrity_status(self) -> str:
        return "Healthy" if not self.observations else "Disruptions Observed"

    def as_dict(self) -> dict[str, object]:
        return {
            "chain_count": self.chain_count,
            "observed_cycle_count": self.observed_cycle_count,
            "path_health": [health.as_dict() for health in self.path_health],
            "observation_count": self.observation_count,
            "integrity_status": self.integrity_status,
            "observations": [
                observation.as_dict() for observation in self.observations
            ],
        }


def validate_dependency_chains(
    cycles: list[Cycle],
    chains: list[DependencyChain],
) -> DependencyChainValidationReport:
    """Validate dependency chains against observed cycle event order."""

    observations: list[DependencyChainObservation] = []
    disrupted_cycles_by_chain: dict[str, set[int]] = {
        chain.chain_id: set() for chain in chains
    }

    for cycle in cycles:
        event_positions = _event_positions(cycle)
        for chain in chains:
            cycle_observations = _validate_cycle_chain(
                cycle_id=cycle.cycle_id,
                event_positions=event_positions,
                chain=chain,
            )
            if cycle_observations:
                disrupted_cycles_by_chain[chain.chain_id].add(cycle.cycle_id)
            observations.extend(cycle_observations)

    path_health = [
        calculate_path_health(
            chain_id=chain.chain_id,
            events=chain.events,
            cycles_observed=len(cycles),
            disrupted_cycle_ids=disrupted_cycles_by_chain[chain.chain_id],
        )
        for chain in chains
    ]

    return DependencyChainValidationReport(
        chain_count=len(chains),
        observed_cycle_count=len(cycles),
        path_health=path_health,
        observations=observations,
    )


def _validate_cycle_chain(
    cycle_id: int,
    event_positions: dict[str, int],
    chain: DependencyChain,
) -> list[DependencyChainObservation]:
    observations: list[DependencyChainObservation] = []
    for event_name in chain.events:
        if event_name not in event_positions:
            observations.append(
                DependencyChainObservation(
                    observation_type="MissingDependencyEvent",
                    chain_id=chain.chain_id,
                    cycle_id=cycle_id,
                    event_name=event_name,
                    source=None,
                    target=None,
                    details=(
                        f"Expected dependency chain event {event_name} "
                        f"was not observed in cycle {cycle_id}."
                    ),
                )
            )

    for source, target in chain.direct_edges:
        source_index = event_positions.get(source)
        target_index = event_positions.get(target)
        if source_index is None or target_index is None:
            continue
        if source_index >= target_index:
            observations.append(
                DependencyChainObservation(
                    observation_type="DependencyOrderDisruption",
                    chain_id=chain.chain_id,
                    cycle_id=cycle_id,
                    event_name=None,
                    source=source,
                    target=target,
                    details=(
                        f"Dependency edge {source}->{target} was not observed "
                        f"in expected order in cycle {cycle_id}."
                    ),
                )
            )

    return observations


def _event_positions(cycle: Cycle) -> dict[str, int]:
    positions: dict[str, int] = {}
    for index, event in enumerate(cycle.events):
        positions.setdefault(event.event_name, index)
    return positions
