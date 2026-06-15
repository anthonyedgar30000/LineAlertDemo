"""Deterministic workflow prioritization from evidence review."""

from __future__ import annotations

from dataclasses import dataclass

from linealert.workflows.decision_tree import DecisionTreeWorkflow, WorkflowStep
from linealert.workflows.evidence_filter import EvidenceReview


CHECK_FIRST = "CHECK FIRST"
CHECK_SECOND = "CHECK SECOND"
DEFERRED = "DEFERRED"
RULED_OUT = "RULED OUT"

TAMP_DELAY_TERMS = [
    "tamp",
    "delay",
    "lag",
    "pressure time",
    "aligner run-on",
    "bottle pressure",
]
NEUTRAL_FOLLOW_UP_TERMS = [
    "label speed",
    "contact",
    "wipe",
    "stable",
    "stability",
]
SENSOR_GAP_TERMS = [
    "sensor",
    "gap",
]
LABEL_SPACING_TERMS = [
    "spacing",
    "multiple",
    "double",
    "overlap",
]


@dataclass(frozen=True)
class PrioritizedWorkflowItem:
    """One prioritized workflow step or branch decision."""

    label: str
    decision: str
    reason: str
    original_index: int | None = None
    check: str | None = None
    actions: list[str] | None = None
    validation: str | None = None

    def as_dict(self) -> dict[str, object]:
        output: dict[str, object] = {
            "label": self.label,
            "decision": self.decision,
            "reason": self.reason,
        }
        if self.original_index is not None:
            output["original_index"] = self.original_index
        if self.check is not None:
            output["check"] = self.check
        if self.actions is not None:
            output["actions"] = list(self.actions)
        if self.validation is not None:
            output["validation"] = self.validation
        return output


@dataclass(frozen=True)
class WorkflowPrioritization:
    """Prioritized workflow decisions with evidence review."""

    workflow_id: str
    symptom: str
    observed_condition: str
    supported_by_evidence: list[str]
    not_supported_by_evidence: list[str]
    check_first: list[PrioritizedWorkflowItem]
    check_second: list[PrioritizedWorkflowItem]
    deferred: list[PrioritizedWorkflowItem]
    ruled_out: list[PrioritizedWorkflowItem]

    def as_dict(self) -> dict[str, object]:
        return {
            "workflow_id": self.workflow_id,
            "symptom": self.symptom,
            "observed_condition": self.observed_condition,
            "supported_by_evidence": list(self.supported_by_evidence),
            "not_supported_by_evidence": list(self.not_supported_by_evidence),
            "check_first": [item.as_dict() for item in self.check_first],
            "check_second": [item.as_dict() for item in self.check_second],
            "deferred": [item.as_dict() for item in self.deferred],
            "ruled_out": [item.as_dict() for item in self.ruled_out],
        }


def prioritize_workflow(
    workflow: DecisionTreeWorkflow,
    evidence_review: EvidenceReview,
    related_workflows: list[DecisionTreeWorkflow] | None = None,
) -> WorkflowPrioritization:
    """Prioritize workflow checks using deterministic evidence rules."""

    check_first: list[PrioritizedWorkflowItem] = []
    check_second: list[PrioritizedWorkflowItem] = []
    deferred: list[PrioritizedWorkflowItem] = []
    ruled_out: list[PrioritizedWorkflowItem] = []

    for index, step in enumerate(workflow.steps, start=1):
        item = _prioritize_step(index=index, step=step, evidence_review=evidence_review)
        if item.decision == CHECK_FIRST:
            check_first.append(item)
        elif item.decision == CHECK_SECOND:
            check_second.append(item)
        elif item.decision == DEFERRED:
            deferred.append(item)
        else:
            ruled_out.append(item)

    for related_workflow in related_workflows or []:
        branch_item = _prioritize_related_workflow(related_workflow, evidence_review)
        if branch_item.decision == RULED_OUT:
            ruled_out.append(branch_item)
        else:
            deferred.append(branch_item)

    return WorkflowPrioritization(
        workflow_id=workflow.workflow_id,
        symptom=workflow.symptom,
        observed_condition=evidence_review.observed_condition,
        supported_by_evidence=evidence_review.supported_by_evidence,
        not_supported_by_evidence=evidence_review.not_supported_by_evidence,
        check_first=check_first,
        check_second=check_second,
        deferred=deferred,
        ruled_out=ruled_out,
    )


def _prioritize_step(
    index: int,
    step: WorkflowStep,
    evidence_review: EvidenceReview,
) -> PrioritizedWorkflowItem:
    text = _step_text(step)
    if _contains_any(text, SENSOR_GAP_TERMS) and not evidence_review.supports_any(
        ["gap detection", "sensor"]
    ):
        return _step_item(
            index=index,
            step=step,
            decision=RULED_OUT,
            reason="No gap detection observations present",
        )
    if _contains_any(text, LABEL_SPACING_TERMS) and not evidence_review.supports_any(
        ["label spacing", "multiple label"]
    ):
        return _step_item(
            index=index,
            step=step,
            decision=DEFERRED,
            reason="No spacing anomalies observed",
        )
    if _contains_any(text, TAMP_DELAY_TERMS):
        return _step_item(
            index=index,
            step=step,
            decision=CHECK_FIRST,
            reason="Observed condition directly relates to tamp delay",
        )
    if _contains_any(text, NEUTRAL_FOLLOW_UP_TERMS):
        return _step_item(
            index=index,
            step=step,
            decision=CHECK_SECOND,
            reason="Guide step may affect observed timing but is not the primary evidence match",
        )
    return _step_item(
        index=index,
        step=step,
        decision=DEFERRED,
        reason="No direct supporting evidence observed for this guide step",
    )


def _prioritize_related_workflow(
    workflow: DecisionTreeWorkflow,
    evidence_review: EvidenceReview,
) -> PrioritizedWorkflowItem:
    workflow_text = _normalize(
        " ".join([workflow.workflow_id, workflow.symptom, *workflow.aliases, *workflow.examples])
    )
    if "multiplelabels" in workflow_text and not evidence_review.supports_any(
        ["multiple label"]
    ):
        return PrioritizedWorkflowItem(
            label=f"{workflow.symptom} workflow",
            decision=RULED_OUT,
            reason="No multiple-label observations present",
        )
    if _contains_any(workflow_text, SENSOR_GAP_TERMS) and not evidence_review.supports_any(
        ["gap detection", "sensor"]
    ):
        return PrioritizedWorkflowItem(
            label=f"{workflow.symptom} workflow",
            decision=RULED_OUT,
            reason="No gap detection observations present",
        )
    if _contains_any(workflow_text, LABEL_SPACING_TERMS) and not evidence_review.supports_any(
        ["label spacing", "multiple label"]
    ):
        return PrioritizedWorkflowItem(
            label=f"{workflow.symptom} workflow",
            decision=DEFERRED,
            reason="No spacing anomalies observed",
        )
    return PrioritizedWorkflowItem(
        label=f"{workflow.symptom} workflow",
        decision=DEFERRED,
        reason="No direct supporting evidence observed for this workflow branch",
    )


def _step_item(
    index: int,
    step: WorkflowStep,
    decision: str,
    reason: str,
) -> PrioritizedWorkflowItem:
    return PrioritizedWorkflowItem(
        label=step.check,
        decision=decision,
        reason=reason,
        original_index=index,
        check=step.check,
        actions=list(step.actions),
        validation=step.validation,
    )


def _step_text(step: WorkflowStep) -> str:
    return _normalize(" ".join([step.check, *step.actions, step.validation]))


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(_normalize(term) in text for term in terms)


def _normalize(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())
