"""Run a complete LineAlert simulator demonstration.

This script orchestrates existing LineAlert modules into a human-readable demo
report. It does not modify simulator behavior or add diagnosis/root-cause logic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "linealert" / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_DIR))

from adapters.simulator_adapter import SimulatorEventSource  # noqa: E402
from linealert.confidence.confidence_engine import evaluate_observation_confidence  # noqa: E402
from linealert.cycles.cycle_builder import build_cycles  # noqa: E402
from linealert.cycles.timeline import format_cycle_timeline  # noqa: E402
from linealert.dependencies.chain_validator import validate_dependency_chains  # noqa: E402
from linealert.dependencies.dependency_chain import load_dependency_chains  # noqa: E402
from linealert.dependencies.dependency_graph import build_dependency_graph  # noqa: E402
from linealert.dependencies.report import generate_dependency_chain_report  # noqa: E402
from linealert.evidence.evidence_collection import EvidenceCollection  # noqa: E402
from linealert.evidence.evidence_fusion import fuse_evidence  # noqa: E402
from linealert.evidence.evidence_item import EvidenceItem  # noqa: E402
from linealert.evidence.report import generate_evidence_fusion_report  # noqa: E402
from linealert.history.drift_tracker import DriftMeasurement, track_historical_drift  # noqa: E402
from linealert.history.observation_history import ObservationHistory  # noqa: E402
from linealert.history.report import generate_historical_context_report  # noqa: E402
from linealert.relationships.expected_map import load_expected_relationship_map  # noqa: E402
from linealert.relationships.observed_map import build_observed_relationship_map  # noqa: E402
from linealert.relationships.report import generate_relationship_integrity_report  # noqa: E402
from linealert.relationships.validator import validate_relationship_integrity  # noqa: E402
from linealert.situation.assessment import build_situation_assessment  # noqa: E402
from linealert.topology.report import attach_topology_context_to_evidence, generate_topology_report  # noqa: E402
from linealert.topology.topology import load_topology  # noqa: E402
from linealert.workflows.engine import find_workflow  # noqa: E402
from linealert.workflows.evidence_filter import review_workflow_evidence  # noqa: E402
from linealert.workflows.loader import load_decision_tree_workflows  # noqa: E402
from linealert.workflows.prioritization import prioritize_workflow  # noqa: E402
from linealert.workflows.priority_report import (  # noqa: E402
    format_priority_report,
    generate_priority_report,
)
from simulator.plc_simulator import FaultMode, PLCSimulator, SimulatorConfig  # noqa: E402
from validation.baseline import generate_baseline, load_relationships  # noqa: E402


REPORT_DIR = REPO_ROOT / "demo" / "reports"
RELATIONSHIP_CONFIG = REPO_ROOT / "config" / "event_relationships.json"
RELATIONSHIP_INTEGRITY_CONFIG = REPO_ROOT / "config" / "relationship_integrity.json"
DEPENDENCY_CHAIN_CONFIG = REPO_ROOT / "config" / "dependency_chains.json"
TOPOLOGY_CONFIG = REPO_ROOT / "config" / "topology.json"
WORKFLOW_CONFIG = REPO_ROOT / "config" / "labeling_decision_trees.json"


def main() -> None:
    args = build_parser().parse_args()
    report = run_demo(scenario=args.scenario, cycles=args.cycles)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    text_path = REPORT_DIR / "demo_report.txt"
    json_path = REPORT_DIR / "demo_report.json"
    priority_text_path = REPORT_DIR / "workflow_prioritization_report.txt"
    priority_json_path = REPORT_DIR / "workflow_prioritization_report.json"
    text_path.write_text(report["text_report"], encoding="utf-8")
    json_path.write_text(
        json.dumps(report["json_report"], indent=2) + "\n",
        encoding="utf-8",
    )
    priority_text_path.write_text(
        report["json_report"]["workflow_prioritization_text"],
        encoding="utf-8",
    )
    priority_json_path.write_text(
        json.dumps(report["json_report"]["workflow_prioritization"], indent=2) + "\n",
        encoding="utf-8",
    )
    print(report["text_report"])
    print(
        "\nReports written to:"
        f"\n- {text_path}"
        f"\n- {json_path}"
        f"\n- {priority_text_path}"
        f"\n- {priority_json_path}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the LineAlert demo report.")
    parser.add_argument(
        "--scenario",
        default="SlowTamp",
        choices=[mode.value for mode in FaultMode] + ["SlowTamp_Prioritized"],
        help="Simulator scenario for production cycles.",
    )
    parser.add_argument(
        "--cycles",
        default=12,
        type=int,
        help="Number of production cycles to observe.",
    )
    return parser


def run_demo(scenario: str, cycles: int) -> dict[str, object]:
    if cycles < 1:
        raise ValueError("--cycles must be at least 1")

    relationships = load_relationships(RELATIONSHIP_CONFIG)
    topology = load_topology(TOPOLOGY_CONFIG)
    topology_report = generate_topology_report(topology)

    baseline_events = _events_for_scenario(FaultMode.NORMAL, cycle_count=20)
    baseline = generate_baseline(events=baseline_events, relationships=relationships)

    fault_mode = _fault_mode_for_demo_scenario(scenario)
    production_events = _events_for_scenario(fault_mode, cycle_count=cycles)
    production_cycles = build_cycles(
        events=production_events,
        relationships=relationships,
        baseline=baseline,
    )

    expected_relationships = load_expected_relationship_map(RELATIONSHIP_INTEGRITY_CONFIG)
    observed_relationships = build_observed_relationship_map(
        cycles=production_cycles,
        expected_map=expected_relationships,
    )
    relationship_report = validate_relationship_integrity(
        expected_map=expected_relationships,
        observed_map=observed_relationships,
    )

    dependency_chains = load_dependency_chains(DEPENDENCY_CHAIN_CONFIG)
    dependency_graph = build_dependency_graph(dependency_chains)
    dependency_report = validate_dependency_chains(
        cycles=production_cycles,
        chains=dependency_chains,
    )

    topology_aware_evidence = _topology_aware_evidence(
        cycles=production_cycles,
        relationships=relationships,
        topology=topology,
    )
    evidence_items = _evidence_items(
        topology_aware_evidence=topology_aware_evidence,
        relationship_report=relationship_report,
        dependency_report=dependency_report,
        topology_report=topology_report,
        production_cycles=production_cycles,
    )
    evidence_collection = EvidenceCollection(items=evidence_items)
    fused_evidence = fuse_evidence(evidence_collection)
    fusion_report = generate_evidence_fusion_report(fused_evidence)

    history = ObservationHistory.from_evidence_items(
        [item for item in evidence_items if item.source == "Baseline Analysis"]
    )
    drift_indicator = track_historical_drift(
        measurements=[
            DriftMeasurement(
                metric_name="Average Tamp Lag",
                cycle_id=0,
                timestamp=baseline_events[0].timestamp.isoformat(),
                value=_baseline_ms(baseline, "TampExtendCommand->TampExtendedSensor"),
            ),
            *[
                DriftMeasurement(
                    metric_name="Average Tamp Lag",
                    cycle_id=evidence["cycle_id"],
                    timestamp=production_cycles[evidence["cycle_id"] - 1].start_timestamp.isoformat(),
                    value=float(evidence["measured_ms"]),
                )
                for evidence in topology_aware_evidence
            ],
        ],
        metric_name="Average Tamp Lag",
    )
    history_report = generate_historical_context_report(
        history=history,
        drift_indicators=[drift_indicator],
    )

    confidence = evaluate_observation_confidence(
        observation="Tamp Extension Lag exceeded baseline",
        evidence_fusion_summary=fusion_report,
        historical_context_summary=history_report,
        topology_integrity_status=topology_report_status(topology_report),
        relationship_integrity_status=relationship_report.integrity_status,
        dependency_chain_status=dependency_report.integrity_status,
        baseline_valid=True,
        configuration_provenance_status="Valid",
        configuration_drift_present=False,
    )

    workflows = load_decision_tree_workflows(WORKFLOW_CONFIG)
    workflow_result = find_workflow(workflows, "Bubbles")
    assert workflow_result.matched_workflow is not None
    priority_evidence_review = review_workflow_evidence(
        observed_condition="Tamp Extension Lag exceeded baseline",
        evidence_summary=fusion_report,
        relationship_integrity=generate_relationship_integrity_report(relationship_report),
        dependency_chains=generate_dependency_chain_report(
            graph=dependency_graph,
            validation_report=dependency_report,
        ),
        topology_validation=topology_report,
        confidence_summary=confidence.as_dict(),
    )
    related_workflows = [
        workflow
        for workflow in workflows
        if workflow.workflow_id in {"multiple_labels_applying", "label_has_stretch_lines"}
    ]
    workflow_prioritization = prioritize_workflow(
        workflow=workflow_result.matched_workflow,
        evidence_review=priority_evidence_review,
        related_workflows=related_workflows,
    )
    situation = build_situation_assessment(
        topology_aware_evidence_records=topology_aware_evidence,
        topology_validation_results=topology_report,
        cycles_observed=len(production_cycles),
        machine_state="Production",
        assessment_id="demo-linealert-situation-assessment",
        evidence_fusion_summary=fusion_report,
    )

    report_data = {
        "scenario": scenario,
        "machine_state": "Production",
        "event_timeline": format_cycle_timeline(production_cycles[0]),
        "cycle_summary": _cycle_summary(production_cycles),
        "baseline_comparison": _baseline_comparison(topology_aware_evidence),
        "topology_validation": topology_report,
        "relationship_integrity": generate_relationship_integrity_report(relationship_report),
        "dependency_chains": generate_dependency_chain_report(
            graph=dependency_graph,
            validation_report=dependency_report,
        ),
        "evidence_summary": fusion_report,
        "historical_context": history_report,
        "confidence_summary": confidence.as_dict(),
        "matched_workflow": _workflow_summary(workflow_result),
        "workflow_prioritization": generate_priority_report(workflow_prioritization),
        "workflow_prioritization_text": format_priority_report(workflow_prioritization),
        "situation_assessment": situation.as_dict(),
    }
    text_report = format_demo_report(report_data)
    return {"text_report": text_report, "json_report": report_data}


def _events_for_scenario(fault_mode: FaultMode, cycle_count: int):
    return SimulatorEventSource(
        simulator=PLCSimulator(
            SimulatorConfig(
                cycle_time_ms=5000,
                fault_mode=fault_mode,
                slow_tamp_delay_ms=500,
                drift_per_cycle_ms=10,
                jitter_ms=0,
                start_time="2026-06-14T10:00:00Z",
            )
        ),
        cycle_count=cycle_count,
    ).read_events()


def _fault_mode_for_demo_scenario(scenario: str) -> FaultMode:
    if scenario == "SlowTamp_Prioritized":
        return FaultMode.SLOW_TAMP
    return FaultMode(scenario)


def _topology_aware_evidence(cycles, relationships, topology) -> list[dict[str, object]]:
    raw_evidence = []
    for cycle in cycles:
        for evidence in cycle.evidence:
            raw_evidence.append(
                {
                    "cycle_id": evidence.cycle_id,
                    "machine_state": "Production",
                    "relationship": evidence.relationship,
                    "observed_ms": evidence.observed_ms,
                    "measured_ms": evidence.observed_ms,
                    "baseline_ms": evidence.baseline_ms,
                    "deviation_percent": evidence.deviation_percent,
                    "status": evidence.status.value,
                }
            )

    enriched = attach_topology_context_to_evidence(
        evidence_records=raw_evidence,
        topology=topology,
        relationships=relationships,
    )
    return [
        {
            "cycle_id": record["cycle_id"],
            "machine_state": record["machine_state"],
            "relationship": record["relationship"],
            "measured_ms": record["measured_ms"],
            "baseline_ms": record["baseline_ms"],
            "deviation_percent": round(float(record["deviation_percent"]), 3),
            "status": record["status"],
            "component_id": record.get("component_id"),
            "component_name": record.get("component_name"),
            "upstream_components": record.get("upstream_components", []),
            "downstream_components": record.get("downstream_components", []),
        }
        for record in enriched
    ]


def _evidence_items(
    topology_aware_evidence: list[dict[str, object]],
    relationship_report,
    dependency_report,
    topology_report: dict[str, object],
    production_cycles,
) -> list[EvidenceItem]:
    items = [
        EvidenceItem(
            source="Baseline Analysis",
            observation="Tamp Extension Lag exceeded baseline",
            severity="Significant Deviation",
            confidence=0.95,
            timestamp=production_cycles[evidence["cycle_id"] - 1].start_timestamp.isoformat(),
            cycle_id=evidence["cycle_id"],
            source_evidence={
                "relationship": evidence["relationship"],
                "measured_ms": evidence["measured_ms"],
                "baseline_ms": evidence["baseline_ms"],
                "deviation_percent": evidence["deviation_percent"],
            },
            cluster="Tamp Operation Deviation",
        )
        for evidence in topology_aware_evidence
    ]
    timestamp = production_cycles[0].start_timestamp.isoformat()
    items.extend(
        [
            EvidenceItem(
                source="Relationship Integrity",
                observation=f"Relationship integrity {relationship_report.integrity_status.lower()}",
                severity="Normal" if relationship_report.integrity_status == "Valid" else "Monitor",
                confidence=0.90,
                timestamp=timestamp,
                cycle_id=production_cycles[0].cycle_id,
                source_evidence=relationship_report.as_dict(),
                cluster="Relationship Integrity",
            ),
            EvidenceItem(
                source="Dependency Chain",
                observation=f"Dependency chain {dependency_report.integrity_status.lower()}",
                severity="Normal" if dependency_report.integrity_status == "Healthy" else "Monitor",
                confidence=0.90,
                timestamp=timestamp,
                cycle_id=production_cycles[0].cycle_id,
                source_evidence=dependency_report.as_dict(),
                cluster="Dependency Chain",
            ),
            EvidenceItem(
                source="Topology Integrity",
                observation=f"Topology validation {topology_report_status(topology_report).lower()}",
                severity="Normal" if topology_report_status(topology_report) == "Valid" else "Monitor",
                confidence=1.0,
                timestamp=timestamp,
                cycle_id=production_cycles[0].cycle_id,
                source_evidence=topology_report,
                cluster="Topology Integrity",
            ),
        ]
    )
    return items


def topology_report_status(topology_report: dict[str, object]) -> str:
    return "Valid" if not topology_report.get("observations") else "Observations Present"


def _cycle_summary(cycles) -> dict[str, object]:
    affected = [cycle.cycle_id for cycle in cycles if cycle.evidence]
    durations = [cycle.duration_ms for cycle in cycles]
    return {
        "cycles_observed": len(cycles),
        "cycles_affected": len(affected),
        "affected_cycle_ids": affected,
        "average_duration_ms": round(sum(durations) / len(durations), 3),
        "statuses": [cycle.status.value for cycle in cycles],
    }


def _baseline_comparison(evidence: list[dict[str, object]]) -> dict[str, object]:
    if not evidence:
        return {
            "relationship": "Tamp Extension Lag",
            "baseline_ms": 600.0,
            "observed_ms": None,
            "deviation_percent": None,
        }
    first = evidence[0]
    return {
        "relationship": first["relationship"],
        "baseline_ms": first["baseline_ms"],
        "observed_ms": first["measured_ms"],
        "deviation_percent": first["deviation_percent"],
    }


def _baseline_ms(baseline, relationship_key: str) -> float:
    return baseline.relationships[relationship_key].avg_ms


def _workflow_summary(workflow_result) -> dict[str, object]:
    workflow = workflow_result.matched_workflow
    if workflow is None:
        return {"matched": False, "display_name": "None", "guide_steps": []}

    guide_steps = []
    for step in workflow.steps:
        guide_steps.append(step.check)
        guide_steps.extend(step.actions)
    # Keep the demo report concise while still sourced from the structured tree.
    selected_steps = [
        workflow.steps[0].check,
        workflow.steps[0].actions[0],
        workflow.steps[1].actions[0],
        workflow.steps[3].actions[0],
    ]
    return {
        "matched": True,
        "workflow_id": workflow.workflow_id,
        "symptom": workflow.symptom,
        "display_name": f"{workflow.symptom} / Tamp Delay Workflow",
        "guide_steps": selected_steps,
        "structured_steps": [step.as_dict() for step in workflow.steps],
        "validation": "Run additional cycles and verify lag returns within baseline.",
        "escalation_conditions": workflow.escalation_conditions,
    }


def format_demo_report(report: dict[str, object]) -> str:
    baseline = report["baseline_comparison"]
    cycles = report["cycle_summary"]
    evidence_summary = report["evidence_summary"]
    history = report["historical_context"]
    confidence = report["confidence_summary"]
    workflow = report["matched_workflow"]
    workflow_prioritization = report["workflow_prioritization"]
    situation = report["situation_assessment"]
    affected_component = (
        situation["affected_components"][0]
        if situation["affected_components"]
        else "None observed"
    )
    observed_condition = (
        situation["observed_conditions"][0]
        if situation["observed_conditions"]
        else "No out-of-baseline relationship observed"
    )
    history_summary = history["observation_summaries"][0] if history["observation_summaries"] else {}

    lines = [
        "LINEALERT DEMO REPORT",
        "",
        "Scenario:",
        str(report["scenario"]),
        "",
        "Machine State:",
        str(report["machine_state"]),
        "",
        "Observed Condition:",
        str(observed_condition),
        "",
        "Baseline:",
        f"{_format_ms(baseline['baseline_ms'])} ms",
        "",
        "Observed:",
        f"{_format_ms(baseline['observed_ms'])} ms",
        "",
        "Deviation:",
        f"{_format_percent(baseline['deviation_percent'])}%",
        "",
        "Cycles Observed:",
        str(cycles["cycles_observed"]),
        "",
        "Cycles Affected:",
        str(cycles["cycles_affected"]),
        "",
        "Event Timeline:",
        str(report["event_timeline"]),
        "",
        "Cycle Summary:",
        f"- Average duration: {_format_ms(cycles['average_duration_ms'])} ms",
        f"- Affected cycle IDs: {', '.join(str(cycle_id) for cycle_id in cycles['affected_cycle_ids'])}",
        "",
        "Evidence Sources:",
        *[f"- {source}" for source in sorted(evidence_summary["source_distribution"])],
        "- Historical Context",
        "- Confidence Engine",
        "",
        "Evidence Summary:",
        f"- Evidence density: {evidence_summary['evidence_density']} observations",
        f"- Sources contributing: {evidence_summary['sources_contributing']}",
        f"- Observation clusters: {', '.join(cluster['cluster'] for cluster in evidence_summary['observation_clusters'])}",
        "",
        "Historical Context:",
        f"- Occurrences: {history_summary.get('occurrences', 0)}",
        f"- Persistence: {history_summary.get('persistence_cycles', 0)} consecutive cycles",
        f"- Evidence density trend: {history['evidence_density_trend']['direction']}",
        "",
        "Confidence:",
        str(confidence["classification"]),
        f"Score: {confidence['confidence']:.3f}",
        "",
        "Affected Component:",
        str(affected_component),
        "",
        "Matched Workflow:",
        str(workflow["display_name"]),
        "",
        "WORKFLOW ASSESSMENT",
        "",
        "Supported By Evidence",
        *[f"- {item}" for item in workflow_prioritization["supported_by_evidence"]],
        "",
        "Not Supported By Evidence",
        *[f"- {item}" for item in workflow_prioritization["not_supported_by_evidence"]],
        "",
        "Workflow Prioritization",
        "",
        "CHECK FIRST",
        *[
            f"{index}. {item['label']}\n   Reason: {item['reason']}"
            for index, item in enumerate(workflow_prioritization["check_first"], start=1)
        ],
        "",
        "CHECK SECOND",
        *[
            f"{index}. {item['label']}\n   Reason: {item['reason']}"
            for index, item in enumerate(
                workflow_prioritization["check_second"],
                start=len(workflow_prioritization["check_first"]) + 1,
            )
        ],
        "",
        "DEFERRED",
        *[
            f"- {item['label']}\n  Reason: {item['reason']}"
            for item in workflow_prioritization["deferred"]
        ],
        "",
        "RULED OUT",
        *[
            f"- {item['label']}\n  Reason: {item['reason']}"
            for item in workflow_prioritization["ruled_out"]
        ],
        "",
        "Suggested Guide Steps:",
        *[f"- {item['label']}" for item in workflow_prioritization["check_first"]],
        "",
        "Validation:",
        str(workflow["validation"]),
        "",
        "Final Situation Assessment:",
        f"- Status: {situation['situation_status']}",
        f"- Topology integrity: {situation['topology_integrity']}",
        f"- Confidence: {situation['confidence']:.3f}",
        "",
        "Important:",
        "- Deterministic evidence routing only.",
        "- Existing evidence boundaries preserved.",
        "- Existing engine logic was not modified.",
        "",
    ]
    return "\n".join(lines)


def _format_ms(value) -> str:
    if value is None:
        return "n/a"
    number = float(value)
    return str(int(number)) if number.is_integer() else f"{number:.1f}"


def _format_percent(value) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.1f}"


if __name__ == "__main__":
    main()
