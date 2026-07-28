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
SIMULATED_FULL_VISION_ENABLED = True


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
            confidence_score="0.94",
            supporting_evidence=(
                f"Observed {drift_summary} at the transfer-stage relationship.",
                "Event order remains valid, which points away from a sequence-control fault.",
                "Peter guide ranks label guide inspection as the first workflow step.",
                "Configuration audit shows no timing-setting change since last rehoming, reducing support for a settings bug.",
                "Simulated operator photo shows label skew matching guide-side drift.",
                "Simulated maintenance photo shows loose guide clamp and guide ring offset.",
                "Simulated post-adjustment vision sample shows 10/10 bottles within tolerance.",
            ),
            contradicting_evidence=(
                "Inline PSI, RPM, motor load, and sensor checks are within tolerance.",
                "Tamp pad inspection shows only minor wear and no residue buildup.",
            ),
            reasoning_rationale=(
                "The simulated visual, maintenance, and post-adjustment validation evidence "
                "directly aligns with a guide-position fault while other subsystem checks "
                "remain within tolerance."
            ),
            missing_context=(
                "Longer production-run validation after the 10-bottle sample",
                "Historical trend showing when guide position began drifting",
            ),
            recommended_validation_step=(
                "Keep the guide secured, run an extended sample, and monitor whether "
                "alignment and timing remain within tolerance."
            ),
        ),
        HypothesisAssessment(
            hypothesis="Tamp pad wear",
            confidence_score="0.36",
            supporting_evidence=(
                f"Observed {drift_summary} between tamp extension and label application.",
                "The affected relationship includes the tamp transfer stage.",
            ),
            contradicting_evidence=(
                "Simulated tamp pad photo shows only minor wear and no residue buildup.",
                "Inline PSI and clicker evidence indicate normal tamp actuation.",
                "Post-guide-adjustment validation restores alignment without pad replacement.",
            ),
            reasoning_rationale=(
                "Tamp pad wear remains mechanically possible, but simulated inspection and "
                "post-adjustment results make it less likely than guide looseness."
            ),
            missing_context=(
                "Long-term tamp pad wear trend",
                "Pad durometer measurement",
            ),
            recommended_validation_step=(
                "Recheck tamp pad condition if alignment drift returns after guide validation."
            ),
        ),
        HypothesisAssessment(
            hypothesis="Product positioning variance",
            confidence_score="0.31",
            supporting_evidence=(
                "Bottle presentation occurs upstream of the delayed label application event.",
                "Position variance could make tamp contact less repeatable.",
            ),
            contradicting_evidence=(
                "Simulated caliper sample shows bottle stop repeatability within tolerance.",
                "Simulated conveyor RPM remains stable during failed and corrected samples.",
                "Post-guide-adjustment validation restores alignment without product-stop changes.",
            ),
            reasoning_rationale=(
                "Upstream positioning can propagate downstream, but the simulated bottle "
                "position and conveyor evidence does not support it as the primary cause."
            ),
            missing_context=(
                "Larger bottle-position sample across multiple SKUs",
                "Changeover fixture inspection record",
            ),
            recommended_validation_step=(
                "Continue monitoring bottle stop repeatability during the extended validation run."
            ),
        ),
        HypothesisAssessment(
            hypothesis="Sensor contamination",
            confidence_score="0.24",
            supporting_evidence=(
                "The delayed observed state depends on Label Applied sensor confirmation.",
                "Sensor contamination could delay readiness or applied-state detection.",
            ),
            contradicting_evidence=(
                "Simulated sensor photo shows a clean label-applied sensor face.",
                "Simulated handheld signal tester shows clean sensor transitions.",
                "No missing, reordered, or bouncing sensor events appear in the cycle trace.",
            ),
            reasoning_rationale=(
                "Sensor contamination is weakly supported because simulated visual and "
                "electrical checks show normal sensor condition and transitions."
            ),
            missing_context=(
                "Longer sensor-transition trend under production vibration",
                "Electrical noise capture during peak line speed",
            ),
            recommended_validation_step=(
                "Retest sensor transitions only if drift returns without guide movement."
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


def render_simulated_full_vision_evidence() -> str:
    """Render deterministic simulated evidence that a real deployment would package."""

    rendered_rows = [
        "Simulated Full-Vision Evidence Package",
        "======================================",
        "Simulation Mode:",
        "Enabled for deterministic demo; evidence represents what a connected LineAlert deployment would package from operators, maintenance, cameras, handheld tools, and inline sensors.",
        "",
        "Vision Measurement Evidence",
        "---------------------------",
        "- Failed bottle sample: horizontal offset +3.2 mm, vertical offset +0.6 mm, skew angle 2.4 degrees.",
        "- Alignment tolerance: +/-1.5 mm horizontal, +/-1.0 degree skew.",
        "- Good comparison bottle after adjustment: horizontal offset +0.4 mm, skew angle 0.3 degrees.",
        "- 10-bottle validation sample after guide adjustment: 10/10 bottles within tolerance.",
        "",
        "Picture Evidence",
        "----------------",
        "- operator_failed_label_001.jpg: label visibly skewed right; linked hypothesis: Label guide loosened; evidence strength: High.",
        "- maintenance_guide_clamp_before.jpg: guide clamp visibly loose and guide ring offset; linked hypothesis: Label guide loosened; evidence strength: High.",
        "- maintenance_tamp_pad_before.jpg: minor tamp pad wear, no residue buildup; linked hypothesis: Tamp pad wear; evidence strength: Low.",
        "- sensor_face_before.jpg: label-applied sensor face clean; linked hypothesis: Sensor contamination; evidence strength: Low.",
        "- validation_10_bottle_after.jpg: post-adjustment bottles within alignment tolerance; linked hypothesis: Label guide loosened; evidence strength: High.",
        "",
        "Operator Feedback Evidence",
        "--------------------------",
        "- Operator observed label skew after changeover: yes.",
        "- Operator observed product wobble: no.",
        "- Operator heard abnormal tamp motion: no.",
        "- Operator confidence: medium-high because skew pattern repeated before guide adjustment.",
        "",
        "Maintenance Feedback Evidence",
        "-----------------------------",
        "- Label guide checked: yes.",
        "- Guide clamp condition: loose.",
        "- Guide ring position: offset toward outboard side.",
        "- Corrective action: guide secured and guide ring realigned.",
        "- Result after action: alignment restored during 10-bottle validation sample.",
        "",
        "Inline Sensor Evidence",
        "----------------------",
        "- Digital PSI gauge at tamp line: 71 psi steady; expected range 68-75 psi.",
        "- Mechanical clicker at Tamp Extend: triggered on all 10 validation cycles.",
        "- Mechanical clicker at Tamp Home: triggered on all 10 validation cycles.",
        "- Conveyor RPM sensor: 142 RPM, stable within +/-1.0%.",
        "- Label feed roller RPM sensor: 142 RPM, matched conveyor ratio within +/-1.0%.",
        "- Label feed motor load sensor: 1.1 A average, no binding spike.",
        "- Label feed motor heat sensor: 54 C, within normal range.",
        "",
        "Handheld Diagnostic Tool Evidence",
        "---------------------------------",
        "- Digital calipers: guide ring offset measured at +2.0 mm before correction and +0.2 mm after correction.",
        "- Handheld tachometer: conveyor and label feed rollers matched target speed.",
        "- Digital pressure gauge: tamp pressure remained within tolerance during actuation.",
        "- Clamp meter: label feed motor current stayed within baseline range.",
        "- IR thermometer: label feed motor temperature remained within normal range.",
        "- Handheld signal tester: label-applied sensor transition clean after guide adjustment.",
        "",
        "Configuration Change Evidence",
        "-----------------------------",
        "- Last machine rehoming event: 2026-06-14T05:10:00Z.",
        "- Timing recipe checksum after rehoming: unchanged.",
        "- Label delay setting since last rehoming: unchanged at 100 ms.",
        "- Tamp extend dwell setting since last rehoming: unchanged.",
        "- Label-applied confirmation timeout since last rehoming: unchanged.",
        "- Interpretation: no timing setting changed after rehoming, so a settings bug is unlikely for this event.",
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
        "- Simulated vision validation shows alignment restored after guide correction",
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
        "- Simulated inline PSI, RPM, motor load, and sensor checks reduce support for pneumatic, speed, load, and sensor faults",
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
        "- Simulated guide correction brings 10-bottle validation sample back within alignment tolerance",
        "- Configuration audit shows no timing setting changed since last rehoming",
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
        "Confidence score: 0.76",
        "Evidence used:",
        "- Bottle Detect precedes Label Ready",
        "- Label Ready precedes Tamp Extend",
        "- Tamp Extend precedes delayed Label Applied",
        "- Simulated bottle stop and conveyor speed evidence reduces upstream product-position support",
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
            "Confirmed in simulated evidence package",
            "",
            "Most Likely Explanation:",
            "Label guide loosened",
            "",
            "Why:",
            (
                "Highest evidence alignment based on timing drift, preserved event "
                "sequence, simulated guide-clamp photo evidence, guide offset "
                "measurement, no timing-setting change since last rehoming, and "
                "post-adjustment validation."
            ),
            "",
            "Reasoning Summary",
            "=================",
            "- Most likely explanation: Label guide loosened",
            "- Confidence score: 0.94",
            (
                "- Why this is not absolute certainty: simulated evidence is deterministic "
                "demo data and still needs longer production-run validation."
            ),
            (
                "- What evidence would confirm it: loose guide found during inspection "
                "and alignment restored after securing the guide."
            ),
            (
                "- What evidence would falsify it: guide inspection passes while drift "
                "persists after controlled bottle, tamp-pad, and configuration checks."
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
            render_simulated_full_vision_evidence(),
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
