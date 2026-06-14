import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from main import (
    AlertLine,
    build_demo_alerts,
    evaluate_contextos_policy,
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

    def test_known_issue_policy_allows_line_alert_invocation(self) -> None:
        decision = evaluate_contextos_policy("Label Alignment Off")

        self.assertTrue(decision.may_invoke_line_alert)
        self.assertEqual(decision.decision, "Proceed")
        self.assertEqual(decision.confidence, "Medium-high")

    def test_unknown_issue_policy_skips_line_alert_invocation(self) -> None:
        output = run_contextos_request("Unexpected Platform Fire", request_id="test-request")

        self.assertIn("decision         : Investigate Further", output)
        self.assertIn("confidence       : Low", output)
        self.assertIn(
            "evidence         : ContextOS did not recognize issue "
            "'Unexpected Platform Fire'; LineAlertDemo was not invoked",
            output,
        )
        self.assertIn(
            "assumptions      : No safe demo mapping exists for the requested issue",
            output,
        )
        self.assertIn("LineAlert Output: SKIPPED", output)
        self.assertIn("LineAlertDemo was not invoked by ContextOS policy.", output)
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
