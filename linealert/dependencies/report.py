"""Dependency chain report formatting."""

from __future__ import annotations

from linealert.dependencies.chain_validator import DependencyChainValidationReport
from linealert.dependencies.dependency_graph import DependencyGraph


def generate_dependency_chain_report(
    graph: DependencyGraph,
    validation_report: DependencyChainValidationReport,
) -> dict[str, object]:
    """Return serializable dependency graph and validation output."""

    return {
        "dependency_graph": graph.as_dict(),
        "validation": validation_report.as_dict(),
    }


def format_dependency_chain_report(
    graph: DependencyGraph,
    validation_report: DependencyChainValidationReport,
) -> str:
    """Render dependency chain observations as text."""

    lines = [
        "DEPENDENCY CHAIN REPORT",
        "",
        "Status:",
        validation_report.integrity_status,
        "",
        "Summary:",
        f"- Chains configured: {validation_report.chain_count}",
        f"- Events in graph: {len(graph.nodes)}",
        f"- Direct dependencies: {len(graph.direct_edges)}",
        f"- Observed cycles: {validation_report.observed_cycle_count}",
        f"- Chain observations: {validation_report.observation_count}",
        "",
        "Path Health:",
    ]
    lines.extend(
        (
            f"- {health.chain_id}: {health.status} "
            f"({health.healthy_cycles}/{health.cycles_observed} healthy cycles)"
        )
        for health in validation_report.path_health
    )

    lines.extend(["", "Observations:"])
    if not validation_report.observations:
        lines.append("- None")
    else:
        lines.extend(
            f"- {observation.observation_type}: {observation.details}"
            for observation in validation_report.observations
        )

    lines.extend(
        [
            "",
            "No diagnosis or root-cause determination performed.",
            "No maintenance recommendations generated.",
        ]
    )
    return "\n".join(lines)
