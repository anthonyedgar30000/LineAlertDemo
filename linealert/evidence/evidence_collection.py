"""Collections of normalized evidence items."""

from __future__ import annotations

from dataclasses import dataclass

from linealert.evidence.evidence_item import EvidenceItem


@dataclass(frozen=True)
class EvidenceCollection:
    """Evidence package before fusion."""

    items: list[EvidenceItem]

    @property
    def evidence_count(self) -> int:
        return len(self.items)

    @property
    def evidence_density(self) -> int:
        """Observation density as total observations in the package."""

        return len(self.items)

    @property
    def source_distribution(self) -> dict[str, int]:
        distribution: dict[str, int] = {}
        for item in self.items:
            distribution[item.source] = distribution.get(item.source, 0) + 1
        return dict(sorted(distribution.items()))

    @property
    def sources_contributing(self) -> int:
        return len(self.source_distribution)

    def by_cluster(self) -> dict[str, list[EvidenceItem]]:
        clusters: dict[str, list[EvidenceItem]] = {}
        for item in self.items:
            clusters.setdefault(item.cluster_key, []).append(item)
        return dict(sorted(clusters.items()))

    def as_dict(self) -> dict[str, object]:
        return {
            "evidence_count": self.evidence_count,
            "evidence_density": self.evidence_density,
            "source_distribution": self.source_distribution,
            "sources_contributing": self.sources_contributing,
            "items": [item.as_dict() for item in self.items],
        }
