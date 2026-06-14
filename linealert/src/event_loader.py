"""Load and normalize machine event data.

The loader is the first evidence boundary in LineAlert. It performs only
structural validation and normalization. It does not infer causes or recommend
actions; later pipeline stages consume its normalized event evidence.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REQUIRED_COLUMNS = ("timestamp", "event_name")


@dataclass(frozen=True)
class Event:
    """A normalized machine event.

    Attributes:
        timestamp: Timezone-aware event timestamp.
        event_name: Normalized event name from the source file.
        source_row: One-based data row number from the CSV file, excluding the
            header. This keeps observations traceable to source evidence.
    """

    timestamp: datetime
    event_name: str
    source_row: int


def load_events(csv_path: str | Path) -> list[Event]:
    """Load, validate, and normalize events from a CSV file.

    The expected CSV format is:

        timestamp,event_name

    Timestamps must be ISO-8601 compatible. A trailing ``Z`` is treated as UTC.
    Naive timestamps are accepted and normalized to UTC so starter datasets can
    stay simple and deterministic.
    """

    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Event CSV not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        _validate_columns(reader.fieldnames)

        events = [
            _event_from_row(row=row, source_row=index)
            for index, row in enumerate(reader, start=1)
        ]

    if not events:
        raise ValueError(f"Event CSV contains no events: {path}")

    return sorted(events, key=lambda event: (event.timestamp, event.source_row))


def _validate_columns(fieldnames: Iterable[str] | None) -> None:
    if fieldnames is None:
        raise ValueError("Event CSV is missing a header row")

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing_columns:
        missing = ", ".join(missing_columns)
        expected = ", ".join(REQUIRED_COLUMNS)
        raise ValueError(f"Event CSV missing columns: {missing}. Expected: {expected}")


def _event_from_row(row: dict[str, str], source_row: int) -> Event:
    raw_timestamp = (row.get("timestamp") or "").strip()
    event_name = (row.get("event_name") or "").strip()

    if not raw_timestamp:
        raise ValueError(f"Row {source_row}: timestamp is required")
    if not event_name:
        raise ValueError(f"Row {source_row}: event_name is required")

    return Event(
        timestamp=_parse_timestamp(raw_timestamp, source_row),
        event_name=event_name,
        source_row=source_row,
    )


def _parse_timestamp(raw_timestamp: str, source_row: int) -> datetime:
    normalized = raw_timestamp.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(
            f"Row {source_row}: invalid ISO-8601 timestamp {raw_timestamp!r}"
        ) from exc

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)
