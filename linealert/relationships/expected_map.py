"""Load expected relationship integrity maps from configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from linealert.relationships.relationship_model import RelationshipDefinition


@dataclass(frozen=True)
class ExpectedRelationshipMap:
    """Configured relationships expected during machine operation."""

    relationships: list[RelationshipDefinition]

    def required_relationships(self) -> list[RelationshipDefinition]:
        return [
            relationship
            for relationship in self.relationships
            if relationship.required
        ]

    def as_dict(self) -> dict[str, object]:
        return {
            "relationships": [
                relationship.as_dict() for relationship in self.relationships
            ]
        }


def load_expected_relationship_map(config_path: str | Path) -> ExpectedRelationshipMap:
    """Load expected source/target coordination relationships from JSON."""

    path = Path(config_path)
    with path.open("r", encoding="utf-8") as config_file:
        raw_config = json.load(config_file)
    if not isinstance(raw_config, dict):
        raise ValueError(f"Relationship integrity config must be an object: {path}")

    raw_relationships = raw_config.get("relationships")
    if not isinstance(raw_relationships, list):
        raise ValueError("Relationship integrity config requires relationships list")

    relationships = [
        _parse_relationship(raw_relationship=raw_relationship, index=index)
        for index, raw_relationship in enumerate(raw_relationships, start=1)
    ]
    return ExpectedRelationshipMap(relationships=relationships)


def _parse_relationship(
    raw_relationship: object, index: int
) -> RelationshipDefinition:
    if not isinstance(raw_relationship, dict):
        raise ValueError(f"Relationship {index} must be an object")

    source = _required_str(raw_relationship, "source", index)
    target = _required_str(raw_relationship, "target", index)
    if source == target:
        raise ValueError(f"Relationship {index} source and target must differ")

    return RelationshipDefinition(
        source=source,
        target=target,
        required=bool(raw_relationship.get("required", True)),
    )


def _required_str(raw_relationship: dict[str, object], field_name: str, index: int) -> str:
    value = raw_relationship.get(field_name)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Relationship {index} missing required field: {field_name}")
    return str(value)
