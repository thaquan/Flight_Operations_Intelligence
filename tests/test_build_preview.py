"""Checks for the small, directly viewable GitHub CSV preview."""

import csv
from pathlib import Path
import tempfile
import unittest

from src.phase1.build_preview import build_preview
from src.phase1.build_sample import OUTPUT_FIELDS


class TestPreview(unittest.TestCase):
    def test_preview_is_deterministic_and_balanced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample = root / "sample.csv"
            preview = root / "preview.csv"
            manifest = root / "preview.json"
            with sample.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS)
                writer.writeheader()
                for month in ("2024-01", "2024-02"):
                    for status, count in (("completed", 5), ("cancelled", 3), ("diverted", 2)):
                        for number in range(count):
                            row = {field: "" for field in OUTPUT_FIELDS}
                            row.update({
                                "source_month": month,
                                "source_row_number": str(1 + number + 10 * (status != "completed")),
                                "sample_status": status,
                                "FlightDate": f"{month}-01",
                            })
                            writer.writerow(row)
            kwargs = dict(
                sample_csv=sample,
                preview_csv=preview,
                manifest_path=manifest,
                completed_per_month=2,
                cancelled_per_month=1,
                diverted_per_month=1,
            )
            first = build_preview(**kwargs)
            csv_bytes = preview.read_bytes()
            second = build_preview(**kwargs)
            self.assertEqual(first, second)
            self.assertEqual(csv_bytes, preview.read_bytes())
            self.assertEqual(first["preview_rows"], 8)
            with preview.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(sum(row["sample_status"] == "completed" for row in rows), 4)
            self.assertEqual(sum(row["sample_status"] == "cancelled" for row in rows), 2)
            self.assertEqual(sum(row["sample_status"] == "diverted" for row in rows), 2)


if __name__ == "__main__":
    unittest.main()
