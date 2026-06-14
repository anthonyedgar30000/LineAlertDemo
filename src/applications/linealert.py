"""LineAlertDemo application adapter for ContextOS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from contextos import ApplicationRegistry, ContextRequest


DEFAULT_ISSUE = "Label Alignment Off"
MACHINE_NAME = "Bottle Labeling Machine"
BASE_TIMESTAMP = "2026-06-14T05:16:00"
EXPECTED_TAMP_TO_APPLIED_MS = 100


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


def render_linealert_report(issue: str) -> str:
    """Render a deterministic industrial investigation package."""

    events = build_demo_cycle()
    timing = calculate_timing_analysis(events)
    drift_classification = classify_drift(timing.delta_ms)

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
            "Candidate Hypotheses",
            "1. Label guide loosened - highest ranked possibility; could shift label path before tamp contact.",
            "2. Tamp pad wear - could reduce consistent label transfer and add application delay.",
            "3. Product positioning variance - could change bottle presentation during tamp extension.",
            "4. Sensor contamination - could delay readiness or applied-state confirmation.",
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
