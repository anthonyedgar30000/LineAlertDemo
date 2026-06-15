"""Validation-suite tests for simulator-backed behavioral evidence."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_DIR))

from validation.anomaly_detector import detect_anomalies  # noqa: E402
from validation.baseline import generate_baseline, load_relationships  # noqa: E402
from validation.report_generator import generate_evidence_report  # noqa: E402
from validation.scenarios import build_validation_scenarios  # noqa: E402


RELATIONSHIP_CONFIG = REPO_ROOT / "config" / "event_relationships.json"


class ValidationSuiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.relationships = load_relationships(RELATIONSHIP_CONFIG)
        scenarios = {
            scenario.name: scenario
            for scenario in build_validation_scenarios(cycle_count=20)
        }
        self.scenarios = scenarios
        self.baseline = generate_baseline(
            events=scenarios["Normal"].event_source.read_events(),
            relationships=self.relationships,
        )

    def test_baseline_generation_stores_expected_timing_values(self) -> None:
        baseline_dict = self.baseline.as_dict()

        self.assertEqual(
            {
                "PrintComplete->TampExtendCommand",
                "ProductDetected->PrintComplete",
                "TampExtendCommand->TampExtendedSensor",
            },
            set(baseline_dict["relationships"]),
        )
        self.assertEqual(
            {
                "avg_ms": 600.0,
                "stddev_ms": 0.0,
                "sample_count": 20,
            },
            baseline_dict["relationships"]["TampExtendCommand->TampExtendedSensor"],
        )
        self.assertEqual(
            {
                "avg_ms": 4800.0,
                "stddev_ms": 0.0,
                "sample_count": 20,
            },
            baseline_dict["cycle_duration_ms"],
        )

    def test_normal_scenario_has_no_anomaly(self) -> None:
        anomalies = self._detect("Normal")

        self.assertEqual([], anomalies)

    def test_slow_tamp_produces_lag_anomaly_without_sequence_violation(self) -> None:
        anomalies = self._detect("SlowTamp")
        issue_types = {anomaly.issue_type for anomaly in anomalies}
        lag_anomaly = next(
            anomaly for anomaly in anomalies if anomaly.issue_type == "ExcessiveLag"
        )

        self.assertIn("ExcessiveLag", issue_types)
        self.assertNotIn("SequenceViolation", issue_types)
        self.assertEqual("Tamp Extension Lag", lag_anomaly.evidence[0].relationship)
        self.assertGreater(lag_anomaly.evidence[0].observed_ms, 1000.0)

    def test_missed_sensor_produces_missing_event_and_sequence_evidence(self) -> None:
        anomalies = self._detect("MissedSensor")
        issue_types = {anomaly.issue_type for anomaly in anomalies}
        missing_anomaly = next(
            anomaly for anomaly in anomalies if anomaly.issue_type == "MissingEvent"
        )

        self.assertIn("MissingEvent", issue_types)
        self.assertIn("SequenceViolation", issue_types)
        self.assertEqual(
            {"TampExtendedSensor"},
            {record.event_name for record in missing_anomaly.evidence},
        )

    def test_drift_scenario_produces_increasing_drift_evidence(self) -> None:
        anomalies = self._detect("Drift")
        issue_types = {anomaly.issue_type for anomaly in anomalies}
        drift_anomaly = next(
            anomaly for anomaly in anomalies if anomaly.issue_type == "IncreasingDrift"
        )

        self.assertIn("IncreasingDrift", issue_types)
        self.assertGreater(drift_anomaly.evidence[0].observed_ms, 700.0)
        self.assertGreater(drift_anomaly.evidence[0].deviation_percent, 25.0)

    def test_random_jitter_produces_rhythm_instability_evidence(self) -> None:
        anomalies = self._detect("RandomJitter")
        issue_types = {anomaly.issue_type for anomaly in anomalies}
        rhythm_anomaly = next(
            anomaly
            for anomaly in anomalies
            if anomaly.issue_type == "RhythmInstability"
        )

        self.assertIn("RhythmInstability", issue_types)
        self.assertGreater(rhythm_anomaly.evidence[0].observed_ms, 25.0)

    def test_scenarios_define_expected_behavioral_outcomes(self) -> None:
        expected_by_scenario = {
            scenario.name: scenario.expected_issue_types
            for scenario in self.scenarios.values()
        }

        self.assertEqual((), expected_by_scenario["Normal"])
        self.assertEqual(("ExcessiveLag",), expected_by_scenario["SlowTamp"])
        self.assertEqual(
            ("MissingEvent", "SequenceViolation"),
            expected_by_scenario["MissedSensor"],
        )
        self.assertEqual(("IncreasingDrift",), expected_by_scenario["Drift"])
        self.assertEqual(("RhythmInstability",), expected_by_scenario["RandomJitter"])

    def test_evidence_report_contains_observations_only(self) -> None:
        anomalies = self._detect("SlowTamp")
        report = generate_evidence_report(anomalies)

        self.assertEqual(1, report["anomaly_count"])
        self.assertEqual(20, report["evidence_count"])
        self.assertEqual("ExcessiveLag", report["anomalies"][0]["issue_type"])
        self.assertEqual(600.0, report["anomalies"][0]["baseline_lag_ms"])
        self.assertEqual(1100.0, report["anomalies"][0]["observed_lag_ms"])
        self.assertEqual("High", report["anomalies"][0]["severity"])
        self.assertNotIn("recommendation", str(report).lower())
        self.assertNotIn("root cause", str(report).lower())

    def _detect(self, scenario_name: str):
        return detect_anomalies(
            events=self.scenarios[scenario_name].event_source.read_events(),
            baseline=self.baseline,
            relationships=self.relationships,
        )


if __name__ == "__main__":
    unittest.main()
