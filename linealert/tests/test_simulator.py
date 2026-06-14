"""Tests for the deterministic PLC simulator input source."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_DIR))

from adapters.simulator_adapter import SimulatorEventSource  # noqa: E402
from event_loader import load_events  # noqa: E402
from simulator.plc_simulator import (  # noqa: E402
    FaultMode,
    MACHINE_SEQUENCE,
    PLCSimulator,
    SimulatorConfig,
    write_events_csv,
)
from timing_engine import calculate_timing_observations  # noqa: E402


class PLCSimulatorTests(unittest.TestCase):
    def test_normal_mode_generates_expected_sequence(self) -> None:
        simulator = PLCSimulator(
            SimulatorConfig(
                cycle_time_ms=5000,
                fault_mode=FaultMode.NORMAL,
                jitter_ms=0,
                start_time="2026-06-14T10:00:00Z",
            )
        )

        events = simulator.generate_events(cycle_count=1)

        self.assertEqual(list(MACHINE_SEQUENCE), [event.event_name for event in events])
        self.assertEqual("2026-06-14T10:00:00.000", events[0].csv_timestamp())
        self.assertEqual("2026-06-14T10:00:04.800", events[-1].csv_timestamp())

    def test_slow_tamp_delays_tamp_extension_and_downstream_events(self) -> None:
        simulator = PLCSimulator(
            SimulatorConfig(
                fault_mode=FaultMode.SLOW_TAMP,
                slow_tamp_delay_ms=500,
                start_time="2026-06-14T10:00:00Z",
            )
        )

        events = simulator.generate_events(cycle_count=1)
        timestamps_by_name = {
            event.event_name: event.csv_timestamp()
            for event in events
        }

        self.assertEqual(
            "2026-06-14T10:00:04.100",
            timestamps_by_name["TampExtendedSensor"],
        )
        self.assertEqual(
            "2026-06-14T10:00:05.300",
            timestamps_by_name["CycleComplete"],
        )

    def test_missed_sensor_skips_tamp_extended_sensor(self) -> None:
        simulator = PLCSimulator(
            SimulatorConfig(
                fault_mode=FaultMode.MISSED_SENSOR,
                start_time="2026-06-14T10:00:00Z",
            )
        )

        event_names = [
            event.event_name for event in simulator.generate_events(cycle_count=1)
        ]

        self.assertNotIn("TampExtendedSensor", event_names)
        self.assertIn("TampHomeSensor", event_names)
        self.assertIn("CycleComplete", event_names)

    def test_drift_delay_increases_each_cycle(self) -> None:
        simulator = PLCSimulator(
            SimulatorConfig(
                fault_mode=FaultMode.DRIFT,
                drift_per_cycle_ms=10,
                start_time="2026-06-14T10:00:00Z",
            )
        )

        tamp_events = [
            event
            for event in simulator.generate_events(cycle_count=3)
            if event.event_name == "TampExtendedSensor"
        ]

        self.assertEqual("2026-06-14T10:00:03.600", tamp_events[0].csv_timestamp())
        self.assertEqual("2026-06-14T10:00:08.610", tamp_events[1].csv_timestamp())
        self.assertEqual("2026-06-14T10:00:13.620", tamp_events[2].csv_timestamp())

    def test_random_jitter_is_seeded_and_repeatable(self) -> None:
        config = SimulatorConfig(
            fault_mode=FaultMode.RANDOM_JITTER,
            jitter_ms=50,
            random_seed=17,
            start_time="2026-06-14T10:00:00Z",
        )

        first_run = [event.csv_timestamp() for event in PLCSimulator(config).generate_events(2)]
        second_run = [event.csv_timestamp() for event in PLCSimulator(config).generate_events(2)]

        self.assertEqual(first_run, second_run)
        self.assertNotEqual(
            [event.csv_timestamp() for event in PLCSimulator().generate_events(2)],
            first_run,
        )

    def test_adapter_returns_linealert_events_for_timing_pipeline(self) -> None:
        source = SimulatorEventSource(
            simulator=PLCSimulator(
                SimulatorConfig(
                    fault_mode=FaultMode.NORMAL,
                    jitter_ms=0,
                    start_time="2026-06-14T10:00:00Z",
                )
            ),
            cycle_count=2,
        )

        events = source.read_events()
        observations = calculate_timing_observations(events)
        observation_keys = {
            observation.observation_key for observation in observations.lags
        }

        self.assertEqual(14, len(events))
        self.assertEqual("CycleStart", events[0].event_name)
        self.assertIn("lag:TampExtendCommand->TampExtendedSensor", observation_keys)
        self.assertIn("cycle:CycleStart", {metric.observation_key for metric in observations.metrics})

    def test_simulator_csv_is_compatible_with_existing_loader(self) -> None:
        simulator = PLCSimulator(
            SimulatorConfig(
                fault_mode=FaultMode.NORMAL,
                jitter_ms=0,
                start_time="2026-06-14T10:00:00Z",
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "simulator_events.csv"
            with output_path.open("w", encoding="utf-8", newline="") as output_file:
                write_events_csv(simulator.generate_events(cycle_count=1), output_file)

            events = load_events(output_path)

        self.assertEqual(list(MACHINE_SEQUENCE), [event.event_name for event in events])


if __name__ == "__main__":
    unittest.main()
