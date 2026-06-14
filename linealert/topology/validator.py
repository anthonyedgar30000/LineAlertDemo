"""Validate machine topology structure and return observations only."""

from __future__ import annotations

from dataclasses import dataclass

from linealert.topology.topology import MachineTopology, connected_components


@dataclass(frozen=True)
class TopologyValidationObservation:
    """A measurable topology-structure observation."""

    observation_type: str
    component_id: str | None = None
    dependency: str | None = None
    details: str = ""

    def as_dict(self) -> dict[str, object]:
        output: dict[str, object] = {
            "observation_type": self.observation_type,
            "details": self.details,
        }
        if self.component_id is not None:
            output["component_id"] = self.component_id
        if self.dependency is not None:
            output["dependency"] = self.dependency
        return output


@dataclass(frozen=True)
class TopologyValidationReport:
    """Validation report containing observations only."""

    missing_components: list[str]
    orphan_components: list[str]
    circular_dependencies: list[str]
    disconnected_chains: list[list[str]]
    observations: list[TopologyValidationObservation]

    def as_dict(self) -> dict[str, object]:
        return {
            "missing_components": list(self.missing_components),
            "orphan_components": list(self.orphan_components),
            "circular_dependencies": list(self.circular_dependencies),
            "disconnected_chains": [list(chain) for chain in self.disconnected_chains],
            "observations": [
                observation.as_dict() for observation in self.observations
            ],
        }


def validate_topology(topology: MachineTopology) -> TopologyValidationReport:
    """Validate topology structure without producing diagnoses."""

    missing_components = _missing_components(topology)
    orphan_components = _orphan_components(topology)
    circular_dependencies = _circular_dependencies(topology)
    disconnected_chains = _disconnected_chains(topology)
    observations = [
        *_missing_component_observations(missing_components),
        *_orphan_observations(orphan_components),
        *_cycle_observations(circular_dependencies),
        *_disconnected_chain_observations(disconnected_chains),
    ]

    return TopologyValidationReport(
        missing_components=missing_components,
        orphan_components=orphan_components,
        circular_dependencies=circular_dependencies,
        disconnected_chains=disconnected_chains,
        observations=observations,
    )


def _missing_components(topology: MachineTopology) -> list[str]:
    referenced_components: set[str] = set()
    for dependency in topology.dependencies:
        referenced_components.add(dependency.upstream)
        referenced_components.add(dependency.downstream)
    return sorted(
        component_id
        for component_id in referenced_components
        if component_id not in topology.components
    )


def _orphan_components(topology: MachineTopology) -> list[str]:
    connected_components_ids: set[str] = set()
    for dependency in topology.dependencies:
        connected_components_ids.add(dependency.upstream)
        connected_components_ids.add(dependency.downstream)
    return sorted(
        component_id
        for component_id in topology.components
        if component_id not in connected_components_ids
    )


def _circular_dependencies(topology: MachineTopology) -> list[str]:
    adjacency = topology.adjacency()
    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: set[str] = set()

    def visit(component_id: str, path: list[str]) -> None:
        if component_id in visiting:
            cycle_start = path.index(component_id)
            cycle_path = path[cycle_start:]
            cycles.add(" -> ".join(cycle_path))
            return
        if component_id in visited:
            return

        visiting.add(component_id)
        for downstream in adjacency.get(component_id, []):
            visit(downstream, [*path, downstream])
        visiting.remove(component_id)
        visited.add(component_id)

    for component_id in sorted(adjacency):
        visit(component_id, [component_id])

    return sorted(cycles)


def _disconnected_chains(topology: MachineTopology) -> list[list[str]]:
    groups = connected_components(topology)
    if len(groups) <= 1:
        return []
    return groups


def _missing_component_observations(
    missing_components: list[str],
) -> list[TopologyValidationObservation]:
    return [
        TopologyValidationObservation(
            observation_type="MissingComponent",
            component_id=component_id,
            details=f"Dependency references undefined component {component_id}.",
        )
        for component_id in missing_components
    ]


def _orphan_observations(
    orphan_components: list[str],
) -> list[TopologyValidationObservation]:
    return [
        TopologyValidationObservation(
            observation_type="OrphanComponent",
            component_id=component_id,
            details=f"Component {component_id} has no topology dependencies.",
        )
        for component_id in orphan_components
    ]


def _cycle_observations(
    circular_dependencies: list[str],
) -> list[TopologyValidationObservation]:
    return [
        TopologyValidationObservation(
            observation_type="CircularDependency",
            dependency=dependency,
            details=f"Dependency cycle observed: {dependency}.",
        )
        for dependency in circular_dependencies
    ]


def _disconnected_chain_observations(
    disconnected_chains: list[list[str]],
) -> list[TopologyValidationObservation]:
    if not disconnected_chains:
        return []
    return [
        TopologyValidationObservation(
            observation_type="DisconnectedChain",
            details="Disconnected topology chain observed: " + " -> ".join(chain) + ".",
        )
        for chain in disconnected_chains
    ]
