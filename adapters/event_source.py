"""Input-source abstraction for LineAlert event providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

try:
    from event_loader import Event
except ImportError:  # pragma: no cover - used when imported from repository root.
    from linealert.src.event_loader import Event


class EventSource(ABC):
    """Interface for components that provide normalized LineAlert events."""

    @abstractmethod
    def read_events(self) -> list[Event]:
        """Return timestamp-sorted events ready for LineAlert analysis."""
