"""LineAlertDemo application adapter for ContextOS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from contextos import ApplicationRegistry, ContextRequest


DEFAULT_ISSUE = "Label Alignment Off"


@dataclass(frozen=True)
class AlertLine:
    """One row in the LineAlertDemo output."""

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


class LineAlertApplication:
    """ContextOS adapter for the LineAlertDemo workload."""

    def name(self) -> str:
        return "LineAlertDemo"

    def capabilities(self) -> Sequence[str]:
        return (DEFAULT_ISSUE,)

    def execute(self, context_request: ContextRequest) -> str:
        return render_alerts(
            build_demo_alerts(context_request.user_intent),
            title=context_request.user_intent,
        )


def register(registry: ApplicationRegistry) -> None:
    """Register LineAlertDemo with a ContextOS application registry."""

    registry.register(LineAlertApplication())
