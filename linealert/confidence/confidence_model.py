"""Confidence model for observation-only confidence reports."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceFactor:
    """Explicit evidence-based factor contributing to confidence."""

    name: str
    description: str
    contribution: float

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "contribution": round(self.contribution, 3),
        }


@dataclass(frozen=True)
class ObservationConfidence:
    """Confidence score for one observation."""

    observation: str
    confidence: float
    classification: str
    factors: list[ConfidenceFactor]

    def as_dict(self) -> dict[str, object]:
        return {
            "observation": self.observation,
            "confidence": round(self.confidence, 3),
            "classification": self.classification,
            "factors": [factor.as_dict() for factor in self.factors],
        }
