# LineAlert

LineAlert is an evidence-first industrial troubleshooting system. The MVP reads
machine event data from CSV files, calculates timing relationships between
events, compares those observations against a baseline, reasons over machine
topology, applies deterministic rules, ranks candidate explanations, and writes
a plain text report.

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
   - Produce rule matches and recommended checks
6. **Hypothesis ranking** (`hypothesis_engine.py`)
   - Generate ranked candidate explanations
   - Apply deterministic, weighted scoring
   - Explain every awarded score with traceable evidence
7. **Text output** (`report_generator.py`)
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
│   ├── troubleshooting_rules.yaml
│   └── labeling_guide.yaml
├── src/
│   ├── event_loader.py
│   ├── timing_engine.py
│   ├── drift_engine.py
│   ├── topology_engine.py
│   ├── expert_system.py
│   ├── hypothesis_engine.py
│   ├── report_generator.py
│   └── main.py
├── output/
│   ├── report.txt
│   └── sample_labeling_interaction.txt
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
    hypotheses:
      - name: "Cylinder sticking"
        observation_key: "lag:TampExtend->ProductTransfer"
        fault_region: "TampExtend subsystem"
        score_weights:
          rule_match: 30
          threshold_violation: 20
          drift_severity: 20
          topology_region_match: 20
          timing_sample_support: 10
```

### Labeling Guide Knowledge Base

`rules/labeling_guide.yaml` is a deterministic expert-system knowledge base
extracted from the provided Labeling Troubleshooting Guide image. It can be
loaded with the same `expert_system.load_rules()` function as timing rules.

The guide rules capture:

- symptoms
- visual examples
- checks
- actions
- key points
- related issues
- escalation conditions
- key adjustment areas

Example guide rule:

```yaml
rules:
  - id: "label_alignment_off"
    issue: "Label Alignment is Off"
    symptom:
      name: "Label Alignment is Off"
      aliases:
        - "Label alignment off"
      examples:
        - "Crooked label"
        - "Rotated label"
    checks:
      - "Peel tip square to bottle?"
      - "Is bottle stable during application?"
    actions:
      - "Adjust Peel Angle"
      - "Adjust Hold Down"
    related_issues:
      - symptom_id: "bubbles_on_labels"
        symptom: "Bubbles on Labels"
        reason: "Insufficient pressure time or unstable contact can create both bubbles and alignment errors."
    escalation_conditions:
      - "Issue continues after all adjustments."
      - "Need replacement parts."
    key_adjustment_areas:
      - area: "Peel Angle"
        purpose: "Peel plate angle setting"
```

Guide-only rules do not contain drift conditions, so they are not automatically
matched by the timing pipeline. They are intended to power deterministic
check/action workflows for observed labeling symptoms.

Example deterministic query:

```python
from expert_system import format_guide_response, load_rules, query_labeling_guide

rules = load_rules("rules/labeling_guide.yaml")
response = query_labeling_guide(rules, "Label alignment is off")
print(format_guide_response("Label alignment is off", response))
```

Sample output is stored at:

```text
linealert/output/sample_labeling_interaction.txt
```

The hypothesis engine only awards points when matching evidence exists:

- `rule_match`: the expert rule conditions matched drift evidence
- `threshold_violation`: the linked drift finding violated its threshold
- `drift_severity`: drift magnitude relative to the threshold, capped at 1.0
- `topology_region_match`: topology first-drift region matches the hypothesis
- `timing_sample_support`: timing metric has repeat observations

Example candidate cause output:

```text
1. Cylinder sticking
   Confidence: High

2. Air pressure issue
   Confidence: Medium

3. Sensor fault
   Confidence: Low
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
