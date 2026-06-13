"""Regression tests for the deterministic LineAlert starter pipeline."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from drift_engine import calculate_drift, load_baseline  # noqa: E402
from event_loader import load_events  # noqa: E402
from expert_system import load_rules, match_rules  # noqa: E402
from hypothesis_engine import generate_ranked_hypotheses  # noqa: E402
from main import run_pipeline  # noqa: E402
from timing_engine import calculate_timing_observations  # noqa: E402
from topology_engine import identify_first_drift_location, load_topology  # noqa: E402


class LineAlertPipelineTests(unittest.TestCase):
    def test_sample_data_produces_drift_and_rule_matches(self) -> None:
        events = load_events(PROJECT_ROOT / "data" / "sample_events.csv")
        observations = calculate_timing_observations(events)
        baseline = load_baseline(PROJECT_ROOT / "data" / "baseline.json")
        drift_findings = calculate_drift(observations.metrics, baseline)
        rules = load_rules(PROJECT_ROOT / "rules" / "troubleshooting_rules.yaml")
        candidate_causes = match_rules(drift_findings, rules)
        topology = load_topology(PROJECT_ROOT / "data" / "topology.yaml")
        topology_findings = identify_first_drift_location(topology, drift_findings)
        ranked_causes = generate_ranked_hypotheses(
            observations=observations,
            drift_findings=drift_findings,
            topology_findings=topology_findings,
            expert_rules=rules,
        )

        violated_keys = {
            finding.observation_key
            for finding in drift_findings
            if finding.threshold_violation
        }
        issues = {cause.issue for cause in candidate_causes}

        self.assertIn("lag:TampExtend->ProductTransfer", violated_keys)
        self.assertNotIn("lag:PrintComplete->TampRequest", violated_keys)
        self.assertNotIn("lag:TampRequest->TampExtend", violated_keys)
        self.assertIn("Product transfer is delayed after tamp extension", issues)
        self.assertEqual(1, len(topology_findings))
        self.assertEqual(
            "TampExtend subsystem",
            topology_findings[0].likely_fault_region,
        )
        self.assertEqual(
            "Delay first appears after TampExtend.",
            topology_findings[0].reason,
        )
        self.assertEqual(
            ["Cylinder sticking", "Air pressure issue", "Sensor fault"],
            [cause.name for cause in ranked_causes],
        )
        self.assertEqual(
            ["High", "Medium", "Low"],
            [cause.confidence for cause in ranked_causes],
        )
        self.assertTrue(
            all(cause.contributions for cause in ranked_causes)
        )
        self.assertEqual(
            [100.0, 65.0, 35.0],
            [cause.score for cause in ranked_causes],
        )
        for cause in ranked_causes:
            self.assertEqual(
                cause.score,
                sum(contribution.points for contribution in cause.contributions),
            )

    def test_topology_graph_reports_upstream_and_downstream_dependencies(self) -> None:
        topology = load_topology(PROJECT_ROOT / "data" / "topology.yaml")

        self.assertEqual(
            ["PrintComplete", "TampRequest"],
            topology.upstream_dependencies("TampExtend"),
        )
        self.assertEqual(
            ["ProductTransfer"],
            topology.downstream_dependencies("TampExtend"),
        )

    def test_labeling_guide_rules_load_as_deterministic_knowledge_base(self) -> None:
        guide_rules = load_rules(PROJECT_ROOT / "rules" / "labeling_guide.yaml")

        self.assertEqual(5, len(guide_rules))
        symptoms = {rule.symptom for rule in guide_rules}
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

        alignment_rule = next(
            rule for rule in guide_rules if rule.rule_id == "label_alignment_off"
        )
        self.assertIn("Peel tip square to bottle?", alignment_rule.checks)
        self.assertIn("Adjust Peel Angle", alignment_rule.actions)
        self.assertEqual(alignment_rule.actions, alignment_rule.recommendations)
        self.assertEqual("bubbles_on_labels", alignment_rule.cross_links[0].symptom_id)

        events = load_events(PROJECT_ROOT / "data" / "sample_events.csv")
        observations = calculate_timing_observations(events)
        baseline = load_baseline(PROJECT_ROOT / "data" / "baseline.json")
        drift_findings = calculate_drift(observations.metrics, baseline)

        self.assertEqual([], match_rules(drift_findings, guide_rules))

    def test_run_pipeline_writes_text_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.txt"
            report = run_pipeline(
                events_path=PROJECT_ROOT / "data" / "sample_events.csv",
                baseline_path=PROJECT_ROOT / "data" / "baseline.json",
                rules_path=PROJECT_ROOT / "rules" / "troubleshooting_rules.yaml",
                topology_path=PROJECT_ROOT / "data" / "topology.yaml",
                output_path=output_path,
            )

            self.assertTrue(output_path.exists())
            self.assertIn("Observations", report)
            self.assertIn("Drift Findings", report)
            self.assertIn("Topology Findings", report)
            self.assertIn("Likely Fault Region: TampExtend subsystem", report)
            self.assertIn("Candidate Causes", report)
            self.assertIn("1. Cylinder sticking", report)
            self.assertIn("Confidence: High", report)
            self.assertIn("rule_match: +30.0/30.0", report)
            self.assertIn("Recommended Checks", report)


if __name__ == "__main__":
    unittest.main()
