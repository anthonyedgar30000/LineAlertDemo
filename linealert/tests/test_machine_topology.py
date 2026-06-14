"""Tests for first-class machine topology objects."""

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
from linealert.topology.topology import MachineTopology, load_topology  # noqa: E402
from linealert.topology.validator import validate_topology  # noqa: E402


TOPOLOGY_CONFIG = REPO_ROOT / "config" / "topology.json"


class MachineTopologyTests(unittest.TestCase):
    def test_valid_topology_loads_and_reports_no_validation_observations(self) -> None:
        topology = load_topology(TOPOLOGY_CONFIG)
        report = topology.report()

        self.assertEqual(4, report["component_count"])
        self.assertEqual(3, report["dependency_count"])
        self.assertEqual([], report["missing_components"])
        self.assertEqual([], report["orphan_components"])
        self.assertEqual([], report["circular_dependencies"])
        self.assertEqual([], report["disconnected_chains"])
        self.assertEqual([], report["observations"])

    def test_component_model_serializes_required_fields(self) -> None:
        component = Component(
            component_id="tamp_cylinder",
            name="Tamp Cylinder",
            component_type="Actuator",
            parent_component="labeler",
            metadata={"station": "apply"},
        )

        self.assertEqual(
            {
                "component_id": "tamp_cylinder",
                "name": "Tamp Cylinder",
                "type": "Actuator",
                "parent_component": "labeler",
                "metadata": {"station": "apply"},
            },
            component.as_dict(),
        )

    def test_visualization_renders_dependency_chain(self) -> None:
        topology = load_topology(TOPOLOGY_CONFIG)

        self.assertEqual(
            "\n".join(
                [
                    "ProductSensor",
                    "  ↓",
                    "PrintHead",
                    "  ↓",
                    "TampCylinder",
                    "  ↓",
                    "TampSensor",
                ]
            ),
            topology.visualize(),
        )

    def test_orphan_component_detection(self) -> None:
        topology = MachineTopology(
            components={
                "ProductSensor": Component("ProductSensor", "Product Sensor", "Sensor"),
                "PrintHead": Component("PrintHead", "Print Head", "Printer"),
                "TampCylinder": Component("TampCylinder", "Tamp Cylinder", "Actuator"),
            },
            dependencies=[Dependency("ProductSensor", "PrintHead")],
        )

        report = validate_topology(topology).as_dict()

        self.assertEqual(["TampCylinder"], report["orphan_components"])
        self.assertEqual("OrphanComponent", report["observations"][0]["observation_type"])

    def test_missing_component_detection(self) -> None:
        topology = MachineTopology(
            components={
                "PrintHead": Component("PrintHead", "Print Head", "Printer"),
            },
            dependencies=[Dependency("PrintHead", "TampCylinder")],
        )

        report = validate_topology(topology).as_dict()

        self.assertEqual(["TampCylinder"], report["missing_components"])
        self.assertEqual("MissingComponent", report["observations"][0]["observation_type"])

    def test_circular_dependency_detection(self) -> None:
        topology = MachineTopology(
            components={
                "PrintHead": Component("PrintHead", "Print Head", "Printer"),
                "TampCylinder": Component("TampCylinder", "Tamp Cylinder", "Actuator"),
                "TampSensor": Component("TampSensor", "Tamp Sensor", "Sensor"),
            },
            dependencies=[
                Dependency("PrintHead", "TampCylinder"),
                Dependency("TampCylinder", "TampSensor"),
                Dependency("TampSensor", "PrintHead"),
            ],
        )

        report = validate_topology(topology).as_dict()

        self.assertEqual(
            ["PrintHead -> TampCylinder -> TampSensor -> PrintHead"],
            report["circular_dependencies"],
        )
        self.assertEqual("CircularDependency", report["observations"][0]["observation_type"])

    def test_disconnected_chain_detection(self) -> None:
        topology = MachineTopology(
            components={
                "ProductSensor": Component("ProductSensor", "Product Sensor", "Sensor"),
                "PrintHead": Component("PrintHead", "Print Head", "Printer"),
                "RejectGate": Component("RejectGate", "Reject Gate", "Actuator"),
                "RejectBin": Component("RejectBin", "Reject Bin", "Bin"),
            },
            dependencies=[
                Dependency("ProductSensor", "PrintHead"),
                Dependency("RejectGate", "RejectBin"),
            ],
        )

        report = validate_topology(topology).as_dict()

        self.assertEqual(
            [["ProductSensor", "PrintHead"], ["RejectGate", "RejectBin"]],
            report["disconnected_chains"],
        )
        self.assertEqual(
            ["DisconnectedChain", "DisconnectedChain"],
            [
                observation["observation_type"]
                for observation in report["observations"]
            ],
        )

    def test_dependency_model_preserves_direction(self) -> None:
        dependency = Dependency("PrintHead", "TampCylinder")

        self.assertEqual("PrintHead -> TampCylinder", dependency.label)
        self.assertEqual(
            {"upstream": "PrintHead", "downstream": "TampCylinder"},
            dependency.as_dict(),
        )


if __name__ == "__main__":
    unittest.main()
