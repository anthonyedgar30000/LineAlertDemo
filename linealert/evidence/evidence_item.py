"""Normalized evidence item with explicit provenance."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvidenceItem:
    """One observation from an evidence-producing system."""

    source: str
    observation: str
    severity: str
    confidence: float
    timestamp: str
    cycle_id: int | None
    source_evidence: dict[str, object]
    cluster: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.source, "source")
        _require_nonempty(self.observation, "observation")
        _require_nonempty(self.severity, "severity")
        _require_nonempty(self.timestamp, "timestamp")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

    @property
    def cluster_key(self) -> str:
        return self.cluster or self.observation

    def as_dict(self) -> dict[str, object]:
        output: dict[str, object] = {
            "source": self.source,
            "observation": self.observation,
            "severity": self.severity,
            "confidence": round(self.confidence, 3),
            "timestamp": self.timestamp,
            "cycle_id": self.cycle_id,
            "source_evidence": dict(self.source_evidence),
            "cluster": self.cluster_key,
        }
        if self.metadata:
            output["metadata"] = dict(self.metadata)
        return output


def _require_nonempty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
