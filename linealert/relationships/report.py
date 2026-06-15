"""Relationship integrity report formatting."""

from __future__ import annotations

from linealert.relationships.validator import RelationshipIntegrityReport


def generate_relationship_integrity_report(
    report: RelationshipIntegrityReport,
) -> dict[str, object]:
    """Return a serializable relationship integrity report."""

    return report.as_dict()


def format_relationship_integrity_report(report: RelationshipIntegrityReport) -> str:
    """Render relationship integrity observations as text."""

    lines = [
        "RELATIONSHIP INTEGRITY REPORT",
        "",
        "Status:",
        report.integrity_status,
        "",
        "Summary:",
        f"- Expected relationships: {report.expected_relationship_count}",
        f"- Observed cycles: {report.observed_cycle_count}",
        f"- Valid relationship observations: {report.valid_observation_count}",
        f"- Integrity observations: {report.observation_count}",
        "",
        "Observations:",
    ]
    observations = report.observations()
    if not observations:
        lines.append("- None")
    else:
        lines.extend(
            f"- {observation.observation_type}: {observation.details}"
            for observation in observations
        )

    lines.extend(
        [
            "",
            "No diagnosis or root-cause determination performed.",
            "No maintenance recommendations generated.",
        ]
    )
    return "\n".join(lines)
