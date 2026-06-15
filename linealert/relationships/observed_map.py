"""Build observed relationship maps from cycle event order."""

from __future__ import annotations

from dataclasses import dataclass

from linealert.cycles.cycle import Cycle
from linealert.relationships.expected_map import ExpectedRelationshipMap
from linealert.relationships.relationship_model import ObservedRelationship


@dataclass(frozen=True)
class ObservedRelationshipMap:
    """Observed coordination state for expected relationships by cycle."""

    observed_relationships: list[ObservedRelationship]

    def for_relationship(self, relationship_key: str) -> list[ObservedRelationship]:
        return [
            relationship
            for relationship in self.observed_relationships
            if relationship.key == relationship_key
        ]

    def as_dict(self) -> dict[str, object]:
        return {
            "observed_relationships": [
                relationship.as_dict()
                for relationship in self.observed_relationships
            ]
        }


def build_observed_relationship_map(
    cycles: list[Cycle],
    expected_map: ExpectedRelationshipMap,
) -> ObservedRelationshipMap:
    """Evaluate configured relationships against each cycle's event order."""

    observed_relationships: list[ObservedRelationship] = []
    for cycle in cycles:
        event_positions = _event_positions(cycle)
        for expected_relationship in expected_map.relationships:
            observed_relationships.append(
                _observe_relationship(
                    cycle_id=cycle.cycle_id,
                    event_positions=event_positions,
                    source=expected_relationship.source,
                    target=expected_relationship.target,
                )
            )

    return ObservedRelationshipMap(observed_relationships=observed_relationships)


def _event_positions(cycle: Cycle) -> dict[str, int]:
    positions: dict[str, int] = {}
    for index, event in enumerate(cycle.events):
        positions.setdefault(event.event_name, index)
    return positions


def _observe_relationship(
    cycle_id: int,
    event_positions: dict[str, int],
    source: str,
    target: str,
) -> ObservedRelationship:
    source_index = event_positions.get(source)
    target_index = event_positions.get(target)
    source_present = source_index is not None
    target_present = target_index is not None
    order_valid = (
        source_present
        and target_present
        and source_index is not None
        and target_index is not None
        and source_index < target_index
    )

    return ObservedRelationship(
        cycle_id=cycle_id,
        source=source,
        target=target,
        source_present=source_present,
        target_present=target_present,
        observed=order_valid,
        order_valid=order_valid,
        source_index=source_index,
        target_index=target_index,
    )
