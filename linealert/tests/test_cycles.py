"""Tests for first-class LineAlert cycle context."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_DIR))

from linealert.cycles.cycle import CycleStatus  # noqa: E402
from linealert.cycles.cycle_builder import build_cycles  # noqa: E402
from linealert.cycles.history import CycleHistory  # noqa: E402
from linealert.cycles.timeline import format_cycle_timeline  # noqa: E402
from validation.baseline import generate_baseline, load_relationships  # noqa: E402
from validation.scenarios import build_validation_scenarios  # noqa: E402


RELATIONSHIP_CONFIG = REPO_ROOT / "config" / "event_relationships.json"
TAMP_RELATIONSHIP = "Tamp Extension Lag"


class CycleContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.relationships = load_relationships(RELATIONSHIP_CONFIG)
        self.scenarios = {
            scenario.name: scenario
            for scenario in build_validation_scenarios(cycle_count=20)
        }
        self.baseline = generate_baseline(
            events=self.scenarios["Normal"].event_source.read_events(),
            relationships=self.relationships,
        )

    def test_cycle_builder_groups_complete_cycles(self) -> None:
        cycles = self._cycles_for("Normal")
        first_cycle = cycles[0]

        self.assertEqual(20, len(cycles))
        self.assertEqual(1, first_cycle.cycle_id)
        self.assertEqual("CycleStart", first_cycle.events[0].event_name)
        self.assertEqual("CycleComplete", first_cycle.events[-1].event_name)
        self.assertEqual(4800.0, first_cycle.duration_ms)
        self.assertEqual(4, len(first_cycle.measurements))
        self.assertEqual([], first_cycle.evidence)

    def test_normal_cycles_are_healthy(self) -> None:
        cycles = self._cycles_for("Normal")

        self.assertEqual(
            {CycleStatus.HEALTHY},
            {cycle.status for cycle in cycles},
        )

    def test_slow_tamp_cycles_are_out_of_baseline_with_cycle_evidence(self) -> None:
        cycles = self._cycles_for("SlowTamp")
        first_cycle = cycles[0]
        evidence = first_cycle.evidence[0]

        self.assertEqual(
            {CycleStatus.OUT_OF_BASELINE},
            {cycle.status for cycle in cycles},
        )
        self.assertEqual(1, evidence.cycle_id)
        self.assertEqual(TAMP_RELATIONSHIP, evidence.relationship)
        self.assertEqual("lag_ms", evidence.measurement)
        self.assertEqual(1100.0, evidence.observed_ms)
        self.assertEqual(600.0, evidence.baseline_ms)
        self.assertGreater(evidence.deviation_percent, 80.0)

    def test_drift_cycles_show_increasing_relationship_deviation(self) -> None:
        cycles = self._cycles_for("Drift")
        tamp_deviations = [
            measurement.deviation_ms
            for cycle in cycles
            for measurement in cycle.measurements
            if measurement.relationship == TAMP_RELATIONSHIP
        ]
        history = CycleHistory(cycles)

        self.assertEqual(0.0, tamp_deviations[0])
        self.assertEqual(190.0, tamp_deviations[-1])
        self.assertEqual(
            {
                "metric": TAMP_RELATIONSHIP,
                "slope_ms_per_cycle": 10.0,
                "direction": "increasing",
            },
            history.trend_over_cycles(TAMP_RELATIONSHIP),
        )

    def test_cycle_timeline_formats_event_offsets(self) -> None:
        cycle = self._cycles_for("Normal")[0]

        self.assertEqual(
            "\n".join(
                [
                    "Cycle 1",
                    "",
                    "00.000 CycleStart",
                    "01.100 ProductDetected",
                    "02.200 PrintComplete",
                    "03.000 TampExtendCommand",
                    "03.600 TampExtendedSensor",
                    "04.300 TampHomeSensor",
                    "04.800 CycleComplete",
                ]
            ),
            format_cycle_timeline(cycle),
        )

    def test_cycle_history_reports_last_cycles_and_averages(self) -> None:
        cycles = self._cycles_for("SlowTamp")
        history = CycleHistory(cycles)

        self.assertEqual([18, 19, 20], [cycle.cycle_id for cycle in history.last(3)])
        self.assertEqual(5300.0, history.average_cycle_duration_ms())
        self.assertEqual(1100.0, history.average_lag_ms(TAMP_RELATIONSHIP))

    def test_cycle_as_dict_contains_context_sections(self) -> None:
        cycle_dict = self._cycles_for("SlowTamp")[0].as_dict()

        self.assertEqual(1, cycle_dict["cycle_id"])
        self.assertEqual("OutOfBaseline", cycle_dict["status"])
        self.assertIn("events", cycle_dict)
        self.assertIn("measurements", cycle_dict)
        self.assertEqual(
            {
                "cycle_id": 1,
                "relationship": TAMP_RELATIONSHIP,
                "measurement": "lag_ms",
                "observed_ms": 1100.0,
                "baseline_ms": 600.0,
                "deviation_percent": 83.333,
                "status": "OutOfBaseline",
            },
            cycle_dict["evidence"][0],
        )

    def _cycles_for(self, scenario_name: str):
        return build_cycles(
            events=self.scenarios[scenario_name].event_source.read_events(),
            relationships=self.relationships,
            baseline=self.baseline,
        )


if __name__ == "__main__":
    unittest.main()
