"""Topology context tests for structure and evidence enrichment."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_DIR))

from linealert.topology.component import Component  # noqa: E402
from linealert.topology.dependency import Dependency  # noqa: E402
from linealert.topology.report import (  # noqa: E402
    attach_topology_context_to_evidence,
    generate_topology_report,
)
from linealert.topology.topology import MachineTopology, load_topology  # noqa: E402
from linealert.topology.validator import validate_topology  # noqa: E402
from validation.baseline import load_relationships  # noqa: E402


TOPOLOGY_CONFIG = REPO_ROOT / "config" / "topology.json"
RELATIONSHIP_CONFIG = REPO_ROOT / "config" / "event_relationships.json"


class TopologyContextTests(unittest.TestCase):
    def test_valid_topology_loads_with_event_component_map(self) -> None:
        topology = load_topology(TOPOLOGY_CONFIG)

        self.assertEqual(4, topology.component_count)
        self.assertEqual(3, topology.dependency_count)
        self.assertEqual(
            "tamp_cylinder",
            topology.event_component_map["TampExtendCommand"],
        )
        self.assertEqual(
            "Tamp Cylinder",
            topology.component_for_event("TampExtendCommand").name,
        )

    def test_orphan_detection_works(self) -> None:
        topology = MachineTopology(
            components={
                "product_sensor": Component("product_sensor", "Product Sensor", "Sensor"),
                "print_head": Component("print_head", "Print Head", "Actuator"),
                "tamp_cylinder": Component("tamp_cylinder", "Tamp Cylinder", "Actuator"),
            },
            dependencies=[Dependency("product_sensor", "print_head")],
        )

        report = validate_topology(topology).as_dict()

        self.assertEqual(["tamp_cylinder"], report["orphan_components"])
        self.assertEqual("OrphanComponent", report["observations"][0]["observation_type"])

    def test_circular_dependency_detection_works(self) -> None:
        topology = MachineTopology(
            components={
                "product_sensor": Component("product_sensor", "Product Sensor", "Sensor"),
                "print_head": Component("print_head", "Print Head", "Actuator"),
                "tamp_cylinder": Component("tamp_cylinder", "Tamp Cylinder", "Actuator"),
            },
            dependencies=[
                Dependency("product_sensor", "print_head"),
                Dependency("print_head", "tamp_cylinder"),
                Dependency("tamp_cylinder", "product_sensor"),
            ],
        )

        report = validate_topology(topology).as_dict()

        self.assertEqual(
            ["print_head -> tamp_cylinder -> product_sensor -> print_head"],
            report["circular_dependencies"],
        )
        self.assertEqual("CircularDependency", report["observations"][0]["observation_type"])

    def test_disconnected_chain_detection_works(self) -> None:
        topology = MachineTopology(
            components={
                "product_sensor": Component("product_sensor", "Product Sensor", "Sensor"),
                "print_head": Component("print_head", "Print Head", "Actuator"),
                "reject_gate": Component("reject_gate", "Reject Gate", "Actuator"),
                "reject_bin": Component("reject_bin", "Reject Bin", "Bin"),
            },
            dependencies=[
                Dependency("product_sensor", "print_head"),
                Dependency("reject_gate", "reject_bin"),
            ],
        )

        report = validate_topology(topology).as_dict()

        self.assertEqual(
            [["product_sensor", "print_head"], ["reject_gate", "reject_bin"]],
            report["disconnected_chains"],
        )
        self.assertEqual(
            ["DisconnectedChain", "DisconnectedChain"],
            [observation["observation_type"] for observation in report["observations"]],
        )

    def test_event_to_component_mapping_detects_unknown_components(self) -> None:
        topology = MachineTopology(
            components={
                "print_head": Component("print_head", "Print Head", "Actuator"),
            },
            dependencies=[],
            event_component_map={"PrintComplete": "missing_print_head"},
        )

        report = validate_topology(topology).as_dict()

        self.assertEqual(
            {"PrintComplete": "missing_print_head"},
            report["events_mapped_to_unknown_components"],
        )
        self.assertEqual(
            "UnknownEventComponentMapping",
            report["observations"][-1]["observation_type"],
        )

    def test_evidence_can_include_topology_context(self) -> None:
        topology = load_topology(TOPOLOGY_CONFIG)
        relationships = load_relationships(RELATIONSHIP_CONFIG)
        evidence = [
            {
                "cycle_id": 42,
                "machine_state": "Production",
                "relationship": "Tamp Extension Lag",
                "observed_ms": 1100,
                "baseline_ms": 600,
                "status": "OutOfBaseline",
            }
        ]

        enriched = attach_topology_context_to_evidence(
            evidence_records=evidence,
            topology=topology,
            relationships=relationships,
        )

        self.assertEqual(
            {
                "cycle_id": 42,
                "machine_state": "Production",
                "relationship": "Tamp Extension Lag",
                "component_id": "tamp_cylinder",
                "component_name": "Tamp Cylinder",
                "observed_ms": 1100,
                "baseline_ms": 600,
                "status": "OutOfBaseline",
                "upstream_components": ["print_head"],
                "downstream_components": ["tamp_sensor"],
            },
            enriched[0],
        )

    def test_topology_report_and_text_view_are_observation_only(self) -> None:
        topology = load_topology(TOPOLOGY_CONFIG)
        report = generate_topology_report(topology)

        self.assertEqual(
            {
                "component_count": 4,
                "dependency_count": 3,
                "missing_components": [],
                "orphan_components": [],
                "circular_dependencies": [],
                "disconnected_chains": [],
                "events_mapped_to_unknown_components": {},
                "observations": [],
            },
            report,
        )
        self.assertEqual(
            "\n".join(
                [
                    "Product Sensor",
                    "  ↓",
                    "Print Head",
                    "  ↓",
                    "Tamp Cylinder",
                    "  ↓",
                    "Tamp Extended Sensor",
                ]
            ),
            topology.visualize(),
        )
        self.assertNotIn("recommend", str(report).lower())
        self.assertNotIn("root cause", str(report).lower())


if __name__ == "__main__":
    unittest.main()
