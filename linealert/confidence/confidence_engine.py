"""Observation-only confidence engine."""

from __future__ import annotations

from linealert.confidence.confidence_model import ObservationConfidence
from linealert.confidence.factors import (
    configuration_validity_factor,
    historical_persistence_factor,
    multi_source_confirmation_factor,
    supporting_evidence_factor,
    topology_validation_factor,
)
from linealert.confidence.scoring import calculate_confidence_score, classify_confidence


def evaluate_observation_confidence(
    observation: str,
    evidence_fusion_summary: dict[str, object],
    historical_context_summary: dict[str, object],
    topology_integrity_status: str,
    relationship_integrity_status: str,
    dependency_chain_status: str,
    baseline_valid: bool,
    configuration_provenance_status: str = "Valid",
    configuration_drift_present: bool = False,
) -> ObservationConfidence:
    """Evaluate confidence using explicit evidence-based factors."""

    evidence_count = int(evidence_fusion_summary.get("evidence_count", 0))
    cluster_count = len(evidence_fusion_summary.get("observation_clusters") or [])
    sources_contributing = int(evidence_fusion_summary.get("sources_contributing", 0))
    history = _history_for_observation(historical_context_summary, observation)

    factors = [
        supporting_evidence_factor(
            evidence_count=evidence_count,
            cluster_count=cluster_count,
        ),
        historical_persistence_factor(
            persistence_cycles=int(history.get("persistence_cycles", 0)),
            recurrence_count=int(history.get("recurrence_count", 0)),
            frequency=int(history.get("occurrences", 0)),
        ),
        multi_source_confirmation_factor(sources_contributing=sources_contributing),
        topology_validation_factor(
            topology_status=topology_integrity_status,
            relationship_integrity_status=relationship_integrity_status,
            dependency_chain_status=dependency_chain_status,
        ),
        configuration_validity_factor(
            baseline_valid=baseline_valid,
            configuration_provenance_status=configuration_provenance_status,
            configuration_drift_present=configuration_drift_present,
        ),
    ]
    score = calculate_confidence_score(factors)
    return ObservationConfidence(
        observation=observation,
        confidence=score,
        classification=classify_confidence(score),
        factors=factors,
    )


def _history_for_observation(
    historical_context_summary: dict[str, object], observation: str
) -> dict[str, object]:
    summaries = historical_context_summary.get("observation_summaries") or []
    for summary in summaries:
        if isinstance(summary, dict) and summary.get("observation") == observation:
            return summary
    return {}
