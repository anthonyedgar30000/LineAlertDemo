"""Tests for first-class Historical Context."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_DIR))

from linealert.evidence.evidence_item import EvidenceItem  # noqa: E402
from linealert.history.drift_tracker import (  # noqa: E402
    DriftMeasurement,
    track_historical_drift,
)
from linealert.history.observation_history import ObservationHistory  # noqa: E402
from linealert.history.persistence import (  # noqa: E402
    load_observation_history,
    save_observation_history,
)
from linealert.history.report import (  # noqa: E402
    format_historical_context_report,
    generate_historical_context_report,
)
from linealert.history.trend_tracker import (  # noqa: E402
    track_cluster_history,
    track_evidence_density,
)


class HistoricalContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.history = ObservationHistory.from_evidence_items(_evidence_items())

    def test_observation_frequency_and_cycles_are_tracked(self) -> None:
        self.assertEqual(
            [10, 12, 15, 18],
            self.history.observation_cycles("Tamp Extension Lag Exceeded Baseline"),
        )
        self.assertEqual(
            4,
            self.history.observation_frequency("Tamp Extension Lag Exceeded Baseline"),
        )

    def test_observation_persistence_detects_consecutive_cycles(self) -> None:
        history = ObservationHistory.from_evidence_items(
            _persistent_evidence_items(cycle_count=12)
        )

        self.assertEqual(
            12,
            history.observation_persistence("Tamp Extension Lag Exceeded Baseline"),
        )

    def test_observation_recurrence_counts_recent_cycles(self) -> None:
        self.assertEqual(
            2,
            self.history.observation_recurrence(
                "Tamp Extension Lag Exceeded Baseline",
                last_n_cycles=2,
            ),
        )

    def test_severity_history_preserves_order(self) -> None:
        self.assertEqual(
            ["Monitor", "Monitor", "Monitor", "Significant Deviation"],
            self.history.severity_history("Tamp Extension Lag Exceeded Baseline"),
        )

    def test_evidence_density_history_tracks_per_cycle_density(self) -> None:
        self.assertEqual(
            {10: 1, 12: 2, 15: 1, 18: 2},
            self.history.evidence_density_by_cycle,
        )
        density_trend = track_evidence_density(self.history)

        self.assertEqual("Increasing", density_trend.direction)
        self.assertEqual(0.333, density_trend.as_dict()["average_step_change"])

    def test_cluster_history_tracks_appearance_persistence_and_recurrence(self) -> None:
        cluster_history = track_cluster_history(
            self.history,
            cluster="Tamp Operation Deviation",
            last_n_cycles=4,
        )

        self.assertEqual([10, 12, 15, 18], cluster_history.cycles_observed)
        self.assertEqual(5, cluster_history.occurrence_count)
        self.assertEqual(1, cluster_history.persistence_cycles)
        self.assertEqual(4, cluster_history.recurrence_count)

    def test_drift_tracking_reports_historical_increase_only(self) -> None:
        indicator = track_historical_drift(
            measurements=[
                DriftMeasurement("Average Tamp Lag", 1, "2026-06-14T10:00:00Z", 600),
                DriftMeasurement("Average Tamp Lag", 20, "2026-06-14T10:20:00Z", 700),
                DriftMeasurement("Average Tamp Lag", 40, "2026-06-14T10:40:00Z", 850),
                DriftMeasurement("Average Tamp Lag", 60, "2026-06-14T11:00:00Z", 1100),
            ],
            metric_name="Average Tamp Lag",
        )

        self.assertEqual("Increasing", indicator.direction)
        self.assertEqual("Historical Increase Detected", indicator.status)
        self.assertEqual(600, indicator.start_value)
        self.assertEqual(1100, indicator.end_value)
        self.assertEqual(500, indicator.change)

    def test_history_persistence_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "history.json"
            save_observation_history(self.history, path)

            loaded = load_observation_history(path)

        self.assertEqual(self.history.as_dict(), loaded.as_dict())

    def test_report_generation_outputs_json_and_text_without_diagnosis(self) -> None:
        drift_indicator = track_historical_drift(
            measurements=[
                DriftMeasurement("Average Tamp Lag", 1, "2026-06-14T10:00:00Z", 600),
                DriftMeasurement("Average Tamp Lag", 60, "2026-06-14T11:00:00Z", 1100),
            ],
            metric_name="Average Tamp Lag",
        )

        report = generate_historical_context_report(
            history=self.history,
            drift_indicators=[drift_indicator],
        )
        text = format_historical_context_report(
            history=self.history,
            drift_indicators=[drift_indicator],
        )

        self.assertEqual([10, 12, 15, 18], report["cycles_observed"])
        self.assertEqual(
            "Tamp Extension Lag Exceeded Baseline",
            report["observation_summaries"][0]["observation"],
        )
        self.assertEqual(
            "Increasing",
            report["evidence_density_trend"]["direction"],
        )
        self.assertEqual(
            "Historical Increase Detected",
            report["historical_drift_indicators"][0]["status"],
        )
        self.assertIn("HISTORICAL CONTEXT", text)
        self.assertIn("Observation:\nTamp Extension Lag Exceeded Baseline", text)
        self.assertIn("Occurrences:\n4", text)
        self.assertIn("Historical Drift:", text)
        self.assertIn("Observed increasing from 600ms to 1100ms", text)
        self.assertIn("No diagnosis or root-cause determination performed.", text)
        self.assertIn("No maintenance recommendations generated.", text)
        self.assertIn("No predictions generated.", text)
        self.assertNotIn("root cause identified", text.lower())
        self.assertNotIn("replace", text.lower())


def _evidence_items() -> list[EvidenceItem]:
    return [
        _item(cycle_id=10, severity="Monitor", confidence=0.80),
        _item(cycle_id=12, severity="Monitor", confidence=0.82),
        EvidenceItem(
            source="Relationship Integrity",
            observation="Missing required relationship",
            severity="Degraded",
            confidence=0.90,
            timestamp="2026-06-14T10:12:01Z",
            cycle_id=12,
            source_evidence={"relationship": "TampExtendCommand->TampExtendedSensor"},
            cluster="Tamp Operation Deviation",
        ),
        _item(cycle_id=15, severity="Monitor", confidence=0.85),
        _item(cycle_id=18, severity="Significant Deviation", confidence=0.95),
        EvidenceItem(
            source="Dependency Chain",
            observation="Dependency chain broken",
            severity="Degraded",
            confidence=0.88,
            timestamp="2026-06-14T10:18:01Z",
            cycle_id=18,
            source_evidence={"chain_id": "chain_1"},
            cluster="Dependency Chain Disruption",
        ),
    ]


def _persistent_evidence_items(cycle_count: int) -> list[EvidenceItem]:
    return [
        _item(cycle_id=cycle_id, severity="Monitor", confidence=0.8)
        for cycle_id in range(1, cycle_count + 1)
    ]


def _item(cycle_id: int, severity: str, confidence: float) -> EvidenceItem:
    return EvidenceItem(
        source="Baseline Analysis",
        observation="Tamp Extension Lag Exceeded Baseline",
        severity=severity,
        confidence=confidence,
        timestamp=f"2026-06-14T10:{cycle_id:02d}:00Z",
        cycle_id=cycle_id,
        source_evidence={
            "relationship": "Tamp Extension Lag",
            "measured_ms": 1100,
            "baseline_ms": 600,
        },
        cluster="Tamp Operation Deviation",
    )


if __name__ == "__main__":
    unittest.main()
