"""Tests for evidence-only Situation Assessment summaries."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_DIR))

from linealert.situation.assessment import (  # noqa: E402
    build_situation_assessment,
    format_situation_assessment,
)


VALID_TOPOLOGY = {
    "component_count": 4,
    "dependency_count": 3,
    "missing_components": [],
    "orphan_components": [],
    "circular_dependencies": [],
    "disconnected_chains": [],
    "events_mapped_to_unknown_components": {},
    "observations": [],
}


class SituationAssessmentTests(unittest.TestCase):
    def test_normal_assessment_when_no_relationships_are_out_of_baseline(self) -> None:
        assessment = build_situation_assessment(
            topology_aware_evidence_records=[],
            topology_validation_results=VALID_TOPOLOGY,
            cycles_observed=12,
            machine_state="Production",
            assessment_id="assessment-normal",
        )

        self.assertEqual("Normal", assessment.situation_status)
        self.assertEqual([], assessment.affected_components)
        self.assertEqual(
            {
                "cycles_observed": 12,
                "cycles_out_of_baseline": 0,
                "percent_affected": 0,
                "affected_components": [],
            },
            assessment.situation_summary.as_dict(),
        )
        self.assertEqual(
            [
                "No out-of-baseline relationships observed",
                "Topology validation passed",
            ],
            assessment.observed_conditions,
        )

    def test_monitor_assessment_when_less_than_25_percent_cycles_are_affected(self) -> None:
        assessment = build_situation_assessment(
            topology_aware_evidence_records=_evidence_records(cycle_ids=[1, 2]),
            topology_validation_results=VALID_TOPOLOGY,
            cycles_observed=12,
            assessment_id="assessment-monitor",
        )

        self.assertEqual("Monitor", assessment.situation_status)
        self.assertEqual(16.667, assessment.situation_summary.as_dict()["percent_affected"])

    def test_degraded_assessment_when_25_percent_or_more_cycles_are_affected(self) -> None:
        assessment = build_situation_assessment(
            topology_aware_evidence_records=_evidence_records(cycle_ids=[1, 2, 3]),
            topology_validation_results=VALID_TOPOLOGY,
            cycles_observed=12,
            assessment_id="assessment-degraded",
        )

        self.assertEqual("Degraded", assessment.situation_status)
        self.assertEqual(25, assessment.situation_summary.as_dict()["percent_affected"])

    def test_significant_deviation_when_75_percent_or_more_cycles_are_affected(self) -> None:
        assessment = build_situation_assessment(
            topology_aware_evidence_records=_evidence_records(cycle_ids=range(1, 13)),
            topology_validation_results=VALID_TOPOLOGY,
            cycles_observed=12,
            assessment_id="assessment-significant",
        )
        assessment_dict = assessment.as_dict()

        self.assertEqual("Significant Deviation", assessment.situation_status)
        self.assertEqual(["Tamp Cylinder"], assessment.affected_components)
        self.assertEqual("Valid", assessment.topology_integrity)
        self.assertEqual(0.95, assessment.confidence)
        self.assertEqual(
            {
                "cycles_observed": 12,
                "cycles_out_of_baseline": 12,
                "percent_affected": 100,
                "affected_components": ["Tamp Cylinder"],
            },
            assessment_dict["situation_summary"],
        )
        self.assertEqual(
            [
                {
                    "relationship": "Tamp Extension Lag",
                    "cycles_affected": 12,
                    "average_measured_ms": 1100.0,
                    "baseline_ms": 600.0,
                    "average_deviation_percent": 83.333,
                }
            ],
            assessment_dict["out_of_baseline_relationships"],
        )
        self.assertIn(
            "12 of 12 cycles exceeded baseline",
            assessment.observed_conditions,
        )

    def test_topology_observations_are_reflected_without_diagnosis(self) -> None:
        topology_with_observation = {
            **VALID_TOPOLOGY,
            "orphan_components": ["reject_gate"],
            "observations": [
                {
                    "observation_type": "OrphanComponent",
                    "component_id": "reject_gate",
                    "details": "Component reject_gate has no topology dependencies.",
                }
            ],
        }

        assessment = build_situation_assessment(
            topology_aware_evidence_records=[],
            topology_validation_results=topology_with_observation,
            cycles_observed=12,
            assessment_id="assessment-topology-observation",
        )

        self.assertEqual("Observations Present", assessment.topology_integrity)
        self.assertIn(
            "Topology validation produced observations",
            assessment.observed_conditions,
        )

    def test_human_readable_assessment_contains_evidence_only_language(self) -> None:
        assessment = build_situation_assessment(
            topology_aware_evidence_records=_evidence_records(cycle_ids=range(1, 13)),
            topology_validation_results=VALID_TOPOLOGY,
            cycles_observed=12,
            assessment_id="assessment-demo",
        )

        text = format_situation_assessment(assessment)

        self.assertIn("SITUATION ASSESSMENT", text)
        self.assertIn("Status:\nSignificant Deviation", text)
        self.assertIn("- Tamp Extension Lag exceeded baseline", text)
        self.assertIn("- Average measured lag 1100 ms", text)
        self.assertIn("- Baseline lag 600 ms", text)
        self.assertIn("- 12 of 12 cycles exceeded baseline", text)
        self.assertIn("- Topology validation passed", text)
        self.assertIn("- Tamp Cylinder", text)
        self.assertIn("No diagnosis or root-cause determination performed.", text)
        self.assertIn("No maintenance recommendations generated.", text)
        self.assertNotIn("Cylinder is failing", text)
        self.assertNotIn("Replace cylinder", text)


def _evidence_records(cycle_ids) -> list[dict[str, object]]:
    return [
        {
            "cycle_id": cycle_id,
            "machine_state": "Production",
            "relationship": "Tamp Extension Lag",
            "measured_ms": 1100.0,
            "baseline_ms": 600.0,
            "deviation_percent": 83.333,
            "status": "OutOfBaseline",
            "component_id": "tamp_cylinder",
            "component_name": "Tamp Cylinder",
            "upstream_components": ["print_head"],
            "downstream_components": ["tamp_sensor"],
        }
        for cycle_id in cycle_ids
    ]


if __name__ == "__main__":
    unittest.main()
