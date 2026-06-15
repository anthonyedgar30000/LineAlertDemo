"""Observation history across cycles.

Historical Context preserves observations over time. It reports frequency,
persistence, recurrence, severity history, evidence density, and cluster
history without diagnosis, recommendations, predictions, or root-cause logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from linealert.evidence.evidence_item import EvidenceItem


@dataclass(frozen=True)
class HistoricalObservation:
    """One historical observation with full provenance."""

    cycle_id: int
    timestamp: str
    observation: str
    evidence_cluster: str
    severity: str
    confidence: float
    source_systems: list[str]
    source_evidence: list[dict[str, object]]
    metadata: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_evidence_item(cls, item: EvidenceItem) -> "HistoricalObservation":
        if item.cycle_id is None:
            raise ValueError("Historical observations require a cycle_id")
        return cls(
            cycle_id=item.cycle_id,
            timestamp=item.timestamp,
            observation=item.observation,
            evidence_cluster=item.cluster_key,
            severity=item.severity,
            confidence=item.confidence,
            source_systems=[item.source],
            source_evidence=[dict(item.source_evidence)],
            metadata=dict(item.metadata),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp,
            "observation": self.observation,
            "evidence_cluster": self.evidence_cluster,
            "severity": self.severity,
            "confidence": round(self.confidence, 3),
            "source_systems": list(self.source_systems),
            "source_evidence": [dict(evidence) for evidence in self.source_evidence],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ObservationHistory:
    """Historical observations and cycle-level query helpers."""

    observations: list[HistoricalObservation]

    @classmethod
    def from_evidence_items(cls, items: list[EvidenceItem]) -> "ObservationHistory":
        return cls(
            observations=[
                HistoricalObservation.from_evidence_item(item)
                for item in items
                if item.cycle_id is not None
            ]
        )

    @property
    def cycles_observed(self) -> list[int]:
        return sorted({observation.cycle_id for observation in self.observations})

    @property
    def evidence_density_by_cycle(self) -> dict[int, int]:
        density: dict[int, int] = {}
        for observation in self.observations:
            density[observation.cycle_id] = density.get(observation.cycle_id, 0) + 1
        return dict(sorted(density.items()))

    def observation_cycles(self, observation_text: str) -> list[int]:
        return sorted(
            {
                observation.cycle_id
                for observation in self.observations
                if observation.observation == observation_text
            }
        )

    def observation_frequency(self, observation_text: str) -> int:
        return len(
            [
                observation
                for observation in self.observations
                if observation.observation == observation_text
            ]
        )

    def observation_recurrence(self, observation_text: str, last_n_cycles: int) -> int:
        if last_n_cycles < 1:
            raise ValueError("last_n_cycles must be at least 1")
        cycles = self.cycles_observed[-last_n_cycles:]
        cycle_set = set(cycles)
        return len(
            [
                observation
                for observation in self.observations
                if observation.observation == observation_text
                and observation.cycle_id in cycle_set
            ]
        )

    def observation_persistence(self, observation_text: str) -> int:
        cycles = self.observation_cycles(observation_text)
        return _max_consecutive_run(cycles)

    def severity_history(self, observation_text: str) -> list[str]:
        return [
            observation.severity
            for observation in sorted(
                self.observations,
                key=lambda item: (item.cycle_id, item.timestamp),
            )
            if observation.observation == observation_text
        ]

    def cluster_cycles(self, cluster: str) -> list[int]:
        return sorted(
            {
                observation.cycle_id
                for observation in self.observations
                if observation.evidence_cluster == cluster
            }
        )

    def cluster_persistence(self, cluster: str) -> int:
        return _max_consecutive_run(self.cluster_cycles(cluster))

    def cluster_recurrence(self, cluster: str, last_n_cycles: int) -> int:
        if last_n_cycles < 1:
            raise ValueError("last_n_cycles must be at least 1")
        cycles = set(self.cycles_observed[-last_n_cycles:])
        return len(
            [
                observation
                for observation in self.observations
                if observation.evidence_cluster == cluster
                and observation.cycle_id in cycles
            ]
        )

    def source_systems_for_observation(self, observation_text: str) -> list[str]:
        sources: set[str] = set()
        for observation in self.observations:
            if observation.observation == observation_text:
                sources.update(observation.source_systems)
        return sorted(sources)

    def as_dict(self) -> dict[str, object]:
        return {
            "cycles_observed": self.cycles_observed,
            "evidence_density_by_cycle": self.evidence_density_by_cycle,
            "observations": [
                observation.as_dict() for observation in self.observations
            ],
        }


def _max_consecutive_run(cycles: list[int]) -> int:
    if not cycles:
        return 0
    max_run = 1
    current_run = 1
    for previous, current in zip(cycles, cycles[1:]):
        if current == previous + 1:
            current_run += 1
        else:
            max_run = max(max_run, current_run)
            current_run = 1
    return max(max_run, current_run)
