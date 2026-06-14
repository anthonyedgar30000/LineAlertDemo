"""Tests for first-class Dependency Chain Analysis."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_DIR))

from event_loader import Event  # noqa: E402
from linealert.cycles.cycle_builder import build_cycles  # noqa: E402
from linealert.dependencies.chain_validator import validate_dependency_chains  # noqa: E402
from linealert.dependencies.dependency_chain import load_dependency_chains  # noqa: E402
from linealert.dependencies.dependency_graph import build_dependency_graph  # noqa: E402
from linealert.dependencies.report import (  # noqa: E402
    format_dependency_chain_report,
    generate_dependency_chain_report,
)
from validation.scenarios import build_validation_scenarios  # noqa: E402


DEPENDENCY_CHAIN_CONFIG = REPO_ROOT / "config" / "dependency_chains.json"


class DependencyChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chains = load_dependency_chains(DEPENDENCY_CHAIN_CONFIG)
        self.graph = build_dependency_graph(self.chains)
        self.scenarios = {
            scenario.name: scenario
            for scenario in build_validation_scenarios(cycle_count=4)
        }

    def test_dependency_chains_load_from_config(self) -> None:
        self.assertEqual(1, len(self.chains))
        self.assertEqual("chain_1", self.chains[0].chain_id)
        self.assertEqual(
            [
                "ProductDetected",
                "PrintComplete",
                "TampExtendCommand",
                "TampExtendedSensor",
                "TampHomeSensor",
                "CycleComplete",
            ],
            self.chains[0].events,
        )

    def test_graph_reports_direct_dependencies(self) -> None:
        self.assertEqual(
            ["TampExtendedSensor"],
            self.graph.direct_dependencies("TampExtendCommand"),
        )
        self.assertIn(
            ("ProductDetected", "PrintComplete"),
            self.graph.direct_edges,
        )

    def test_graph_reports_transitive_dependencies(self) -> None:
        self.assertEqual(
            [
                "PrintComplete",
                "TampExtendCommand",
                "TampExtendedSensor",
                "TampHomeSensor",
                "CycleComplete",
            ],
            self.graph.transitive_dependencies("ProductDetected"),
        )

    def test_normal_cycles_have_healthy_dependency_path(self) -> None:
        cycles = build_cycles(self.scenarios["Normal"].event_source.read_events())
        report = validate_dependency_chains(cycles=cycles, chains=self.chains)
        report_dict = generate_dependency_chain_report(self.graph, report)

        self.assertEqual("Healthy", report.integrity_status)
        self.assertEqual(0, report.observation_count)
        self.assertEqual("Healthy", report.path_health[0].status)
        self.assertEqual(4, report.path_health[0].healthy_cycles)
        self.assertEqual(100.0, report.path_health[0].percent_healthy)
        self.assertEqual(1, report_dict["validation"]["chain_count"])

    def test_missed_sensor_reports_dependency_chain_disruptions(self) -> None:
        cycles = build_cycles(self.scenarios["MissedSensor"].event_source.read_events())
        report = validate_dependency_chains(cycles=cycles, chains=self.chains)

        self.assertEqual("Disruptions Observed", report.integrity_status)
        self.assertEqual(4, report.observation_count)
        self.assertEqual("Disrupted", report.path_health[0].status)
        self.assertEqual(0, report.path_health[0].healthy_cycles)
        self.assertEqual(
            {"MissingDependencyEvent"},
            {observation.observation_type for observation in report.observations},
        )
        self.assertEqual(
            {"TampExtendedSensor"},
            {observation.event_name for observation in report.observations},
        )

    def test_order_disruption_is_reported_without_diagnosis(self) -> None:
        cycles = build_cycles(_events_with_home_before_extended_sensor())
        report = validate_dependency_chains(cycles=cycles, chains=self.chains)

        self.assertEqual(1, report.observation_count)
        self.assertEqual(
            "DependencyOrderDisruption",
            report.observations[0].observation_type,
        )
        self.assertEqual("TampExtendedSensor", report.observations[0].source)
        self.assertEqual("TampHomeSensor", report.observations[0].target)

    def test_text_report_contains_observations_only(self) -> None:
        cycles = build_cycles(self.scenarios["MissedSensor"].event_source.read_events())
        report = validate_dependency_chains(cycles=cycles, chains=self.chains)

        text = format_dependency_chain_report(self.graph, report)

        self.assertIn("DEPENDENCY CHAIN REPORT", text)
        self.assertIn("Status:\nDisruptions Observed", text)
        self.assertIn("MissingDependencyEvent", text)
        self.assertIn("Path Health:", text)
        self.assertIn("No diagnosis or root-cause determination performed.", text)
        self.assertIn("No maintenance recommendations generated.", text)
        self.assertNotIn("root cause identified", text.lower())
        self.assertNotIn("replace", text.lower())


def _events_with_home_before_extended_sensor() -> list[Event]:
    start = datetime(2026, 6, 14, 10, 0, 0, tzinfo=timezone.utc)
    event_names = [
        "CycleStart",
        "ProductDetected",
        "PrintComplete",
        "TampExtendCommand",
        "TampHomeSensor",
        "TampExtendedSensor",
        "CycleComplete",
    ]
    return [
        Event(
            timestamp=start + timedelta(milliseconds=index * 100),
            event_name=event_name,
            source_row=index + 1,
        )
        for index, event_name in enumerate(event_names)
    ]


if __name__ == "__main__":
    unittest.main()
