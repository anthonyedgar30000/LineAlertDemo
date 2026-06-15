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

## Relationship Integrity Validation

Relationship Integrity Validation compares the expected coordination model
against event relationships observed inside cycles:

```text
Events
↓
Cycles
↓
Relationships
↓
Baselines
↓
Topology
↓
Configuration Provenance
↓
Situation Assessment
```

This layer reports relationship observations only.

### Relationship Integrity File Tree

```text
config/
└── relationship_integrity.json

linealert/relationships/
├── __init__.py
├── expected_map.py
├── observed_map.py
├── relationship_model.py
├── report.py
└── validator.py

linealert/tests/
└── test_relationship_integrity.py
```

### Example Relationship Integrity Config

```json
{
  "relationships": [
    {
      "source": "TampExtendCommand",
      "target": "TampExtendedSensor",
      "required": true
    },
    {
      "source": "PrintComplete",
      "target": "TampExtendCommand",
      "required": true
    }
  ]
}
```

### Example Relationship Integrity Report

```json
{
  "expected_relationship_count": 3,
  "observed_cycle_count": 4,
  "valid_observation_count": 8,
  "missing_required_relationships": [
    {
      "observation_type": "MissingRequiredRelationship",
      "relationship": "TampExtendCommand->TampExtendedSensor",
      "source": "TampExtendCommand",
      "target": "TampExtendedSensor",
      "required": true,
      "cycle_id": 1,
      "details": "Required relationship TampExtendCommand->TampExtendedSensor was not observed in cycle 1; missing event(s): TampExtendedSensor."
    }
  ],
  "order_violations": [],
  "observation_count": 1,
  "integrity_status": "Observations Present"
}
```

No diagnosis, root-cause determination, corrective action, or maintenance
recommendation is generated by Relationship Integrity Validation.

## Dependency Chain Analysis

Dependency Chain Analysis models machine behavior as ordered dependency paths.
It identifies direct dependencies, transitive dependencies, dependency chain
disruptions, and path health from observed cycle timelines.

```text
Events
↓
Cycles
↓
Relationships
↓
Baselines
↓
Topology
↓
Configuration Provenance
↓
Relationship Integrity
↓
Situation Assessment
```

This layer reports chain observations only.

### Dependency Chain File Tree

```text
config/
└── dependency_chains.json

linealert/dependencies/
├── __init__.py
├── chain_validator.py
├── dependency_chain.py
├── dependency_graph.py
├── path_health.py
└── report.py

linealert/tests/
└── test_dependency_chains.py
```

### Example Dependency Chain Config

```json
{
  "chains": [
    [
      "ProductDetected",
      "PrintComplete",
      "TampExtendCommand",
      "TampExtendedSensor",
      "TampHomeSensor",
      "CycleComplete"
    ]
  ]
}
```

### Example Dependency Chain Report

```json
{
  "dependency_graph": {
    "nodes": [
      "CycleComplete",
      "PrintComplete",
      "ProductDetected",
      "TampExtendCommand",
      "TampExtendedSensor",
      "TampHomeSensor"
    ],
    "direct_edges": [
      {
        "source": "ProductDetected",
        "target": "PrintComplete"
      }
    ]
  },
  "validation": {
    "chain_count": 1,
    "observed_cycle_count": 4,
    "path_health": [
      {
        "chain_id": "chain_1",
        "healthy_cycles": 0,
        "disrupted_cycles": 4,
        "percent_healthy": 0.0,
        "status": "Disrupted"
      }
    ],
    "observation_count": 4,
    "integrity_status": "Disruptions Observed"
  }
}
```

No diagnosis, root-cause determination, corrective action, or maintenance
recommendation is generated by Dependency Chain Analysis.

## Evidence Fusion

Evidence Fusion aggregates observations from independent evidence-producing
systems while preserving provenance for every supporting item.

```text
Events
↓
Cycles
↓
Relationships
↓
Baselines
↓
Topology Integrity
↓
Configuration Provenance
↓
Relationship Integrity
↓
Dependency Chains
↓
Situation Assessment
```

Evidence Fusion is observation-only. It does not invent observations, diagnose,
infer root cause, recommend maintenance, choose corrective actions, or perform
AI reasoning.

### Evidence Fusion File Tree

