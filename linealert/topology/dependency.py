"""Machine topology dependency edges."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Dependency:
    """Directed dependency from upstream component to downstream component."""

    upstream: str
    downstream: str
    metadata: dict[str, object] | None = None

    @property
    def label(self) -> str:
        return f"{self.upstream} -> {self.downstream}"

    def as_dict(self) -> dict[str, object]:
        output: dict[str, object] = {
            "upstream": self.upstream,
            "downstream": self.downstream,
        }
        if self.metadata:
            output["metadata"] = dict(self.metadata)
        return output
