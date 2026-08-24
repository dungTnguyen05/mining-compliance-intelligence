# test grounded incident analysis without external API calls

from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

PIPELINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPELINE_DIR))

import ai_incident_analysis as analysis

def make_incident() -> dict:
    return {
        "incident_id": "INC-2025-127",
        "incident_date": "2025-07-08",
        "location": "Open Cut - South Pit",
        "type_code": "OTH",
        "severity": "Low",
        "description": (
            "Operator raised concerns about repeated verbal abuse from supervisor "
            "over several weeks, feeling anxious before shift."
        ),
        "source_row": 16,
        "source_record_hash": "a" * 64,
    }

def make_finding() -> dict:
    return {
        "primary_hazard_domain": "psychosocial",
        "secondary_hazard_domains": [],
        "event_mechanism": "bullying_or_harmful_behavior",
        "psychosocial_hazard": True,
        "psychosocial_types": [
            "bullying",
            "conflict_or_poor_workplace_relationships",
        ],
        "severity_consistency": "insufficient_context",
        "suggested_severity": "Not assessed",
        "category_evidence_quote": (
            "repeated verbal abuse from supervisor over several weeks"
        ),
        "severity_evidence_quote": None,
        "explanation": "The description reports repeated harmful behavior.",
    }

class IncidentLoadingTests(unittest.TestCase):
    def test_loads_all_incidents_and_preserves_source_row(self):
        incidents = analysis.load_incidents()
        incident = analysis.find_incident(incidents, "INC-2025-127")

        self.assertEqual(len(incidents), 42)
        self.assertEqual(incident["source_row"], 16)
        self.assertEqual(len(incident["source_record_hash"]), 64)

    def test_raw_source_hash_is_stable_and_sensitive_to_changes(self):
        record = {
            "incident_id": "INC-1",
            "description": "original description",
        }

        first_hash = analysis.hash_source_record(
            record,
            ("incident_id", "description"),
        )
        second_hash = analysis.hash_source_record(
            record,
            ("incident_id", "description"),
        )

        changed_record = {
            **record,
            "description": "changed description",
        }
        changed_hash = analysis.hash_source_record(
            changed_record,
            ("incident_id", "description"),
        )

        self.assertEqual(first_hash, second_hash)
        self.assertNotEqual(first_hash, changed_hash)

    def test_model_input_contains_only_required_analysis_fields(self):
        model_input = analysis.build_model_input(make_incident())

        self.assertEqual(
            model_input,
            {
                "recorded_type_code": "OTH",
                "recorded_severity": "Low",
                "description": make_incident()["description"],
            },
        )

class PromptTests(unittest.TestCase):
    def test_defines_severity_field_relationships(self):
        self.assertIn(
            "suggested_severity must equal the\n  recorded severity",
            analysis.SYSTEM_PROMPT,
        )
        self.assertIn(
            "suggested_severity must\n  differ from the recorded severity",
            analysis.SYSTEM_PROMPT,
        )

class FindingValidationTests(unittest.TestCase):
    def test_accepts_grounded_psychosocial_finding(self):
        incident = make_incident()
        finding = analysis.parse_finding(json.dumps(make_finding()))

        analysis.validate_finding(finding, incident)

    def test_rejects_schema_value_outside_taxonomy(self):
        finding = make_finding()
        finding["primary_hazard_domain"] = "workplace_drama"

        with self.assertRaises(analysis.ModelResponseError):
            analysis.parse_finding(json.dumps(finding))

    def test_rejects_invented_evidence(self):
        finding = make_finding()
        finding["category_evidence_quote"] = "invented evidence"

        with self.assertRaisesRegex(
            analysis.ModelResponseError,
            "exact substring",
        ):
            analysis.validate_finding(finding, make_incident())

    def test_insufficient_context_cannot_include_severity_evidence(self):
        finding = make_finding()
        finding["severity_evidence_quote"] = "feeling anxious before shift"

        with self.assertRaisesRegex(
            analysis.ModelResponseError,
            "cannot include severity evidence",
        ):
            analysis.validate_finding(finding, make_incident())

    def test_consistent_severity_requires_evidence(self):
        finding = make_finding()
        finding["severity_consistency"] = "consistent"
        finding["suggested_severity"] = "Low"

        with self.assertRaisesRegex(
            analysis.ModelResponseError,
            "requires grounded severity evidence",
        ):
            analysis.validate_finding(finding, make_incident())

    def test_inconsistent_severity_must_suggest_different_value(self):
        finding = make_finding()
        finding["severity_consistency"] = "appears_inconsistent"
        finding["suggested_severity"] = "Low"
        finding["severity_evidence_quote"] = "feeling anxious before shift"

        with self.assertRaisesRegex(
            analysis.ModelResponseError,
            "suggest a different severity",
        ):
            analysis.validate_finding(finding, make_incident())

    def test_psychosocial_flag_requires_psychosocial_domain(self):
        finding = make_finding()
        finding["primary_hazard_domain"] = "other"

        with self.assertRaisesRegex(
            analysis.ModelResponseError,
            "must include its hazard domain",
        ):
            analysis.validate_finding(finding, make_incident())

    def test_rejects_job_demands_inferred_from_anxiety_alone(self):
        finding = make_finding()
        finding["psychosocial_types"].append("job_demands")

        with self.assertRaisesRegex(
            analysis.ModelResponseError,
            "job demands require explicit evidence",
        ):
            analysis.validate_finding(finding, make_incident())

    def test_accepts_job_demands_with_explicit_workload_evidence(self):
        incident = make_incident()
        incident["description"] = (
            f"{incident['description']} The operator also reported excessive "
            "workload caused by understaffing."
        )
        finding = make_finding()
        finding["psychosocial_types"].append("job_demands")

        analysis.validate_finding(finding, incident)

    def test_accepts_job_demands_with_extended_shift_evidence(self):
        incident = make_incident()
        incident["description"] = (
            "Multiple crews reporting fatigue after extended shifts covering "
            "generator operations and manual restarts during the March power "
            "outage."
        )
        finding = make_finding()
        finding["psychosocial_types"] = ["job_demands"]
        finding["category_evidence_quote"] = "fatigue after extended shifts"

        analysis.validate_finding(finding, incident)

