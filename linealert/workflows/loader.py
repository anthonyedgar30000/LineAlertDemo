"""Load structured troubleshooting decision trees."""

from __future__ import annotations

import json
from pathlib import Path

from linealert.workflows.decision_tree import DecisionTreeWorkflow, WorkflowStep


def load_decision_tree_workflows(config_path: str | Path) -> list[DecisionTreeWorkflow]:
    """Load workflows from a structured decision-tree JSON file."""

    path = Path(config_path)
    with path.open("r", encoding="utf-8") as config_file:
        raw_config = json.load(config_file)
    if not isinstance(raw_config, dict):
        raise ValueError(f"Workflow config must be a JSON object: {path}")

    raw_workflows = raw_config.get("workflows")
    if not isinstance(raw_workflows, list):
        raise ValueError("Workflow config must contain a workflows list")

    workflows = [
        _parse_workflow(raw_workflow=raw_workflow, index=index)
        for index, raw_workflow in enumerate(raw_workflows, start=1)
    ]
    workflow_ids = [workflow.workflow_id for workflow in workflows]
    if len(set(workflow_ids)) != len(workflow_ids):
        raise ValueError("Workflow ids must be unique")
    return workflows


def _parse_workflow(raw_workflow: object, index: int) -> DecisionTreeWorkflow:
    if not isinstance(raw_workflow, dict):
        raise ValueError(f"Workflow {index} must be an object")

    workflow_id = _required_str(raw_workflow, "workflow_id", f"Workflow {index}")
    symptom = _required_str(raw_workflow, "symptom", f"Workflow {index}")
    steps = _parse_steps(raw_workflow.get("steps"), workflow_id)
    return DecisionTreeWorkflow(
        workflow_id=workflow_id,
        symptom=symptom,
        aliases=_string_list(raw_workflow.get("aliases") or [], f"{workflow_id} aliases"),
        examples=_string_list(raw_workflow.get("examples") or [], f"{workflow_id} examples"),
        steps=steps,
        related_workflows_if_unresolved=_string_list(
            raw_workflow.get("related_workflows_if_unresolved") or [],
            f"{workflow_id} related_workflows_if_unresolved",
        ),
        escalation_conditions=_string_list(
            raw_workflow.get("escalation_conditions") or [],
            f"{workflow_id} escalation_conditions",
        ),
    )


def _parse_steps(raw_steps: object, workflow_id: str) -> list[WorkflowStep]:
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError(f"Workflow {workflow_id} requires at least one step")

    steps: list[WorkflowStep] = []
    for index, raw_step in enumerate(raw_steps, start=1):
        if not isinstance(raw_step, dict):
            raise ValueError(f"Workflow {workflow_id} step {index} must be an object")
        steps.append(
            WorkflowStep(
                check=_required_str(raw_step, "check", f"{workflow_id} step {index}"),
                actions=_string_list(
                    raw_step.get("actions"),
                    f"{workflow_id} step {index} actions",
                    require_values=True,
                ),
                validation=_required_str(
                    raw_step,
                    "validation",
                    f"{workflow_id} step {index}",
                ),
            )
        )
    return steps


def _required_str(raw_object: dict[str, object], field_name: str, context: str) -> str:
    value = raw_object.get(field_name)
    if value is None or str(value).strip() == "":
        raise ValueError(f"{context} missing required field: {field_name}")
    return str(value)


def _string_list(
    raw_values: object,
    context: str,
    require_values: bool = False,
) -> list[str]:
    if not isinstance(raw_values, list):
        raise ValueError(f"{context} must be a list")
    values = [str(value) for value in raw_values if str(value).strip()]
    if require_values and not values:
        raise ValueError(f"{context} requires at least one value")
    return values
