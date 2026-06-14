# LineAlertDemo

LineAlertDemo contains the deterministic LineAlert analysis MVP under
`linealert/` plus input-source utilities for generating machine events.

## PLC Simulator Input Source

The PLC simulator is a deterministic machine-behavior generator for validating
LineAlert concepts. It is not a PLC emulator. It produces realistic timestamped
events that can be adapted to the existing LineAlert event structure or written
as CSV for the current loader.

### New File Tree

```text
adapters/
├── __init__.py
├── event_source.py
└── simulator_adapter.py
config/
└── simulator.json
simulator/
├── __init__.py
└── plc_simulator.py
linealert/tests/
└── test_simulator.py
```

### Architecture

- `simulator/plc_simulator.py` owns deterministic machine-cycle generation.
- `adapters/event_source.py` defines the `EventSource` interface for swappable
  future inputs such as Modbus TCP, OPC UA, Panasonic USB decoders, or real PLCs.
- `adapters/simulator_adapter.py` converts simulator events into the existing
  LineAlert `Event` dataclass without changing timing, drift, topology, rules,
  reporting, or UI logic.
- `config/simulator.json` provides default cycle timing and fault settings.

### Machine Cycle

Each generated cycle emits:

```text
CycleStart
ProductDetected
PrintComplete
TampExtendCommand
TampExtendedSensor
TampHomeSensor
CycleComplete
```

### Example Event Stream

```csv
timestamp,event_name,value
2026-06-14T10:00:00.000,CycleStart,1
2026-06-14T10:00:01.100,ProductDetected,1
2026-06-14T10:00:02.200,PrintComplete,1
2026-06-14T10:00:03.000,TampExtendCommand,1
2026-06-14T10:00:03.600,TampExtendedSensor,1
2026-06-14T10:00:04.300,TampHomeSensor,1
2026-06-14T10:00:04.800,CycleComplete,1
```

### Fault Modes

- `Normal`: nominal deterministic cycle.
- `SlowTamp`: delays `TampExtendedSensor` and downstream cycle events.
- `MissedSensor`: omits `TampExtendedSensor`.
- `Drift`: increases tamp-delay by `drift_per_cycle_ms` each cycle.
- `RandomJitter`: applies seeded bounded timing jitter using `jitter_ms`.

### Sample Execution

Generate three cycles immediately:

```bash
python3 simulator/plc_simulator.py --cycles 3 --no-realtime
```

Write simulator events to CSV, then run the existing LineAlert pipeline against
that CSV:

```bash
python3 simulator/plc_simulator.py --cycles 3 --no-realtime --output /tmp/simulator_events.csv
cd linealert
python3 src/main.py --events /tmp/simulator_events.csv
```

Stream continuously using configured timing:

```bash
python3 simulator/plc_simulator.py --config config/simulator.json
```

The current LineAlert CSV loader requires `timestamp,event_name` and tolerates
the simulator's additional `value` column.

## Deterministic Validation Suite

The validation suite proves that behavioral degradation can be detected from
event timelines alone. It keeps the flow separate:

```text
Events
↓
Evidence
↓
Analysis
↓
Recommendations
```

Recommendations are not part of this layer.

### Validation File Tree

```text
config/
└── event_relationships.json
validation/
├── __init__.py
├── anomaly_detector.py
├── baseline.py
├── report_generator.py
└── scenarios.py
linealert/tests/
└── test_validation.py
```

### Timing Model

`config/event_relationships.json` defines first-version timing relationships:

```json
{
  "relationships": [
    {
      "name": "Tamp Extension Lag",
      "from": "TampExtendCommand",
      "to": "TampExtendedSensor",
      "type": "lag"
    }
  ]
}
```

### Example Baseline

Generated from Normal simulator cycles:

```json
{
  "relationships": {
    "TampExtendCommand->TampExtendedSensor": {
      "avg_ms": 600.0,
      "stddev_ms": 0.0,
      "sample_count": 20
    }
  },
  "cycle_duration_ms": {
    "avg_ms": 4800.0,
    "stddev_ms": 0.0,
    "sample_count": 20
  }
}
```

### Example Anomaly Report

SlowTamp produces lag evidence only:

```json
{
  "issue_type": "ExcessiveLag",
  "relationship": "Tamp Extension Lag",
  "baseline_lag_ms": 600.0,
  "observed_lag_ms": 1100.0,
  "deviation_percent": 83.333,
  "severity": "High",
  "confidence": 0.99,
  "evidence_count": 20
}
```

### Validation Scenarios

- `Normal`: no anomaly.
- `SlowTamp`: lag anomaly, sequence remains valid.
- `MissedSensor`: missing event and sequence evidence.
- `Drift`: increasing lag deviation evidence.
- `RandomJitter`: rhythm instability evidence.

Run verification:

```bash
python3 -m unittest discover "linealert/tests"
```
