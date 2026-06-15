"""JSON persistence for historical observations."""

from __future__ import annotations

import json
from pathlib import Path

from linealert.history.observation_history import HistoricalObservation, ObservationHistory


def save_observation_history(
    history: ObservationHistory,
    output_path: str | Path,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history.as_dict(), indent=2) + "\n", encoding="utf-8")


def load_observation_history(input_path: str | Path) -> ObservationHistory:
    path = Path(input_path)
    raw_history = json.loads(path.read_text(encoding="utf-8"))
    raw_observations = raw_history.get("observations") if isinstance(raw_history, dict) else None
    if not isinstance(raw_observations, list):
        raise ValueError(f"Historical context file missing observations: {path}")

    return ObservationHistory(
        observations=[
            HistoricalObservation(
                cycle_id=int(raw_observation["cycle_id"]),
                timestamp=str(raw_observation["timestamp"]),
                observation=str(raw_observation["observation"]),
                evidence_cluster=str(raw_observation["evidence_cluster"]),
                severity=str(raw_observation["severity"]),
                confidence=float(raw_observation["confidence"]),
                source_systems=[
                    str(source) for source in raw_observation.get("source_systems", [])
                ],
                source_evidence=[
                    dict(evidence)
                    for evidence in raw_observation.get("source_evidence", [])
                    if isinstance(evidence, dict)
                ],
                metadata=(
                    dict(raw_observation.get("metadata") or {})
                    if isinstance(raw_observation, dict)
                    else {}
                ),
            )
            for raw_observation in raw_observations
            if isinstance(raw_observation, dict)
        ]
    )
