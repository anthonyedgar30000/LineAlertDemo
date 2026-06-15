"""Validate expected relationships against observed cycle coordination."""

from __future__ import annotations

from dataclasses import dataclass

from linealert.relationships.expected_map import ExpectedRelationshipMap
from linealert.relationships.observed_map import ObservedRelationshipMap
from linealert.relationships.relationship_model import (
    RelationshipIntegrityObservation,
)


@dataclass(frozen=True)
class RelationshipIntegrityReport:
    """Relationship integrity validation report with observations only."""

    expected_relationship_count: int
    observed_cycle_count: int
    valid_observation_count: int
    missing_required_relationships: list[RelationshipIntegrityObservation]
    order_violations: list[RelationshipIntegrityObservation]

    @property
    def observation_count(self) -> int:
        return len(self.missing_required_relationships) + len(self.order_violations)

    @property
    def integrity_status(self) -> str:
        return "Valid" if self.observation_count == 0 else "Observations Present"

    def observations(self) -> list[RelationshipIntegrityObservation]:
        return [
            *self.missing_required_relationships,
            *self.order_violations,
        ]

    def as_dict(self) -> dict[str, object]:
        return {
            "expected_relationship_count": self.expected_relationship_count,
            "observed_cycle_count": self.observed_cycle_count,
            "valid_observation_count": self.valid_observation_count,
            "missing_required_relationships": [
                observation.as_dict()
                for observation in self.missing_required_relationships
            ],
            "order_violations": [
                observation.as_dict()
                for observation in self.order_violations
            ],
            "observation_count": self.observation_count,
            "integrity_status": self.integrity_status,
            "observations": [
                observation.as_dict() for observation in self.observations()
            ],
        }


def validate_relationship_integrity(
    expected_map: ExpectedRelationshipMap,
    observed_map: ObservedRelationshipMap,
) -> RelationshipIntegrityReport:
    """Compare expected and observed relationship maps."""

    required_by_key = {
        relationship.key: relationship
        for relationship in expected_map.relationships
        if relationship.required
    }
    missing_required_relationships: list[RelationshipIntegrityObservation] = []
    order_violations: list[RelationshipIntegrityObservation] = []
    valid_observation_count = 0

    for observed_relationship in observed_map.observed_relationships:
        expected_relationship = required_by_key.get(observed_relationship.key)
        if expected_relationship is None:
            continue

        if observed_relationship.observed:
            valid_observation_count += 1
            continue

        if (
            observed_relationship.source_present
            and observed_relationship.target_present
            and not observed_relationship.order_valid
        ):
            order_violations.append(
                RelationshipIntegrityObservation(
                    observation_type="OrderViolation",
                    relationship=observed_relationship.key,
                    source=observed_relationship.source,
                    target=observed_relationship.target,
                    required=True,
                    cycle_id=observed_relationship.cycle_id,
                    details=(
                        f"{observed_relationship.source} was not observed before "
                        f"{observed_relationship.target} in cycle "
                        f"{observed_relationship.cycle_id}."
                    ),
                )
            )
            continue

        missing_required_relationships.append(
            RelationshipIntegrityObservation(
                observation_type="MissingRequiredRelationship",
                relationship=observed_relationship.key,
                source=observed_relationship.source,
                target=observed_relationship.target,
                required=True,
                cycle_id=observed_relationship.cycle_id,
                details=_missing_details(observed_relationship),
            )
        )

    return RelationshipIntegrityReport(
        expected_relationship_count=len(expected_map.relationships),
        observed_cycle_count=_observed_cycle_count(observed_map),
        valid_observation_count=valid_observation_count,
        missing_required_relationships=missing_required_relationships,
        order_violations=order_violations,
    )


def _observed_cycle_count(observed_map: ObservedRelationshipMap) -> int:
    return len(
        {
            relationship.cycle_id
            for relationship in observed_map.observed_relationships
        }
    )


def _missing_details(observed_relationship) -> str:
    missing_events = []
    if not observed_relationship.source_present:
        missing_events.append(observed_relationship.source)
    if not observed_relationship.target_present:
        missing_events.append(observed_relationship.target)
    missing = ", ".join(missing_events)
    return (
        f"Required relationship {observed_relationship.key} was not observed "
        f"in cycle {observed_relationship.cycle_id}; missing event(s): {missing}."
    )
