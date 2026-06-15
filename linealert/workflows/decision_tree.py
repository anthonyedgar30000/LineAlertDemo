"""Structured symptom-check-action-validation-escalation workflow models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowStep:
    """One check/action/validation step from a troubleshooting guide."""

    check: str
    actions: list[str]
    validation: str

    def as_dict(self) -> dict[str, object]:
        return {
            "check": self.check,
            "actions": list(self.actions),
            "validation": self.validation,
        }


@dataclass(frozen=True)
class DecisionTreeWorkflow:
    """A complete structured workflow for one visible symptom."""

    workflow_id: str
    symptom: str
    aliases: list[str]
    examples: list[str]
    steps: list[WorkflowStep]
    related_workflows_if_unresolved: list[str]
    escalation_conditions: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "workflow_id": self.workflow_id,
            "symptom": self.symptom,
            "aliases": list(self.aliases),
            "examples": list(self.examples),
            "steps": [step.as_dict() for step in self.steps],
            "related_workflows_if_unresolved": list(self.related_workflows_if_unresolved),
            "escalation_conditions": list(self.escalation_conditions),
        }


@dataclass(frozen=True)
class WorkflowResult:
    """Deterministic result for a reported symptom."""

    reported_symptom: str
    matched_workflow: DecisionTreeWorkflow | None

    def as_dict(self) -> dict[str, object]:
        return {
            "reported_symptom": self.reported_symptom,
            "matched": self.matched_workflow is not None,
            "workflow": (
                self.matched_workflow.as_dict()
                if self.matched_workflow is not None
                else None
            ),
        }
