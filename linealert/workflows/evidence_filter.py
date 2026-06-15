"""Evidence review helpers for workflow prioritization.

The filter summarizes existing outputs for workflow prioritization. It does not
create diagnoses, root-cause claims, or recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceReview:
    """Evidence support and absence statements used by prioritization."""

    observed_condition: str
    supported_by_evidence: list[str]
    not_supported_by_evidence: list[str]
    evidence_terms: set[str]
    relationship_integrity_valid: bool
    dependency_chain_valid: bool
    topology_valid: bool
    confidence_high: bool

    def supports_any(self, terms: list[str]) -> bool:
        normalized_terms = [_normalize(term) for term in terms]
        return any(
            term and any(term in evidence for evidence in self.evidence_terms)
            for term in normalized_terms
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "observed_condition": self.observed_condition,
            "supported_by_evidence": list(self.supported_by_evidence),
            "not_supported_by_evidence": list(self.not_supported_by_evidence),
            "relationship_integrity_valid": self.relationship_integrity_valid,
            "dependency_chain_valid": self.dependency_chain_valid,
            "topology_valid": self.topology_valid,
            "confidence_high": self.confidence_high,
        }


def review_workflow_evidence(
    observed_condition: str,
    evidence_summary: dict[str, object],
    relationship_integrity: dict[str, object],
    dependency_chains: dict[str, object],
    topology_validation: dict[str, object],
    confidence_summary: dict[str, object],
) -> EvidenceReview:
    """Summarize evidence and absence-of-evidence for workflow prioritization."""

    evidence_terms = _collect_evidence_terms(
        evidence_summary=evidence_summary,
        observed_condition=observed_condition,
    )
    relationship_valid = relationship_integrity.get("integrity_status") == "Valid"
    dependency_valid = (
        (dependency_chains.get("validation") or {}).get("integrity_status") == "Healthy"
    )
    topology_valid = not topology_validation.get("observations")
    confidence_high = confidence_summary.get("classification") in {"High", "Very High"}

    supported = []
    if _normalize("Tamp Extension Lag exceeded baseline") in evidence_terms:
        supported.append("Baseline Analysis: Tamp Extension Lag exceeded baseline")
    if relationship_valid:
        supported.append("Relationship Integrity: required relationships observed in order")
    if dependency_valid:
        supported.append("Dependency Chain: configured dependency path observed")
    if topology_valid:
        supported.append("Topology Integrity: topology validation passed")
    if confidence_high:
        supported.append(
            f"Confidence Engine: {confidence_summary.get('classification')} confidence"
        )

    not_supported = []
    absence_checks = [
        ("gap detection", "No gap detection observations present"),
        ("label spacing", "No spacing anomalies observed"),
        ("multiple label", "No multiple-label observations present"),
        ("sensor", "No sensor gap observations present"),
    ]
    for term, statement in absence_checks:
        if not any(_normalize(term) in evidence for evidence in evidence_terms):
            not_supported.append(statement)

    return EvidenceReview(
        observed_condition=observed_condition,
        supported_by_evidence=supported,
        not_supported_by_evidence=not_supported,
        evidence_terms=evidence_terms,
        relationship_integrity_valid=relationship_valid,
        dependency_chain_valid=dependency_valid,
        topology_valid=topology_valid,
        confidence_high=confidence_high,
    )


def _collect_evidence_terms(
    evidence_summary: dict[str, object], observed_condition: str
) -> set[str]:
    terms = {_normalize(observed_condition)}
    for cluster in evidence_summary.get("observation_clusters") or []:
        if not isinstance(cluster, dict):
            continue
        if cluster.get("cluster"):
            terms.add(_normalize(str(cluster["cluster"])))
        for item in cluster.get("supporting_evidence") or []:
            if not isinstance(item, dict):
                continue
            for key in ("source", "observation", "severity"):
                if item.get(key):
                    terms.add(_normalize(str(item[key])))
            source_evidence = item.get("source_evidence")
            if isinstance(source_evidence, dict):
                for value in source_evidence.values():
                    terms.add(_normalize(str(value)))
    return {term for term in terms if term}


def _normalize(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())
