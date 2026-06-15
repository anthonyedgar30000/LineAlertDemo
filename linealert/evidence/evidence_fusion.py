"""Observation-only evidence fusion.

Evidence Fusion aggregates existing observations. It never invents evidence:
each fused cluster contains the original source system, source evidence,
timestamp, and cycle id for every supporting item.
"""

from __future__ import annotations

from dataclasses import dataclass

from linealert.evidence.evidence_collection import EvidenceCollection
from linealert.evidence.evidence_item import EvidenceItem
from linealert.evidence.evidence_score import aggregate_severity, average_confidence


@dataclass(frozen=True)
class ObservationCluster:
    """A group of evidence items sharing a caller-provided observation cluster."""

    cluster: str
    supporting_evidence: list[EvidenceItem]
    evidence_count: int
    sources_contributing: int
    source_distribution: dict[str, int]
    cycles_observed: list[int]
    severity: str
    confidence: float

    def as_dict(self) -> dict[str, object]:
        return {
            "cluster": self.cluster,
            "evidence_count": self.evidence_count,
            "sources_contributing": self.sources_contributing,
            "source_distribution": dict(self.source_distribution),
            "cycles_observed": list(self.cycles_observed),
            "severity": self.severity,
            "confidence": self.confidence,
            "supporting_evidence": [
                item.as_dict() for item in self.supporting_evidence
            ],
        }


@dataclass(frozen=True)
class FusedEvidencePackage:
    """Fused evidence package with provenance-preserving clusters."""

    evidence_count: int
    evidence_density: int
    source_distribution: dict[str, int]
    sources_contributing: int
    observation_clusters: list[ObservationCluster]

    def as_dict(self) -> dict[str, object]:
        return {
            "evidence_count": self.evidence_count,
            "evidence_density": self.evidence_density,
            "source_distribution": dict(self.source_distribution),
            "sources_contributing": self.sources_contributing,
            "observation_clusters": [
                cluster.as_dict() for cluster in self.observation_clusters
            ],
        }


def fuse_evidence(collection: EvidenceCollection) -> FusedEvidencePackage:
    """Aggregate evidence items into provenance-preserving observation clusters."""

    clusters = [
        _build_cluster(cluster=cluster, items=items)
        for cluster, items in collection.by_cluster().items()
    ]
    return FusedEvidencePackage(
        evidence_count=collection.evidence_count,
        evidence_density=collection.evidence_density,
        source_distribution=collection.source_distribution,
        sources_contributing=collection.sources_contributing,
        observation_clusters=clusters,
    )


def _build_cluster(cluster: str, items: list[EvidenceItem]) -> ObservationCluster:
    source_distribution: dict[str, int] = {}
    for item in items:
        source_distribution[item.source] = source_distribution.get(item.source, 0) + 1

    cycle_ids = sorted(
        {
            int(item.cycle_id)
            for item in items
            if item.cycle_id is not None
        }
    )

    return ObservationCluster(
        cluster=cluster,
        supporting_evidence=list(items),
        evidence_count=len(items),
        sources_contributing=len(source_distribution),
        source_distribution=dict(sorted(source_distribution.items())),
        cycles_observed=cycle_ids,
        severity=aggregate_severity(items),
        confidence=average_confidence(items),
    )
