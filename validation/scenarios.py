"""Deterministic validation scenarios backed by the PLC simulator."""

from __future__ import annotations

from dataclasses import dataclass

from adapters.simulator_adapter import SimulatorEventSource
from simulator.plc_simulator import FaultMode, PLCSimulator, SimulatorConfig


@dataclass(frozen=True)
class ValidationScenario:
    """A simulator-backed validation scenario and its expected observations."""

    name: str
    event_source: SimulatorEventSource
    expected_issue_types: tuple[str, ...]
    expected_outcomes: tuple[str, ...]


def build_validation_scenarios(cycle_count: int = 20) -> list[ValidationScenario]:
    """Create validation scenarios for all deterministic simulator fault modes."""

    return [
        ValidationScenario(
            name="Normal",
            event_source=_source(FaultMode.NORMAL, cycle_count),
            expected_issue_types=(),
            expected_outcomes=("No anomaly",),
        ),
        ValidationScenario(
            name="SlowTamp",
            event_source=_source(
                FaultMode.SLOW_TAMP,
                cycle_count,
                slow_tamp_delay_ms=500,
            ),
            expected_issue_types=("ExcessiveLag",),
            expected_outcomes=(
                "Tamp lag increases",
                "Drift score increases",
                "Sequence remains valid",
            ),
        ),
        ValidationScenario(
            name="MissedSensor",
            event_source=_source(FaultMode.MISSED_SENSOR, cycle_count),
            expected_issue_types=("MissingEvent", "SequenceViolation"),
            expected_outcomes=(
                "Missing event detected",
                "Sequence violation detected",
            ),
        ),
        ValidationScenario(
            name="Drift",
            event_source=_source(
                FaultMode.DRIFT,
                cycle_count,
                drift_per_cycle_ms=10,
            ),
            expected_issue_types=("IncreasingDrift",),
            expected_outcomes=(
                "Tamp lag increases gradually",
                "Increasing deviation detected",
            ),
        ),
        ValidationScenario(
            name="RandomJitter",
            event_source=_source(
                FaultMode.RANDOM_JITTER,
                cycle_count,
                jitter_ms=50,
                random_seed=17,
            ),
            expected_issue_types=("RhythmInstability",),
            expected_outcomes=("Timing variance detected",),
        ),
    ]


def _source(
    fault_mode: FaultMode,
    cycle_count: int,
    slow_tamp_delay_ms: int = 500,
    drift_per_cycle_ms: int = 0,
    jitter_ms: int = 0,
    random_seed: int = 7,
) -> SimulatorEventSource:
    return SimulatorEventSource(
        simulator=PLCSimulator(
            SimulatorConfig(
                cycle_time_ms=5000,
                fault_mode=fault_mode,
                jitter_ms=jitter_ms,
                drift_per_cycle_ms=drift_per_cycle_ms,
                slow_tamp_delay_ms=slow_tamp_delay_ms,
                random_seed=random_seed,
                start_time="2026-06-14T10:00:00Z",
            )
        ),
        cycle_count=cycle_count,
    )
