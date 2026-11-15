"""Small self-contained tests. No raw BTS data is required for CI."""

import csv
from pathlib import Path
import tempfile
import unittest
import zipfile

from src.phase1.profile_bts import (
    BUSINESS_KEY_COLUMNS,
    REQUIRED_COLUMNS,
    is_valid_hhmm,
    make_key,
    parse_flag,
    parse_flight_date,
    profile,
)


class TestBTSProfile(unittest.TestCase):
    def test_status_flag_parser(self):
        self.assertEqual(parse_flag("1.00"), 1)
        self.assertEqual(parse_flag("0.00"), 0)
        self.assertIsNone(parse_flag(""))
        self.assertIsNone(parse_flag("5"))

    def test_date_parser(self):
        self.assertEqual(parse_flight_date("2025-01-03").isoformat(), "2025-01-03")
        self.assertEqual(parse_flight_date("20250103").isoformat(), "2025-01-03")
        self.assertIsNone(parse_flight_date("garbage"))

    def test_hhmm_parser(self):
        self.assertTrue(is_valid_hhmm("0659"))
        self.assertTrue(is_valid_hhmm("0"))
        self.assertTrue(is_valid_hhmm("2400"))
        self.assertFalse(is_valid_hhmm("2460"))
        self.assertFalse(is_valid_hhmm("2361"))
        self.assertFalse(is_valid_hhmm(""))

    def test_missing_key_does_not_get_hashed(self):
        row = {name: "x" for name in BUSINESS_KEY_COLUMNS}
        self.assertIsNotNone(make_key(row, BUSINESS_KEY_COLUMNS))
        row["CRSDepTime"] = ""
        self.assertIsNone(make_key(row, BUSINESS_KEY_COLUMNS))

    def test_realistic_two_row_fixture(self):
        fields = list(dict.fromkeys((*REQUIRED_COLUMNS, "CRSArrTime", "")))
        base = {
            "FlightDate": "2025-01-01", "Reporting_Airline": "AA",
            "DOT_ID_Reporting_Airline": "19805", "Flight_Number_Reporting_Airline": "100",
            "OriginAirportID": "12478", "DestAirportID": "12892", "Origin": "JFK", "Dest": "LAX",
            "CRSDepTime": "0659", "CRSArrTime": "1020", "DepDelay": "-3.00",
            "ArrDelay": "-7.00", "ArrDel15": "0.00", "Cancelled": "0.00", "Diverted": "0.00",
        }
        cancelled = dict(base, Flight_Number_Reporting_Airline="101", Cancelled="1.00", ArrDelay="", ArrDel15="", DepDelay="")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2025_1.zip"
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                import io

                csv_bytes = io.StringIO()
                writer = csv.DictWriter(csv_bytes, fieldnames=fields)
                writer.writeheader()
                writer.writerows([base, cancelled])
                archive.writestr("flights.csv", csv_bytes.getvalue())
            result = profile(path, "2025-01")

        self.assertEqual(result["dataset"]["rows"], 2)
        self.assertEqual(result["dataset"]["status_counts"]["cancelled"], 1)
        self.assertEqual(result["kpis"]["arrival_delay15_eligible_flights"], 1)
        self.assertEqual(result["kpis"]["arrival_on_time_pct"], 100.0)
        self.assertEqual(result["anomalies"].get("duplicate_candidate_business_key", 0), 0)
        self.assertEqual(result["dataset"]["empty_header_positions"], [len(fields) - 1])


if __name__ == "__main__":
    unittest.main()
