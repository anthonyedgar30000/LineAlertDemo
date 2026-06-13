"""Generate ranked candidate explanations with deterministic scoring.

The hypothesis engine does not learn from data and does not call AI services.
It applies rule-defined weights to evidence already produced by earlier stages:
timing observations, drift findings, topology findings, and expert rules.
Every awarded point is captured as a score contribution so the final ranking is
traceable back to observed evidence.
"""

from __future__ import annotations

from dataclasses import dataclass

from drift_engine import DriftFinding
from expert_system import HypothesisTemplate, RuleCondition, TroubleshootingRule
from timing_engine import TimingMetric, TimingObservations
from topology_engine import TopologyFinding


DEFAULT_HYPOTHESIS_WEIGHTS = {
    "rule_match": 30.0,
    "threshold_violation": 20.0,
    "drift_severity": 20.0,
    "topology_region_match": 20.0,
    "timing_sample_support": 10.0,
}


@dataclass(frozen=True)
class ScoreContribution:
    """One evidence-backed contribution to a hypothesis score."""

    evidence_type: str
    points: float
    max_points: float
    explanation: str


@dataclass(frozen=True)
class RankedCandidateCause:
    """A ranked candidate explanation with traceable scoring evidence."""

    name: str
    confidence: str
    score: float
    max_score: float
    rank: int
    fault_region: str
    observation_key: str
    contributions: list[ScoreContribution]


def generate_ranked_hypotheses(
    observations: TimingObservations,
    drift_findings: list[DriftFinding],
    topology_findings: list[TopologyFinding],
    expert_rules: list[TroubleshootingRule],
) -> list[RankedCandidateCause]:
    """Generate ranked candidate causes using deterministic weighted scoring."""

    metrics_by_key = {
        metric.observation_key: metric for metric in observations.metrics
    }
    drift_by_key = {
        finding.observation_key: finding for finding in drift_findings
    }

    candidates: list[RankedCandidateCause] = []
    for rule in expert_rules:
        if not _rule_matches(rule, drift_by_key):
            continue

        for template in _hypothesis_templates_for_rule(rule):
            contributions = _score_hypothesis(
                template=template,
                rule=rule,
                metrics_by_key=metrics_by_key,
                drift_by_key=drift_by_key,
                topology_findings=topology_findings,
            )
            score = sum(contribution.points for contribution in contributions)
            max_score = sum(contribution.max_points for contribution in contributions)
            if max_score == 0:
                continue

            candidates.append(
                RankedCandidateCause(
                    name=template.name,
                    confidence=_confidence_from_score(score),
                    score=score,
                    max_score=max_score,
                    rank=0,
                    fault_region=template.fault_region,
                    observation_key=template.observation_key,
                    contributions=contributions,
                )
            )

    ranked = sorted(
        candidates,
        key=lambda candidate: (-candidate.score, candidate.name),
    )
    return [
        RankedCandidateCause(
            name=candidate.name,
            confidence=candidate.confidence,
            score=candidate.score,
            max_score=candidate.max_score,
            rank=index,
            fault_region=candidate.fault_region,
            observation_key=candidate.observation_key,
            contributions=candidate.contributions,
        )
        for index, candidate in enumerate(ranked, start=1)
    ]


def _hypothesis_templates_for_rule(
    rule: TroubleshootingRule,
) -> list[HypothesisTemplate]:
    if rule.hypotheses:
        return rule.hypotheses

    observation_key = _first_rule_observation_key(rule)
    if not observation_key:
        return []

    return [
        HypothesisTemplate(
            name=rule.issue,
            observation_key=observation_key,
            fault_region="",
            score_weights=DEFAULT_HYPOTHESIS_WEIGHTS,
        )
    ]


def _score_hypothesis(
    template: HypothesisTemplate,
    rule: TroubleshootingRule,
    metrics_by_key: dict[str, TimingMetric],
    drift_by_key: dict[str, DriftFinding],
    topology_findings: list[TopologyFinding],
) -> list[ScoreContribution]:
    weights = _normalized_weights(template.score_weights)
    contributions = [
        _rule_match_contribution(rule=rule, weight=weights["rule_match"]),
        _threshold_contribution(
            finding=drift_by_key.get(template.observation_key),
            weight=weights["threshold_violation"],
        ),
        _drift_severity_contribution(
            finding=drift_by_key.get(template.observation_key),
            weight=weights["drift_severity"],
        ),
        _topology_contribution(
            template=template,
            topology_findings=topology_findings,
            weight=weights["topology_region_match"],
        ),
        _timing_sample_contribution(
            metric=metrics_by_key.get(template.observation_key),
            weight=weights["timing_sample_support"],
        ),
    ]
    return [
        contribution for contribution in contributions if contribution.max_points > 0
    ]


