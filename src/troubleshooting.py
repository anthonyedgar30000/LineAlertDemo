"""Deterministic troubleshooting guide engine for industrial workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import yaml


DEFAULT_PETER_GUIDE_PATH = (
    Path(__file__).resolve().parents[1]
    / "linealert"
    / "rules"
    / "peter_label_alignment_guide.yaml"
)


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
    ranking_keywords: tuple[str, ...]


@dataclass(frozen=True)
class TroubleshootingGuide:
    guide_name: str
    issue_name: str
    ordered_steps: tuple[TroubleshootingStep, ...]


class TroubleshootingEngine:
    """Ranks guide steps from observed evidence and candidate hypotheses."""

    def __init__(self, guides: Sequence[TroubleshootingGuide] | None = None) -> None:
        configured_guides = (
            tuple(guides) if guides is not None else (load_peter_label_alignment_guide(),)
        )
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
        return step.ranking_keywords

    @staticmethod
    def _normalize(value: str) -> str:
        return value.casefold()


def load_peter_label_alignment_guide() -> TroubleshootingGuide:
    """Load the active Peter Label Alignment Guide from external YAML data."""

    return load_troubleshooting_guide(DEFAULT_PETER_GUIDE_PATH)


def load_troubleshooting_guide(guide_path: str | Path) -> TroubleshootingGuide:
    path = Path(guide_path)
    with path.open("r", encoding="utf-8") as guide_file:
        raw_data = yaml.safe_load(guide_file) or {}
    return _parse_troubleshooting_guide(raw_data, path)


def build_peter_label_alignment_guide() -> TroubleshootingGuide:
    """Backward-compatible loader for the Peter Label Alignment Guide."""

    return load_peter_label_alignment_guide()


def _parse_troubleshooting_guide(
    raw_data: dict[str, Any],
    guide_path: Path,
) -> TroubleshootingGuide:
    guide = raw_data.get("guide")
    if not isinstance(guide, dict):
        raise ValueError(f"Guide YAML must contain a 'guide' mapping: {guide_path}")

    steps = guide.get("ordered_steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError(
            f"Guide YAML must contain a non-empty 'ordered_steps' list: {guide_path}"
        )

    return TroubleshootingGuide(
        guide_name=_required_string(guide, "name", guide_path),
        issue_name=_required_string(guide, "issue", guide_path),
        ordered_steps=tuple(_parse_step(step, guide_path) for step in steps),
    )


def _parse_step(raw_step: Any, guide_path: Path) -> TroubleshootingStep:
    if not isinstance(raw_step, dict):
        raise ValueError(f"Guide step must be a mapping: {guide_path}")

    actions = raw_step.get("actions")
    if not isinstance(actions, dict):
        raise ValueError(f"Guide step must contain an 'actions' mapping: {guide_path}")

    return TroubleshootingStep(
        step_id=_required_string(raw_step, "id", guide_path),
        title=_required_string(raw_step, "title", guide_path),
        description=_required_string(raw_step, "description", guide_path),
        expected_failure_modes=_required_string_tuple(
            raw_step,
            "failure_modes",
            guide_path,
        ),
        expected_components=_required_string_tuple(
            raw_step,
            "related_components",
            guide_path,
        ),
        pass_action=_required_string(actions, "pass", guide_path),
        fail_action=_required_string(actions, "fail", guide_path),
        verification_action=_required_string(actions, "verification", guide_path),
        ranking_keywords=_required_string_tuple(
            raw_step,
            "ranking_keywords",
            guide_path,
        ),
    )


def _required_string(
    mapping: dict[str, Any],
    key: str,
    guide_path: Path,
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Guide field '{key}' must be a non-empty string: {guide_path}")
    return value


def _required_string_tuple(
    mapping: dict[str, Any],
    key: str,
    guide_path: Path,
) -> tuple[str, ...]:
    values = mapping.get(key)
    if not isinstance(values, list) or not values:
        raise ValueError(
            f"Guide field '{key}' must be a non-empty string list: {guide_path}"
        )
    if not all(isinstance(value, str) and value for value in values):
        raise ValueError(
            f"Guide field '{key}' must contain only non-empty strings: {guide_path}"
        )
    return tuple(values)
