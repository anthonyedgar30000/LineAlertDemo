"""Minimal in-process ContextOS router for governed demo workloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import uuid4


ApplicationHandler = Callable[["ContextRequest"], str]


@dataclass(frozen=True)
class ContextRequest:
    """A request entering ContextOS before application selection."""

    request_id: str
    source_app: str
    user_intent: str
    operation_scope: str

    @classmethod
    def create(
        cls,
        *,
        user_intent: str,
        operation_scope: str = "demo",
        source_app: str = "ContextOS",
        request_id: str | None = None,
    ) -> "ContextRequest":
        return cls(
            request_id=request_id or str(uuid4()),
            source_app=source_app,
            user_intent=user_intent,
            operation_scope=operation_scope,
        )


@dataclass(frozen=True)
class ContextResponse:
    """A governed response returned by ContextOS after routing."""

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
    application_output_label: str
    application_output: str | None

    def render(self) -> str:
        envelope_rows = [
            ("request_id", self.request_id),
            ("source_app", self.source_app),
            ("target_app", self.target_app),
            ("user_intent", self.user_intent),
            ("operation_scope", self.operation_scope),
            ("evidence", self.evidence),
            ("assumptions", self.assumptions),
            ("decision", self.decision),
            ("confidence", self.confidence),
            ("tradeoff_summary", self.tradeoff_summary),
        ]
        label_width = max(len(label) for label, _ in envelope_rows)
        rendered_rows = [
            "ContextOS Governed Response",
            "===========================",
            "",
            "ContextOS Envelope:",
        ]

        rendered_rows.extend(
            f"{label:<{label_width}} : {value}" for label, value in envelope_rows
        )
        if self.application_output is None:
            rendered_rows.extend(
                [
                    "",
                    f"{self.application_output_label}: SKIPPED",
                    f"{self.target_app} was not invoked by ContextOS policy.",
                ]
            )
        else:
            rendered_rows.extend(["", f"{self.application_output_label}:", self.application_output])
        return "\n".join(rendered_rows)


@dataclass(frozen=True)
class RegisteredApplication:
    name: str
    output_label: str
    handler: ApplicationHandler


class ApplicationRegistry:
    """Registry mapping user intents to executable applications."""

    def __init__(self) -> None:
        self._applications_by_intent: dict[str, RegisteredApplication] = {}

    def register(
        self,
        *,
        intent: str,
        name: str,
        handler: ApplicationHandler,
        output_label: str,
    ) -> None:
        self._applications_by_intent[self._normalize_intent(intent)] = RegisteredApplication(
            name=name,
            output_label=output_label,
            handler=handler,
        )

    def get_application(self, user_intent: str) -> RegisteredApplication | None:
        return self._applications_by_intent.get(self._normalize_intent(user_intent))

    @staticmethod
    def _normalize_intent(user_intent: str) -> str:
        return user_intent.casefold()


class ContextRouter:
    """Routes ContextOS requests to registered applications under governance."""

    def __init__(self, registry: ApplicationRegistry) -> None:
        self._registry = registry

    def route(self, request: ContextRequest) -> ContextResponse:
        application = self._registry.get_application(request.user_intent)
        if application is None:
            return ContextResponse(
                request_id=request.request_id,
                source_app=request.source_app,
                target_app="Unresolved",
                user_intent=request.user_intent,
                operation_scope=request.operation_scope,
                evidence=(
                    f"ContextOS did not recognize intent '{request.user_intent}'; "
                    "no registered application was invoked"
                ),
                assumptions="No safe registered application mapping exists for the request",
                decision="Investigate Further",
                confidence="Low",
                tradeoff_summary=(
                    "Skipping unknown intents avoids unsafe fallback behavior; new "
                    "applications or intents must be registered before execution"
                ),
                application_output_label="Application Output",
                application_output=None,
            )

        application_output = application.handler(request)
        return ContextResponse(
            request_id=request.request_id,
            source_app=request.source_app,
            target_app=application.name,
            user_intent=request.user_intent,
            operation_scope=request.operation_scope,
            evidence=(
                f"ContextOS matched intent '{request.user_intent}' to registered "
                f"application '{application.name}'"
            ),
            assumptions="Registered application mapping is safe to invoke locally",
            decision="Proceed",
            confidence="Medium-high",
            tradeoff_summary=(
                "Registered intent proceeds through the selected application; policy "
                "remains limited to explicit registry mappings"
            ),
            application_output_label=application.output_label,
            application_output=application_output,
        )
