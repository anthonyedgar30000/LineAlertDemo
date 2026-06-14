"""Evidence-only aggregate scoring helpers."""

from __future__ import annotations

from statistics import mean

from linealert.evidence.evidence_item import EvidenceItem


SEVERITY_WEIGHTS = {
    "Normal": 0.0,
    "Monitor": 1.0,
    "Degraded": 2.0,
    "Significant Deviation": 3.0,
}


def average_confidence(items: list[EvidenceItem]) -> float:
    if not items:
        return 0.0
    return round(mean(item.confidence for item in items), 3)


def aggregate_severity(items: list[EvidenceItem]) -> str:
    """Return the highest observed severity label."""

    if not items:
        return "Normal"
    return max(
        (item.severity for item in items),
        key=lambda severity: SEVERITY_WEIGHTS.get(severity, 1.0),
    )