```text
linealert/evidence/
├── __init__.py
├── evidence_collection.py
├── evidence_fusion.py
├── evidence_item.py
├── evidence_score.py
└── report.py

linealert/tests/
└── test_evidence_fusion.py
```

### Example Evidence Item

```json
{
  "source": "Baseline Analysis",
  "observation": "Tamp lag exceeded baseline",
  "severity": "Monitor",
  "confidence": 0.95,
  "timestamp": "2026-06-14T10:02:00Z",
  "cycle_id": 7,
  "source_evidence": {
    "relationship": "Tamp Extension Lag",
    "measured_ms": 1100,
    "baseline_ms": 600
  },
  "cluster": "Tamp Operation Deviation"
}
```

### Example Evidence Fusion JSON

```json
{
  "evidence_count": 3,
  "evidence_density": 3,
  "source_distribution": {
    "Baseline Analysis": 1,
    "Dependency Chain": 1,
    "Relationship Integrity": 1
  },
  "sources_contributing": 3,
  "observation_clusters": [
    {
      "cluster": "Tamp Operation Deviation",
      "evidence_count": 3,
      "sources_contributing": 3,
      "supporting_evidence": [
        {
          "source": "Baseline Analysis",
          "observation": "Tamp lag exceeded baseline",
          "timestamp": "2026-06-14T10:02:00Z",
          "cycle_id": 7
        }
      ]
    }
  ]
}
```

### Human-Readable Evidence Summary

```text
EVIDENCE SUMMARY

Observation Cluster:
Tamp Operation Deviation

Supporting Evidence:

Baseline Analysis:
- Tamp lag exceeded baseline

Dependency Chain:
- Dependency chain broken

Relationship Integrity:
- Missing required relationship

Evidence Density:
3 observations

Sources Contributing:
3
```

## Historical Context

Historical Context preserves observations across cycles and reports observed
history patterns without diagnosis, root-cause analysis, recommendations,
corrective actions, AI reasoning, or predictions.

```text
Events
↓
Cycles
↓
Relationships
↓
Dependency Chains
↓
Baselines
↓
Topology Integrity
↓
Configuration Provenance
↓
Evidence Collection
↓
Evidence Fusion
↓
Situation Assessment
```

### Historical Context File Tree

```text
linealert/history/
├── __init__.py
├── drift_tracker.py
├── observation_history.py
├── persistence.py
├── report.py
└── trend_tracker.py

linealert/tests/
└── test_history.py
```

### Stored Historical Fields

Historical observations preserve:

- cycle id
- timestamp
- observation
- evidence cluster
- severity
- confidence
- source systems
- source evidence

### Example Historical Context JSON

```json
{
  "cycles_observed": [10, 12, 15, 18],
  "observation_summaries": [
    {
      "observation": "Tamp Extension Lag Exceeded Baseline",
      "cycles": [10, 12, 15, 18],
      "occurrences": 4,
      "persistence_cycles": 1,
      "recurrence_count": 4,
      "severity_history": [
        "Monitor",
        "Monitor",
        "Monitor",
        "Significant Deviation"
      ],
      "source_systems": ["Baseline Analysis"]
    }
  ],
  "evidence_density_trend": {
    "density_by_cycle": {
      "10": 1,
      "12": 2,
      "15": 1,
      "18": 2
    },
    "direction": "Increasing"
  },
  "historical_drift_indicators": [
    {
      "metric_name": "Average Tamp Lag",
      "start_cycle": 1,
      "end_cycle": 60,
      "start_value": 600,
      "end_value": 1100,
      "direction": "Increasing",
      "status": "Historical Increase Detected"
    }
  ]
}
```

### Human-Readable Historical Context

```text
HISTORICAL CONTEXT

Observation:
Tamp Extension Lag Exceeded Baseline

Occurrences:
4

Persistence:
1 consecutive cycles

Evidence Density Trend:
Increasing

Historical Drift:
Observed increasing from 600ms to 1100ms
Historical Increase Detected

No diagnosis or root-cause determination performed.
No maintenance recommendations generated.
No predictions generated.
```

## Structured Troubleshooting Workflows

Structured Troubleshooting Workflows represent guide content as deterministic
decision trees:

```text
Symptom
↓
Check
↓
Action
↓
Validation
↓
Escalation
```

