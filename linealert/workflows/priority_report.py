"""Workflow prioritization reports."""

from __future__ import annotations

from linealert.workflows.prioritization import WorkflowPrioritization


def generate_priority_report(prioritization: WorkflowPrioritization) -> dict[str, object]:
    """Return a JSON-ready prioritization report."""

    return prioritization.as_dict()


def format_priority_report(prioritization: WorkflowPrioritization) -> str:
    """Render a deterministic workflow assessment report."""

    lines = [
        "WORKFLOW ASSESSMENT",
        "",
        "Observed Condition:",
        prioritization.observed_condition,
        "",
        "Supported By Evidence",
    ]
    lines.extend(_bullets(prioritization.supported_by_evidence))
    lines.extend(["", "Not Supported By Evidence"])
    lines.extend(_bullets(prioritization.not_supported_by_evidence))
    lines.extend(["", "Workflow Prioritization", "", "CHECK FIRST"])
    lines.extend(_numbered_items(prioritization.check_first))
    lines.extend(["", "CHECK SECOND"])
    lines.extend(_numbered_items(prioritization.check_second, start=len(prioritization.check_first) + 1))
    lines.extend(["", "DEFERRED"])
    lines.extend(_decision_items(prioritization.deferred))
    lines.extend(["", "RULED OUT"])
    lines.extend(_decision_items(prioritization.ruled_out))
    lines.extend(
        [
            "",
            "Deterministic workflow routing only.",
            "Existing evidence boundaries preserved.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _bullets(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values] if values else ["- none"]


def _numbered_items(items, start: int = 1) -> list[str]:
    if not items:
        return ["- none"]
    lines: list[str] = []
    for offset, item in enumerate(items, start=start):
        lines.extend(
            [
                f"{offset}. {item.label}",
                f"   Reason: {item.reason}",
            ]
        )
        if item.actions:
            lines.extend(f"   Action Step: {action}" for action in item.actions)
    return lines


def _decision_items(items) -> list[str]:
    if not items:
        return ["- none"]
    lines: list[str] = []
    for item in items:
        lines.extend(
            [
                f"- {item.label}",
                f"  Reason: {item.reason}",
            ]
        )
    return lines
