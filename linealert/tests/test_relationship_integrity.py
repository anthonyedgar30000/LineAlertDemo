"""Tests for Relationship Integrity Validation."""

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
from linealert.relationships.expected_map import (  # noqa: E402
    ExpectedRelationshipMap,
    load_expected_relationship_map,
)
from linealert.relationships.observed_map import build_observed_relationship_map  # noqa: E402
from linealert.relationships.relationship_model import RelationshipDefinition  # noqa: E402
from linealert.relationships.report import (  # noqa: E402
    format_relationship_integrity_report,
    generate_relationship_integrity_report,
)
from linealert.relationships.validator import validate_relationship_integrity  # noqa: E402
from validation.scenarios import build_validation_scenarios  # noqa: E402


RELATIONSHIP_INTEGRITY_CONFIG = REPO_ROOT / "config" / "relationship_integrity.json"


class RelationshipIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.expected_map = load_expected_relationship_map(RELATIONSHIP_INTEGRITY_CONFIG)
        self.scenarios = {
            scenario.name: scenario
            for scenario in build_validation_scenarios(cycle_count=4)
        }

    def test_expected_relationship_map_loads_required_relationships(self) -> None:
        self.assertEqual(3, len(self.expected_map.relationships))
        self.assertEqual(
            [
                "TampExtendCommand->TampExtendedSensor",
                "PrintComplete->TampExtendCommand",
                "ProductDetected->PrintComplete",
            ],
            [relationship.key for relationship in self.expected_map.relationships],
        )
        self.assertEqual(3, len(self.expected_map.required_relationships()))

    def test_normal_cycles_have_valid_relationship_integrity(self) -> None:
        cycles = build_cycles(self.scenarios["Normal"].event_source.read_events())
        observed_map = build_observed_relationship_map(cycles, self.expected_map)
        report = validate_relationship_integrity(self.expected_map, observed_map)
        report_dict = generate_relationship_integrity_report(report)

        self.assertEqual("Valid", report.integrity_status)
        self.assertEqual(4, report.observed_cycle_count)
        self.assertEqual(12, report.valid_observation_count)
        self.assertEqual([], report.missing_required_relationships)
        self.assertEqual([], report.order_violations)
        self.assertEqual(0, report_dict["observation_count"])

    def test_missed_sensor_reports_missing_required_relationships(self) -> None:
        cycles = build_cycles(self.scenarios["MissedSensor"].event_source.read_events())
        observed_map = build_observed_relationship_map(cycles, self.expected_map)
        report = validate_relationship_integrity(self.expected_map, observed_map)

        self.assertEqual("Observations Present", report.integrity_status)
        self.assertEqual(4, len(report.missing_required_relationships))
        self.assertEqual(
            {"TampExtendCommand->TampExtendedSensor"},
            {
                observation.relationship
                for observation in report.missing_required_relationships
            },
        )
        self.assertTrue(
            all(
                observation.observation_type == "MissingRequiredRelationship"
                for observation in report.missing_required_relationships
            )
        )

    def test_order_violation_reports_observed_relationship_deviation(self) -> None:
        expected_map = ExpectedRelationshipMap(
            relationships=[
                RelationshipDefinition(
                    source="TampExtendCommand",
                    target="TampExtendedSensor",
                    required=True,
                )
            ]
        )
        cycles = build_cycles(_events_with_tamp_sensor_before_command())
        observed_map = build_observed_relationship_map(cycles, expected_map)
        report = validate_relationship_integrity(expected_map, observed_map)

        self.assertEqual(1, len(report.order_violations))
        self.assertEqual("OrderViolation", report.order_violations[0].observation_type)
        self.assertEqual(
            "TampExtendCommand->TampExtendedSensor",
            report.order_violations[0].relationship,
        )

    def test_optional_missing_relationship_does_not_create_observation(self) -> None:
        expected_map = ExpectedRelationshipMap(
            relationships=[
                RelationshipDefinition(
                    source="TampExtendCommand",
                    target="TampExtendedSensor",
                    required=False,
                )
            ]
        )
        cycles = build_cycles(self.scenarios["MissedSensor"].event_source.read_events())
        observed_map = build_observed_relationship_map(cycles, expected_map)
        report = validate_relationship_integrity(expected_map, observed_map)

        self.assertEqual("Valid", report.integrity_status)
        self.assertEqual(0, report.observation_count)

    def test_text_report_contains_observations_only(self) -> None:
        cycles = build_cycles(self.scenarios["MissedSensor"].event_source.read_events())
        observed_map = build_observed_relationship_map(cycles, self.expected_map)
        report = validate_relationship_integrity(self.expected_map, observed_map)

        text = format_relationship_integrity_report(report)

        self.assertIn("RELATIONSHIP INTEGRITY REPORT", text)
        self.assertIn("Status:\nObservations Present", text)
        self.assertIn("MissingRequiredRelationship", text)
        self.assertIn("No diagnosis or root-cause determination performed.", text)
        self.assertIn("No maintenance recommendations generated.", text)
        self.assertNotIn("root cause identified", text.lower())
        self.assertNotIn("replace", text.lower())


def _events_with_tamp_sensor_before_command() -> list[Event]:
    start = datetime(2026, 6, 14, 10, 0, 0, tzinfo=timezone.utc)
    event_names = [
        "CycleStart",
        "ProductDetected",
        "PrintComplete",
        "TampExtendedSensor",
        "TampExtendCommand",
        "TampHomeSensor",
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
