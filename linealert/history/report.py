"""Historical Context reports."""

from __future__ import annotations

from linealert.history.drift_tracker import HistoricalDriftIndicator
from linealert.history.observation_history import ObservationHistory
from linealert.history.trend_tracker import (
    ClusterHistory,
    EvidenceDensityTrend,
    track_cluster_history,
    track_evidence_density,
)


def generate_historical_context_report(
    history: ObservationHistory,
    drift_indicators: list[HistoricalDriftIndicator] | None = None,
) -> dict[str, object]:
    """Return a JSON-serializable historical context report."""

    density_trend = track_evidence_density(history)
    clusters = sorted(
        {observation.evidence_cluster for observation in history.observations}
    )
    cluster_history = [
        track_cluster_history(history, cluster).as_dict()
        for cluster in clusters
    ]
    observations = sorted(
        {observation.observation for observation in history.observations},
        key=lambda observation: (
            -history.observation_frequency(observation),
            observation,
        ),
    )

    return {
        "cycles_observed": history.cycles_observed,
        "observation_summaries": [
            _observation_summary(history, observation)
            for observation in observations
        ],
        "evidence_density_trend": density_trend.as_dict(),
        "cluster_history": cluster_history,
        "historical_drift_indicators": [
            indicator.as_dict() for indicator in (drift_indicators or [])
        ],
    }


def format_historical_context_report(
    history: ObservationHistory,
    drift_indicators: list[HistoricalDriftIndicator] | None = None,
) -> str:
    """Render a human-readable historical context report."""

    report = generate_historical_context_report(
        history=history,
        drift_indicators=drift_indicators,
    )
    lines = ["HISTORICAL CONTEXT", ""]

    for summary in report["observation_summaries"]:
        lines.extend(
            [
                "Observation:",
                str(summary["observation"]),
                "",
                "Occurrences:",
                str(summary["occurrences"]),
                "",
                "Persistence:",
                f"{summary['persistence_cycles']} consecutive cycles",
                "",
                "Recurrence:",
                f"{summary['recurrence_count']} observations in tracked cycles",
                "",
                "Severity History:",
                ", ".join(summary["severity_history"]),
                "",
            ]
        )

    density = report["evidence_density_trend"]
    lines.extend(
        [
            "Evidence Density Trend:",
            str(density["direction"]),
            "",
        ]
    )

    for drift in report["historical_drift_indicators"]:
        lines.extend(
            [
                "Historical Drift:",
                (
                    f"Observed {drift['direction'].lower()} from "
                    f"{drift['start_value']}{drift['unit']} to "
                    f"{drift['end_value']}{drift['unit']}"
                ),
                str(drift["status"]),
                "",
            ]
        )

    lines.extend(
        [
            "No diagnosis or root-cause determination performed.",
            "No maintenance recommendations generated.",
            "No predictions generated.",
        ]
    )
    return "\n".join(lines).rstrip()


def _observation_summary(
    history: ObservationHistory, observation: str
) -> dict[str, object]:
    return {
        "observation": observation,
        "cycles": history.observation_cycles(observation),
        "occurrences": history.observation_frequency(observation),
        "persistence_cycles": history.observation_persistence(observation),
        "recurrence_count": history.observation_recurrence(
            observation,
            max(1, len(history.cycles_observed)),
        ),
        "severity_history": history.severity_history(observation),
        "source_systems": history.source_systems_for_observation(observation),
    }
