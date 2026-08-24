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
        "explanation": (
            "The description reports repeated harmful behavior. The description "
            "does not provide enough information to assess severity."
        ),
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
                "description": make_incident()["description"],
            },
        )

class PromptTests(unittest.TestCase):
    def test_deanchors_severity_and_requires_direct_domain_evidence(self):
        self.assertIn(
            "recorded severity is intentionally\nnot supplied",
            analysis.SYSTEM_PROMPT,
        )
        self.assertIn(
            "Do not add a secondary domain",
            analysis.SYSTEM_PROMPT,
        )
        self.assertIn(
            "set severity_consistency to consistent as a placeholder",
            analysis.SYSTEM_PROMPT,
        )
        self.assertIn(
            "First aid or medical treatment can never be assessed as Low",
            analysis.SYSTEM_PROMPT,
        )
        self.assertIn(
            "does not prove that an event was contained",
            analysis.SYSTEM_PROMPT,
        )

        self.assertIn(
            "Do not treat missing injury or damage details as proof",
            analysis.SYSTEM_PROMPT,
        )
        self.assertIn(
            "environmental_threshold_exceedance",
            analysis.EVENT_MECHANISMS,
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
        finding["psychosocial_types"] = [
            "job_demands",
            "work_related_fatigue",
        ]
        finding["category_evidence_quote"] = "fatigue after extended shifts"

        analysis.validate_finding(finding, incident)

    def test_derives_severity_consistency_after_model_response(self):
        finding = make_finding()
        finding["suggested_severity"] = "Low"
        finding["severity_evidence_quote"] = "feeling anxious before shift"

        analysis.derive_severity_consistency(finding, "Medium")

        self.assertEqual(
            finding["severity_consistency"],
            "appears_inconsistent",
        )

    def test_rejects_dropped_object_as_slips_trips_falls(self):
        incident = make_incident()
        incident["description"] = (
            "Dropped object (hand tool) from CHPP walkway, exclusion zone in "
            "place, no injury."
        )
        incident["severity"] = "Medium"
        finding = make_finding()
        finding.update(
            {
                "primary_hazard_domain": "plant_equipment",
                "secondary_hazard_domains": ["slips_trips_falls"],
                "event_mechanism": "dropped_object",
                "psychosocial_hazard": False,
                "psychosocial_types": [],
                "severity_consistency": "consistent",
                "suggested_severity": "Medium",
                "category_evidence_quote": incident["description"],
                "severity_evidence_quote": incident["description"],
            }
        )

        with self.assertRaisesRegex(
            analysis.ModelResponseError,
            "slips_trips_falls requires explicit evidence",
        ):
            analysis.validate_finding(finding, incident)

    def test_rejects_location_as_plant_equipment_evidence(self):
        incident = make_incident()
        incident["description"] = (
            "Operator slipped on wet stairs at wash plant, grazed elbow, "
            "first aid administered."
        )
        incident["severity"] = "Medium"
        finding = make_finding()
        finding.update(
            {
                "primary_hazard_domain": "slips_trips_falls",
                "secondary_hazard_domains": ["plant_equipment"],
                "event_mechanism": "slip_or_trip",
                "psychosocial_hazard": False,
                "psychosocial_types": [],
                "severity_consistency": "consistent",
                "suggested_severity": "Medium",
                "category_evidence_quote": (
                    "Operator slipped on wet stairs at wash plant"
                ),
                "severity_evidence_quote": (
                    "grazed elbow, first aid administered"
                ),
            }
        )

        with self.assertRaisesRegex(
            analysis.ModelResponseError,
            "plant_equipment requires explicit evidence",
        ):
            analysis.validate_finding(finding, incident)

    def test_rejects_inferred_role_clarity(self):
        incident = make_incident()
        incident["description"] = (
            "Crew member reported exclusion from toolbox talks and rostering "
            "decisions after raising a safety concern, describes ongoing stress "
            "and poor sleep."
        )
        finding = make_finding()
        finding["psychosocial_types"] = [
            "poor_organizational_justice",
            "lack_of_role_clarity",
        ]
        finding["category_evidence_quote"] = (
            "exclusion from toolbox talks and rostering decisions"
        )

        with self.assertRaisesRegex(
            analysis.ModelResponseError,
            "lack_of_role_clarity requires explicit evidence",
        ):
            analysis.validate_finding(finding, incident)

    def test_rejects_fatigue_inferred_from_overtime(self):
        incident = make_incident()
        incident["description"] = (
            "Worker disclosed feeling overwhelmed by sustained overtime and "
            "understaffing on night shift, requested confidential support."
        )
        finding = make_finding()
        finding["psychosocial_types"] = [
            "job_demands",
            "work_related_fatigue",
        ]
        finding["category_evidence_quote"] = (
            "feeling overwhelmed by sustained overtime and understaffing"
        )

        with self.assertRaisesRegex(
            analysis.ModelResponseError,
            "work_related_fatigue requires explicit evidence",
        ):
            analysis.validate_finding(finding, incident)

    def test_rejects_other_as_secondary_domain(self):
        finding = make_finding()
        finding["secondary_hazard_domains"] = ["other"]

        with self.assertRaisesRegex(
            analysis.ModelResponseError,
            "other cannot be used as a secondary",
        ):
            analysis.validate_finding(finding, make_incident())

    def test_normalizes_other_as_secondary_domain(self):
        finding = make_finding()
        finding["secondary_hazard_domains"] = ["other"]

        normalizations = analysis.normalize_taxonomy(finding)

        self.assertEqual(finding["secondary_hazard_domains"], [])
        self.assertEqual(
            normalizations,
            ["removed_other_secondary_domain"],
        )

    def test_removes_unsupported_environmental_domain_from_dust(self):
        finding = make_finding()
        finding.update(
            {
                "primary_hazard_domain": "occupational_health",
                "secondary_hazard_domains": ["environmental"],
                "event_mechanism": "dust_exceedance",
            }
        )

        normalizations = analysis.normalize_context_dependent_domains(
            finding,
            "Dust exceedance recorded at crusher, fogger offline.",
        )

        self.assertEqual(finding["secondary_hazard_domains"], [])
        self.assertEqual(
            normalizations,
            ["removed_unsupported_dust_environmental_domain"],
        )

    def test_does_not_assume_low_for_speeding_without_context(self):
        finding = make_finding()
        finding.update(
            {
                "event_mechanism": "speeding",
                "severity_consistency": "consistent",
                "suggested_severity": "Low",
                "severity_evidence_quote": "driver coached",
                "explanation": "The record describes a speeding event.",
            }
        )

        normalizations = analysis.normalize_context_dependent_severity(
            finding,
            "LV exceeded speed limit on haul road, driver coached.",
        )

        self.assertEqual(finding["suggested_severity"], "Not assessed")
        self.assertEqual(
            normalizations,
            ["removed_unsupported_low_severity"],
        )

    def test_removes_conflicting_assessed_severity_explanation(self):
        finding = make_finding()
        finding["explanation"] = (
            "The record describes a dropped object. No injury was reported, "
            "so the severity is Low."
        )

        normalizations = analysis.normalize_severity_explanation(finding)

        self.assertNotIn("severity is Low", finding["explanation"])
        self.assertIn(
            "does not provide enough consequence or magnitude",
            finding["explanation"],
        )
        self.assertEqual(
            normalizations,
            [
                "removed_conflicting_severity_explanation",
                "added_insufficient_context_explanation",
            ],
        )
        analysis.validate_severity_explanation(finding)

    def test_adds_missing_insufficient_context_explanation(self):
        finding = make_finding()
        finding["explanation"] = (
            "The description explicitly indicates an environmental release."
        )

        normalizations = analysis.normalize_severity_explanation(finding)

        self.assertIn(
            "does not provide enough consequence or magnitude",
            finding["explanation"],
        )
        self.assertEqual(
            normalizations,
            ["added_insufficient_context_explanation"],
        )

    def test_does_not_assume_low_for_dust_exceedance(self):
        finding = make_finding()
        finding.update(
            {
                "event_mechanism": "dust_exceedance",
                "severity_consistency": "consistent",
                "suggested_severity": "Low",
                "severity_evidence_quote": "Dust exceedance recorded",
                "explanation": "The record describes a dust exceedance.",
            }
        )

        normalizations = analysis.normalize_context_dependent_severity(
            finding,
            "Dust exceedance recorded at crusher, fogger offline.",
        )

        self.assertEqual(finding["suggested_severity"], "Not assessed")
        self.assertEqual(
            finding["severity_consistency"],
            "insufficient_context",
        )
        self.assertIsNone(finding["severity_evidence_quote"])
        self.assertEqual(
            normalizations,
            ["removed_unsupported_low_severity"],
        )

    def test_rejects_low_severity_when_first_aid_is_reported(self):
        incident = make_incident()
        incident["description"] = (
            "Operator slipped on wet stairs, grazed elbow, first aid "
            "administered."
        )
        incident["severity"] = "Medium"
        finding = make_finding()
        finding.update(
            {
                "primary_hazard_domain": "slips_trips_falls",
                "secondary_hazard_domains": [],
                "event_mechanism": "slip_or_trip",
                "psychosocial_hazard": False,
                "psychosocial_types": [],
                "severity_consistency": "appears_inconsistent",
                "suggested_severity": "Low",
                "category_evidence_quote": "Operator slipped on wet stairs",
                "severity_evidence_quote": (
                    "grazed elbow, first aid administered"
                ),
            }
        )

        with self.assertRaisesRegex(
            analysis.ModelResponseError,
            "requires at least Medium severity",
        ):
            analysis.validate_finding(finding, incident)

    def test_normalizes_unsupported_containment_sentence(self):
        finding = make_finding()
        finding["explanation"] = (
            "The description reports a hydrocarbon sheen. The event was "
            "contained because a spill kit was deployed."
        )

        normalizations = analysis.normalize_explanation(
            finding,
            "Hydrocarbon sheen observed, spill kit deployed.",
        )

        self.assertEqual(
            finding["explanation"],
            "The description reports a hydrocarbon sheen.",
        )
        self.assertEqual(
            normalizations,
            ["removed_unsupported_containment_claim"],
        )
        analysis.validate_explanation_grounding(
            finding,
            "Hydrocarbon sheen observed, spill kit deployed.",
        )

    def test_rejects_unsupported_containment_claim(self):
        finding = make_finding()
        finding["explanation"] = "The event was contained."

        with self.assertRaisesRegex(
            analysis.ModelResponseError,
            "containment without explicit source evidence",
        ):
            analysis.validate_finding(finding, make_incident())

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

    def test_stops_immediately_after_rate_limit(self):
        class RateLimitError(Exception):
            status_code = 429

        sleep_delays = []

        with patch.object(
            analysis,
            "request_finding",
            side_effect=RateLimitError("limited"),
        ) as request:
            with self.assertRaisesRegex(
                analysis.IncidentAnalysisError,
                "failed after 1 attempt",
            ) as raised:
                analysis.analyze_incident(
                    object(),
                    make_incident(),
                    "test-model",
                    sleep=sleep_delays.append,
                )

        self.assertEqual(request.call_count, 1)
        self.assertEqual(sleep_delays, [])
        self.assertEqual(raised.exception.attempts, 1)
        self.assertTrue(analysis.is_rate_limit_error(raised.exception))

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
        incident["description"] = (
            "{} {}".format(incident["description"], incident_id)
        )
        incident["source_record_hash"] = record_hash

        return incident

    def make_result(self, incident: dict) -> dict:
        return {
            "source": analysis.source_metadata(incident),
            "finding": make_finding(),
            "provenance": {
                "model": "test-model",
                "analysis_version": analysis.ANALYSIS_VERSION,
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

    def test_marks_conflicting_duplicate_severities_as_stale(self):
        first = self.make_distinct_incident("INC-1", "a" * 64)
        second = self.make_distinct_incident("INC-2", "b" * 64)
        second["description"] = first["description"]
        second["severity"] = "Medium"
        first_result = self.make_result(first)
        second_result = self.make_result(second)

        for result, severity in (
            (first_result, "Low"),
            (second_result, "Medium"),
        ):
            result["finding"]["suggested_severity"] = severity
            result["finding"]["severity_consistency"] = "consistent"
            result["finding"]["severity_evidence_quote"] = (
                "feeling anxious before shift"
            )

        stale_hashes = analysis.find_stale_finding_hashes(
            {
                first["source_record_hash"]: first_result,
                second["source_record_hash"]: second_result,
            },
            {
                first["source_record_hash"]: first,
                second["source_record_hash"]: second,
            },
        )

        self.assertEqual(
            stale_hashes,
            {first["source_record_hash"], second["source_record_hash"]},
        )

    def test_marks_missing_analysis_version_as_stale(self):
        incident = self.make_distinct_incident("INC-1", "a" * 64)
        result = self.make_result(incident)
        result["provenance"].pop("analysis_version")

        stale_hashes = analysis.find_stale_finding_hashes(
            {incident["source_record_hash"]: result},
            {incident["source_record_hash"]: incident},
        )

        self.assertEqual(stale_hashes, {incident["source_record_hash"]})

    def test_reuses_one_assessment_for_identical_descriptions(self):
        first = self.make_distinct_incident("INC-1", "a" * 64)
        second = self.make_distinct_incident("INC-2", "b" * 64)
        second["description"] = first["description"]
        second["severity"] = "Medium"
        first_result = self.make_result(first)
        first_result["finding"]["suggested_severity"] = "Low"
        first_result["finding"]["severity_consistency"] = "consistent"
        first_result["finding"]["severity_evidence_quote"] = (
            "feeling anxious before shift"
        )

        with TemporaryDirectory() as directory:
            output_path = Path(directory) / "findings.jsonl"
            failures_path = Path(directory) / "failures.jsonl"

            with patch.object(
                analysis,
                "analyze_incident",
                return_value=first_result,
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

            saved_by_hash = {
                record["source"]["record_hash"]: record
                for record in analysis.read_jsonl(output_path)
            }
            reused = saved_by_hash[second["source_record_hash"]]

            self.assertEqual(analyze.call_count, 1)
            self.assertEqual(succeeded, 2)
            self.assertEqual(failed, 0)
            self.assertEqual(
                reused["finding"]["suggested_severity"],
                "Low",
            )
            self.assertEqual(
                reused["finding"]["severity_consistency"],
                "appears_inconsistent",
            )
            self.assertEqual(reused["provenance"]["attempts"], 0)

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
