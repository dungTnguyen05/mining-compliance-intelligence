# load grounded AI incident findings into PostgreSQL

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ai_incident_analysis import (
    DEFAULT_OUTPUT_PATH,
    IncidentAnalysisError,
    parse_finding,
    read_jsonl,
    validate_finding,
)
from load_data import create_schema, get_connection


UPSERT_FINDING_SQL = """
    INSERT INTO incident_ai_findings (
        source_record_hash,
        primary_hazard_domain,
        secondary_hazard_domains,
        event_mechanism,
        psychosocial_hazard,
        psychosocial_types,
        severity_consistency,
        suggested_severity,
        category_evidence_quote,
        severity_evidence_quote,
        explanation,
        response_id,
        model,
        processed_at,
        attempts
    )
    VALUES (
        %(source_record_hash)s,
        %(primary_hazard_domain)s,
        %(secondary_hazard_domains)s,
        %(event_mechanism)s,
        %(psychosocial_hazard)s,
        %(psychosocial_types)s,
        %(severity_consistency)s,
        %(suggested_severity)s,
        %(category_evidence_quote)s,
        %(severity_evidence_quote)s,
        %(explanation)s,
        %(response_id)s,
        %(model)s,
        %(processed_at)s,
        %(attempts)s
    )
    ON CONFLICT (source_record_hash)
    DO UPDATE SET
        primary_hazard_domain = EXCLUDED.primary_hazard_domain,
        secondary_hazard_domains = EXCLUDED.secondary_hazard_domains,
        event_mechanism = EXCLUDED.event_mechanism,
        psychosocial_hazard = EXCLUDED.psychosocial_hazard,
        psychosocial_types = EXCLUDED.psychosocial_types,
        severity_consistency = EXCLUDED.severity_consistency,
        suggested_severity = EXCLUDED.suggested_severity,
        category_evidence_quote = EXCLUDED.category_evidence_quote,
        severity_evidence_quote = EXCLUDED.severity_evidence_quote,
        explanation = EXCLUDED.explanation,
        response_id = EXCLUDED.response_id,
        model = EXCLUDED.model,
        processed_at = EXCLUDED.processed_at,
        attempts = EXCLUDED.attempts,
        updated_at = NOW()
"""


def require_mapping(
    record: Mapping[str, Any],
    field: str,
    position: int,
) -> Mapping[str, Any]:
    """return one required object field from an artifact"""
    value = record.get(field)

    if not isinstance(value, Mapping):
        raise IncidentAnalysisError(
            f"AI finding {position} has no valid {field} object"
        )

    return value


def prepare_finding_parameters(
    record: Mapping[str, Any],
    position: int,
) -> dict[str, Any]:
    """validate one artifact and prepare its database parameters"""
    source = require_mapping(record, "source", position)
    raw_finding = require_mapping(record, "finding", position)
    provenance = require_mapping(record, "provenance", position)

    finding = parse_finding(
        json.dumps(raw_finding, ensure_ascii=False)
    )
    validate_finding(finding, source)

    required_source_fields = (
        "record_hash",
        "incident_id",
        "description",
        "severity",
    )
    missing_source_fields = [
        field for field in required_source_fields
        if not source.get(field)
    ]

    if missing_source_fields:
        missing = ", ".join(missing_source_fields)
        raise IncidentAnalysisError(
            f"AI finding {position} is missing source fields: {missing}"
        )

    required_provenance_fields = (
        "model",
        "processed_at",
        "attempts",
    )
    missing_provenance_fields = [
        field for field in required_provenance_fields
        if provenance.get(field) is None
    ]

    if missing_provenance_fields:
        missing = ", ".join(missing_provenance_fields)
        raise IncidentAnalysisError(
            f"AI finding {position} is missing provenance fields: {missing}"
        )

    return {
        "source_record_hash": source["record_hash"],
        **finding,
        "response_id": provenance.get("response_id"),
        "model": provenance["model"],
        "processed_at": provenance["processed_at"],
        "attempts": int(provenance["attempts"]),
    }


def load_finding_records(path: Path) -> list[dict[str, Any]]:
    """read and validate all saved AI findings"""
    records = read_jsonl(path)

    return [
        prepare_finding_parameters(record, position)
        for position, record in enumerate(records, start=1)
    ]


def upsert_findings(
    connection: Any,
    findings: Sequence[Mapping[str, Any]],
) -> int:
    """upsert validated findings linked to loaded incidents"""
    try:
        with connection.cursor() as cursor:
            for finding in findings:
                cursor.execute(
                    """
                    SELECT 1
                    FROM incidents
                    WHERE source_record_hash = %s
                    """,
                    (finding["source_record_hash"],),
                )

                if cursor.fetchone() is None:
                    raise IncidentAnalysisError(
                        "no loaded incident matches source record hash "
                        f"{finding['source_record_hash']}; "
                        "run pipeline/load_data.py first"
                    )

                cursor.execute(UPSERT_FINDING_SQL, finding)

        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return len(findings)


def build_parser() -> argparse.ArgumentParser:
    """build command line options for loading AI findings"""
    parser = argparse.ArgumentParser(
        description="load grounded AI incident findings into PostgreSQL"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="path to the AI findings JSONL artifact",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """validate and upsert the available AI findings"""
    args = build_parser().parse_args(argv)
    connection = get_connection()

    try:
        create_schema(connection)
        findings = load_finding_records(args.input)
        loaded_count = upsert_findings(connection, findings)
        print(f"loaded {loaded_count} AI incident findings")

        return 0
    except (IncidentAnalysisError, OSError, ValueError) as error:
        print(f"error: {error}")

        return 1
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
