#!/usr/bin/env python3
"""Command line demo for line alert rendering."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Iterable, Sequence
from uuid import uuid4


DEFAULT_ISSUE = "Label Alignment Off"


@dataclass(frozen=True)
class AlertLine:
    """One row in the line alert demo output."""

    label: str
    message: str


@dataclass(frozen=True)
class ContextOSEnvelope:
    """Governance metadata wrapped around a LineAlertDemo request."""

    request_id: str
    source_app: str
    target_app: str
    user_intent: str
    operation_scope: str
    evidence: str
    assumptions: str
    decision: str
    confidence: str
    tradeoff_summary: str


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


def build_contextos_envelope(issue: str, *, request_id: str | None = None) -> ContextOSEnvelope:
    """Build the governance envelope for a local LineAlertDemo invocation."""

    return ContextOSEnvelope(
        request_id=request_id or str(uuid4()),
        source_app="ContextOS",
        target_app="LineAlertDemo",
        user_intent=issue,
        operation_scope="demo",
        evidence=(
            f"ContextOS received demo request for issue '{issue}'; "
            "LineAlertDemo core renderer invoked locally"
        ),
        assumptions="Local adapter represents the ContextOS app boundary for this demo",
        decision="Proceed",
        confidence="Medium-high",
        tradeoff_summary=(
            "Small in-process adapter avoids external dependencies; full service "
            "integration remains outside this demo"
        ),
    )


def render_contextos_response(envelope: ContextOSEnvelope, line_alert_output: str) -> str:
    """Render a governed ContextOS response with the original LineAlert output."""

    envelope_rows = [
        ("request_id", envelope.request_id),
        ("source_app", envelope.source_app),
        ("target_app", envelope.target_app),
        ("user_intent", envelope.user_intent),
        ("operation_scope", envelope.operation_scope),
        ("evidence", envelope.evidence),
        ("assumptions", envelope.assumptions),
        ("decision", envelope.decision),
        ("confidence", envelope.confidence),
        ("tradeoff_summary", envelope.tradeoff_summary),
    ]
    label_width = max(len(label) for label, _ in envelope_rows)
    rendered_rows = [
        "ContextOS Governed Response",
        "===========================",
        "",
        "ContextOS Envelope:",
    ]

    rendered_rows.extend(f"{label:<{label_width}} : {value}" for label, value in envelope_rows)
    rendered_rows.extend(["", "LineAlert Output:", line_alert_output])
    return "\n".join(rendered_rows)


def run_contextos_request(issue: str, *, request_id: str | None = None) -> str:
    """Route a ContextOS request through LineAlertDemo and return a governed response."""

    envelope = build_contextos_envelope(issue, request_id=request_id)
    line_alert_output = render_alerts(build_demo_alerts(issue), title=issue)
    return render_contextos_response(envelope, line_alert_output)


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

    print(run_contextos_request(args.issue))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
