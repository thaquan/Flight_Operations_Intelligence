"""Offline checks for deterministic BTS sample generation."""

import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from src.phase1.build_sample import (
    OUTPUT_FIELDS,
    SAMPLE_FIELDS,
    build_sample,
    file_sha256,
    month_quotas,
    sample_month,
    status_of,
)
from src.phase1.download_bts import source_for


def make_month(source_root: Path, profile_dir: Path, month: str) -> dict:
    _, source = source_for(month, source_root)
    source.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for status, count in (("completed", 12), ("cancelled", 5), ("diverted", 4)):
        for index in range(count):
            row = {field: "" for field in SAMPLE_FIELDS}
            row.update({
                "FlightDate": f"{month}-01",
                "Year": month[:4],
                "Month": str(int(month[5:])),
                "Reporting_Airline": "AA",
                "Flight_Number_Reporting_Airline": str(index + 100),
                "Origin": "JFK",
                "Dest": "LAX",
                "Cancelled": "1.00" if status == "cancelled" else "0.00",
                "Diverted": "1.00" if status == "diverted" else "0.00",
                "ArrDel15": "0.00" if status == "completed" else "",
            })
            rows.append(row)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=SAMPLE_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("flights.csv", output.getvalue())
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / f"{month}.json").write_text(json.dumps({
        "dataset": {"rows": 21, "status_counts": {
            "completed": 12, "cancelled": 5, "diverted_not_cancelled": 4,
        }},
    }), encoding="utf-8")
    return {"month": month, "sha256": file_sha256(source)}


class TestSampleBuilder(unittest.TestCase):
    def test_outcome_flags(self):
        self.assertEqual(status_of({"Cancelled": "0.00", "Diverted": "1.00"}), "diverted")
        self.assertEqual(status_of({"Cancelled": "1.00", "Diverted": "0.00"}), "cancelled")
        with self.assertRaises(ValueError):
            status_of({"Cancelled": "1.00", "Diverted": "1.00"})

    def test_month_quotas_are_exact(self):
        quotas = month_quotas(10_000, 24, 6, 3)
        self.assertEqual(len(quotas), 24)
        self.assertEqual(sum(sum(item.values()) for item in quotas), 10_000)
        self.assertEqual(quotas[0], {"completed": 408, "cancelled": 6, "diverted": 3})
        self.assertEqual(quotas[-1], {"completed": 407, "cancelled": 6, "diverted": 3})
        with self.assertRaises(ValueError):
            month_quotas(5, 2, 2, 1)

    def test_sample_is_reproducible_and_traceable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw = root / "raw"
            profiles = root / "profiles"
            manifest = {"files": [
                make_month(raw, profiles, "2024-01"),
                make_month(raw, profiles, "2024-02"),
            ]}
            csv_path = root / "sample" / "sample.csv"
            json_path = root / "sample" / "sample_manifest.json"
            kwargs = dict(
                source_root=raw,
                acquisition_manifest=manifest,
                profile_dir=profiles,
                output_csv=csv_path,
                output_manifest=json_path,
                months=["2024-01", "2024-02"],
                sample_size=20,
                seed=42,
                min_cancelled=2,
                min_diverted=1,
            )
            first = build_sample(**kwargs)
            first_csv = csv_path.read_bytes()
            first_manifest = json_path.read_bytes()
            second = build_sample(**kwargs)
            self.assertEqual(first, second)
            self.assertEqual(first_csv, csv_path.read_bytes())
            self.assertEqual(first_manifest, json_path.read_bytes())
            self.assertEqual(first["rows"], 20)
            with csv_path.open(newline="", encoding="utf-8") as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(tuple(reader.fieldnames), OUTPUT_FIELDS)
                rows = list(reader)
            self.assertEqual(len(rows), 20)
            self.assertEqual(sum(row["sample_status"] == "cancelled" for row in rows), 4)
            self.assertEqual(sum(row["sample_status"] == "diverted" for row in rows), 2)
            self.assertTrue(all(row["source_month"] in ("2024-01", "2024-02") for row in rows))
            self.assertTrue(all(int(row["source_row_number"]) > 0 for row in rows))

    def test_modified_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw = root / "raw"
            profiles = root / "profiles"
            record = make_month(raw, profiles, "2024-01")
            record["sha256"] = "not-the-real-hash"
            with self.assertRaisesRegex(ValueError, "checksum"):
                build_sample(
                    raw, {"files": [record]}, profiles,
                    root / "sample" / "sample.csv",
                    root / "sample" / "manifest.json",
                    ["2024-01"], sample_size=10, min_cancelled=2, min_diverted=1,
                )


if __name__ == "__main__":
    unittest.main()
