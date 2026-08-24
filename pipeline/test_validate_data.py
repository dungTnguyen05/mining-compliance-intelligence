from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

PIPELINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPELINE_DIR))

from validate_data import validate_reporting_periods


class ReportingPeriodTests(unittest.TestCase):
    def test_flags_missing_fuel_month(self):
        electricity = pd.DataFrame({
            "period": pd.to_datetime([
                "2025-10-01",
                "2025-11-01",
                "2025-12-01",
            ]),
        })
        fuel = pd.DataFrame({
            "delivery_date": pd.to_datetime([
                "2025-10-15",
                "2025-12-15",
            ]),
        })
        incidents = pd.DataFrame({
            "incident_date": pd.to_datetime([]),
        })

        issues = validate_reporting_periods(
            electricity,
            fuel,
            incidents,
        )

        self.assertIn({
            "issue": "missing fuel delivery month",
            "action": "flagged",
            "record_key": "2025-11",
            "count": 1,
            "months": ["2025-11"],
            "reason": (
                "missing fuel records cannot be treated as zero Scope 1 emissions"
            ),
        }, issues)

    def test_accepts_complete_fuel_month_coverage(self):
        electricity = pd.DataFrame({
            "period": pd.to_datetime([
                "2025-10-01",
                "2025-11-01",
            ]),
        })
        fuel = pd.DataFrame({
            "delivery_date": pd.to_datetime([
                "2025-10-15",
                "2025-11-15",
            ]),
        })
        incidents = pd.DataFrame({
            "incident_date": pd.to_datetime([]),
        })

        issues = validate_reporting_periods(
            electricity,
            fuel,
            incidents,
        )

        self.assertFalse(any(
            issue["issue"] == "missing fuel delivery month"
            for issue in issues
        ))


if __name__ == "__main__":
    unittest.main()
