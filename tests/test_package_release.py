"""Small-file tests for the GitHub Release packaging contract."""

from pathlib import Path
import tempfile
import unittest
import zipfile

from src.phase1.download_bts import source_for, verify_zip
from src.phase1.package_release import package_year


class TestReleasePackaging(unittest.TestCase):
    def test_yearly_bundle_preserves_official_zip_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_root = root / "raw"
            records = []
            for month_number in range(1, 13):
                month = f"2024-{month_number:02d}"
                _, source = source_for(month, raw_root)
                source.parent.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(source, "w") as archive:
                    archive.writestr("flights.csv", f"FlightDate\n2024-{month_number:02d}-01\n")
                checked = verify_zip(source)
                records.append({"month": month, **checked})
            destination = root / "assets" / "2024.zip"
            first = package_year(2024, raw_root, {"files": records}, destination)
            self.assertEqual(first["action"], "created")
            self.assertEqual(len(first["months"]), 12)
            with zipfile.ZipFile(destination) as outer:
                self.assertEqual(len(outer.namelist()), 14)
                self.assertIsNone(outer.testzip())
                checksum_text = outer.read("SHA256SUMS.txt").decode("ascii")
                self.assertEqual(len(checksum_text.splitlines()), 12)
                january = records[0]["month"]
                _, original = source_for(january, raw_root)
                entry = f"data/raw/bts/2024/{original.name}"
                self.assertEqual(outer.read(entry), original.read_bytes())
            second = package_year(2024, raw_root, {"files": records}, destination)
            self.assertEqual(second["action"], "reused")
            self.assertEqual(second["sha256"], first["sha256"])

    def test_missing_month_prevents_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "missing months"):
                package_year(2025, Path(directory), {"files": []}, Path(directory) / "asset.zip")


if __name__ == "__main__":
    unittest.main()
