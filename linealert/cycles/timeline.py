"""Human-readable timeline views for machine cycles."""

from __future__ import annotations

from linealert.cycles.cycle import Cycle


def format_cycle_timeline(cycle: Cycle) -> str:
    """Render one cycle as offsets from CycleStart."""

    lines = [f"Cycle {cycle.cycle_id}", ""]
    for event in cycle.events:
        offset_ms = (event.timestamp - cycle.start_timestamp).total_seconds() * 1000
        lines.append(f"{_format_offset(offset_ms)} {event.event_name}")
    return "\n".join(lines)


def get_cycle_timeline(cycles: list[Cycle], cycle_id: int) -> str:
    """Return a formatted timeline for one cycle id."""

    return format_cycle_timeline(get_cycle(cycles=cycles, cycle_id=cycle_id))


def get_cycle(cycles: list[Cycle], cycle_id: int) -> Cycle:
    for cycle in cycles:
        if cycle.cycle_id == cycle_id:
            return cycle
    raise ValueError(f"Cycle not found: {cycle_id}")


def _format_offset(offset_ms: float) -> str:
    seconds = offset_ms / 1000
    return f"{seconds:06.3f}"
