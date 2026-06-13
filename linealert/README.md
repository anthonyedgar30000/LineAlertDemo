# LineAlert

LineAlert is an evidence-first industrial troubleshooting system. The MVP reads
machine event data from CSV files, calculates timing relationships between
events, compares those observations against a baseline, reasons over machine
topology, applies deterministic rules, and writes a plain text report.

This starter project intentionally excludes:

- Machine learning or AI components
- Web dashboards or UI code
- Database integration
- Network services

## Architecture Principles

LineAlert keeps each stage separate:

1. **Evidence collection** (`event_loader.py`)
   - Load CSV event data
   - Validate the required `timestamp,event_name` structure
   - Return normalized, timestamp-sorted events
2. **Timing evidence** (`timing_engine.py`)
   - Calculate event-to-event lag
   - Calculate repeated-event cycle timing
   - Produce timing observations and aggregate metrics
3. **Drift evidence** (`drift_engine.py`)
   - Compare timing observations against a JSON baseline
   - Calculate drift values
   - Flag threshold violations
4. **Topology reasoning** (`topology_engine.py`)
   - Load machine dependency relationships from YAML
   - Build a directed graph
   - Determine upstream and downstream dependencies
   - Identify the first dependency edge where drift appears
5. **Deterministic interpretation** (`expert_system.py`)
   - Load YAML troubleshooting rules
   - Match drift evidence to rule conditions
   - Produce candidate causes and recommended checks
6. **Text output** (`report_generator.py`)
   - Generate a human-readable report with observations, drift findings,
     topology findings, candidate causes, and recommended checks

## Project Structure

```text
linealert/
├── data/
│   ├── sample_events.csv
│   ├── baseline.json
│   └── topology.yaml
├── rules/
│   └── troubleshooting_rules.yaml
├── src/
│   ├── event_loader.py
│   ├── timing_engine.py
│   ├── drift_engine.py
│   ├── topology_engine.py
│   ├── expert_system.py
│   ├── report_generator.py
│   └── main.py
├── output/
│   └── report.txt
├── tests/
├── requirements.txt
└── README.md
```

## Input Formats

### Event CSV

```csv
timestamp,event_name
2026-01-01T00:00:00Z,PrintComplete
2026-01-01T00:00:01Z,TampRequest
```

### Baseline JSON

```json
{
  "observations": {
    "lag:TampExtend->ProductTransfer": {
      "expected_seconds": 3.0,
      "threshold_seconds": 1.0
    }
  }
}
```

### Topology YAML

```yaml
dependencies:
  - from: "PrintComplete"
    to: "TampRequest"
  - from: "TampRequest"
    to: "TampExtend"
  - from: "TampExtend"
    to: "ProductTransfer"
```

When `PrintComplete -> TampRequest` and `TampRequest -> TampExtend` are normal
but `TampExtend -> ProductTransfer` is delayed, the topology engine reports:

```text
Likely Fault Region: TampExtend subsystem
Reason: Delay first appears after TampExtend.
```

### Rule YAML

```yaml
rules:
  - issue: "Product transfer is delayed after tamp extension"
    conditions:
      all:
        - observation_key: "lag:TampExtend->ProductTransfer"
          direction: "high"
          min_drift_seconds: 1.0
    recommendations:
      - "Inspect the TampExtend subsystem for incomplete extension or slow retract clearance."
```

## Run the Sample Pipeline

From the repository root:

```bash
cd linealert
python3 -m pip install -r requirements.txt
python3 src/main.py
```

The generated report is written to:

```text
linealert/output/report.txt
```

## Run Tests

```bash
cd linealert
python3 -m unittest discover tests
```
