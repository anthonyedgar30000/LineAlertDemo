import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from applications.linealert import AlertLine, build_demo_alerts, render_alerts
from contextos import ContextRequest, ContextRouter
from main import build_application_registry, main, run_contextos_request


FORBIDDEN_DEMO_TERMS = (
    "Northbound platform",
    "Boarding delay",
    "Passenger guidance",
    "center display",
)


class RenderAlertsTests(unittest.TestCase):
    def test_labels_share_the_same_separator_column(self) -> None:
        output = render_alerts(
            [
                AlertLine("A", "short label"),
                AlertLine("Medium", "medium label"),
                AlertLine("Much longer label", "long label"),
            ]
        )

        rows = output.splitlines()[2:]
        separator_columns = {row.index(":") for row in rows}

        self.assertEqual(separator_columns, {len("Much longer label") + 1})

    def test_label_alignment_issue_demo_contains_expected_rows(self) -> None:
        output = render_alerts(
            build_demo_alerts("Label Alignment Off"),
            title="LineAlert Report",
        )

        self.assertIn("LineAlert Report", output)
        self.assertIn("Issue              : Label Alignment Off", output)
        self.assertIn("Asset              : Label Applicator Station", output)
        self.assertIn(
            "Observed Condition : Label placement drift detected",
            output,
        )
        self.assertIn(
            "Expected State     : Label applied within alignment tolerance",
            output,
        )
        self.assertIn(
            "Observed State     : Label position outside expected tolerance window",
            output,
        )
        self.assertIn(
            "Likely Layer       : Mechanical alignment / sensor timing",
            output,
        )
        self.assertIn(
            "Recommended Action : Inspect label guide, tamp alignment, and sensor timing before rebaseline",
            output,
        )
        self.assertIn(
            "Escalation         : Operator Lead if repeated after adjustment",
            output,
        )
        for term in FORBIDDEN_DEMO_TERMS:
            self.assertNotIn(term, output)

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
        self.assertIn("LineAlert Report", output)
        self.assertIn(
            "Recommended Action : Inspect label guide, tamp alignment, and sensor timing before rebaseline",
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
            "Recommended Action : Inspect label guide, tamp alignment, and sensor timing before rebaseline",
            response.application_output,
        )
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
        for term in FORBIDDEN_DEMO_TERMS:
            self.assertNotIn(term, output)


if __name__ == "__main__":
    unittest.main()
