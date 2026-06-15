"""Machine component model independent from event timing."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Component:
    """A physical or logical machine component."""

    component_id: str
    name: str
    component_type: str
    parent_component: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        output: dict[str, object] = {
            "component_id": self.component_id,
            "name": self.name,
            "type": self.component_type,
            "metadata": dict(self.metadata),
        }
        if self.parent_component is not None:
            output["parent_component"] = self.parent_component
        return output
