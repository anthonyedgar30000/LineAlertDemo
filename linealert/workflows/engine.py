"""Deterministic workflow lookup from structured decision trees."""

from __future__ import annotations

from linealert.workflows.decision_tree import DecisionTreeWorkflow, WorkflowResult


def find_workflow(
    workflows: list[DecisionTreeWorkflow],
    reported_symptom: str,
) -> WorkflowResult:
    """Find a workflow by symptom, alias, id, or contained normalized text."""

    normalized_report = _normalize(reported_symptom)
    if not normalized_report:
        return WorkflowResult(reported_symptom=reported_symptom, matched_workflow=None)

    for workflow in workflows:
        if normalized_report in _workflow_lookup_terms(workflow):
            return WorkflowResult(
                reported_symptom=reported_symptom,
                matched_workflow=workflow,
            )

    for workflow in workflows:
        for term in _workflow_lookup_terms(workflow):
            if term and (term in normalized_report or normalized_report in term):
                return WorkflowResult(
                    reported_symptom=reported_symptom,
                    matched_workflow=workflow,
                )

    return WorkflowResult(reported_symptom=reported_symptom, matched_workflow=None)


def _workflow_lookup_terms(workflow: DecisionTreeWorkflow) -> set[str]:
    return {
        normalized
        for term in [
            workflow.workflow_id,
            workflow.symptom,
            *workflow.aliases,
            *workflow.examples,
        ]
        if (normalized := _normalize(term))
    }


def _normalize(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())
