"""Evidence-only situation assessment summaries.

The Situation Assessment layer summarizes observed evidence into an
investigation-ready snapshot. It does not diagnose, infer root cause, recommend
maintenance, or choose corrective actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable
from uuid import uuid4


ALLOWED_SITUATION_STATUSES = (
    "Normal",
    "Monitor",
    "Degraded",
    "Significant Deviation",
)
OUT_OF_BASELINE_STATUS = "OutOfBaseline"


@dataclass(frozen=True)
class RelationshipAssessment:
    """Measured relationship summary used by a situation assessment."""

    relationship: str
    cycles_affected: int
    average_measured_ms: float | None
    baseline_ms: float | None
    average_deviation_percent: float | None

    def as_dict(self) -> dict[str, object]:
        return {
            "relationship": self.relationship,
            "cycles_affected": self.cycles_affected,
            "average_measured_ms": _round_optional(self.average_measured_ms),
            "baseline_ms": _round_optional(self.baseline_ms),
            "average_deviation_percent": _round_optional(
                self.average_deviation_percent
            ),
        }


@dataclass(frozen=True)
class SituationSummary:
    """Compact cycle and component impact summary."""

    cycles_observed: int
    cycles_out_of_baseline: int
    percent_affected: float
    affected_components: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "cycles_observed": self.cycles_observed,
            "cycles_out_of_baseline": self.cycles_out_of_baseline,
            "percent_affected": _round_number(self.percent_affected),
            "affected_components": list(self.affected_components),
        }


@dataclass(frozen=True)
class SituationAssessment:
    """Evidence-based assessment record with no diagnostic conclusions."""

    assessment_id: str
    machine_state: str
    cycles_observed: int
    situation_status: str
    affected_components: list[str]
    observed_conditions: list[str]
    out_of_baseline_relationships: list[RelationshipAssessment]
    topology_integrity: str
    confidence: float
    situation_summary: SituationSummary

    def as_dict(self) -> dict[str, object]:
        return {
            "assessment_id": self.assessment_id,
            "machine_state": self.machine_state,
            "cycles_observed": self.cycles_observed,
            "situation_status": self.situation_status,
            "affected_components": list(self.affected_components),
            "observed_conditions": list(self.observed_conditions),
            "out_of_baseline_relationships": [
                relationship.as_dict()
                for relationship in self.out_of_baseline_relationships
            ],
            "topology_integrity": self.topology_integrity,
            "confidence": round(self.confidence, 3),
            "situation_summary": self.situation_summary.as_dict(),
        }


def build_situation_assessment(
    topology_aware_evidence_records: Iterable[dict[str, object]],
    topology_validation_results: dict[str, object],
    cycles_observed: int | None = None,
    machine_state: str | None = None,
    assessment_id: str | None = None,
    baseline_comparison_results: dict[str, object] | None = None,
    relationship_measurements: Iterable[dict[str, object]] | None = None,
    cycle_statistics: dict[str, object] | None = None,
) -> SituationAssessment:
    """Create an evidence-only situation assessment.

    Optional baseline, relationship, and cycle inputs are accepted to keep the
    boundary explicit for future callers. Current status rules are derived from
    topology-aware evidence records and the provided cycle count.
    """

    del baseline_comparison_results, relationship_measurements, cycle_statistics

    evidence_records = list(topology_aware_evidence_records)
    out_of_baseline_records = [
        record
        for record in evidence_records
        if str(record.get("status")) == OUT_OF_BASELINE_STATUS
    ]
    observed_cycle_count = cycles_observed or _infer_cycles_observed(evidence_records)
    cycles_out_of_baseline = len(
        {
            int(record["cycle_id"])
            for record in out_of_baseline_records
            if record.get("cycle_id") is not None
        }
    )
    percent_affected = (
        (cycles_out_of_baseline / observed_cycle_count) * 100
        if observed_cycle_count
        else 0.0
    )
    affected_components = _affected_components(out_of_baseline_records)
    relationship_assessments = _relationship_assessments(out_of_baseline_records)
    topology_integrity = _topology_integrity(topology_validation_results)

    summary = SituationSummary(
        cycles_observed=observed_cycle_count,
        cycles_out_of_baseline=cycles_out_of_baseline,
        percent_affected=percent_affected,
        affected_components=affected_components,
    )

    return SituationAssessment(
        assessment_id=assessment_id or f"assessment-{uuid4()}",
        machine_state=machine_state or _machine_state(evidence_records),
        cycles_observed=observed_cycle_count,
        situation_status=_situation_status(
            out_of_baseline_count=cycles_out_of_baseline,
            percent_affected=percent_affected,
        ),
        affected_components=affected_components,
        observed_conditions=_observed_conditions(
            relationship_assessments=relationship_assessments,
            cycles_out_of_baseline=cycles_out_of_baseline,
            cycles_observed=observed_cycle_count,
            topology_integrity=topology_integrity,
        ),
        out_of_baseline_relationships=relationship_assessments,
        topology_integrity=topology_integrity,
        confidence=_confidence(
            cycles_observed=observed_cycle_count,
            evidence_count=len(evidence_records),
            topology_integrity=topology_integrity,
        ),
        situation_summary=summary,
    )


def format_situation_assessment(assessment: SituationAssessment) -> str:
    """Render a human-readable assessment with evidence statements only."""

    lines = [
        "SITUATION ASSESSMENT",
        "",
        "Assessment ID:",
        assessment.assessment_id,
        "",
        "Machine State:",
        assessment.machine_state,
        "",
        "Status:",
        assessment.situation_status,
        "",
        "Situation Summary:",
        f"- Cycles observed: {assessment.situation_summary.cycles_observed}",
        (
            "- Cycles out of baseline: "
            f"{assessment.situation_summary.cycles_out_of_baseline}"
        ),
        (
            "- Percent affected: "
            f"{_format_number(assessment.situation_summary.percent_affected)}%"
        ),
        "",
        "Observed Conditions:",
    ]
    lines.extend(f"- {condition}" for condition in assessment.observed_conditions)
    lines.extend(["", "Affected Components:"])
    if assessment.affected_components:
        lines.extend(f"- {component}" for component in assessment.affected_components)
    else:
        lines.append("- None observed")
    lines.extend(
        [
            "",
            "Topology Integrity:",
            assessment.topology_integrity,
            "",
            "Confidence:",
            f"{assessment.confidence:.3f}",
            "",
            "No diagnosis or root-cause determination performed.",
            "No maintenance recommendations generated.",
        ]
    )
    return "\n".join(lines)


def _infer_cycles_observed(evidence_records: list[dict[str, object]]) -> int:
    cycle_ids = [
        int(record["cycle_id"])
        for record in evidence_records
        if record.get("cycle_id") is not None
    ]
    return max(cycle_ids) if cycle_ids else 0


def _affected_components(records: list[dict[str, object]]) -> list[str]:
    return sorted(
        {
            str(record["component_name"])
            for record in records
            if record.get("component_name")
        }
    )


def _relationship_assessments(
    records: list[dict[str, object]]
) -> list[RelationshipAssessment]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for record in records:
        relationship = str(record.get("relationship") or "Unknown Relationship")
        grouped.setdefault(relationship, []).append(record)

    assessments = []
    for relationship, relationship_records in sorted(grouped.items()):
        assessments.append(
            RelationshipAssessment(
                relationship=relationship,
                cycles_affected=len(
                    {
                        int(record["cycle_id"])
                        for record in relationship_records
                        if record.get("cycle_id") is not None
                    }
                ),
                average_measured_ms=_average_present(
                    _numeric_value(record, "measured_ms", "observed_ms")
                    for record in relationship_records
                ),
                baseline_ms=_average_present(
                    _numeric_value(record, "baseline_ms", "expected_ms")
                    for record in relationship_records
                ),
                average_deviation_percent=_average_present(
                    _numeric_value(record, "deviation_percent")
                    for record in relationship_records
                ),
            )
        )
    return assessments


def _topology_integrity(topology_validation_results: dict[str, object]) -> str:
    observations = topology_validation_results.get("observations") or []
    if observations:
        return "Observations Present"

    integrity_fields = (
        "missing_components",
        "orphan_components",
        "circular_dependencies",
        "disconnected_chains",
        "events_mapped_to_unknown_components",
    )
    if any(topology_validation_results.get(field) for field in integrity_fields):
        return "Observations Present"
    return "Valid"


def _situation_status(out_of_baseline_count: int, percent_affected: float) -> str:
    if out_of_baseline_count == 0:
        return "Normal"
    if percent_affected >= 75.0:
        return "Significant Deviation"
    if percent_affected >= 25.0:
        return "Degraded"
    return "Monitor"


def _machine_state(evidence_records: list[dict[str, object]]) -> str:
    for record in evidence_records:
        if record.get("machine_state"):
            return str(record["machine_state"])
    return "Unknown"


def _observed_conditions(
    relationship_assessments: list[RelationshipAssessment],
    cycles_out_of_baseline: int,
    cycles_observed: int,
    topology_integrity: str,
) -> list[str]:
    if not relationship_assessments:
        condition = "No out-of-baseline relationships observed"
        return [condition, _topology_condition(topology_integrity)]

    conditions: list[str] = []
    for relationship in relationship_assessments:
        conditions.append(f"{relationship.relationship} exceeded baseline")
        if relationship.average_measured_ms is not None:
            conditions.append(
                "Average measured lag "
                f"{_format_number(relationship.average_measured_ms)} ms"
            )
        if relationship.baseline_ms is not None:
            conditions.append(
                f"Baseline lag {_format_number(relationship.baseline_ms)} ms"
            )
        if relationship.average_deviation_percent is not None:
            conditions.append(
                "Average deviation "
                f"{_format_number(relationship.average_deviation_percent)}%"
            )

    conditions.append(
        f"{cycles_out_of_baseline} of {cycles_observed} cycles exceeded baseline"
    )
    conditions.append(_topology_condition(topology_integrity))
    return conditions


def _topology_condition(topology_integrity: str) -> str:
    if topology_integrity == "Valid":
        return "Topology validation passed"
    return "Topology validation produced observations"


def _confidence(
    cycles_observed: int, evidence_count: int, topology_integrity: str
) -> float:
    confidence = 0.70
    if cycles_observed > 0:
        confidence += 0.15
    if evidence_count > 0:
        confidence += 0.05
    confidence += 0.05 if topology_integrity == "Valid" else -0.10
    return max(0.0, min(0.95, confidence))


def _average_present(values: Iterable[float | None]) -> float | None:
    present_values = [value for value in values if value is not None]
    if not present_values:
        return None
    return mean(present_values)


def _numeric_value(
    record: dict[str, object], *field_names: str
) -> float | None:
    for field_name in field_names:
        value = record.get(field_name)
        if value is None:
            continue
        return float(value)
    return None


def _round_optional(value: float | None) -> float | None:
    return round(value, 3) if value is not None else None


def _round_number(value: float) -> int | float:
    rounded = round(value, 3)
    return int(rounded) if rounded.is_integer() else rounded


def _format_number(value: float) -> str:
    rounded = _round_number(value)
    return str(rounded)
