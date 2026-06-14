import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from contextos import ContextRequest, ContextRouter
from main import (
    AlertLine,
    build_application_registry,
    build_demo_alerts,
    main,
    render_alerts,
    run_contextos_request,
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
            title="Label Alignment Off",
        )

        self.assertIn("Label Alignment Off", output)
        self.assertIn("Passenger guidance : Use the center display for reroutes", output)

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
        self.assertIn("LineAlert Output:", output)
        self.assertIn("Passenger guidance : Use the center display for reroutes", output)

    def test_line_alert_is_registered_application(self) -> None:
        registry = build_application_registry()
        application = registry.get_application("Label Alignment Off")

        self.assertIsNotNone(application)
        self.assertEqual(application.name, "LineAlertDemo")

    def test_contextos_router_selects_registered_line_alert_application(self) -> None:
        request = ContextRequest.create(
            user_intent="Label Alignment Off",
            request_id="test-request",
        )
        response = ContextRouter(build_application_registry()).route(request)

        self.assertEqual(response.target_app, "LineAlertDemo")
        self.assertEqual(response.decision, "Proceed")
        self.assertEqual(response.confidence, "Medium-high")
        self.assertIn(
            "Passenger guidance : Use the center display for reroutes",
            response.application_output,
        )

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
        self.assertIn("LineAlert Output:", output)


if __name__ == "__main__":
    unittest.main()
