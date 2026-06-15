"""Tests for structured troubleshooting workflows."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_DIR))

from linealert.workflows.engine import find_workflow  # noqa: E402
from linealert.workflows.loader import load_decision_tree_workflows  # noqa: E402
from linealert.workflows.report import (  # noqa: E402
    format_workflow_report,
    generate_workflow_report,
)


WORKFLOW_CONFIG = REPO_ROOT / "config" / "labeling_decision_trees.json"


class StructuredWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflows = load_decision_tree_workflows(WORKFLOW_CONFIG)

    def test_workflows_load_as_structured_decision_trees(self) -> None:
        self.assertEqual(5, len(self.workflows))
        symptoms = {workflow.symptom for workflow in self.workflows}

        self.assertEqual(
            {
                "Label Alignment is Off",
                "Label Has Folds",
                "Label Has Stretch Lines",
                "Bubbles on Labels",
                "Multiple Labels Applying",
            },
            symptoms,
        )
        self.assertTrue(all(workflow.steps for workflow in self.workflows))

    def test_symptom_lookup_matches_aliases_and_examples(self) -> None:
        result = find_workflow(self.workflows, "crooked label")

        self.assertIsNotNone(result.matched_workflow)
        assert result.matched_workflow is not None
        self.assertEqual("label_alignment_off", result.matched_workflow.workflow_id)

    def test_workflow_preserves_symptom_check_action_validation_escalation(self) -> None:
        result = find_workflow(self.workflows, "Multiple Labels Applying")
        workflow = result.matched_workflow
        assert workflow is not None

        self.assertEqual("Multiple Labels Applying", workflow.symptom)
        self.assertEqual(
            "Is sensor detecting gaps properly?",
            workflow.steps[0].check,
        )
        self.assertEqual(["Adjust Sensor Sensitivity"], workflow.steps[0].actions)
        self.assertEqual(
            "Run product and verify label count and spacing after this action.",
            workflow.steps[0].validation,
        )
        self.assertIn("label_has_stretch_lines", workflow.related_workflows_if_unresolved)
        self.assertIn(
            "Issue continues after all checks and actions.",
            workflow.escalation_conditions,
        )

    def test_json_report_contains_workflow_only(self) -> None:
        result = find_workflow(self.workflows, "Label has folds")
        report = generate_workflow_report(result)

        self.assertTrue(report["matched"])
        self.assertEqual("Label Has Folds", report["workflow"]["symptom"])
        self.assertEqual(
            {
                "check": "Is label speed too high?",
                "actions": ["Decrease Label Speed"],
                "validation": "Run product and verify label surface after this action.",
            },
            report["workflow"]["steps"][0],
        )

    def test_text_report_uses_action_steps_not_recommendations_or_diagnosis(self) -> None:
        result = find_workflow(self.workflows, "Bubbles")
        text = format_workflow_report(result)
        lowered = text.lower()

        self.assertIn("STRUCTURED TROUBLESHOOTING WORKFLOW", text)
        self.assertIn("Matched Symptom: Bubbles on Labels", text)
        self.assertIn("Action Steps:", text)
        self.assertIn("Validation:", text)
        self.assertIn("Escalation Conditions:", text)
        self.assertNotIn("recommend", lowered)
        self.assertNotIn("diagnos", lowered)
        self.assertNotIn("root cause", lowered)
        self.assertNotIn("failing", lowered)

    def test_unmatched_symptom_returns_escalation_without_inference(self) -> None:
        result = find_workflow(self.workflows, "unknown issue")
        text = format_workflow_report(result)

        self.assertIsNone(result.matched_workflow)
        self.assertIn("Matched Symptom: none", text)
        self.assertIn("No structured workflow matched this symptom.", text)
        self.assertNotIn("recommend", text.lower())
        self.assertNotIn("diagnos", text.lower())


if __name__ == "__main__":
    unittest.main()
