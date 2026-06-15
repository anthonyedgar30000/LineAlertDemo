"""Confidence factor builders."""

from __future__ import annotations

from linealert.confidence.confidence_model import ConfidenceFactor


def supporting_evidence_factor(evidence_count: int, cluster_count: int) -> ConfidenceFactor:
    contribution = min(0.25, (evidence_count * 0.03) + (cluster_count * 0.02))
    return ConfidenceFactor(
        name="Supporting Evidence",
        description=(
            f"{evidence_count} supporting evidence item(s) across "
            f"{cluster_count} observation cluster(s)"
        ),
        contribution=round(contribution, 3),
    )


def historical_persistence_factor(
    persistence_cycles: int, recurrence_count: int, frequency: int
) -> ConfidenceFactor:
    contribution = min(
        0.20,
        (persistence_cycles * 0.01)
        + (recurrence_count * 0.005)
        + (frequency * 0.002),
    )
    return ConfidenceFactor(
        name="Historical Persistence",
        description=(
            f"Observed across {frequency} occurrence(s); "
            f"{persistence_cycles} consecutive cycle(s); "
            f"{recurrence_count} recurrence observation(s)"
        ),
        contribution=round(contribution, 3),
    )


def multi_source_confirmation_factor(sources_contributing: int) -> ConfidenceFactor:
    contribution = 0.20 if sources_contributing > 1 else 0.05
    return ConfidenceFactor(
        name="Multi-Source Confirmation",
        description=f"{sources_contributing} supporting evidence source(s)",
        contribution=round(contribution, 3),
    )


def topology_validation_factor(
    topology_status: str,
    relationship_integrity_status: str,
    dependency_chain_status: str,
) -> ConfidenceFactor:
    validated_count = sum(
        [
            topology_status == "Valid",
            relationship_integrity_status == "Valid",
            dependency_chain_status in {"Healthy", "Valid"},
        ]
    )
    contribution = validated_count * 0.05
    return ConfidenceFactor(
        name="Topology Validation",
        description=(
            f"Topology={topology_status}; "
            f"RelationshipIntegrity={relationship_integrity_status}; "
            f"DependencyChains={dependency_chain_status}"
        ),
        contribution=round(contribution, 3),
    )


def configuration_validity_factor(
    baseline_valid: bool,
    configuration_provenance_status: str,
    configuration_drift_present: bool,
) -> ConfidenceFactor:
    contribution = 0.0
    if baseline_valid:
        contribution += 0.07
    if configuration_provenance_status == "Valid":
        contribution += 0.05
    if not configuration_drift_present:
        contribution += 0.03
    return ConfidenceFactor(
        name="Configuration Validity",
        description=(
            f"BaselineValid={baseline_valid}; "
            f"ConfigurationProvenance={configuration_provenance_status}; "
            f"ConfigurationDriftPresent={configuration_drift_present}"
        ),
        contribution=round(contribution, 3),
    )
