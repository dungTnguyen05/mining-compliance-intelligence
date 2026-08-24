# test AI finding database preparation without changing PostgreSQL

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

PIPELINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPELINE_DIR))

import load_ai_findings as loader
from ai_incident_analysis import IncidentAnalysisError


def make_artifact() -> dict:
    description = "Worker reported excessive workload caused by understaffing."

    return {
        "source": {
            "record_hash": "a" * 64,
            "incident_id": "INC-1",
            "description": description,
            "severity": "Low",
        },
        "finding": {
            "primary_hazard_domain": "psychosocial",
            "secondary_hazard_domains": [],
            "event_mechanism": "workload_or_fatigue",
            "psychosocial_hazard": True,
            "psychosocial_types": ["job_demands"],
            "severity_consistency": "insufficient_context",
            "suggested_severity": "Not assessed",
            "category_evidence_quote": "excessive workload",
            "severity_evidence_quote": None,
            "explanation": (
                "Explicit workload pressure is described. The description does "
                "not provide enough information to assess severity."
            ),
        },
        "provenance": {
            "response_id": "response-1",
            "model": "test-model",
            "processed_at": "2026-08-24T00:00:00+00:00",
            "attempts": 1,
        },
    }


class FindingLoaderTests(unittest.TestCase):
    def test_prepares_validated_database_parameters(self):
        parameters = loader.prepare_finding_parameters(
            make_artifact(),
            1,
        )

        self.assertEqual(parameters["source_record_hash"], "a" * 64)
        self.assertEqual(parameters["psychosocial_types"], ["job_demands"])
        self.assertEqual(parameters["model"], "test-model")

    def test_accepts_reused_finding_with_zero_attempts(self):
        artifact = make_artifact()
        artifact["provenance"]["attempts"] = 0

        parameters = loader.prepare_finding_parameters(artifact, 1)

        self.assertEqual(parameters["attempts"], 0)

    def test_rejects_negative_attempts(self):
        artifact = make_artifact()
        artifact["provenance"]["attempts"] = -1

        with self.assertRaisesRegex(
            IncidentAnalysisError,
            "cannot have negative attempts",
        ):
            loader.prepare_finding_parameters(artifact, 1)

    def test_rejects_ungrounded_artifact(self):
        artifact = make_artifact()
        artifact["finding"]["category_evidence_quote"] = "invented quote"

        with self.assertRaisesRegex(
            IncidentAnalysisError,
            "exact substring",
        ):
            loader.prepare_finding_parameters(artifact, 1)

    def test_loads_every_jsonl_record(self):
        artifact = make_artifact()

        with TemporaryDirectory() as directory:
            path = Path(directory) / "findings.jsonl"
            path.write_text(
                f"{json.dumps(artifact)}\n{json.dumps(artifact)}\n",
                encoding="utf-8",
            )

            findings = loader.load_finding_records(path)

        self.assertEqual(len(findings), 2)


if __name__ == "__main__":
    unittest.main()
