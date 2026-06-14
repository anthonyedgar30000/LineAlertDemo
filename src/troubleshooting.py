"""Deterministic troubleshooting guide engine for industrial workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class TroubleshootingStep:
    step_id: str
    title: str
    description: str
    expected_failure_modes: tuple[str, ...]
    expected_components: tuple[str, ...]
    pass_action: str
    fail_action: str
    verification_action: str


@dataclass(frozen=True)
class TroubleshootingGuide:
    guide_name: str
    issue_name: str
    ordered_steps: tuple[TroubleshootingStep, ...]


class TroubleshootingEngine:
    """Ranks guide steps from observed evidence and candidate hypotheses."""

    def __init__(self, guides: Sequence[TroubleshootingGuide] | None = None) -> None:
        configured_guides = tuple(guides) if guides is not None else (build_peter_label_alignment_guide(),)
        self._guides_by_issue = {
            self._normalize(guide.issue_name): guide for guide in configured_guides
        }

    def load_guide(self, issue_name: str) -> TroubleshootingGuide:
        guide = self._guides_by_issue.get(self._normalize(issue_name))
        if guide is None:
            raise ValueError(f"No troubleshooting guide registered for issue: {issue_name}")
        return guide

    def rank_steps_from_evidence(
        self,
        guide: TroubleshootingGuide,
        candidate_hypotheses: Sequence[str],
    ) -> list[TroubleshootingStep]:
        return sorted(
            guide.ordered_steps,
            key=lambda step: (
                self._first_matching_hypothesis_index(step, candidate_hypotheses),
                int(step.step_id),
            ),
        )

    def generate_workflow(
        self,
        issue_name: str,
        candidate_hypotheses: Sequence[str],
        supporting_evidence: Sequence[str],
    ) -> str:
        guide = self.load_guide(issue_name)
        ranked_steps = self.rank_steps_from_evidence(guide, candidate_hypotheses)
        starting_step = ranked_steps[0]
        highest_ranked_hypothesis = self._matching_hypothesis(
            starting_step,
            candidate_hypotheses,
        )

        rendered_rows = [
            "Peter Troubleshooting Guide",
            "===========================",
            f"Guide: {guide.guide_name}",
            f"Issue: {guide.issue_name}",
            "",
            "Prioritized Workflow",
            "====================",
        ]
        rendered_rows.extend(
            f"{index}. {step.title} - {step.description}"
            for index, step in enumerate(ranked_steps, start=1)
        )
        rendered_rows.extend(
            [
                "",
                "Troubleshooting Workflow",
                "========================",
                "",
                "Guide:",
                guide.guide_name,
                "",
                "Current Recommended Starting Step:",
                starting_step.title,
                "",
                "Reason:",
                "Highest ranked hypothesis:",
                highest_ranked_hypothesis,
                "",
                "Supporting Evidence:",
            ]
        )
        rendered_rows.extend(f"- {evidence}" for evidence in supporting_evidence)
        rendered_rows.extend(
            [
                "",
                "Verification Steps",
                "==================",
                "Verification Required:",
                starting_step.verification_action,
                "Confirm alignment restored",
                "",
                "Step Details:",
            ]
        )
        for step in ranked_steps:
            rendered_rows.extend(
                [
                    f"- Step {step.step_id}: {step.title}",
                    f"  Pass: {step.pass_action}",
                    f"  Fail: {step.fail_action}",
                    f"  Verify: {step.verification_action}",
                ]
            )
        return "\n".join(rendered_rows)

    def _first_matching_hypothesis_index(
        self,
        step: TroubleshootingStep,
        candidate_hypotheses: Sequence[str],
    ) -> int:
        for index, hypothesis in enumerate(candidate_hypotheses):
            normalized_hypothesis = hypothesis.casefold()
            if any(
                keyword in normalized_hypothesis
                for keyword in self._ranking_keywords(step)
            ):
                return index
        return len(candidate_hypotheses)

    def _matching_hypothesis(
        self,
        step: TroubleshootingStep,
        candidate_hypotheses: Sequence[str],
    ) -> str:
        match_index = self._first_matching_hypothesis_index(step, candidate_hypotheses)
        if match_index >= len(candidate_hypotheses):
            return "No direct hypothesis match; inspect ordered guide step"
        return candidate_hypotheses[match_index]

    @staticmethod
    def _ranking_keywords(step: TroubleshootingStep) -> tuple[str, ...]:
        if step.step_id == "1":
            return ("guide",)
        if step.step_id == "2":
            return ("tamp",)
        if step.step_id == "3":
            return ("positioning",)
        if step.step_id == "4":
            return ("sensor",)
        return ()

    @staticmethod
    def _normalize(value: str) -> str:
        return value.casefold()


def build_peter_label_alignment_guide() -> TroubleshootingGuide:
    return TroubleshootingGuide(
        guide_name="Peter Label Alignment Guide",
        issue_name="Label Alignment Off",
        ordered_steps=(
            TroubleshootingStep(
                step_id="1",
                title="Inspect Label Guide",
                description="Check the label guide for looseness or misalignment.",
                expected_failure_modes=("Label guide loosened", "Guide misalignment"),
                expected_components=("Label Feed Assembly", "Label Guide"),
                pass_action="Continue to tamp pad inspection if alignment drift persists.",
                fail_action="Secure and realign the label guide before rebaseline.",
                verification_action="Run 10 bottles and confirm alignment within tolerance",
            ),
            TroubleshootingStep(
                step_id="2",
                title="Inspect Tamp Pad",
                description="Check tamp pad condition and label transfer consistency.",
                expected_failure_modes=("Tamp pad wear", "Poor label transfer"),
                expected_components=("Tamp Cylinder", "Tamp Pad"),
                pass_action="Continue to product stop position verification.",
                fail_action="Clean or replace tamp pad before rebaseline.",
                verification_action="Observe consistent label transfer",
            ),
            TroubleshootingStep(
                step_id="3",
                title="Verify Product Stop Position",
                description="Check bottle presentation and stop repeatability.",
                expected_failure_modes=(
                    "Product positioning variance",
                    "Conveyor instability",
                ),
                expected_components=("Conveyor", "Product Detect Sensor"),
                pass_action="Continue to sensor inspection.",
                fail_action="Stabilize bottle stop position before rebaseline.",
                verification_action="Measure bottle stop repeatability",
            ),
            TroubleshootingStep(
                step_id="4",
                title="Inspect Sensors",
                description="Check readiness and applied-state sensor transitions.",
                expected_failure_modes=(
                    "Label ready sensor contamination",
                    "Applied sensor contamination",
                ),
                expected_components=("Label Ready Sensor", "Label Applied Sensor"),
                pass_action="Document results and monitor next production run.",
                fail_action="Clean and validate sensors before rebaseline.",
                verification_action=(
                    "Sensor transitions occur within expected timing window"
                ),
            ),
        ),
    )
