"""Tests for the 24-month acquisition and reconciliation contract."""

from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from src.phase1.build_report import summarize
from src.phase1.download_bts import month_range, source_for, verify_zip


class TestAcquisition(unittest.TestCase):
    def test_month_range_has_24_consecutive_months(self):
        months = month_range("2024-01", "2025-12")
        self.assertEqual(len(months), 24)
        self.assertEqual(months[0], "2024-01")
        self.assertEqual(months[-1], "2025-12")
        with self.assertRaises(ValueError):
            month_range("2024-13", "2025-01")
        with self.assertRaises(ValueError):
            month_range("2025-12", "2024-01")

    def test_official_filename_has_unpadded_month(self):
        url, destination = source_for("2024-01", Path("data/raw/bts"))
        self.assertTrue(url.endswith("_2024_1.zip"))
        self.assertEqual(destination.parent.name, "2024")

    def test_zip_checksum_and_csv_member(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("sample.csv", "FlightDate\n2024-01-01\n")
            result = verify_zip(path)
            self.assertEqual(result["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(result["csv_member"], "sample.csv")
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("wrong.txt", "not a CSV")
            with self.assertRaises(ValueError):
                verify_zip(path)


def fake_month(month: str) -> dict:
    year, m = (int(p) for p in month.split("-"))
    first = date(year, m, 1)
    next_month = date(year + (m == 12), m % 12 + 1, 1)
    last = next_month - timedelta(days=1)
    return {
        "source": {"zip_sha256": f"sha-{month}", "zip_bytes": 123},
        "dataset": {
            "rows": 4,
            "date_min": first.isoformat(),
            "date_max": last.isoformat(),
            "distinct_flight_dates": last.day,
            "invalid_flight_date_count": 0,
            "missing_required_columns": [],
            "status_counts": {"completed": 3, "cancelled": 1, "diverted_not_cancelled": 0},
        },
        "daily_counts": {(first + timedelta(days=day)).isoformat(): 1 for day in range(last.day)},
        "columns": [{"name": "Origin", "null_count": 0}],
        "anomalies": {},
        "kpis": {
            "scheduled_flights": 4,
            "completed_flights": 3,
            "cancelled_flights": 1,
            "diverted_not_cancelled_flights": 0,
            "arrival_delay15_eligible_flights": 3,
            "on_time_arrivals": 2,
            "arrival_delayed_15min": 1,
        },
        "origin_counts": {"LAX": 3, "SFO": 1},
        "destination_counts": {"JFK": 4},
        "reporting_airline_counts": {"AA": 4},
        "route_counts": {"LAX|JFK": 3, "SFO|JFK": 1},
    }


class TestReconciliation(unittest.TestCase):
    def setUp(self):
        self.months = month_range("2024-01", "2025-12")
        self.profiles = {month: fake_month(month) for month in self.months}
        self.manifest = {
            "files": [
                {"month": month, "sha256": f"sha-{month}", "zip_bytes": 123}
                for month in self.months
            ],
            "failures": [],
        }

    def test_complete_verified_period(self):
        report = summarize(self.manifest, self.profiles)
        self.assertTrue(report["phase1_complete"])
        self.assertEqual(report["period"]["verified_months"], 24)
        self.assertEqual(report["overall"]["scheduled_flights"], 96)
        self.assertEqual(report["by_year"]["2024"]["scheduled_flights"], 48)
        self.assertEqual(report["top_20_origin_airports"][0]["flights"], 72)
        self.assertEqual(report["overall"]["arrival_delay15_pct"], round(100 / 3, 4))

    def test_missing_month_blocks_completion(self):
        self.profiles.pop("2025-12")
        report = summarize(self.manifest, self.profiles)
        self.assertFalse(report["phase1_complete"])
        self.assertTrue(any("2025-12" in error for error in report["checks"]["errors"]))

    def test_sha_mismatch_blocks_completion(self):
        self.profiles["2024-06"]["source"]["zip_sha256"] = "wrong"
        report = summarize(self.manifest, self.profiles)
        self.assertFalse(report["phase1_complete"])
        self.assertTrue(any("SHA-256" in error for error in report["checks"]["errors"]))

    def test_missing_calendar_day_blocks_completion(self):
        self.profiles["2024-02"]["daily_counts"].pop("2024-02-29")
        report = summarize(self.manifest, self.profiles)
        self.assertFalse(report["phase1_complete"])
        self.assertTrue(any("28/29" in error for error in report["checks"]["errors"]))

    def test_candidate_key_collision_is_explicit_warning(self):
        self.profiles["2025-01"]["anomalies"] = {"duplicate_candidate_business_key": 2}
        report = summarize(self.manifest, self.profiles)
        self.assertTrue(report["phase1_complete"])
        self.assertTrue(any("candidate business key" in message for message in report["checks"]["warnings"]))


if __name__ == "__main__":
    unittest.main()
