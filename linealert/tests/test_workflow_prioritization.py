"""Tests for workflow prioritization from evidence."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_DIR))

from linealert.workflows.evidence_filter import review_workflow_evidence  # noqa: E402
from linealert.workflows.engine import find_workflow  # noqa: E402
from linealert.workflows.loader import load_decision_tree_workflows  # noqa: E402
from linealert.workflows.prioritization import prioritize_workflow  # noqa: E402
from linealert.workflows.priority_report import (  # noqa: E402
    format_priority_report,
    generate_priority_report,
)


WORKFLOW_CONFIG = REPO_ROOT / "config" / "labeling_decision_trees.json"


class WorkflowPrioritizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflows = load_decision_tree_workflows(WORKFLOW_CONFIG)
        self.bubbles = find_workflow(self.workflows, "Bubbles").matched_workflow
        self.multiple_labels = find_workflow(
            self.workflows, "Multiple Labels Applying"
        ).matched_workflow
        assert self.bubbles is not None
        assert self.multiple_labels is not None
        self.review = review_workflow_evidence(
            observed_condition="Tamp Extension Lag exceeded baseline",
            evidence_summary=_evidence_summary(),
            relationship_integrity=_relationship_integrity(),
            dependency_chains=_dependency_chains(),
            topology_validation=_topology_validation(),
            confidence_summary=_confidence_summary(),
        )

    def test_evidence_review_splits_supported_and_not_supported_items(self) -> None:
        self.assertIn(
            "Baseline Analysis: Tamp Extension Lag exceeded baseline",
            self.review.supported_by_evidence,
        )
        self.assertIn(
            "Relationship Integrity: required relationships observed in order",
            self.review.supported_by_evidence,
        )
        self.assertIn(
            "No gap detection observations present",
            self.review.not_supported_by_evidence,
        )
        self.assertTrue(self.review.confidence_high)

    def test_evidence_prioritizes_workflow_steps(self) -> None:
        prioritization = prioritize_workflow(
            workflow=self.bubbles,
            evidence_review=self.review,
        )

        self.assertEqual(
            ["Enough pressure time?", "Is bottle stable?"],
            [item.label for item in prioritization.check_first],
        )
        self.assertEqual(
            ["Is contact pressure consistent?", "Does slowing machine help?"],
            [item.label for item in prioritization.check_second],
        )
        self.assertTrue(
            all("Reason:" not in item.reason for item in prioritization.check_first)
        )
        self.assertEqual(
            {
                "Observed condition directly relates to tamp delay",
                "Guide step may affect observed timing but is not the primary evidence match",
            },
            {item.reason for item in [*prioritization.check_first, *prioritization.check_second]},
        )

    def test_unsupported_workflow_branches_are_suppressed(self) -> None:
        prioritization = prioritize_workflow(
            workflow=self.bubbles,
            evidence_review=self.review,
            related_workflows=[self.multiple_labels],
        )

        self.assertEqual(
            ["Multiple Labels Applying workflow"],
            [item.label for item in prioritization.ruled_out],
        )
        self.assertEqual(
            "No multiple-label observations present",
            prioritization.ruled_out[0].reason,
        )

    def test_spacing_branch_can_be_deferred(self) -> None:
        prioritization = prioritize_workflow(
            workflow=self.multiple_labels,
            evidence_review=self.review,
        )

        deferred_labels = [item.label for item in prioritization.deferred]
        ruled_out_labels = [item.label for item in prioritization.ruled_out]
        self.assertIn("Is spacing consistent?", deferred_labels)
        self.assertIn("Is sensor detecting gaps properly?", ruled_out_labels)
        self.assertEqual(
            "No spacing anomalies observed",
            next(item for item in prioritization.deferred if item.label == "Is spacing consistent?").reason,
        )

    def test_every_prioritization_decision_has_explanation(self) -> None:
        prioritization = prioritize_workflow(
            workflow=self.bubbles,
            evidence_review=self.review,
            related_workflows=[self.multiple_labels],
        )
        decisions = [
            *prioritization.check_first,
            *prioritization.check_second,
            *prioritization.deferred,
            *prioritization.ruled_out,
        ]

        self.assertTrue(decisions)
        self.assertTrue(all(item.reason for item in decisions))

    def test_priority_report_contains_required_sections_without_forbidden_language(self) -> None:
        prioritization = prioritize_workflow(
            workflow=self.bubbles,
            evidence_review=self.review,
            related_workflows=[self.multiple_labels],
        )
        report = generate_priority_report(prioritization)
        text = format_priority_report(prioritization)
        lowered = text.lower()

        self.assertIn("supported_by_evidence", report)
        self.assertIn("WORKFLOW ASSESSMENT", text)
        self.assertIn("Supported By Evidence", text)
        self.assertIn("Not Supported By Evidence", text)
        self.assertIn("CHECK FIRST", text)
        self.assertIn("CHECK SECOND", text)
        self.assertIn("DEFERRED", text)
        self.assertIn("RULED OUT", text)
        self.assertIn("Reason: Observed condition directly relates to tamp delay", text)
        self.assertNotIn("diagnos", lowered)
        self.assertNotIn("root cause", lowered)
        self.assertNotIn("probab", lowered)
    def test_gap_supported_evidence_prevents_sensor_rule_out(self) -> None:
        review = review_workflow_evidence(
            observed_condition="Sensor gap observation present",
            evidence_summary={
                "observation_clusters": [
                    {
                        "cluster": "Sensor Gap",
                        "supporting_evidence": [
                            {
                                "source": "Relationship Integrity",
                                "observation": "Sensor gap detection observation present",
                                "severity": "Monitor",
                            }
                        ],
                    }
                ]
            },
            relationship_integrity=_relationship_integrity(),
            dependency_chains=_dependency_chains(),
            topology_validation=_topology_validation(),
            confidence_summary=_confidence_summary(),
        )

        prioritization = prioritize_workflow(
            workflow=self.multiple_labels,
            evidence_review=review,
        )

        self.assertNotIn(
            "Is sensor detecting gaps properly?",
            [item.label for item in prioritization.ruled_out],
        )


def _evidence_summary() -> dict[str, object]:
    return {
        "observation_clusters": [
            {
                "cluster": "Tamp Operation Deviation",
                "supporting_evidence": [
                    {
                        "source": "Baseline Analysis",
                        "observation": "Tamp Extension Lag exceeded baseline",
                        "severity": "Significant Deviation",
                        "source_evidence": {
                            "relationship": "Tamp Extension Lag",
                            "measured_ms": 1100,
                            "baseline_ms": 600,
                        },
                    }
                ],
            }
        ]
    }


def _relationship_integrity() -> dict[str, object]:
    return {"integrity_status": "Valid", "observations": []}


def _dependency_chains() -> dict[str, object]:
    return {"validation": {"integrity_status": "Healthy", "observations": []}}


def _topology_validation() -> dict[str, object]:
    return {"observations": []}


def _confidence_summary() -> dict[str, object]:
    return {"classification": "Very High"}


if __name__ == "__main__":
    unittest.main()
