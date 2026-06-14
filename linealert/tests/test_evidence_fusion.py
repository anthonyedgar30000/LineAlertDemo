"""Tests for first-class Evidence Fusion."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_DIR))

from linealert.evidence.evidence_collection import EvidenceCollection  # noqa: E402
from linealert.evidence.evidence_fusion import fuse_evidence  # noqa: E402
from linealert.evidence.evidence_item import EvidenceItem  # noqa: E402
from linealert.evidence.report import (  # noqa: E402
    format_evidence_fusion_report,
    generate_evidence_fusion_report,
)
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


class EvidenceFusionTests(unittest.TestCase):
    def test_evidence_collection_calculates_density_and_source_distribution(self) -> None:
        collection = EvidenceCollection(items=_multi_source_items())

        self.assertEqual(4, collection.evidence_count)
        self.assertEqual(4, collection.evidence_density)
        self.assertEqual(
            {
                "Baseline Analysis": 2,
                "Dependency Chain": 1,
                "Relationship Integrity": 1,
            },
            collection.source_distribution,
        )
        self.assertEqual(3, collection.sources_contributing)

    def test_fusion_clusters_multi_source_observations_without_inventing_evidence(self) -> None:
        fused = fuse_evidence(EvidenceCollection(items=_multi_source_items()))
        cluster = fused.observation_clusters[0]

        self.assertEqual("Tamp Operation Deviation", cluster.cluster)
        self.assertEqual(4, cluster.evidence_count)
        self.assertEqual(3, cluster.sources_contributing)
        self.assertEqual([7, 8], cluster.cycles_observed)
        self.assertEqual("Significant Deviation", cluster.severity)
        self.assertEqual(0.927, cluster.confidence)
        self.assertEqual(
            [
                "Tamp lag exceeded baseline",
                "Dependency chain broken",
                "Missing required relationship",
                "Tamp lag exceeded baseline",
            ],
            [item.observation for item in cluster.supporting_evidence],
        )

    def test_fusion_preserves_full_provenance(self) -> None:
        fused = fuse_evidence(EvidenceCollection(items=_multi_source_items()))
        evidence = fused.observation_clusters[0].supporting_evidence[0].as_dict()

        self.assertEqual("Baseline Analysis", evidence["source"])
        self.assertEqual("Tamp lag exceeded baseline", evidence["observation"])
        self.assertEqual("2026-06-14T10:02:00Z", evidence["timestamp"])
        self.assertEqual(7, evidence["cycle_id"])
        self.assertEqual(
            {
                "relationship": "Tamp Extension Lag",
                "measured_ms": 1100,
                "baseline_ms": 600,
            },
            evidence["source_evidence"],
        )

    def test_single_source_observation_forms_its_own_cluster(self) -> None:
        fused = fuse_evidence(
            EvidenceCollection(
                items=[
                    *_multi_source_items(),
                    EvidenceItem(
                        source="Topology Integrity",
                        observation="Topology validation passed",
                        severity="Normal",
                        confidence=1.0,
                        timestamp="2026-06-14T10:02:00Z",
                        cycle_id=None,
                        source_evidence={"observations": []},
                        cluster="Topology Integrity",
                    ),
                ]
            )
        )

        self.assertEqual(
            ["Tamp Operation Deviation", "Topology Integrity"],
            [cluster.cluster for cluster in fused.observation_clusters],
        )
        topology_cluster = fused.observation_clusters[1]
        self.assertEqual(1, topology_cluster.evidence_count)
        self.assertEqual(1, topology_cluster.sources_contributing)

    def test_report_generation_outputs_json_and_text_summary(self) -> None:
        fused = fuse_evidence(EvidenceCollection(items=_multi_source_items()))
        report = generate_evidence_fusion_report(fused)
        text = format_evidence_fusion_report(fused)

        self.assertEqual(4, report["evidence_count"])
        self.assertEqual(4, report["evidence_density"])
        self.assertEqual(3, report["sources_contributing"])
        self.assertEqual("Tamp Operation Deviation", report["observation_clusters"][0]["cluster"])
        self.assertIn("EVIDENCE SUMMARY", text)
        self.assertIn("Observation Cluster:\nTamp Operation Deviation", text)
        self.assertIn("Baseline Analysis:", text)
        self.assertIn("- Tamp lag exceeded baseline", text)
        self.assertIn("Evidence Density: 4 observations", text)
        self.assertIn("Sources Contributing: 3", text)
        self.assertNotIn("root cause identified", text.lower())
        self.assertNotIn("replace", text.lower())

    def test_situation_assessment_includes_evidence_fusion_summary(self) -> None:
        fused = fuse_evidence(EvidenceCollection(items=_multi_source_items()))
        assessment = build_situation_assessment(
            topology_aware_evidence_records=[
                {
                    "cycle_id": 7,
                    "machine_state": "Production",
                    "relationship": "Tamp Extension Lag",
                    "measured_ms": 1100,
                    "baseline_ms": 600,
                    "deviation_percent": 83.333,
                    "status": "OutOfBaseline",
                    "component_name": "Tamp Cylinder",
                }
            ],
            topology_validation_results=VALID_TOPOLOGY,
            cycles_observed=8,
            assessment_id="assessment-with-fusion",
            evidence_fusion_summary=fused.as_dict(),
        )
        assessment_dict = assessment.as_dict()
        text = format_situation_assessment(assessment)

        self.assertEqual(
            {
                "evidence_count": 4,
                "evidence_density": 4,
                "evidence_sources_contributing": 3,
                "evidence_source_distribution": {
                    "Baseline Analysis": 2,
                    "Dependency Chain": 1,
                    "Relationship Integrity": 1,
                },
                "observation_clusters": ["Tamp Operation Deviation"],
            },
            assessment_dict["evidence_summary"],
        )
        self.assertIn("Evidence Summary:", text)
        self.assertIn("- Evidence density: 4 observations", text)
        self.assertIn("- Evidence sources contributing: 3", text)
        self.assertIn("  - Tamp Operation Deviation", text)


def _multi_source_items() -> list[EvidenceItem]:
    return [
        EvidenceItem(
            source="Baseline Analysis",
            observation="Tamp lag exceeded baseline",
            severity="Significant Deviation",
            confidence=0.95,
            timestamp="2026-06-14T10:02:00Z",
            cycle_id=7,
            source_evidence={
                "relationship": "Tamp Extension Lag",
                "measured_ms": 1100,
                "baseline_ms": 600,
            },
            cluster="Tamp Operation Deviation",
        ),
        EvidenceItem(
            source="Dependency Chain",
            observation="Dependency chain broken",
            severity="Degraded",
            confidence=0.90,
            timestamp="2026-06-14T10:02:00Z",
            cycle_id=7,
            source_evidence={
                "chain_id": "chain_1",
                "observation_type": "MissingDependencyEvent",
            },
            cluster="Tamp Operation Deviation",
        ),
        EvidenceItem(
            source="Relationship Integrity",
            observation="Missing required relationship",
            severity="Degraded",
            confidence=0.92,
            timestamp="2026-06-14T10:02:00Z",
            cycle_id=7,
            source_evidence={
                "relationship": "TampExtendCommand->TampExtendedSensor",
                "observation_type": "MissingRequiredRelationship",
            },
            cluster="Tamp Operation Deviation",
        ),
        EvidenceItem(
            source="Baseline Analysis",
            observation="Tamp lag exceeded baseline",
            severity="Significant Deviation",
            confidence=0.94,
            timestamp="2026-06-14T10:02:05Z",
            cycle_id=8,
            source_evidence={
                "relationship": "Tamp Extension Lag",
                "measured_ms": 1100,
                "baseline_ms": 600,
            },
            cluster="Tamp Operation Deviation",
        ),
    ]


if __name__ == "__main__":
    unittest.main()
