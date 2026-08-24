# preserve stable source identity for incident records

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

import pandas as pd


INCIDENT_SOURCE_FIELDS = (
    "incident_id",
    "incident_date",
    "location",
    "type_code",
    "severity",
    "description",
)


def hash_source_record(
    record: Mapping[str, Any],
    columns: Sequence[str] = INCIDENT_SOURCE_FIELDS,
) -> str:
    """return a stable SHA-256 hash of raw source values"""
    source_values = {
        column: None if pd.isna(record[column]) else str(record[column])
        for column in columns
    }
    canonical_record = json.dumps(
        source_values,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(canonical_record.encode("utf-8")).hexdigest()


def add_incident_source_identity(
    incidents: pd.DataFrame,
) -> pd.DataFrame:
    """attach source row and hash before cleaning changes source values"""
    identified_incidents = incidents.copy()
    source_columns = list(identified_incidents.columns)

    identified_incidents["source_row"] = range(
        2,
        len(identified_incidents) + 2,
    )
    identified_incidents["source_record_hash"] = identified_incidents.apply(
        lambda row: hash_source_record(row, source_columns),
        axis=1,
    )

    return identified_incidents
