"""Confidence score and classification helpers."""

from __future__ import annotations

from linealert.confidence.confidence_model import ConfidenceFactor


BASE_CONFIDENCE = 0.20


def calculate_confidence_score(factors: list[ConfidenceFactor]) -> float:
    return round(min(1.0, BASE_CONFIDENCE + sum(factor.contribution for factor in factors)), 3)


def classify_confidence(score: float) -> str:
    if score < 0.20:
        return "Very Low"
    if score < 0.40:
        return "Low"
    if score < 0.60:
        return "Moderate"
    if score < 0.80:
        return "High"
    return "Very High"
