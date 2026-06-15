"""Observation confidence reports."""

from __future__ import annotations

from linealert.confidence.confidence_model import ObservationConfidence


def generate_confidence_report(confidence: ObservationConfidence) -> dict[str, object]:
    return confidence.as_dict()


def format_confidence_report(confidence: ObservationConfidence) -> str:
    lines = [
        "OBSERVATION CONFIDENCE",
        "",
        "Observation:",
        confidence.observation,
        "",
        "Confidence:",
        f"{confidence.confidence:.3f}",
        "",
        "Classification:",
        confidence.classification,
        "",
        "Supporting Factors:",
    ]
    lines.extend(f"- {factor.description}" for factor in confidence.factors)
    lines.extend(
        [
            "",
            "No diagnosis or root-cause determination performed.",
            "No maintenance recommendations generated.",
            "No predictions generated.",
        ]
    )
    return "\n".join(lines)