This layer executes the workflow structure shown in troubleshooting guides. It
does not create recommendations, diagnoses, root-cause statements, AI reasoning,
or inferred corrective actions.

### Workflow File Tree

```text
config/
└── labeling_decision_trees.json

linealert/workflows/
├── __init__.py
├── decision_tree.py
├── engine.py
├── loader.py
└── report.py

linealert/tests/
└── test_workflows.py
```

### Example Workflow JSON

```json
{
  "workflow_id": "label_alignment_off",
  "symptom": "Label Alignment is Off",
  "steps": [
    {
      "check": "Peel tip square to bottle?",
      "actions": ["Adjust Peel Angle"],
      "validation": "Run product and verify label placement after this action."
    }
  ],
  "related_workflows_if_unresolved": ["bubbles_on_labels"],
  "escalation_conditions": [
    "Issue continues after all checks and actions."
  ]
}
```

### Example Workflow Report

```text
STRUCTURED TROUBLESHOOTING WORKFLOW

Reported Symptom: "Bubbles"

Matched Symptom: Bubbles on Labels

Workflow Steps:
1. Check:
   Enough pressure time?
   Action Steps:
   - Increase Aligner Run-On
   Validation:
   Run product and verify label adhesion after this action.

If Unresolved, Review Related Workflows:
- label_alignment_off

Escalation Conditions:
- Issue continues after all checks and actions.
```

## Observation Confidence

Observation Confidence evaluates the strength and trustworthiness of
observations using explicit evidence-based factors.

```text
Events
↓
Cycles
↓
Relationships
↓
Dependency Chains
↓
Baseline Analysis
↓
Topology Integrity
↓
Configuration Provenance
↓
Evidence Collection
↓
Evidence Fusion
↓
Historical Context
↓
Situation Assessment
```

Confidence is observation-only. It does not diagnose, infer root cause,
recommend maintenance, choose corrective actions, predict outcomes, or perform
AI reasoning.

### Observation Confidence File Tree

```text
linealert/confidence/
├── __init__.py
├── confidence_engine.py
├── confidence_model.py
├── factors.py
├── report.py
└── scoring.py

linealert/tests/
└── test_confidence.py
```

### Confidence Factors

The confidence engine emits explicit factors:

- Supporting Evidence
- Historical Persistence
- Multi-Source Confirmation
- Topology Validation
- Configuration Validity

### Confidence Classifications

- Very Low
- Low
- Moderate
- High
- Very High

### Example Confidence JSON

```json
{
  "observation": "Tamp Extension Lag Exceeded Baseline",
  "confidence": 0.95,
  "classification": "Very High",
  "factors": [
    {
      "name": "Supporting Evidence",
      "description": "6 supporting evidence item(s) across 2 observation cluster(s)",
      "contribution": 0.22
    },
    {
      "name": "Historical Persistence",
      "description": "Observed across 42 occurrence(s); 12 consecutive cycle(s); 42 recurrence observation(s)",
      "contribution": 0.2
    },
    {
      "name": "Multi-Source Confirmation",
      "description": "3 supporting evidence source(s)",
      "contribution": 0.2
    },
    {
      "name": "Topology Validation",
      "description": "Topology=Valid; RelationshipIntegrity=Valid; DependencyChains=Healthy",
      "contribution": 0.15
    },
    {
      "name": "Configuration Validity",
      "description": "BaselineValid=True; ConfigurationProvenance=Valid; ConfigurationDriftPresent=False",
      "contribution": 0.15
    }
  ]
}
```

### Human-Readable Confidence Report

```text
OBSERVATION CONFIDENCE

Observation:
Tamp Extension Lag Exceeded Baseline

Confidence:
0.950

Classification:
Very High

Supporting Factors:
- 6 supporting evidence item(s) across 2 observation cluster(s)
- Observed across 42 occurrence(s); 12 consecutive cycle(s); 42 recurrence observation(s)
- 3 supporting evidence source(s)
- Topology=Valid; RelationshipIntegrity=Valid; DependencyChains=Healthy
- BaselineValid=True; ConfigurationProvenance=Valid; ConfigurationDriftPresent=False

No diagnosis or root-cause determination performed.
No maintenance recommendations generated.
No predictions generated.
```
