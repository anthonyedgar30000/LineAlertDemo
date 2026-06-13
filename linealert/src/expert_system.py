"""Apply deterministic troubleshooting rules to drift evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from drift_engine import DriftFinding


HYPOTHESIS_SCORE_KEYS = {
    "rule_match",
    "threshold_violation",
    "drift_severity",
    "topology_region_match",
    "timing_sample_support",
}


@dataclass(frozen=True)
class RuleCondition:
    """One deterministic condition in a troubleshooting rule."""

    observation_key: str
    direction: str = "any"
    min_drift_seconds: float = 0.0
    violation_required: bool = True


@dataclass(frozen=True)
class HypothesisTemplate:
    """A rule-defined candidate explanation and its deterministic weights."""

    name: str
    observation_key: str
    fault_region: str
    score_weights: dict[str, float]


@dataclass(frozen=True)
class TroubleshootingRule:
    """A deterministic rule that maps evidence patterns to checks."""

    issue: str
    all_conditions: list[RuleCondition]
    any_conditions: list[RuleCondition]
    recommendations: list[str]
    hypotheses: list[HypothesisTemplate]


@dataclass(frozen=True)
class CandidateCause:
    """A rule-derived interpretation and recommended checks."""

    issue: str
    matched_evidence: list[str]
    recommendations: list[str]


def load_rules(rules_path: str | Path) -> list[TroubleshootingRule]:
    """Load deterministic troubleshooting rules from YAML.

    Expected format:

        rules:
          - issue: "Human-readable issue"
            conditions:
              all:
                - observation_key: "lag:A->B"
                  direction: "high"
                  min_drift_seconds: 1.0
            recommendations:
              - "Recommended check"
            hypotheses:
              - name: "Candidate explanation"
                observation_key: "lag:A->B"
                fault_region: "A subsystem"
                score_weights:
                  rule_match: 30
                  threshold_violation: 20
                  drift_severity: 20
                  topology_region_match: 20
                  timing_sample_support: 10
    """

    path = Path(rules_path)
    if not path.exists():
        raise FileNotFoundError(f"Rules YAML not found: {path}")

    with path.open("r", encoding="utf-8") as rules_file:
        raw_rules = yaml.safe_load(rules_file) or {}

    rules = raw_rules.get("rules")
    if not isinstance(rules, list):
        raise ValueError("Rules YAML must contain a 'rules' list")

    return [_parse_rule(raw_rule, index) for index, raw_rule in enumerate(rules, start=1)]


def match_rules(
    drift_findings: list[DriftFinding], rules: list[TroubleshootingRule]
) -> list[CandidateCause]:
    """Match drift evidence to troubleshooting rules."""

    findings_by_key = {
        finding.observation_key: finding for finding in drift_findings
    }
    candidate_causes: list[CandidateCause] = []

    for rule in rules:
        all_matches = [
            _match_condition(condition, findings_by_key)
            for condition in rule.all_conditions
        ]
        any_matches = [
            _match_condition(condition, findings_by_key)
            for condition in rule.any_conditions
        ]

        all_satisfied = all(all_matches) if rule.all_conditions else True
        any_satisfied = any(any_matches) if rule.any_conditions else True

        if all_satisfied and any_satisfied:
            matched_evidence = _matched_evidence(rule, findings_by_key)
            candidate_causes.append(
                CandidateCause(
                    issue=rule.issue,
                    matched_evidence=matched_evidence,
                    recommendations=rule.recommendations,
                )
            )

    return candidate_causes


def _parse_rule(raw_rule: Any, index: int) -> TroubleshootingRule:
    if not isinstance(raw_rule, dict):
        raise ValueError(f"Rule {index} must be a mapping")

    issue = str(raw_rule.get("issue", "")).strip()
    if not issue:
        raise ValueError(f"Rule {index} requires an issue")

    raw_conditions = raw_rule.get("conditions") or {}
    if not isinstance(raw_conditions, dict):
        raise ValueError(f"Rule {index} conditions must be a mapping")

    recommendations = raw_rule.get("recommendations") or []
    if not isinstance(recommendations, list) or not recommendations:
        raise ValueError(f"Rule {index} requires at least one recommendation")

    raw_hypotheses = raw_rule.get("hypotheses") or []
    if not isinstance(raw_hypotheses, list):
        raise ValueError(f"Rule {index} hypotheses must be a list")

    return TroubleshootingRule(
        issue=issue,
        all_conditions=[
            _parse_condition(condition, index)
            for condition in raw_conditions.get("all", [])
        ],
        any_conditions=[
            _parse_condition(condition, index)
            for condition in raw_conditions.get("any", [])
        ],
        recommendations=[str(recommendation) for recommendation in recommendations],
        hypotheses=[
            _parse_hypothesis(hypothesis, index, raw_conditions)
            for hypothesis in raw_hypotheses
        ],
    )


def _parse_hypothesis(
    raw_hypothesis: Any,
    rule_index: int,
    raw_conditions: dict[str, Any],
) -> HypothesisTemplate:
    if not isinstance(raw_hypothesis, dict):
        raise ValueError(f"Rule {rule_index} hypothesis must be a mapping")

    name = str(raw_hypothesis.get("name", "")).strip()
    if not name:
        raise ValueError(f"Rule {rule_index} hypothesis requires a name")

    observation_key = str(raw_hypothesis.get("observation_key", "")).strip()
    if not observation_key:
        observation_key = _first_condition_observation_key(raw_conditions)
    if not observation_key:
        raise ValueError(
            f"Rule {rule_index} hypothesis {name!r} requires observation_key"
        )

    fault_region = str(raw_hypothesis.get("fault_region", "")).strip()
    score_weights = raw_hypothesis.get("score_weights") or {}
    if not isinstance(score_weights, dict):
        raise ValueError(
            f"Rule {rule_index} hypothesis {name!r} score_weights must be a mapping"
        )

    parsed_weights: dict[str, float] = {}
    for key, value in score_weights.items():
        weight_name = str(key)
        if weight_name not in HYPOTHESIS_SCORE_KEYS:
            valid_keys = ", ".join(sorted(HYPOTHESIS_SCORE_KEYS))
            raise ValueError(
                f"Rule {rule_index} hypothesis {name!r} has unknown "
                f"score weight {weight_name!r}. Valid keys: {valid_keys}"
            )
        weight_value = float(value)
        if weight_value < 0:
            raise ValueError(
                f"Rule {rule_index} hypothesis {name!r} score weight "
                f"{weight_name!r} must be >= 0"
            )
        parsed_weights[weight_name] = weight_value

    return HypothesisTemplate(
        name=name,
        observation_key=observation_key,
        fault_region=fault_region,
        score_weights=parsed_weights,
    )


def _first_condition_observation_key(raw_conditions: dict[str, Any]) -> str:
    for group_name in ("all", "any"):
        conditions = raw_conditions.get(group_name, [])
        if not isinstance(conditions, list) or not conditions:
            continue
        first_condition = conditions[0]
        if isinstance(first_condition, dict):
            return str(first_condition.get("observation_key", "")).strip()
    return ""


def _parse_condition(raw_condition: Any, rule_index: int) -> RuleCondition:
    if not isinstance(raw_condition, dict):
        raise ValueError(f"Rule {rule_index} condition must be a mapping")

    observation_key = str(raw_condition.get("observation_key", "")).strip()
    if not observation_key:
        raise ValueError(f"Rule {rule_index} condition requires observation_key")

    direction = str(raw_condition.get("direction", "any")).strip()
    if direction not in {"high", "low", "on_target", "any"}:
        raise ValueError(
            f"Rule {rule_index} condition direction must be high, low, "
            "on_target, or any"
        )

    return RuleCondition(
        observation_key=observation_key,
        direction=direction,
        min_drift_seconds=float(raw_condition.get("min_drift_seconds", 0.0)),
        violation_required=bool(raw_condition.get("violation_required", True)),
    )


def _match_condition(
    condition: RuleCondition, findings_by_key: dict[str, DriftFinding]
) -> bool:
    finding = findings_by_key.get(condition.observation_key)
    if finding is None:
        return False

    if condition.violation_required and not finding.threshold_violation:
        return False

    if condition.direction != "any" and finding.direction != condition.direction:
        return False

    return abs(finding.drift_seconds) >= condition.min_drift_seconds


def _matched_evidence(
    rule: TroubleshootingRule, findings_by_key: dict[str, DriftFinding]
) -> list[str]:
    matched: list[str] = []
    for condition in [*rule.all_conditions, *rule.any_conditions]:
        finding = findings_by_key.get(condition.observation_key)
        if finding is None:
            continue
        matched.append(
            f"{finding.observation_key}: actual {finding.actual_seconds:.2f}s, "
            f"baseline {finding.expected_seconds:.2f}s, "
            f"drift {finding.drift_seconds:+.2f}s"
        )
    return matched
