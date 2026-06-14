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
class RuleCrossLink:
    """A deterministic relationship from one symptom rule to another."""

    symptom_id: str
    symptom: str
    reason: str


@dataclass(frozen=True)
class KeyAdjustmentArea:
    """A guide-defined adjustment area and what it controls."""

    area: str
    purpose: str


@dataclass(frozen=True)
class TroubleshootingRule:
    """A deterministic rule that maps evidence patterns to checks."""

    rule_id: str
    issue: str
    symptom: str
    symptom_aliases: list[str]
    examples: list[str]
    checks: list[str]
    actions: list[str]
    related_issues: list[RuleCrossLink]
    escalation_conditions: list[str]
    key_adjustment_areas: list[KeyAdjustmentArea]
    key_point: str
    cross_links: list[RuleCrossLink]
    all_conditions: list[RuleCondition]
    any_conditions: list[RuleCondition]
    recommendations: list[str]
    hypotheses: list[HypothesisTemplate]


@dataclass(frozen=True)
class GuideResponse:
    """Deterministic response for a reported labeling symptom."""

    rule_id: str
    symptom: str
    examples: list[str]
    checks: list[str]
    actions: list[str]
    related_issues: list[RuleCrossLink]
    escalation_conditions: list[str]
    key_adjustment_areas: list[KeyAdjustmentArea]
    key_point: str


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
            checks:
              - "Deterministic check from a guide"
            actions:
              - "Deterministic action from a guide"
            related_issues:
              - symptom_id: "related_symptom"
                symptom: "Related Symptom"
                reason: "Why the symptoms are related"
            escalation_conditions:
              - "Escalate if deterministic condition remains true"
            key_adjustment_areas:
              - area: "Adjustment Area"
                purpose: "What this adjustment controls"
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
        if not rule.all_conditions and not rule.any_conditions:
            continue

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


def query_labeling_guide(
    rules: list[TroubleshootingRule],
    reported_symptom: str,
) -> GuideResponse | None:
    """Return guide checks/actions for a reported symptom.

    Matching is deterministic and string-based. The function first tries exact
    normalized matches against rule symptom names, issues, ids, and aliases. If
    none match, it tries a contained-alias match in rule order.
    """

    normalized_report = _normalize_lookup_text(reported_symptom)
    if not normalized_report:
        return None

    for rule in rules:
        if normalized_report in _guide_lookup_terms(rule):
            return _guide_response_from_rule(rule)

    for rule in rules:
        for term in _guide_lookup_terms(rule):
            if term and (term in normalized_report or normalized_report in term):
                return _guide_response_from_rule(rule)

    return None


def format_guide_response(
    reported_symptom: str,
    response: GuideResponse | None,
) -> str:
    """Format a deterministic text response for a guide query."""

    lines = [
        "LineAlert Labeling Guide Interaction",
        "====================================",
        f'User reports: "{reported_symptom}"',
        "",
    ]

    if response is None:
        lines.extend(
            [
                "Matched Symptom: none",
                "",
                "Escalation Guidance:",
                "- No deterministic guide rule matched this symptom.",
            ]
        )
        return "\n".join(lines).rstrip() + "\n"

    lines.extend(
        [
            f"Matched Symptom: {response.symptom}",
            "",
            "Relevant Checks:",
            *_format_bullets(response.checks),
            "",
            "Recommended Actions:",
            *_format_bullets(response.actions),
            "",
            "Related Symptoms if Problem Persists:",
            *_format_related_issues(response.related_issues),
            "",
            "Escalation Guidance:",
            *_format_bullets(response.escalation_conditions),
            "",
            "Key Adjustment Areas:",
            *_format_key_adjustment_areas(response.key_adjustment_areas),
        ]
    )

    if response.key_point:
        lines.extend(["", f"Key Point: {response.key_point}"])

    return "\n".join(lines).rstrip() + "\n"


