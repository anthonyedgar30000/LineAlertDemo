"""Generate observation-only anomaly and evidence reports."""

from __future__ import annotations

from statistics import mean

from validation.anomaly_detector import Anomaly, EvidenceRecord


def generate_anomaly_report(anomalies: list[Anomaly]) -> list[dict[str, object]]:
    """Summarize detected anomalies as measurement records."""

    return [_report_for_anomaly(anomaly) for anomaly in anomalies]


def generate_evidence_report(anomalies: list[Anomaly]) -> dict[str, object]:
    """Return a serializable evidence report without conclusions."""

    return {
        "anomaly_count": len(anomalies),
        "evidence_count": sum(len(anomaly.evidence) for anomaly in anomalies),
        "anomalies": generate_anomaly_report(anomalies),
        "evidence": [
            evidence.as_dict()
            for anomaly in anomalies
            for evidence in anomaly.evidence
        ],
    }


def _report_for_anomaly(anomaly: Anomaly) -> dict[str, object]:
    expected_values = _present_values(
        evidence.expected_ms for evidence in anomaly.evidence
    )
    observed_values = _present_values(
        evidence.observed_ms for evidence in anomaly.evidence
    )
    deviation_values = _present_values(
        evidence.deviation_percent for evidence in anomaly.evidence
    )
    relationship = _first_present(
        evidence.relationship for evidence in anomaly.evidence
    )

    return {
        "issue_type": anomaly.issue_type,
        "relationship": relationship,
        "baseline_lag_ms": _rounded_mean(expected_values),
        "observed_lag_ms": _rounded_mean(observed_values),
        "deviation_percent": _rounded_mean(deviation_values),
        "severity": _severity(deviation_values, len(anomaly.evidence)),
        "confidence": round(anomaly.confidence, 3),
        "evidence_count": len(anomaly.evidence),
    }


def _present_values(values: object) -> list[float]:
    return [value for value in values if value is not None]


def _first_present(values: object) -> str | None:
    for value in values:
        if value is not None:
            return value
    return None


def _rounded_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(mean(values), 3)


def _severity(deviation_values: list[float], evidence_count: int) -> str:
    if not deviation_values:
        return "Observed"
    largest_deviation = max(abs(value) for value in deviation_values)
    if largest_deviation >= 75 or evidence_count >= 10:
        return "High"
    if largest_deviation >= 25 or evidence_count >= 3:
        return "Medium"
    return "Low"