def _normalized_weights(raw_weights: dict[str, float]) -> dict[str, float]:
    weights = DEFAULT_HYPOTHESIS_WEIGHTS.copy()
    weights.update({key: float(value) for key, value in raw_weights.items()})
    return weights


def _rule_match_contribution(
    rule: TroubleshootingRule,
    weight: float,
) -> ScoreContribution:
    return ScoreContribution(
        evidence_type="rule_match",
        points=weight,
        max_points=weight,
        explanation=f"Expert rule matched: {rule.issue}.",
    )


def _threshold_contribution(
    finding: DriftFinding | None,
    weight: float,
) -> ScoreContribution:
    if finding is None:
        return ScoreContribution(
            evidence_type="threshold_violation",
            points=0.0,
            max_points=weight,
            explanation="No matching drift finding was available.",
        )

    points = weight if finding.threshold_violation else 0.0
    status = "violated" if finding.threshold_violation else "did not violate"
    return ScoreContribution(
        evidence_type="threshold_violation",
        points=points,
        max_points=weight,
        explanation=(
            f"{finding.observation_key} {status} threshold: "
            f"drift {finding.drift_seconds:+.2f}s, "
            f"threshold +/-{finding.threshold_seconds:.2f}s."
        ),
    )


def _drift_severity_contribution(
    finding: DriftFinding | None,
    weight: float,
) -> ScoreContribution:
    if finding is None:
        return ScoreContribution(
            evidence_type="drift_severity",
            points=0.0,
            max_points=weight,
            explanation="No matching drift finding was available.",
        )

    ratio = _drift_severity_ratio(finding)
    points = weight * ratio
    return ScoreContribution(
        evidence_type="drift_severity",
        points=points,
        max_points=weight,
        explanation=(
            f"Drift severity ratio is {ratio:.2f} based on "
            f"{abs(finding.drift_seconds):.2f}s drift over "
            f"{finding.threshold_seconds:.2f}s threshold."
        ),
    )


def _topology_contribution(
    template: HypothesisTemplate,
    topology_findings: list[TopologyFinding],
    weight: float,
) -> ScoreContribution:
    matched_region = any(
        finding.likely_fault_region == template.fault_region
        for finding in topology_findings
    )
    points = weight if matched_region else 0.0
    if matched_region:
        explanation = (
            f"Topology first-drift region matches {template.fault_region}."
        )
    else:
        explanation = (
            f"Topology first-drift region does not match {template.fault_region}."
        )

    return ScoreContribution(
        evidence_type="topology_region_match",
        points=points,
        max_points=weight,
        explanation=explanation,
    )


def _timing_sample_contribution(
    metric: TimingMetric | None,
    weight: float,
) -> ScoreContribution:
    if metric is None:
        return ScoreContribution(
            evidence_type="timing_sample_support",
            points=0.0,
            max_points=weight,
            explanation="No matching timing metric was available.",
        )

    ratio = min(metric.sample_count / 3, 1.0)
    points = weight * ratio
    return ScoreContribution(
        evidence_type="timing_sample_support",
        points=points,
        max_points=weight,
        explanation=(
            f"Timing metric has {metric.sample_count} sample(s); "
            f"sample support ratio is {ratio:.2f}."
        ),
    )


def _drift_severity_ratio(finding: DriftFinding) -> float:
    if finding.threshold_seconds == 0:
        return 1.0 if finding.threshold_violation else 0.0
    return min(abs(finding.drift_seconds) / finding.threshold_seconds, 1.0)


def _confidence_from_score(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 45:
        return "Medium"
    if score > 0:
        return "Low"
    return "None"


def _rule_matches(
    rule: TroubleshootingRule,
    drift_by_key: dict[str, DriftFinding],
) -> bool:
    if not rule.all_conditions and not rule.any_conditions:
        return False

    all_satisfied = (
        all(_condition_matches(condition, drift_by_key) for condition in rule.all_conditions)
        if rule.all_conditions
        else True
    )
    any_satisfied = (
        any(_condition_matches(condition, drift_by_key) for condition in rule.any_conditions)
        if rule.any_conditions
        else True
    )
    return all_satisfied and any_satisfied


def _condition_matches(
    condition: RuleCondition,
    drift_by_key: dict[str, DriftFinding],
) -> bool:
    finding = drift_by_key.get(condition.observation_key)
    if finding is None:
        return False

    if condition.violation_required and not finding.threshold_violation:
        return False

    if condition.direction != "any" and finding.direction != condition.direction:
        return False

    return abs(finding.drift_seconds) >= condition.min_drift_seconds


def _first_rule_observation_key(rule: TroubleshootingRule) -> str:
    for condition in [*rule.all_conditions, *rule.any_conditions]:
        return condition.observation_key
    return ""
