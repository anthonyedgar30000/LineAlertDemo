"""Command-line entry point for the LineAlert MVP pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from drift_engine import calculate_drift, load_baseline
from event_loader import load_events
from expert_system import load_rules, match_rules
from report_generator import build_report, write_report
from timing_engine import calculate_timing_observations
from topology_engine import identify_first_drift_location, load_topology


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_pipeline(
    events_path: str | Path,
    baseline_path: str | Path,
    rules_path: str | Path,
    topology_path: str | Path,
    output_path: str | Path,
) -> str:
    """Run the evidence-first troubleshooting pipeline."""

    events = load_events(events_path)
    observations = calculate_timing_observations(events)

    baseline = load_baseline(baseline_path)
    drift_findings = calculate_drift(observations.metrics, baseline)

    rules = load_rules(rules_path)
    candidate_causes = match_rules(drift_findings, rules)

    topology = load_topology(topology_path)
    topology_findings = identify_first_drift_location(topology, drift_findings)

    report_text = build_report(
        observations=observations,
        drift_findings=drift_findings,
        topology_findings=topology_findings,
        candidate_causes=candidate_causes,
    )
    write_report(report_text=report_text, output_path=output_path)
    return report_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run LineAlert deterministic troubleshooting analysis."
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
    run_pipeline(
        events_path=args.events,
        baseline_path=args.baseline,
        rules_path=args.rules,
        topology_path=args.topology,
        output_path=args.output,
    )
    print(f"Report written to {args.output}")


if __name__ == "__main__":
    main()
