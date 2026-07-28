#!/usr/bin/env python3
"""Command line demo for line alert rendering."""

from __future__ import annotations

import argparse
from typing import Sequence

from applications.linealert import DEFAULT_ISSUE, register as register_linealert
from contextos import ApplicationRegistry, ContextRequest, ContextRouter


def build_application_registry() -> ApplicationRegistry:
    """Register applications available to ContextOS."""

    registry = ApplicationRegistry()
    register_linealert(registry)
    return registry


def run_contextos_request(issue: str, *, request_id: str | None = None) -> str:
    """Submit a request to ContextOS and render the governed response."""

    request = ContextRequest.create(user_intent=issue, request_id=request_id)
    router = ContextRouter(build_application_registry())
    return router.route(request).render()


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
