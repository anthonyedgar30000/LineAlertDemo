"""Topology reports and topology-aware evidence context helpers."""

from __future__ import annotations

from typing import Iterable

from linealert.topology.topology import MachineTopology
from linealert.topology.validator import validate_topology
from validation.baseline import EventRelationship


def generate_topology_report(topology: MachineTopology) -> dict[str, object]:
    """Return a structural topology report with observations only."""

    validation = validate_topology(topology).as_dict()
    return {
        "component_count": topology.component_count,
        "dependency_count": topology.dependency_count,
        **validation,
    }


def attach_topology_context_to_evidence(
    evidence_records: Iterable[dict[str, object]],
    topology: MachineTopology,
    relationships: Iterable[EventRelationship],
) -> list[dict[str, object]]:
    """Attach component context to evidence dictionaries without changing evidence logic."""

    component_by_relationship = _component_by_relationship(
        topology=topology,
        relationships=relationships,
    )
    enriched_records: list[dict[str, object]] = []
    for evidence in evidence_records:
        enriched = dict(evidence)
        relationship_name = evidence.get("relationship")
        component_id = (
            component_by_relationship.get(str(relationship_name))
            if relationship_name is not None
            else None
        )
        if component_id is not None:
            component = topology.components.get(component_id)
            enriched.update(
                {
                    "component_id": component_id,
                    "component_name": component.name if component is not None else component_id,
                    "upstream_components": topology.upstream_components(component_id),
                    "downstream_components": topology.downstream_components(component_id),
                }
            )
        enriched_records.append(enriched)

    return enriched_records


def _component_by_relationship(
    topology: MachineTopology,
    relationships: Iterable[EventRelationship],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for relationship in relationships:
        component_id = topology.event_component_map.get(relationship.from_event)
        if component_id is not None:
            mapping[relationship.name] = component_id
    return mapping
