# prepare incident records for grounded AI analysis

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd
from dotenv import load_dotenv

from clean_data import clean_incident_register


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "incident_register.csv"
SOURCE_FIELDS = (
    "incident_id",
    "incident_date",
    "location",
    "type_code",
    "severity",
    "description",
)


class IncidentAnalysisError(RuntimeError):
    # base exception for expected incident analysis failures
    pass


class ConfigurationError(IncidentAnalysisError):
    # raised when required local configuration is missing
    pass


def get_required_environment(name: str) -> str:
    """return one required non-empty environment value"""
    value = os.getenv(name)

    if not value:
        raise ConfigurationError(f"{name} is not set in .env")

    return value


def load_ai_configuration() -> tuple[str, str, str]:
    """load required AI configuration from the project environment file"""
    load_dotenv(PROJECT_ROOT / ".env")

    return (
        get_required_environment("AI_GATEWAY_API_KEY"),
        get_required_environment("AI_GATEWAY_BASE_URL"),
        get_required_environment("AI_MODEL"),
    )


def hash_source_record(
    record: Mapping[str, Any],
    columns: Sequence[str] = SOURCE_FIELDS,
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


def load_incidents(path: Path = DEFAULT_INPUT_PATH) -> list[dict[str, Any]]:
    """read and clean incidents while preserving raw source identity"""
    raw_incidents = pd.read_csv(path, dtype=str, keep_default_na=False)
    source_columns = list(raw_incidents.columns)

    raw_incidents["source_row"] = range(2, len(raw_incidents) + 2)
    raw_incidents["source_record_hash"] = raw_incidents.apply(
        lambda row: hash_source_record(row, source_columns),
        axis=1,
    )

    cleaned_incidents, _ = clean_incident_register(raw_incidents)

    missing_columns = set(SOURCE_FIELDS) - set(cleaned_incidents.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise IncidentAnalysisError(f"incident register is missing columns: {missing}")

    incidents: list[dict[str, Any]] = []
    for record in cleaned_incidents.to_dict(orient="records"):
        incident_date = record["incident_date"]

        if pd.isna(incident_date):
            raise IncidentAnalysisError(
                f"incident {record['incident_id']} has an invalid incident date"
            )

        record["incident_date"] = incident_date.date().isoformat()
        record["source_row"] = int(record["source_row"])
        incidents.append(record)

    return incidents


def build_model_input(incident: Mapping[str, Any]) -> dict[str, str]:
    """select only fields needed for model analysis"""
    return {
        "recorded_type_code": incident["type_code"],
        "recorded_severity": incident["severity"],
        "description": incident["description"],
    }


def source_metadata(
    incident: Mapping[str, Any],
    input_path: Path = DEFAULT_INPUT_PATH,
) -> dict[str, Any]:
    """attach source identity and a cleaned source snapshot in Python"""
    try:
        source_file = input_path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        source_file = str(input_path.resolve())

    return {
        "file": source_file,
        "source_row": int(incident["source_row"]),
        "record_hash": incident["source_record_hash"],
        **{field: incident[field] for field in SOURCE_FIELDS},
    }
