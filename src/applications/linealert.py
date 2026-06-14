"""LineAlertDemo application adapter for ContextOS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from contextos import ApplicationRegistry, ContextRequest
from troubleshooting import TroubleshootingEngine


DEFAULT_ISSUE = "Label Alignment Off"
MACHINE_NAME = "Bottle Labeling Machine"
BASE_TIMESTAMP = "2026-06-14T05:16:00"
EXPECTED_TAMP_TO_APPLIED_MS = 100
CANDIDATE_HYPOTHESES = (
    (
        "Label guide loosened",
        "highest ranked possibility; could shift label path before tamp contact.",
    ),
    (
        "Tamp pad wear",
        "could reduce consistent label transfer and add application delay.",
    ),
    (
        "Product positioning variance",
        "could change bottle presentation during tamp extension.",
    ),
    (
        "Sensor contamination",
        "could delay readiness or applied-state confirmation.",
    ),
)
EXPECTED_EVENT_ORDER = (
    "Bottle Detect",
    "Print Complete",
    "Label Ready",
    "Tamp Extend",
    "Label Applied",
    "Tamp Home",
)
TRANSITIVE_REASONING_CHAIN = (
    "Bottle Detect",
    "Label Ready",
    "Tamp Extend",
    "Label Applied",
)


@dataclass(frozen=True)
class MachineEvent:
    """One deterministic event in the bottle labeling cycle."""

    name: str
    offset_ms: int


@dataclass(frozen=True)
class TimingAnalysis:
    """Expected vs observed relationship timing for the simulated cycle."""

    expected_lag_ms: int
    observed_lag_ms: int

    @property
    def delta_ms(self) -> int:
        return self.observed_lag_ms - self.expected_lag_ms


@dataclass(frozen=True)
class HypothesisAssessment:
    """Evidence-based abductive assessment for one candidate explanation."""

    hypothesis: str
    confidence_score: str
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]
    reasoning_rationale: str
    missing_context: tuple[str, ...]
    recommended_validation_step: str


def build_demo_cycle() -> list[MachineEvent]:
    """Return deterministic bottle labeling cycle data with timing drift."""

    return [
        MachineEvent("Bottle Detect", 0),
        MachineEvent("Print Complete", 72),
        MachineEvent("Label Ready", 118),
        MachineEvent("Tamp Extend", 240),
        MachineEvent("Label Applied", 393),
        MachineEvent("Tamp Home", 520),
    ]


def format_event_timestamp(offset_ms: int) -> str:
    return f"{BASE_TIMESTAMP}.{offset_ms:03d}Z"


def calculate_timing_analysis(events: Sequence[MachineEvent]) -> TimingAnalysis:
    event_offsets = {event.name: event.offset_ms for event in events}
    observed_lag = event_offsets["Label Applied"] - event_offsets["Tamp Extend"]
    return TimingAnalysis(
        expected_lag_ms=EXPECTED_TAMP_TO_APPLIED_MS,
        observed_lag_ms=observed_lag,
    )


def classify_drift(delta_ms: int) -> str:
    if delta_ms <= 10:
        return "No Drift"
    if delta_ms <= 30:
        return "Minor Drift"
    if delta_ms <= 75:
        return "Moderate Drift"
    return "Severe Drift"


def build_hypothesis_assessments(
    timing: TimingAnalysis,
    drift_classification: str,
) -> tuple[HypothesisAssessment, ...]:
    """Return deterministic evidence assessments for LineAlert hypotheses."""

    drift_summary = f"+{timing.delta_ms} ms {drift_classification.lower()}"
    return (
        HypothesisAssessment(
            hypothesis="Label guide loosened",
            confidence_score="0.78",
            supporting_evidence=(
                f"Observed {drift_summary} at the transfer-stage relationship.",
                "Event order remains valid, which points away from a sequence-control fault.",
                "Peter guide ranks label guide inspection as the first workflow step.",
            ),
            contradicting_evidence=(
                "No direct physical inspection result confirms guide looseness.",
                "No before/after guide adjustment sample is available.",
            ),
            reasoning_rationale=(
                "A loose guide can shift the label path before tamp contact while preserving "
                "the controller event sequence."
            ),
            missing_context=(
                "Guide clamp condition",
                "Label path alignment measurement",
                "Post-adjustment bottle sample",
            ),
            recommended_validation_step=(
                "Inspect and secure the label guide, then run 10 bottles and confirm "
                "alignment within tolerance."
            ),
        ),
        HypothesisAssessment(
            hypothesis="Tamp pad wear",
            confidence_score="0.64",
            supporting_evidence=(
                f"Observed {drift_summary} between tamp extension and label application.",
                "The affected relationship includes the tamp transfer stage.",
            ),
            contradicting_evidence=(
                "No tamp pad wear measurement or residue observation is available.",
                "The first-ranked guide evidence aligns more directly with label path guidance.",
            ),
            reasoning_rationale=(
                "A worn tamp pad could slow or destabilize label transfer after extension, "
                "but the demo evidence does not directly inspect pad condition."
            ),
            missing_context=(
                "Tamp pad face condition",
                "Transfer pressure consistency",
                "Residue or wear inspection result",
            ),
            recommended_validation_step=(
                "Inspect the tamp pad surface and verify consistent label transfer."
            ),
        ),
        HypothesisAssessment(
            hypothesis="Product positioning variance",
            confidence_score="0.56",
            supporting_evidence=(
                "Bottle presentation occurs upstream of the delayed label application event.",
                "Position variance could make tamp contact less repeatable.",
            ),
            contradicting_evidence=(
                "The observed event sequence is valid through Tamp Extend.",
                "No bottle stop repeatability data is available.",
            ),
            reasoning_rationale=(
                "An upstream positioning issue can plausibly surface downstream as label "
                "application delay, but the current evidence does not isolate bottle position."
            ),
            missing_context=(
                "Bottle stop repeatability measurement",
                "Conveyor spacing observations",
                "Product presentation photos or sensor traces",
            ),
            recommended_validation_step=(
                "Measure bottle stop repeatability at the applicator station."
            ),
        ),
        HypothesisAssessment(
            hypothesis="Sensor contamination",
            confidence_score="0.49",
            supporting_evidence=(
                "The delayed observed state depends on Label Applied sensor confirmation.",
                "Sensor contamination could delay readiness or applied-state detection.",
            ),
            contradicting_evidence=(
                "The sequence remains valid with no missing or reordered sensor events.",
                "No sensor signal quality or contamination inspection evidence is available.",
            ),
            reasoning_rationale=(
                "A contaminated sensor could report application late, but the deterministic "
                "cycle does not show sensor dropout or sequence instability."
            ),
            missing_context=(
                "Sensor lens inspection",
                "Signal transition trace",
                "Sensor cleaning validation result",
            ),
            recommended_validation_step=(
                "Clean and validate label-ready and applied-state sensor transitions."
            ),
        ),
    )


def render_machine_context() -> str:
    """Render physical machine context for the LineAlert application."""

    rendered_rows = [
        "Machine Context",
        "===============",
        "",
        "Machine:",
        MACHINE_NAME,
        "",
        "Purpose:",
        "Apply printed labels to bottles moving on a conveyor.",
        "",
        "Physical Components",
        "",
        "Conveyor",
        "- Moves bottles through the labeling station.",
        "",
        "Product Detect Sensor",
        "- Detects bottle arrival.",
        "- Starts the labeling sequence.",
        "",
        "Print Engine",
        "- Generates or confirms label print completion.",
        "",
        "Label Feed Assembly",
        "- Advances label stock into position.",
        "",
        "Label Ready Sensor",
        "- Confirms the label is available for application.",
        "",
        "Tamp Cylinder",
        "- Extends the tamp mechanism toward the bottle.",
        "",
        "Tamp Pad",
        "- Contacts or transfers the label onto the bottle surface.",
        "",
        "Label Applied Sensor",
        "- Confirms the label application event.",
        "",
        "Tamp Home Sensor",
        "- Confirms the tamp mechanism returned to home position.",
        "",
        "Controller",
        "- Coordinates machine sequence and timing.",
        "",
        "Expected Interaction Model",
        "",
        "Bottle Detect",
        "->",
        "Print Complete",
        "->",
        "Label Ready",
        "->",
        "Tamp Extend",
        "->",
        "Label Applied",
        "->",
        "Tamp Home",
        "",
        "Interaction Explanation",
        (
            "During a normal cycle, the conveyor presents a bottle to the product "
            "detect sensor. The controller coordinates print completion, label "
            "feed readiness, tamp extension, label application confirmation, and "
            "tamp return before the next bottle is processed."
        ),
        "",
        "Monitored Relationships",
        "- Bottle Detect -> Print Complete",
        "- Print Complete -> Label Ready",
        "- Label Ready -> Tamp Extend",
        "- Tamp Extend -> Label Applied",
        "- Label Applied -> Tamp Home",
    ]
    return "\n".join(rendered_rows)


def render_reasoning_engine_sections(
    events: Sequence[MachineEvent],
    timing: TimingAnalysis,
    drift_classification: str,
    hypothesis_assessments: Sequence[HypothesisAssessment],
) -> str:
    observed_event_order = tuple(event.name for event in events)
    sequence_validity = (
        "Valid" if observed_event_order == EXPECTED_EVENT_ORDER else "Invalid"
    )
    expected_order = " -> ".join(EXPECTED_EVENT_ORDER)
    observed_order = " -> ".join(observed_event_order)
    transitive_chain = " -> ".join(TRANSITIVE_REASONING_CHAIN)

    rendered_rows = [
        "Temporal Reasoning",
        "==================",
        f"Sequence validity: {sequence_validity}",
        f"Expected event order: {expected_order}",
        f"Observed event order: {observed_order}",
        f"Timing deviation: +{timing.delta_ms} ms on Tamp Extend -> Label Applied",
        "Confidence score: 0.86",
        "Evidence used:",
        f"- Expected lag {timing.expected_lag_ms} ms",
        f"- Observed lag {timing.observed_lag_ms} ms",
        "- Deterministic cycle timestamps preserve event order",
        "",
        "Topological Reasoning",
        "=====================",
        (
            "Machine components involved: Product Detect Sensor, Label Feed Assembly, "
            "Tamp Cylinder, Tamp Pad, Label Applied Sensor, Controller"
        ),
        "Component relationship affected: Tamp Extend -> Label Applied",
        (
            "Upstream/downstream dependency interpretation: upstream detection and "
            "label-ready events completed in order; the deviation appears downstream "
            "at the tamp-to-application relationship."
        ),
        "Confidence score: 0.74",
        "Evidence used:",
        "- Bottle Detect, Print Complete, and Label Ready occurred before Tamp Extend",
        "- Label Applied followed Tamp Extend but exceeded the expected lag",
        "- Monitored relationship identifies the affected transfer-stage edge",
        "",
        "Constraint Reasoning",
        "====================",
        "Expected timing tolerance: Tamp Extend -> Label Applied within 100 ms",
        f"Observed violation: observed lag {timing.observed_lag_ms} ms",
        f"Drift threshold crossed: {drift_classification} (+{timing.delta_ms} ms)",
        "Confidence score: 0.82",
        "Evidence used:",
        f"- Expected lag {timing.expected_lag_ms} ms",
        f"- Observed lag {timing.observed_lag_ms} ms",
        f"- Delta +{timing.delta_ms} ms falls in the {drift_classification} band",
        "",
        "Transitive Reasoning",
        "====================",
        f"Derived relationship chain: {transitive_chain}",
        (
            "Downstream symptom can plausibly originate upstream: yes; bottle "
            "presentation or label readiness issues can propagate to tamp transfer, "
            "but current evidence localizes the measured deviation at Tamp Extend -> "
            "Label Applied."
        ),
        "Confidence score: 0.68",
        "Evidence used:",
        "- Bottle Detect precedes Label Ready",
        "- Label Ready precedes Tamp Extend",
        "- Tamp Extend precedes delayed Label Applied",
        "",
        "Abductive Hypothesis Ranking",
        "============================",
    ]
    for index, assessment in enumerate(hypothesis_assessments, start=1):
        rendered_rows.extend(
            [
                f"{index}. Hypothesis: {assessment.hypothesis}",
                f"   Confidence score: {assessment.confidence_score}",
                "   Supporting evidence:",
            ]
        )
        rendered_rows.extend(
            f"   - {evidence}" for evidence in assessment.supporting_evidence
        )
        rendered_rows.append("   Contradicting evidence:")
        rendered_rows.extend(
            f"   - {evidence}" for evidence in assessment.contradicting_evidence
        )
        rendered_rows.extend(
            [
                f"   Reasoning rationale: {assessment.reasoning_rationale}",
                "   Missing context:",
            ]
        )
        rendered_rows.extend(f"   - {context}" for context in assessment.missing_context)
        rendered_rows.extend(
            [
                (
                    "   Recommended validation step: "
                    f"{assessment.recommended_validation_step}"
                ),
                "",
            ]
        )

    rendered_rows.extend(
        [
            "Root Cause Status:",
            "Not conclusively proven",
            "",
            "Most Likely Explanation:",
            "Label guide loosened",
            "",
            "Why:",
            (
                "Highest evidence alignment based on timing drift, preserved event "
                "sequence, and mechanical transfer-stage deviation."
            ),
            "",
            "Reasoning Summary",
            "=================",
            "- Most likely explanation: Label guide loosened",
            "- Confidence score: 0.78",
            (
                "- Why this is not certain: no direct inspection, adjustment result, "
                "or repeated physical measurement confirms the guide condition."
            ),
            (
                "- What evidence would confirm it: loose guide found during inspection "
                "and alignment restored after securing the guide."
            ),
            (
                "- What evidence would falsify it: guide inspection passes while drift "
                "persists after controlled bottle and tamp-pad checks."
            ),
            "- Next best troubleshooting step: Inspect Label Guide",
        ]
    )
    return "\n".join(rendered_rows).rstrip()


def render_linealert_report(issue: str) -> str:
    """Render a deterministic industrial investigation package."""

    events = build_demo_cycle()
    timing = calculate_timing_analysis(events)
    drift_classification = classify_drift(timing.delta_ms)
    hypothesis_titles = tuple(hypothesis for hypothesis, _ in CANDIDATE_HYPOTHESES)
    hypothesis_assessments = build_hypothesis_assessments(
        timing,
        drift_classification,
    )
    troubleshooting_workflow = TroubleshootingEngine().generate_workflow(
        issue_name=issue,
        candidate_hypotheses=hypothesis_titles,
        supporting_evidence=(
            f"Expected lag {timing.expected_lag_ms} ms",
            f"Observed lag {timing.observed_lag_ms} ms",
            f"Drift +{timing.delta_ms} ms",
        ),
    )

    rendered_rows = [
        render_machine_context(),
        "",
        "LineAlert Investigation Package",
        "===============================",
        "",
        "Machine",
        MACHINE_NAME,
        "",
        "Issue",
        issue,
        "",
        "Observed Evidence",
    ]
    rendered_rows.extend(
        f"- {format_event_timestamp(event.offset_ms)} {event.name}" for event in events
    )
    rendered_rows.extend(
        [
            "- Tamp Extend observed at 240 ms",
            "- Label Applied observed at 393 ms",
            "- Observed lag calculated from deterministic cycle data",
            "",
            "Expected State",
            "Tamp Extend -> Label Applied within 100 ms",
            "",
            "Observed State",
            "Tamp Extend -> Label Applied in 153 ms",
            "",
            "Relationship Analysis",
            "- Expected relationship: Tamp Extend precedes Label Applied by 100 ms",
            "- Observed relationship: Tamp Extend precedes Label Applied by 153 ms",
            (
                "- Relationship integrity: Sequence valid; timing relationship shows "
                f"{drift_classification.lower()}"
            ),
            "",
            "Timing Analysis",
            f"- Expected lag: {timing.expected_lag_ms} ms",
            f"- Observed lag: {timing.observed_lag_ms} ms",
            f"- Delta: +{timing.delta_ms} ms",
            "",
            "Drift Analysis",
            "- No Drift: 0-10 ms delta",
            "- Minor Drift: 11-30 ms delta",
            f"- Moderate Drift: 31-75 ms delta ({'observed' if drift_classification == 'Moderate Drift' else 'not observed'})",
            "- Severe Drift: >75 ms delta",
            "",
            render_reasoning_engine_sections(
                events,
                timing,
                drift_classification,
                hypothesis_assessments,
            ),
            "",
            "Candidate Hypotheses",
        ]
    )
    rendered_rows.extend(
        f"{index}. {hypothesis} - {detail}"
        for index, (hypothesis, detail) in enumerate(CANDIDATE_HYPOTHESES, start=1)
    )
    rendered_rows.extend(
        [
            "",
            troubleshooting_workflow,
            "",
            "Recommended Actions",
            "1. Inspect and secure the label guide before changing timing parameters.",
            "2. Check tamp pad face condition and replace if wear or residue is observed.",
            "3. Verify bottle stop, spacing, and conveyor presentation at the applicator station.",
            "4. Clean and validate label-ready and applied-state sensors before rebaseline.",
            "",
            "Escalation Guidance",
            "Escalate to Operator Lead if moderate drift repeats after guide, tamp, and sensor checks.",
            "",
            "Confidence Assessment",
            "Medium-high: deterministic timing data shows a valid sequence with +53 ms drift; root cause is not confirmed.",
            "",
            "Tradeoff Summary",
            "Mechanical and sensor checks are low-risk first steps; changing timing baselines before inspection could mask the underlying cause.",
        ]
    )
    return "\n".join(rendered_rows)


class LineAlertApplication:
    """ContextOS adapter for the LineAlertDemo workload."""

    def name(self) -> str:
        return "LineAlertDemo"

    def capabilities(self) -> Sequence[str]:
        return (DEFAULT_ISSUE,)

    def execute(self, context_request: ContextRequest) -> str:
        return render_linealert_report(context_request.user_intent)


def register(registry: ApplicationRegistry) -> None:
    """Register LineAlertDemo with a ContextOS application registry."""

    registry.register(LineAlertApplication())
