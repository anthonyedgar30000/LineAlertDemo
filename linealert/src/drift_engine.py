"""Compare timing observations against deterministic baselines."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from timing_engine import TimingMetric


@dataclass(frozen=True)
class BaselineEntry:
    """Known-good expected timing and tolerated drift for one observation."""

    observation_key: str
    expected_seconds: float
    threshold_seconds: float


@dataclass(frozen=True)
class DriftFinding:
    """Evidence describing drift from baseline.

    This object is still evidence, not a diagnosis. The expert system interprets
    these findings against deterministic rules.
    """

    observation_key: str
    metric_type: str
    event_path: str
    actual_seconds: float
    expected_seconds: float
    drift_seconds: float
    drift_percent: float
    threshold_seconds: float
    threshold_violation: bool
    direction: str
    sample_count: int


def load_baseline(baseline_path: str | Path) -> dict[str, BaselineEntry]:
    """Load baseline timing expectations from JSON."""

    path = Path(baseline_path)
    if not path.exists():
        raise FileNotFoundError(f"Baseline JSON not found: {path}")

    with path.open("r", encoding="utf-8") as baseline_file:
        raw_baseline = json.load(baseline_file)

    observations = raw_baseline.get("observations")
    if not isinstance(observations, dict):
        raise ValueError("Baseline JSON must contain an 'observations' object")

    baseline: dict[str, BaselineEntry] = {}
    for key, raw_entry in observations.items():
        try:
            expected_seconds = float(raw_entry["expected_seconds"])
            threshold_seconds = float(raw_entry["threshold_seconds"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Baseline entry {key!r} requires numeric expected_seconds "
                "and threshold_seconds"
            ) from exc

        if threshold_seconds < 0:
            raise ValueError(f"Baseline entry {key!r} threshold_seconds must be >= 0")

        baseline[key] = BaselineEntry(
            observation_key=key,
            expected_seconds=expected_seconds,
            threshold_seconds=threshold_seconds,
        )

    return baseline


def calculate_drift(
    metrics: list[TimingMetric], baseline: dict[str, BaselineEntry]
) -> list[DriftFinding]:
    """Calculate drift values for metrics that have baseline entries."""

    findings: list[DriftFinding] = []
    for metric in metrics:
        entry = baseline.get(metric.observation_key)
        if entry is None:
            continue

        drift_seconds = metric.value_seconds - entry.expected_seconds
        threshold_violation = abs(drift_seconds) > entry.threshold_seconds
        findings.append(
            DriftFinding(
                observation_key=metric.observation_key,
                metric_type=metric.metric_type,
                event_path=metric.event_path,
                actual_seconds=metric.value_seconds,
                expected_seconds=entry.expected_seconds,
                drift_seconds=drift_seconds,
                drift_percent=_calculate_percent_drift(
                    drift_seconds=drift_seconds,
                    expected_seconds=entry.expected_seconds,
                ),
                threshold_seconds=entry.threshold_seconds,
                threshold_violation=threshold_violation,
                direction=_direction_from_drift(drift_seconds),
                sample_count=metric.sample_count,
            )
        )

    return sorted(findings, key=lambda finding: finding.observation_key)


def _calculate_percent_drift(drift_seconds: float, expected_seconds: float) -> float:
    if expected_seconds == 0:
        return 0.0
    return (drift_seconds / expected_seconds) * 100


def _direction_from_drift(drift_seconds: float) -> str:
    if drift_seconds > 0:
        return "high"
    if drift_seconds < 0:
        return "low"
    return "on_target"
