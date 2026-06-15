"""Report structured troubleshooting workflows without inference."""

from __future__ import annotations

from linealert.workflows.decision_tree import WorkflowResult


def generate_workflow_report(result: WorkflowResult) -> dict[str, object]:
    """Return a JSON-ready workflow report."""

    return result.as_dict()


def format_workflow_report(result: WorkflowResult) -> str:
    """Render symptom-check-action-validation-escalation workflow steps."""

    lines = [
        "STRUCTURED TROUBLESHOOTING WORKFLOW",
        "",
        f'Reported Symptom: "{result.reported_symptom}"',
        "",
    ]

    workflow = result.matched_workflow
    if workflow is None:
        lines.extend(
            [
                "Matched Symptom: none",
                "",
                "Escalation:",
                "- No structured workflow matched this symptom.",
            ]
        )
        return "\n".join(lines).rstrip() + "\n"

    lines.extend(
        [
            f"Matched Symptom: {workflow.symptom}",
            "",
            "Workflow Steps:",
        ]
    )
    for index, step in enumerate(workflow.steps, start=1):
        lines.extend(
            [
                f"{index}. Check:",
                f"   {step.check}",
                "   Action Steps:",
                *[f"   - {action}" for action in step.actions],
                "   Validation:",
                f"   {step.validation}",
            ]
        )

    lines.extend(["", "If Unresolved, Review Related Workflows:"])
    if workflow.related_workflows_if_unresolved:
        lines.extend(
            f"- {workflow_id}"
            for workflow_id in workflow.related_workflows_if_unresolved
        )
    else:
        lines.append("- none")

    lines.extend(["", "Escalation Conditions:"])
    if workflow.escalation_conditions:
        lines.extend(
            f"- {condition}"
            for condition in workflow.escalation_conditions
        )
    else:
        lines.append("- none")

    return "\n".join(lines).rstrip() + "\n"
