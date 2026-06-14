"""Deterministic PLC-style machine event simulator.

This module is intentionally a machine-behavior generator, not a PLC emulator.
It produces timestamped event sequences that can be written as CSV and fed into
the existing LineAlert evidence pipeline.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable, Iterator, TextIO


MACHINE_SEQUENCE = (
    "CycleStart",
    "ProductDetected",
    "PrintComplete",
    "TampExtendCommand",
    "TampExtendedSensor",
    "TampHomeSensor",
    "CycleComplete",
)

DEFAULT_EVENT_OFFSET_RATIOS = {
    "CycleStart": 0.00,
    "ProductDetected": 0.22,
    "PrintComplete": 0.44,
    "TampExtendCommand": 0.60,
    "TampExtendedSensor": 0.72,
    "TampHomeSensor": 0.86,
    "CycleComplete": 0.96,
}

DEFAULT_START_TIME = "2026-06-14T10:00:00Z"
TAMP_EXTENDED_EVENT = "TampExtendedSensor"
DELAYED_TAMP_EVENTS = frozenset(
    {"TampExtendedSensor", "TampHomeSensor", "CycleComplete"}
)


class FaultMode(str, Enum):
    """Supported deterministic fault-injection modes."""

    NORMAL = "Normal"
    SLOW_TAMP = "SlowTamp"
    MISSED_SENSOR = "MissedSensor"
    DRIFT = "Drift"
    RANDOM_JITTER = "RandomJitter"


@dataclass(frozen=True)
class SimulatorEvent:
    """A generated machine event before LineAlert-specific adaptation."""

    timestamp: datetime
    event_name: str
    value: int = 1
    cycle_index: int = 0

    def csv_timestamp(self) -> str:
        """Return the CSV timestamp format expected by LineAlert examples."""

        utc_timestamp = self.timestamp.astimezone(timezone.utc).replace(tzinfo=None)
        return utc_timestamp.isoformat(timespec="milliseconds")

    def as_csv_row(self) -> dict[str, str | int]:
        return {
            "timestamp": self.csv_timestamp(),
            "event_name": self.event_name,
            "value": self.value,
        }


@dataclass(frozen=True)
class SimulatorConfig:
    """Configuration for deterministic machine-cycle generation."""

    cycle_time_ms: int = 5000
    fault_mode: FaultMode | str = FaultMode.NORMAL
    jitter_ms: int = 0
    drift_per_cycle_ms: int = 0
    slow_tamp_delay_ms: int = 500
    random_seed: int = 7
    start_time: datetime | str = field(
        default_factory=lambda: parse_timestamp(DEFAULT_START_TIME)
    )
    event_offsets_ms: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if isinstance(self.fault_mode, str):
            object.__setattr__(self, "fault_mode", FaultMode(self.fault_mode))
        if isinstance(self.start_time, str):
            object.__setattr__(self, "start_time", parse_timestamp(self.start_time))

    @classmethod
    def from_dict(cls, raw_config: dict[str, object]) -> "SimulatorConfig":
        fault_mode = FaultMode(str(raw_config.get("fault_mode", FaultMode.NORMAL.value)))
        start_time = parse_timestamp(str(raw_config.get("start_time", DEFAULT_START_TIME)))
        event_offsets = raw_config.get("event_offsets_ms")
        if event_offsets is not None and not isinstance(event_offsets, dict):
            raise ValueError("event_offsets_ms must be an object keyed by event name")

        return cls(
            cycle_time_ms=_positive_int(raw_config, "cycle_time_ms", 5000),
            fault_mode=fault_mode,
            jitter_ms=_non_negative_int(raw_config, "jitter_ms", 0),
            drift_per_cycle_ms=_non_negative_int(raw_config, "drift_per_cycle_ms", 0),
            slow_tamp_delay_ms=_non_negative_int(raw_config, "slow_tamp_delay_ms", 500),
            random_seed=_non_negative_int(raw_config, "random_seed", 7),
            start_time=start_time,
            event_offsets_ms=(
                {str(name): int(offset) for name, offset in event_offsets.items()}
                if event_offsets is not None
                else None
            ),
        )

    @classmethod
    def from_file(cls, config_path: str | Path) -> "SimulatorConfig":
        path = Path(config_path)
        with path.open("r", encoding="utf-8") as config_file:
            raw_config = json.load(config_file)
        if not isinstance(raw_config, dict):
            raise ValueError(f"Simulator config must be a JSON object: {path}")
        return cls.from_dict(raw_config)

    def event_offsets(self) -> dict[str, int]:
        offsets = (
            self.event_offsets_ms
            if self.event_offsets_ms is not None
            else {
                event_name: round(self.cycle_time_ms * ratio)
                for event_name, ratio in DEFAULT_EVENT_OFFSET_RATIOS.items()
            }
        )
        _validate_event_offsets(offsets=offsets, cycle_time_ms=self.cycle_time_ms)
        return dict(offsets)


class PLCSimulator:
    """Generate deterministic machine-cycle events with optional faults."""

    def __init__(self, config: SimulatorConfig | None = None) -> None:
        self.config = config or SimulatorConfig()
        self._random = random.Random(self.config.random_seed)

    @classmethod
    def from_config_file(cls, config_path: str | Path) -> "PLCSimulator":
        return cls(SimulatorConfig.from_file(config_path))

    def run(self) -> Iterator[SimulatorEvent]:
        """Yield simulator events continuously."""

        yield from self._event_stream(cycle_count=None)

    def generate_events(self, cycle_count: int) -> list[SimulatorEvent]:
        """Generate a finite number of complete cycles for tests or CSV files."""

        if cycle_count < 1:
            raise ValueError("cycle_count must be at least 1")
        return list(self._event_stream(cycle_count=cycle_count))

    def _event_stream(self, cycle_count: int | None) -> Iterator[SimulatorEvent]:
        cycle_index = 0
        cycle_start = self.config.start_time
        while cycle_count is None or cycle_index < cycle_count:
            cycle_events = self._generate_cycle(cycle_start, cycle_index)
            for event in cycle_events:
                yield event

            last_offset_ms = max(
                int((event.timestamp - cycle_start).total_seconds() * 1000)
                for event in cycle_events
            )
            next_cycle_ms = max(self.config.cycle_time_ms, last_offset_ms + 1)
            cycle_start += timedelta(milliseconds=next_cycle_ms)
            cycle_index += 1

    def _generate_cycle(
        self, cycle_start: datetime, cycle_index: int
    ) -> list[SimulatorEvent]:
        offsets = self.config.event_offsets()
        delay_ms = self._tamp_delay_ms(cycle_index)
        events: list[SimulatorEvent] = []

        for event_name in MACHINE_SEQUENCE:
            if (
                self.config.fault_mode is FaultMode.MISSED_SENSOR
                and event_name == TAMP_EXTENDED_EVENT
            ):
                continue

            event_delay_ms = delay_ms if event_name in DELAYED_TAMP_EVENTS else 0
            jitter_ms = self._jitter_ms()
            timestamp = cycle_start + timedelta(
                milliseconds=offsets[event_name] + event_delay_ms + jitter_ms
            )
            events.append(
                SimulatorEvent(
                    timestamp=timestamp,
                    event_name=event_name,
                    value=1,
                    cycle_index=cycle_index,
                )
            )

        return sorted(events, key=lambda event: event.timestamp)

    def _tamp_delay_ms(self, cycle_index: int) -> int:
        if self.config.fault_mode is FaultMode.SLOW_TAMP:
            return self.config.slow_tamp_delay_ms
        if self.config.fault_mode is FaultMode.DRIFT:
            return cycle_index * self.config.drift_per_cycle_ms
        return 0

    def _jitter_ms(self) -> int:
        if self.config.fault_mode is not FaultMode.RANDOM_JITTER:
            return 0
        if self.config.jitter_ms == 0:
            return 0
        return self._random.randint(-self.config.jitter_ms, self.config.jitter_ms)


def write_events_csv(events: Iterable[SimulatorEvent], output_file: TextIO) -> None:
    """Write generated simulator events using LineAlert-compatible CSV columns."""

    writer = csv.DictWriter(output_file, fieldnames=("timestamp", "event_name", "value"))
    writer.writeheader()
    for event in events:
        writer.writerow(event.as_csv_row())


def parse_timestamp(raw_timestamp: str) -> datetime:
    normalized = raw_timestamp.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _positive_int(
    raw_config: dict[str, object], field_name: str, default_value: int
) -> int:
    value = int(raw_config.get(field_name, default_value))
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than 0")
    return value


def _non_negative_int(
    raw_config: dict[str, object], field_name: str, default_value: int
) -> int:
    value = int(raw_config.get(field_name, default_value))
    if value < 0:
        raise ValueError(f"{field_name} must be 0 or greater")
    return value


def _validate_event_offsets(offsets: dict[str, int], cycle_time_ms: int) -> None:
    missing_events = [event for event in MACHINE_SEQUENCE if event not in offsets]
    if missing_events:
        raise ValueError(f"event_offsets_ms missing events: {', '.join(missing_events)}")

    ordered_offsets = [int(offsets[event_name]) for event_name in MACHINE_SEQUENCE]
    if ordered_offsets[0] != 0:
        raise ValueError("CycleStart offset must be 0")
    if any(offset < 0 for offset in ordered_offsets):
        raise ValueError("event_offsets_ms values must be 0 or greater")
    if ordered_offsets != sorted(ordered_offsets):
        raise ValueError("event_offsets_ms values must follow machine sequence order")
    if ordered_offsets[-1] >= cycle_time_ms:
        raise ValueError("CycleComplete offset must be less than cycle_time_ms")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the LineAlert PLC simulator.")
    parser.add_argument(
        "--config",
        default=Path(__file__).resolve().parents[1] / "config" / "simulator.json",
        type=Path,
        help="Path to simulator JSON config.",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        help="Generate a finite number of cycles. Omit to stream continuously.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="CSV output path. Defaults to stdout.",
    )
    parser.add_argument(
        "--no-realtime",
        action="store_true",
        help="Emit generated timestamps immediately instead of sleeping between events.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    simulator = PLCSimulator.from_config_file(args.config)
    event_stream = (
        simulator.generate_events(args.cycles) if args.cycles is not None else simulator.run()
    )
    output_file = args.output.open("w", encoding="utf-8", newline="") if args.output else sys.stdout

    try:
        _stream_csv(
            event_stream=iter(event_stream),
            output_file=output_file,
            realtime=not args.no_realtime,
        )
    finally:
        if args.output:
            output_file.close()


def _stream_csv(
    event_stream: Iterator[SimulatorEvent], output_file: TextIO, realtime: bool
) -> None:
    writer = csv.DictWriter(output_file, fieldnames=("timestamp", "event_name", "value"))
    writer.writeheader()
    previous_event: SimulatorEvent | None = None

    for event in event_stream:
        if realtime and previous_event is not None:
            sleep_seconds = (event.timestamp - previous_event.timestamp).total_seconds()
            time.sleep(max(0.0, sleep_seconds))
        writer.writerow(event.as_csv_row())
        output_file.flush()
        previous_event = event


if __name__ == "__main__":
    main()
