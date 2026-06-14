"""Adapter from simulator events to LineAlert normalized events."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

try:
    from event_loader import Event
except ImportError:  # pragma: no cover - used when imported from repository root.
    from linealert.src.event_loader import Event

from adapters.event_source import EventSource
from simulator.plc_simulator import PLCSimulator, SimulatorEvent


class SimulatorEventSource(EventSource):
    """Read deterministic simulator output as LineAlert pipeline events."""

    def __init__(self, simulator: PLCSimulator, cycle_count: int) -> None:
        if cycle_count < 1:
            raise ValueError("cycle_count must be at least 1")
        self.simulator = simulator
        self.cycle_count = cycle_count

    @classmethod
    def from_config_file(
        cls, config_path: str | Path, cycle_count: int
    ) -> "SimulatorEventSource":
        return cls(
            simulator=PLCSimulator.from_config_file(config_path),
            cycle_count=cycle_count,
        )

    def read_events(self) -> list[Event]:
        simulator_events = self.simulator.generate_events(self.cycle_count)
        return simulator_events_to_linealert_events(simulator_events)


def simulator_events_to_linealert_events(
    simulator_events: Iterable[SimulatorEvent],
) -> list[Event]:
    """Convert raw simulator events into the structure LineAlert already expects."""

    return [
        Event(
            timestamp=event.timestamp,
            event_name=event.event_name,
            source_row=index,
        )
        for index, event in enumerate(
            sorted(simulator_events, key=lambda item: item.timestamp),
            start=1,
        )
    ]
