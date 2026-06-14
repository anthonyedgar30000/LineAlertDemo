"""Command-line entry point for the LineAlert MVP pipeline."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from drift_engine import DriftFinding, calculate_drift, load_baseline
from event_loader import load_events
from expert_system import (
    CandidateCause,
    TroubleshootingRule,
    load_rules,
    match_rules,
    query_labeling_guide,
)
from hypothesis_engine import RankedCandidateCause, generate_ranked_hypotheses
from report_generator import build_demo_report, build_report, write_report
from timing_engine import TimingObservations, calculate_timing_observations
from topology_engine import (
    TopologyFinding,
    identify_first_drift_location,
    load_topology,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PipelineEvidence:
    """Evidence shared by standard and demo report modes."""

    observations: TimingObservations
    drift_findings: list[DriftFinding]
    rules: list[TroubleshootingRule]
    candidate_causes: list[CandidateCause]
    topology_findings: list[TopologyFinding]
    ranked_candidate_causes: list[RankedCandidateCause]


def _load_evidence(
    events_path: str | Path,
    baseline_path: str | Path,
    rules_path: str | Path,
    topology_path: str | Path,
) -> PipelineEvidence:
    events = load_events(events_path)
    observations = calculate_timing_observations(events)

    baseline = load_baseline(baseline_path)
    drift_findings = calculate_drift(observations.metrics, baseline)

    rules = load_rules(rules_path)
    candidate_causes = match_rules(drift_findings, rules)

    topology = load_topology(topology_path)
    topology_findings = identify_first_drift_location(topology, drift_findings)
    ranked_candidate_causes = generate_ranked_hypotheses(
        observations=observations,
        drift_findings=drift_findings,
        topology_findings=topology_findings,
        expert_rules=rules,
    )

    return PipelineEvidence(
        observations=observations,
        drift_findings=drift_findings,
        rules=rules,
        candidate_causes=candidate_causes,
        topology_findings=topology_findings,
        ranked_candidate_causes=ranked_candidate_causes,
    )


def run_pipeline(
    events_path: str | Path,
    baseline_path: str | Path,
    rules_path: str | Path,
    topology_path: str | Path,
    output_path: str | Path,
) -> str:
    """Run the evidence-first troubleshooting pipeline."""

    evidence = _load_evidence(
        events_path=events_path,
        baseline_path=baseline_path,
        rules_path=rules_path,
        topology_path=topology_path,
    )

    report_text = build_report(
        observations=evidence.observations,
        drift_findings=evidence.drift_findings,
        topology_findings=evidence.topology_findings,
        candidate_causes=evidence.candidate_causes,
        ranked_candidate_causes=evidence.ranked_candidate_causes,
    )
    write_report(report_text=report_text, output_path=output_path)
    return report_text


def run_demo(
    issue: str,
    events_path: str | Path,
    baseline_path: str | Path,
    rules_path: str | Path,
    guide_rules_path: str | Path,
    topology_path: str | Path,
    output_path: str | Path,
) -> str:
    """Run the end-to-end deterministic demo report."""

    evidence = _load_evidence(
        events_path=events_path,
        baseline_path=baseline_path,
        rules_path=rules_path,
        topology_path=topology_path,
    )
    guide_rules = load_rules(guide_rules_path)
    guide_response = query_labeling_guide(guide_rules, issue)

    report_text = build_demo_report(
        issue=issue,
        guide_response=guide_response,
        observations=evidence.observations,
        drift_findings=evidence.drift_findings,
        topology_findings=evidence.topology_findings,
        ranked_candidate_causes=evidence.ranked_candidate_causes,
    )
    write_report(report_text=report_text, output_path=output_path)
    return report_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run LineAlert deterministic troubleshooting analysis."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the end-to-end demo report mode.",
    )
    parser.add_argument(
        "--issue",
        default="Label Alignment Off",
        help="Reported issue text for demo mode.",
    )
    parser.add_argument(
        "--events",
        default=PROJECT_ROOT / "data" / "sample_events.csv",
        type=Path,
        help="Path to CSV event data.",
    )
    parser.add_argument(
        "--baseline",
        default=PROJECT_ROOT / "data" / "baseline.json",
        type=Path,
        help="Path to JSON timing baseline.",
    )
    parser.add_argument(
        "--rules",
        default=PROJECT_ROOT / "rules" / "troubleshooting_rules.yaml",
        type=Path,
        help="Path to YAML troubleshooting rules.",
    )
    parser.add_argument(
        "--guide-rules",
        default=PROJECT_ROOT / "rules" / "labeling_guide.yaml",
        type=Path,
        help="Path to YAML labeling guide rules for demo mode.",
    )
    parser.add_argument(
        "--topology",
        default=PROJECT_ROOT / "data" / "topology.yaml",
        type=Path,
        help="Path to YAML machine dependency topology.",
    )
    parser.add_argument(
        "--output",
        default=PROJECT_ROOT / "output" / "report.txt",
        type=Path,
        help="Path for the generated text report.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_path = args.output
    if args.demo and output_path == PROJECT_ROOT / "output" / "report.txt":
        output_path = PROJECT_ROOT / "output" / "demo_report.txt"

    if args.demo:
        run_demo(
            issue=args.issue,
            events_path=args.events,
            baseline_path=args.baseline,
            rules_path=args.rules,
            guide_rules_path=args.guide_rules,
            topology_path=args.topology,
            output_path=output_path,
        )
    else:
        run_pipeline(
            events_path=args.events,
            baseline_path=args.baseline,
            rules_path=args.rules,
            topology_path=args.topology,
            output_path=output_path,
        )
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