class RetryTests(unittest.TestCase):
    def test_retries_rejected_model_finding(self):
        finding = make_finding()
        provenance = {
            "response_id": "response-1",
            "model": "test-model",
            "processed_at": "2026-08-24T00:00:00+00:00",
        }

        with patch.object(
            analysis,
            "request_finding",
            side_effect=[
                analysis.ModelResponseError("not grounded"),
                (finding, provenance),
            ],
        ):
            result = analysis.analyze_incident(
                object(),
                make_incident(),
                "test-model",
                sleep=lambda _: None,
            )

        self.assertEqual(result["provenance"]["attempts"], 2)
        self.assertEqual(result["source"]["source_row"], 16)

    def test_does_not_retry_configuration_error(self):
        with patch.object(
            analysis,
            "request_finding",
            side_effect=analysis.ConfigurationError("bad configuration"),
        ) as request:
            with self.assertRaises(analysis.ConfigurationError):
                analysis.analyze_incident(
                    object(),
                    make_incident(),
                    "test-model",
                    sleep=lambda _: None,
                )

        self.assertEqual(request.call_count, 1)

class BatchResumeTests(unittest.TestCase):
    def make_distinct_incident(
        self,
        incident_id: str,
        record_hash: str,
    ) -> dict:
        incident = deepcopy(make_incident())
        incident["incident_id"] = incident_id
        incident["source_record_hash"] = record_hash

        return incident

    def make_result(self, incident: dict) -> dict:
        return {
            "source": {
                "record_hash": incident["source_record_hash"],
            },
            "finding": make_finding(),
            "provenance": {
                "model": "test-model",
            },
        }

    def test_resumes_pending_records_and_removes_old_failure(self):
        completed = self.make_distinct_incident("INC-1", "a" * 64)
        pending = self.make_distinct_incident("INC-2", "b" * 64)

        with TemporaryDirectory() as directory:
            output_path = Path(directory) / "findings.jsonl"
            failures_path = Path(directory) / "failures.jsonl"

            analysis.write_jsonl(
                output_path,
                [self.make_result(completed)],
            )
            analysis.write_jsonl(
                failures_path,
                [
                    {
                        "source": {
                            "record_hash": pending["source_record_hash"],
                        },
                        "error": {
                            "type": "RateLimitError",
                            "message": "limited",
                        },
                    }
                ],
            )

            with patch.object(
                analysis,
                "analyze_incident",
                return_value=self.make_result(pending),
            ) as analyze:
                succeeded, failed = analysis.analyze_all(
                    object(),
                    [completed, pending],
                    "test-model",
                    max_attempts=1,
                    input_path=analysis.DEFAULT_INPUT_PATH,
                    output_path=output_path,
                    failures_path=failures_path,
                    request_delay=0,
                    sleep=lambda _: None,
                )

            self.assertEqual(analyze.call_count, 1)
            self.assertEqual(
                analyze.call_args.args[1]["incident_id"],
                "INC-2",
            )
            self.assertEqual(succeeded, 2)
            self.assertEqual(failed, 0)
            self.assertEqual(len(analysis.read_jsonl(output_path)), 2)
            self.assertEqual(analysis.read_jsonl(failures_path), [])

    def test_checkpoints_rate_limit_failure_and_pauses_batch(self):
        first = self.make_distinct_incident("INC-1", "a" * 64)
        second = self.make_distinct_incident("INC-2", "b" * 64)

        class RateLimitError(Exception):
            status_code = 429

        with TemporaryDirectory() as directory:
            output_path = Path(directory) / "findings.jsonl"
            failures_path = Path(directory) / "failures.jsonl"

            with patch.object(
                analysis,
                "analyze_incident",
                side_effect=RateLimitError("limited"),
            ) as analyze:
                succeeded, failed = analysis.analyze_all(
                    object(),
                    [first, second],
                    "test-model",
                    max_attempts=1,
                    input_path=analysis.DEFAULT_INPUT_PATH,
                    output_path=output_path,
                    failures_path=failures_path,
                    request_delay=0,
                    sleep=lambda _: None,
                )

            saved_failures = analysis.read_jsonl(failures_path)

            self.assertEqual(analyze.call_count, 1)
            self.assertEqual(succeeded, 0)
            self.assertEqual(failed, 1)
            self.assertEqual(len(saved_failures), 1)
            self.assertEqual(
                saved_failures[0]["source"]["record_hash"],
                first["source_record_hash"],
            )
            self.assertEqual(analysis.read_jsonl(output_path), [])

if __name__ == "__main__":
    unittest.main()
