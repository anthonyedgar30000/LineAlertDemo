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
from main import run_pipeline  # noqa: E402
from timing_engine import calculate_timing_observations  # noqa: E402


class LineAlertPipelineTests(unittest.TestCase):
    def test_sample_data_produces_drift_and_rule_matches(self) -> None:
        events = load_events(PROJECT_ROOT / "data" / "sample_events.csv")
        observations = calculate_timing_observations(events)
        baseline = load_baseline(PROJECT_ROOT / "data" / "baseline.json")
        drift_findings = calculate_drift(observations.metrics, baseline)
        rules = load_rules(PROJECT_ROOT / "rules" / "troubleshooting_rules.yaml")
        candidate_causes = match_rules(drift_findings, rules)

        violated_keys = {
            finding.observation_key
            for finding in drift_findings
            if finding.threshold_violation
        }
        issues = {cause.issue for cause in candidate_causes}

        self.assertIn("lag:CycleStart->SensorTriggered", violated_keys)
        self.assertIn("lag:SensorTriggered->MotorStarted", violated_keys)
        self.assertIn("cycle:CycleStart", violated_keys)
        self.assertIn("Sensor response lag is increasing", issues)
        self.assertIn("Motor start is delayed after sensor trigger", issues)
        self.assertIn("Overall cycle timing is stretching", issues)

    def test_run_pipeline_writes_text_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "report.txt"
            report = run_pipeline(
                events_path=PROJECT_ROOT / "data" / "sample_events.csv",
                baseline_path=PROJECT_ROOT / "data" / "baseline.json",
                rules_path=PROJECT_ROOT / "rules" / "troubleshooting_rules.yaml",
                output_path=output_path,
            )

            self.assertTrue(output_path.exists())
            self.assertIn("Observations", report)
            self.assertIn("Drift Findings", report)
            self.assertIn("Candidate Causes", report)
            self.assertIn("Recommended Checks", report)


if __name__ == "__main__":
    unittest.main()
