#!/usr/bin/env python3
"""Command line demo for line alert rendering."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Iterable, Sequence


DEFAULT_ISSUE = "Label Alignment Off"


@dataclass(frozen=True)
class AlertLine:
    """One row in the line alert demo output."""

    label: str
    message: str


def build_demo_alerts(issue: str) -> list[AlertLine]:
    """Return representative alert rows for the requested issue demo."""

    if issue.casefold() == DEFAULT_ISSUE.casefold():
        return [
            AlertLine("Line", "Northbound platform"),
            AlertLine("Status", "Boarding delay"),
            AlertLine("Next update", "03:55 UTC"),
            AlertLine("Passenger guidance", "Use the center display for reroutes"),
        ]

    return [
        AlertLine("Issue", issue),
        AlertLine("Status", "Demo scenario loaded"),
        AlertLine("Next update", "Pending"),
    ]


def render_alerts(alerts: Iterable[AlertLine], *, title: str = "Line Alert Demo") -> str:
    """Render alert rows with a consistently aligned label column."""

    rows = list(alerts)
    if not rows:
        return title

    label_width = max(len(row.label) for row in rows)
    rendered_rows = [title, "=" * len(title)]

    for row in rows:
        rendered_rows.append(f"{row.label:<{label_width}} : {row.message}")

    return "\n".join(rendered_rows)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render LineAlertDemo scenarios.")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="render a built-in demo scenario",
    )
    parser.add_argument(
        "--issue",
        default=DEFAULT_ISSUE,
        help="issue scenario to render",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.demo:
        print("Nothing to render. Pass --demo to display a scenario.")
        return 0

    print(render_alerts(build_demo_alerts(args.issue), title=args.issue))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
