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

## Cycle Context

Cycle Context organizes events and evidence into complete machine cycles:

```text
Cycle
├── Events
├── Relationships
├── Measurements
├── Evidence
└── Status
```

### Cycle File Tree

```text
linealert/cycles/
├── __init__.py
├── cycle.py
├── cycle_builder.py
├── history.py
└── timeline.py

linealert/tests/
└── test_cycles.py
```

### Cycle Status

Cycle status is derived strictly from baseline-relative measurements:

- `Healthy`: measurements are within baseline limits.
- `Monitor`: measurements have moderate deviation.
- `OutOfBaseline`: measurements exceed baseline limits or required
  relationship measurements are absent.

No maintenance recommendations, diagnoses, or root-cause classifications are
generated by cycle context.

### Example Cycle Object

```json
{
  "cycle_id": 1,
  "start_timestamp": "2026-06-14T10:00:00+00:00",
  "end_timestamp": "2026-06-14T10:00:05.300000+00:00",
  "duration_ms": 5300.0,
  "status": "OutOfBaseline",
  "events": ["CycleStart", "ProductDetected", "PrintComplete"],
  "measurements": [
    {
      "name": "Tamp Extension Lag",
      "metric": "lag_ms",
      "observed_ms": 1100.0,
      "baseline_ms": 600.0,
      "deviation_percent": 83.333,
      "status": "OutOfBaseline"
    }
  ],
  "evidence": [
    {
      "cycle_id": 1,
      "relationship": "Tamp Extension Lag",
      "measurement": "lag_ms",
      "observed_ms": 1100.0,
      "baseline_ms": 600.0,
      "deviation_percent": 83.333,
      "status": "OutOfBaseline"
    }
  ]
}
```

### Example Cycle Timeline

```text
Cycle 1

00.000 CycleStart
01.100 ProductDetected
02.200 PrintComplete
03.000 TampExtendCommand
03.600 TampExtendedSensor
04.300 TampHomeSensor
04.800 CycleComplete
```

### Cycle History

`CycleHistory` supports:

- last N cycles
- average cycle duration
- average relationship lag
- trend direction and slope over cycles

## Machine Topology

Machine Topology represents component structure independently from timing
relationships, state context, cycle context, and evidence:

```text
Machine
├── Components
├── Connections
├── Dependencies
└── Topology

Events
↓
Machine State Context
↓
Cycles
↓
Relationships
↓
Evidence
↓
Topology Context
```

Topology provides structural context only.

### Topology File Tree

```text
config/
└── topology.json

linealert/topology/
├── __init__.py
├── component.py
├── dependency.py
├── report.py
├── topology.py
└── validator.py

linealert/tests/
├── test_machine_topology.py
└── test_topology.py
```

### Example Topology JSON

```json
{
  "components": [
    {
      "component_id": "product_sensor",
      "name": "Product Sensor",
      "type": "Sensor"
    },
    {
      "component_id": "print_head",
      "name": "Print Head",
      "type": "Actuator"
    },
    {
      "component_id": "tamp_cylinder",
      "name": "Tamp Cylinder",
      "type": "Actuator"
    },
    {
      "component_id": "tamp_sensor",
      "name": "Tamp Extended Sensor",
      "type": "Sensor"
    }
  ],
  "dependencies": [
    ["product_sensor", "print_head"],
    ["print_head", "tamp_cylinder"],
    ["tamp_cylinder", "tamp_sensor"]
  ],
  "event_component_map": {
    "ProductDetected": "product_sensor",
    "PrintComplete": "print_head",
    "TampExtendCommand": "tamp_cylinder",
    "TampExtendedSensor": "tamp_sensor"
  }
}
```

### Example Validation Report

```json
{
  "component_count": 4,
  "dependency_count": 3,
  "missing_components": [],
  "orphan_components": [],
  "circular_dependencies": [],
  "disconnected_chains": [],
  "events_mapped_to_unknown_components": {},
  "observations": []
}
```

Topology validation detects structural observations only:

- missing components
- orphan components
- circular dependencies
- disconnected chains
- events mapped to unknown components

### Example Topology Visualization

```text
Product Sensor
  ↓
Print Head
  ↓
Tamp Cylinder
  ↓
Tamp Extended Sensor
```

### Example Topology-Aware Evidence Record

Topology context is attached outside the cycle and anomaly engines:

```json
{
  "cycle_id": 42,
  "machine_state": "Production",
  "relationship": "Tamp Extension Lag",
  "component_id": "tamp_cylinder",
  "component_name": "Tamp Cylinder",
  "observed_ms": 1100,
  "baseline_ms": 600,
  "status": "OutOfBaseline",
  "upstream_components": ["print_head"],
  "downstream_components": ["tamp_sensor"]
}
```
