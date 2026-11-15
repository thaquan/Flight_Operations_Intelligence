"""Create a compact GitHub-friendly CSV preview from the 10,000-row BTS sample."""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path

from .build_sample import OUTPUT_FIELDS, file_sha256


def build_preview(
    sample_csv: Path,
    preview_csv: Path,
    manifest_path: Path,
    seed: int = 42,
    completed_per_month: int = 46,
    cancelled_per_month: int = 3,
    diverted_per_month: int = 1,
) -> dict:
    quotas = {
        "completed": completed_per_month,
        "cancelled": cancelled_per_month,
        "diverted": diverted_per_month,
    }
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    with sample_csv.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != OUTPUT_FIELDS:
            raise ValueError("Sample columns do not match the expected BTS sample schema")
        for row in reader:
            status = row["sample_status"]
            if status not in quotas:
                raise ValueError(f"Unknown sample status: {status}")
            groups[(row["source_month"], status)].append(row)

    months = sorted({month for month, _ in groups})
    selected: list[dict[str, str]] = []
    for month in months:
        for status, quota in quotas.items():
            available = groups.get((month, status), [])
            if len(available) < quota:
                raise ValueError(f"{month}: insufficient {status} records for preview")
            ranked = sorted(
                available,
                key=lambda row: hashlib.sha256(
                    f"{seed}:{month}:{status}:{row['source_row_number']}".encode("ascii")
                ).digest(),
            )
            selected.extend(ranked[:quota])
    selected.sort(key=lambda row: (row["source_month"], int(row["source_row_number"])))
    preview_csv.parent.mkdir(parents=True, exist_ok=True)
    temporary = preview_csv.with_suffix(preview_csv.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(selected)
    temporary.replace(preview_csv)
    result = {
        "source_sample_sha256": file_sha256(sample_csv),
        "preview_sha256": file_sha256(preview_csv),
        "preview_rows": len(selected),
        "months": months,
        "rows_per_month": sum(quotas.values()),
        "status_quotas_per_month": quotas,
        "sampling_warning": "Illustrative stratified subset, not for population KPI estimates.",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_manifest = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    temporary_manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary_manifest.replace(manifest_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/sample/bts_flights_2024_2025_sample_10000.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/sample/bts_flights_preview_1200.csv"))
    parser.add_argument("--manifest", type=Path, default=Path("data/sample/preview_manifest.json"))
    args = parser.parse_args()
    result = build_preview(args.input, args.output, args.manifest)
    print(f"Created {result['preview_rows']:,} preview rows across {len(result['months'])} months")
    print(f"SHA-256: {result['preview_sha256']}")


if __name__ == "__main__":
    main()
