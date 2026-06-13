"""Generate text reports from observations, drift, and rule results."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from drift_engine import DriftFinding
from expert_system import CandidateCause
from timing_engine import TimingObservations


def build_report(
    observations: TimingObservations,
    drift_findings: list[DriftFinding],
    candidate_causes: list[CandidateCause],
) -> str:
    """Create a deterministic, human-readable report."""

    lines: list[str] = [
        "LineAlert Troubleshooting Report",
        "=" * 33,
        f"Generated UTC: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "Architecture",
        "------------",
        "Evidence is measured first, drift is calculated second, and rules are",
        "applied last. Recommendations are deterministic checks, not predictions.",
        "",
    ]

    lines.extend(_observations_section(observations))
    lines.extend(_drift_section(drift_findings))
    lines.extend(_candidate_causes_section(candidate_causes))
    lines.extend(_recommended_checks_section(candidate_causes))

    return "\n".join(lines).rstrip() + "\n"


def write_report(report_text: str, output_path: str | Path) -> None:
    """Write the report to a plain text file."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_text, encoding="utf-8")


def _observations_section(observations: TimingObservations) -> list[str]:
    lines = [
        "Observations",
        "------------",
        f"Adjacent event lags measured: {len(observations.lags)}",
        f"Repeated-event cycles measured: {len(observations.cycles)}",
        "",
        "Aggregated timing metrics:",
    ]

    if not observations.metrics:
        lines.append("- No timing metrics available.")
    else:
        for metric in observations.metrics:
            lines.append(
                f"- {metric.observation_key}: {metric.value_seconds:.2f}s "
                f"average from {metric.sample_count} sample(s)"
            )

    lines.append("")
    return lines


def _drift_section(drift_findings: list[DriftFinding]) -> list[str]:
    lines = [
        "Drift Findings",
        "--------------",
    ]

    if not drift_findings:
        lines.append("- No baseline-matched drift findings.")
    else:
        for finding in drift_findings:
            status = "VIOLATION" if finding.threshold_violation else "within threshold"
            lines.append(
                f"- {finding.observation_key}: actual {finding.actual_seconds:.2f}s, "
                f"baseline {finding.expected_seconds:.2f}s, "
                f"drift {finding.drift_seconds:+.2f}s "
                f"({finding.drift_percent:+.1f}%), "
                f"threshold +/-{finding.threshold_seconds:.2f}s [{status}]"
            )

    lines.append("")
    return lines


def _candidate_causes_section(candidate_causes: list[CandidateCause]) -> list[str]:
    lines = [
        "Candidate Causes",
        "----------------",
    ]

    if not candidate_causes:
        lines.append("- No rules matched current drift evidence.")
    else:
        for cause in candidate_causes:
            lines.append(f"- {cause.issue}")
            for evidence in cause.matched_evidence:
                lines.append(f"  Evidence: {evidence}")

    lines.append("")
    return lines


def _recommended_checks_section(candidate_causes: list[CandidateCause]) -> list[str]:
    lines = [
        "Recommended Checks",
        "------------------",
    ]

    if not candidate_causes:
        lines.append("- Continue collecting evidence or review baseline coverage.")
    else:
        seen: set[str] = set()
        for cause in candidate_causes:
            for recommendation in cause.recommendations:
                if recommendation in seen:
                    continue
                seen.add(recommendation)
                lines.append(f"- {recommendation}")

    lines.append("")
    return lines
