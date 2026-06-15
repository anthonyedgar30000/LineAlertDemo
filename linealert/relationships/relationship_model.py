"""Relationship integrity data models.

Relationship integrity compares configured coordination expectations against
observed event order. It reports observations only; no diagnosis, maintenance
recommendations, or root-cause inference are produced here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RelationshipDefinition:
    """Expected coordination between two events."""

    source: str
    target: str
    required: bool = True

    @property
    def key(self) -> str:
        return f"{self.source}->{self.target}"

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "target": self.target,
            "required": self.required,
        }


@dataclass(frozen=True)
class ObservedRelationship:
    """Observed relationship state within one cycle."""

    cycle_id: int
    source: str
    target: str
    source_present: bool
    target_present: bool
    observed: bool
    order_valid: bool
    source_index: int | None = None
    target_index: int | None = None

    @property
    def key(self) -> str:
        return f"{self.source}->{self.target}"

    def as_dict(self) -> dict[str, object]:
        output: dict[str, object] = {
            "cycle_id": self.cycle_id,
            "source": self.source,
            "target": self.target,
            "source_present": self.source_present,
            "target_present": self.target_present,
            "observed": self.observed,
            "order_valid": self.order_valid,
        }
        if self.source_index is not None:
            output["source_index"] = self.source_index
        if self.target_index is not None:
            output["target_index"] = self.target_index
        return output


@dataclass(frozen=True)
class RelationshipIntegrityObservation:
    """Deviation between expected and observed relationship integrity."""

    observation_type: str
    relationship: str
    source: str
    target: str
    required: bool
    cycle_id: int
    details: str

    def as_dict(self) -> dict[str, object]:
        return {
            "observation_type": self.observation_type,
            "relationship": self.relationship,
            "source": self.source,
            "target": self.target,
            "required": self.required,
            "cycle_id": self.cycle_id,
            "details": self.details,
        }