def _parse_rule(raw_rule: Any, index: int) -> TroubleshootingRule:
    if not isinstance(raw_rule, dict):
        raise ValueError(f"Rule {index} must be a mapping")

    issue = str(raw_rule.get("issue", "")).strip()
    if not issue:
        raise ValueError(f"Rule {index} requires an issue")

    raw_conditions = raw_rule.get("conditions") or {}
    if not isinstance(raw_conditions, dict):
        raise ValueError(f"Rule {index} conditions must be a mapping")

    symptom_name, symptom_aliases, symptom_examples = _parse_symptom(
        raw_rule.get("symptom", issue),
        index,
    )
    examples = _parse_string_list(
        raw_rule.get("examples") or symptom_examples,
        f"Rule {index} examples",
    )
    actions = _parse_string_list(raw_rule.get("actions") or [], f"Rule {index} actions")
    recommendations = raw_rule.get("recommendations") or actions
    if not isinstance(recommendations, list) or not recommendations:
        raise ValueError(
            f"Rule {index} requires at least one recommendation or action"
        )

    raw_hypotheses = raw_rule.get("hypotheses") or []
    if not isinstance(raw_hypotheses, list):
        raise ValueError(f"Rule {index} hypotheses must be a list")

    related_issues = _parse_cross_links(
        raw_rule.get("related_issues") or raw_rule.get("cross_links") or [],
        index,
    )

    return TroubleshootingRule(
        rule_id=str(raw_rule.get("id", "")).strip(),
        issue=issue,
        symptom=symptom_name,
        symptom_aliases=symptom_aliases,
        examples=examples,
        checks=_parse_string_list(
            raw_rule.get("checks") or [],
            f"Rule {index} checks",
        ),
        actions=actions,
        related_issues=related_issues,
        escalation_conditions=_parse_string_list(
            raw_rule.get("escalation_conditions") or [],
            f"Rule {index} escalation_conditions",
        ),
        key_adjustment_areas=_parse_key_adjustment_areas(
            raw_rule.get("key_adjustment_areas") or [],
            index,
        ),
        key_point=str(raw_rule.get("key_point", "")).strip(),
        cross_links=related_issues,
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


def _parse_symptom(raw_symptom: Any, rule_index: int) -> tuple[str, list[str], list[str]]:
    if isinstance(raw_symptom, str):
        symptom = raw_symptom.strip()
        if not symptom:
            raise ValueError(f"Rule {rule_index} symptom must not be empty")
        return symptom, [], []

    if not isinstance(raw_symptom, dict):
        raise ValueError(f"Rule {rule_index} symptom must be a string or mapping")

    symptom = str(raw_symptom.get("name", "")).strip()
    if not symptom:
        raise ValueError(f"Rule {rule_index} symptom requires a name")

    aliases = _parse_string_list(
        raw_symptom.get("aliases") or [],
        f"Rule {rule_index} symptom aliases",
    )
    examples = _parse_string_list(
        raw_symptom.get("examples") or [],
        f"Rule {rule_index} symptom examples",
    )
    return symptom, aliases, examples


def _parse_string_list(raw_values: Any, field_name: str) -> list[str]:
    if not isinstance(raw_values, list):
        raise ValueError(f"{field_name} must be a list")
    return [str(value) for value in raw_values]


def _parse_cross_links(raw_cross_links: Any, rule_index: int) -> list[RuleCrossLink]:
    if not isinstance(raw_cross_links, list):
        raise ValueError(f"Rule {rule_index} cross_links must be a list")

    cross_links: list[RuleCrossLink] = []
    for link_index, raw_link in enumerate(raw_cross_links, start=1):
        if not isinstance(raw_link, dict):
            raise ValueError(
                f"Rule {rule_index} cross link {link_index} must be a mapping"
            )

        symptom_id = str(raw_link.get("symptom_id", "")).strip()
        symptom = str(raw_link.get("symptom", "")).strip()
        reason = str(raw_link.get("reason", "")).strip()
        if not symptom_id or not symptom or not reason:
            raise ValueError(
                f"Rule {rule_index} cross link {link_index} requires "
                "symptom_id, symptom, and reason"
            )

        cross_links.append(
            RuleCrossLink(
                symptom_id=symptom_id,
                symptom=symptom,
                reason=reason,
            )
        )

    return cross_links


def _parse_key_adjustment_areas(
    raw_areas: Any,
    rule_index: int,
) -> list[KeyAdjustmentArea]:
    if not isinstance(raw_areas, list):
        raise ValueError(f"Rule {rule_index} key_adjustment_areas must be a list")

    areas: list[KeyAdjustmentArea] = []
    for area_index, raw_area in enumerate(raw_areas, start=1):
        if not isinstance(raw_area, dict):
            raise ValueError(
                f"Rule {rule_index} key adjustment area {area_index} must be a mapping"
            )

        area = str(raw_area.get("area", "")).strip()
        purpose = str(raw_area.get("purpose", "")).strip()
        if not area or not purpose:
            raise ValueError(
                f"Rule {rule_index} key adjustment area {area_index} "
                "requires area and purpose"
            )

        areas.append(KeyAdjustmentArea(area=area, purpose=purpose))

    return areas


def _guide_lookup_terms(rule: TroubleshootingRule) -> set[str]:
    terms = {
        rule.rule_id,
        rule.issue,
        rule.symptom,
        *rule.symptom_aliases,
    }
    return {
        normalized
        for term in terms
        if (normalized := _normalize_lookup_text(term))
    }


def _guide_response_from_rule(rule: TroubleshootingRule) -> GuideResponse:
    return GuideResponse(
        rule_id=rule.rule_id,
        symptom=rule.symptom,
        examples=rule.examples,
        checks=rule.checks,
        actions=rule.actions,
        related_issues=rule.related_issues,
        escalation_conditions=rule.escalation_conditions,
        key_adjustment_areas=rule.key_adjustment_areas,
        key_point=rule.key_point,
    )


def _normalize_lookup_text(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def _format_bullets(values: list[str]) -> list[str]:
    if not values:
        return ["- none"]
    return [f"- {value}" for value in values]


def _format_related_issues(related_issues: list[RuleCrossLink]) -> list[str]:
    if not related_issues:
        return ["- none"]
    return [
        f"- {issue.symptom}: {issue.reason}"
        for issue in related_issues
    ]


def _format_key_adjustment_areas(
    key_adjustment_areas: list[KeyAdjustmentArea],
) -> list[str]:
    if not key_adjustment_areas:
        return ["- none"]
    return [
        f"- {area.area}: {area.purpose}"
        for area in key_adjustment_areas
    ]


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
