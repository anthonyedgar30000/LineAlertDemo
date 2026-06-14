import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from applications.linealert import (
    build_demo_cycle,
    calculate_timing_analysis,
    classify_drift,
    render_linealert_report,
)
from contextos import ContextRequest, ContextRouter
from main import build_application_registry, main, run_contextos_request
from troubleshooting import TroubleshootingEngine


FORBIDDEN_DEMO_TERMS = (
    "Northbound platform",
    "Boarding delay",
    "Passenger guidance",
    "center display",
)

PHYSICAL_COMPONENTS = (
    "Conveyor",
    "Product Detect Sensor",
    "Print Engine",
    "Label Feed Assembly",
    "Label Ready Sensor",
    "Tamp Cylinder",
    "Tamp Pad",
    "Label Applied Sensor",
    "Tamp Home Sensor",
    "Controller",
)

MONITORED_RELATIONSHIPS = (
    "Bottle Detect -> Print Complete",
    "Print Complete -> Label Ready",
    "Label Ready -> Tamp Extend",
    "Tamp Extend -> Label Applied",
    "Label Applied -> Tamp Home",
)


class RenderAlertsTests(unittest.TestCase):
    def test_demo_cycle_has_expected_timing_drift(self) -> None:
        timing = calculate_timing_analysis(build_demo_cycle())

        self.assertEqual(timing.expected_lag_ms, 100)
        self.assertEqual(timing.observed_lag_ms, 153)
        self.assertEqual(timing.delta_ms, 53)
        self.assertEqual(classify_drift(timing.delta_ms), "Moderate Drift")

    def test_label_alignment_issue_demo_contains_investigation_package(self) -> None:
        output = render_linealert_report("Label Alignment Off")

        self.assertIn("Machine Context", output)
        self.assertLess(
            output.index("Machine Context"),
            output.index("LineAlert Investigation Package"),
        )
        self.assertIn("Purpose:", output)
        self.assertIn(
            "Apply printed labels to bottles moving on a conveyor.",
            output,
        )
        self.assertIn("Physical Components", output)
        self.assertIn("Expected Interaction Model", output)
        self.assertIn("Interaction Explanation", output)
        self.assertIn("Monitored Relationships", output)
        self.assertIn("LineAlert Investigation Package", output)
        self.assertIn("Machine\nBottle Labeling Machine", output)
        self.assertIn("Issue\nLabel Alignment Off", output)
        self.assertIn("Observed Evidence", output)
        self.assertIn("- 2026-06-14T05:16:00.240Z Tamp Extend", output)
        self.assertIn("- 2026-06-14T05:16:00.393Z Label Applied", output)
        self.assertIn("Expected State", output)
        self.assertIn("Tamp Extend -> Label Applied within 100 ms", output)
        self.assertIn("Observed State", output)
        self.assertIn("Tamp Extend -> Label Applied in 153 ms", output)
        self.assertIn("Relationship Analysis", output)
        self.assertIn("Timing Analysis", output)
        self.assertIn("- Delta: +53 ms", output)
        self.assertIn("Drift Analysis", output)
        self.assertIn("- Moderate Drift: 31-75 ms delta (observed)", output)
        self.assertIn("Candidate Hypotheses", output)
        self.assertIn("1. Label guide loosened", output)
        self.assertIn("2. Tamp pad wear", output)
        self.assertIn("3. Product positioning variance", output)
        self.assertIn("4. Sensor contamination", output)
        self.assertIn("Peter Troubleshooting Guide", output)
        self.assertIn("Guide: Peter Label Alignment Guide", output)
        self.assertIn("Prioritized Workflow", output)
        self.assertIn("Troubleshooting Workflow", output)
        self.assertIn("Current Recommended Starting Step:", output)
        self.assertIn("Inspect Label Guide", output)
        self.assertIn("Highest ranked hypothesis:", output)
        self.assertIn("Label guide loosened", output)
        self.assertIn("Supporting Evidence:", output)
        self.assertIn("- Expected lag 100 ms", output)
        self.assertIn("- Observed lag 153 ms", output)
        self.assertIn("- Drift +53 ms", output)
        self.assertIn("Verification Steps", output)
        self.assertIn("Run 10 bottles and confirm alignment within tolerance", output)
        self.assertIn("Confirm alignment restored", output)
        self.assertIn("Recommended Actions", output)
        self.assertIn("Escalation Guidance", output)
        self.assertIn("Confidence Assessment", output)
        self.assertIn("Tradeoff Summary", output)
        for component in PHYSICAL_COMPONENTS:
            self.assertIn(component, output)
        for relationship in MONITORED_RELATIONSHIPS:
            self.assertIn(relationship, output)
        for term in FORBIDDEN_DEMO_TERMS:
            self.assertNotIn(term, output)

    def test_troubleshooting_engine_ranks_peter_guide_from_hypotheses(self) -> None:
        engine = TroubleshootingEngine()
        guide = engine.load_guide("Label Alignment Off")
        ranked_steps = engine.rank_steps_from_evidence(
            guide,
            (
                "Label guide loosened",
                "Tamp pad wear",
                "Product positioning variance",
                "Sensor contamination",
            ),
        )

        self.assertEqual(guide.guide_name, "Peter Label Alignment Guide")
        self.assertEqual(ranked_steps[0].title, "Inspect Label Guide")
        self.assertEqual(ranked_steps[1].title, "Inspect Tamp Pad")
        self.assertEqual(ranked_steps[2].title, "Verify Product Stop Position")
        self.assertEqual(ranked_steps[3].title, "Inspect Sensors")

    def test_contextos_request_wraps_line_alert_output(self) -> None:
        output = run_contextos_request("Label Alignment Off", request_id="test-request")

        self.assertIn("ContextOS Envelope:", output)
        self.assertIn("request_id", output)
        self.assertIn("test-request", output)
        self.assertIn("source_app", output)
        self.assertIn("ContextOS", output)
        self.assertIn("target_app", output)
        self.assertIn("LineAlertDemo", output)
        self.assertIn("decision", output)
        self.assertIn("Proceed", output)
        self.assertIn("Application Output:", output)
        self.assertIn("Machine Context", output)
        self.assertIn("LineAlert Investigation Package", output)
        self.assertIn("- Delta: +53 ms", output)
        self.assertIn("Peter Troubleshooting Guide", output)
        self.assertIn("Current Recommended Starting Step:", output)
        self.assertIn(
            "1. Inspect and secure the label guide before changing timing parameters.",
            output,
        )
        for term in FORBIDDEN_DEMO_TERMS:
            self.assertNotIn(term, output)

    def test_line_alert_is_registered_application(self) -> None:
        registry = build_application_registry()
        application = registry.get_application("Label Alignment Off")

        self.assertIsNotNone(application)
        self.assertEqual(application.name(), "LineAlertDemo")
        self.assertEqual(application.capabilities(), ("Label Alignment Off",))

    def test_contextos_router_selects_registered_line_alert_application(self) -> None:
        request = ContextRequest.create(
            user_intent="Label Alignment Off",
            request_id="test-request",
        )
        response = ContextRouter(build_application_registry()).route(request)

        self.assertEqual(response.target_app, "LineAlertDemo")
        self.assertEqual(response.decision, "Proceed")
        self.assertEqual(response.confidence, "Medium-high")
        self.assertIsNotNone(response.application_output)
        self.assertIn(
            "LineAlert Investigation Package",
            response.application_output,
        )
        self.assertIn("Machine Context", response.application_output)
        for component in PHYSICAL_COMPONENTS:
            self.assertIn(component, response.application_output)
        self.assertIn("- Delta: +53 ms", response.application_output)
        for term in FORBIDDEN_DEMO_TERMS:
            self.assertNotIn(term, response.application_output)

    def test_unknown_issue_policy_skips_line_alert_invocation(self) -> None:
        output = run_contextos_request("Unexpected Platform Fire", request_id="test-request")

        self.assertIn("decision         : Investigate Further", output)
        self.assertIn("confidence       : Low", output)
        self.assertIn(
            "evidence         : ContextOS did not recognize intent "
            "'Unexpected Platform Fire'; no registered application was invoked",
            output,
        )
        self.assertIn(
            "assumptions      : No safe registered application mapping exists for the request",
            output,
        )
        self.assertIn("Application Output: SKIPPED", output)
        self.assertIn("Unresolved was not invoked by ContextOS policy.", output)
        self.assertNotIn("Demo scenario loaded", output)

    def test_demo_cli_routes_through_contextos(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = main(["--demo", "--issue", "Label Alignment Off"])

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("ContextOS Governed Response", output)
        self.assertIn("ContextOS Envelope:", output)
        self.assertIn("Application Output:", output)
        self.assertIn("Machine Context", output)
        for term in FORBIDDEN_DEMO_TERMS:
            self.assertNotIn(term, output)


if __name__ == "__main__":
    unittest.main()
