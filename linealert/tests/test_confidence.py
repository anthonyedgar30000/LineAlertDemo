"""Tests for Observation Confidence."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_DIR))

from linealert.confidence.confidence_engine import evaluate_observation_confidence  # noqa: E402
from linealert.confidence.factors import (  # noqa: E402
    configuration_validity_factor,
    historical_persistence_factor,
    multi_source_confirmation_factor,
    supporting_evidence_factor,
    topology_validation_factor,
)
from linealert.confidence.report import (  # noqa: E402
    format_confidence_report,
    generate_confidence_report,
)
from linealert.confidence.scoring import calculate_confidence_score, classify_confidence  # noqa: E402


OBSERVATION = "Tamp Extension Lag Exceeded Baseline"


class ObservationConfidenceTests(unittest.TestCase):
    def test_evidence_strength_scoring(self) -> None:
        factor = supporting_evidence_factor(evidence_count=6, cluster_count=2)

        self.assertEqual("Supporting Evidence", factor.name)
        self.assertEqual(0.22, factor.contribution)
        self.assertIn("6 supporting evidence item", factor.description)

    def test_source_diversity_scoring(self) -> None:
        single_source = multi_source_confirmation_factor(sources_contributing=1)
        multi_source = multi_source_confirmation_factor(sources_contributing=3)

        self.assertEqual(0.05, single_source.contribution)
        self.assertEqual(0.20, multi_source.contribution)
        self.assertIn("3 supporting evidence source", multi_source.description)

    def test_historical_stability_scoring(self) -> None:
        factor = historical_persistence_factor(
            persistence_cycles=12,
            recurrence_count=42,
            frequency=42,
        )

        self.assertEqual("Historical Persistence", factor.name)
        self.assertEqual(0.20, factor.contribution)
        self.assertIn("12 consecutive cycle", factor.description)

    def test_topology_confidence_scoring(self) -> None:
        factor = topology_validation_factor(
            topology_status="Valid",
            relationship_integrity_status="Valid",
            dependency_chain_status="Healthy",
        )

        self.assertEqual("Topology Validation", factor.name)
        self.assertEqual(0.15, factor.contribution)
        self.assertIn("Topology=Valid", factor.description)

    def test_configuration_confidence_scoring(self) -> None:
        factor = configuration_validity_factor(
            baseline_valid=True,
            configuration_provenance_status="Valid",
            configuration_drift_present=False,
        )

        self.assertEqual("Configuration Validity", factor.name)
        self.assertEqual(0.15, factor.contribution)
        self.assertIn("BaselineValid=True", factor.description)

    def test_classification_logic(self) -> None:
        self.assertEqual("Very Low", classify_confidence(0.10))
        self.assertEqual("Low", classify_confidence(0.30))
        self.assertEqual("Moderate", classify_confidence(0.50))
        self.assertEqual("High", classify_confidence(0.70))
        self.assertEqual("Very High", classify_confidence(0.90))

    def test_confidence_engine_generates_very_high_confidence(self) -> None:
        confidence = evaluate_observation_confidence(
            observation=OBSERVATION,
            evidence_fusion_summary=_fusion_summary(),
            historical_context_summary=_history_summary(),
            topology_integrity_status="Valid",
            relationship_integrity_status="Valid",
            dependency_chain_status="Healthy",
            baseline_valid=True,
            configuration_provenance_status="Valid",
            configuration_drift_present=False,
        )
        report = confidence.as_dict()

        self.assertEqual(1.0, confidence.confidence)
        self.assertEqual("Very High", confidence.classification)
        self.assertEqual(
            [
                "Supporting Evidence",
                "Historical Persistence",
                "Multi-Source Confirmation",
                "Topology Validation",
                "Configuration Validity",
            ],
            [factor["name"] for factor in report["factors"]],
        )

    def test_confidence_engine_handles_lower_support(self) -> None:
        confidence = evaluate_observation_confidence(
            observation=OBSERVATION,
            evidence_fusion_summary={
                "evidence_count": 1,
                "sources_contributing": 1,
                "observation_clusters": [{"cluster": "Tamp Operation Deviation"}],
            },
            historical_context_summary={"observation_summaries": []},
            topology_integrity_status="Observations Present",
            relationship_integrity_status="Observations Present",
            dependency_chain_status="Disruptions Observed",
            baseline_valid=False,
            configuration_provenance_status="Unknown",
            configuration_drift_present=True,
        )

        self.assertEqual(0.30, confidence.confidence)
        self.assertEqual("Low", confidence.classification)

    def test_score_calculation_caps_at_one(self) -> None:
        factors = [
            supporting_evidence_factor(100, 10),
            historical_persistence_factor(100, 100, 100),
            multi_source_confirmation_factor(4),
            topology_validation_factor("Valid", "Valid", "Healthy"),
            configuration_validity_factor(True, "Valid", False),
        ]

        self.assertEqual(1.0, calculate_confidence_score(factors))

    def test_report_generation_outputs_json_and_text_without_diagnosis(self) -> None:
        confidence = evaluate_observation_confidence(
            observation=OBSERVATION,
            evidence_fusion_summary=_fusion_summary(),
            historical_context_summary=_history_summary(),
            topology_integrity_status="Valid",
            relationship_integrity_status="Valid",
            dependency_chain_status="Healthy",
            baseline_valid=True,
            configuration_provenance_status="Valid",
            configuration_drift_present=False,
        )
        report = generate_confidence_report(confidence)
        text = format_confidence_report(confidence)

        self.assertEqual(OBSERVATION, report["observation"])
        self.assertEqual(1.0, report["confidence"])
        self.assertEqual("Very High", report["classification"])
        self.assertIn("OBSERVATION CONFIDENCE", text)
        self.assertIn("Confidence:\n1.000", text)
        self.assertIn("Classification:\nVery High", text)
        self.assertIn("Supporting Factors:", text)
        self.assertIn("RelationshipIntegrity=Valid", text)
        self.assertIn("No diagnosis or root-cause determination performed.", text)
        self.assertIn("No maintenance recommendations generated.", text)
        self.assertIn("No predictions generated.", text)
        self.assertNotIn("root cause identified", text.lower())
        self.assertNotIn("replace", text.lower())


def _fusion_summary() -> dict[str, object]:
    return {
        "evidence_count": 6,
        "evidence_density": 6,
        "source_distribution": {
            "Baseline Analysis": 2,
            "Dependency Chain": 2,
            "Relationship Integrity": 2,
        },
        "sources_contributing": 3,
        "observation_clusters": [
            {"cluster": "Tamp Operation Deviation"},
            {"cluster": "Topology Integrity"},
        ],
    }


def _history_summary() -> dict[str, object]:
    return {
        "observation_summaries": [
            {
                "observation": OBSERVATION,
                "occurrences": 42,
                "persistence_cycles": 12,
                "recurrence_count": 42,
            }
        ]
    }


if __name__ == "__main__":
    unittest.main()
