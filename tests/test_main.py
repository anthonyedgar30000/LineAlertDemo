import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from main import AlertLine, build_demo_alerts, render_alerts


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


if __name__ == "__main__":
    unittest.main()
