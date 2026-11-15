"""Create a reproducible, inspectable sample of real BTS flight records."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import zipfile

from .download_bts import month_range, source_for
from .profile_bts import parse_flag


SAMPLE_FIELDS = (
    "FlightDate",
    "Year",
    "Month",
    "DayOfWeek",
    "Reporting_Airline",
    "DOT_ID_Reporting_Airline",
    "Flight_Number_Reporting_Airline",
    "Tail_Number",
    "OriginAirportID",
    "Origin",
    "DestAirportID",
    "Dest",
    "CRSDepTime",
    "DepTime",
    "CRSArrTime",
    "ArrTime",
    "DepDelay",
    "ArrDelay",
    "ArrDel15",
    "Cancelled",
    "CancellationCode",
    "Diverted",
    "Distance",
    "CarrierDelay",
    "WeatherDelay",
    "NASDelay",
    "SecurityDelay",
    "LateAircraftDelay",
)
STATUS_ORDER = ("completed", "cancelled", "diverted")
OUTPUT_FIELDS = ("source_month", "source_row_number", "sample_status", *SAMPLE_FIELDS)


def status_of(row: dict[str, str]) -> str:
    cancelled = parse_flag(row.get("Cancelled"))
    diverted = parse_flag(row.get("Diverted"))
    if cancelled is None or diverted is None or (cancelled == 1 and diverted == 1):
        raise ValueError("Invalid or conflicting BTS cancellation/diversion indicators")
    if cancelled == 1:
        return "cancelled"
    if diverted == 1:
        return "diverted"
    return "completed"


def month_quotas(sample_size: int, month_count: int, cancelled: int, diverted: int) -> list[dict[str, int]]:
    if month_count < 1:
        raise ValueError("At least one month is required")
    base, extra = divmod(sample_size, month_count)
    if base < cancelled + diverted + 1:
        raise ValueError("Sample size is too small for the requested outcome quotas")
    return [
        {
            "completed": base + (index < extra) - cancelled - diverted,
            "cancelled": cancelled,
            "diverted": diverted,
        }
        for index in range(month_count)
    ]


def _random_for(seed: int, month: str, status: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{month}:{status}".encode("ascii")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def sample_month(
    source: Path,
    month: str,
    quotas: dict[str, int],
    seed: int,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Reservoir-sample each flight outcome without loading the CSV into memory."""
    with zipfile.ZipFile(source) as archive:
        members = [entry for entry in archive.infolist() if entry.filename.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"{month}: expected exactly one source CSV")
        with archive.open(members[0]) as source_csv:
            reader = csv.DictReader(io.TextIOWrapper(source_csv, encoding="utf-8-sig", newline=""))
            missing_fields = sorted(set(SAMPLE_FIELDS) - set(reader.fieldnames or []))
            if missing_fields:
                raise ValueError(f"{month}: missing sample fields {missing_fields}")

            reservoirs: dict[str, list[dict[str, str]]] = {status: [] for status in STATUS_ORDER}
            rng = {status: _random_for(seed, month, status) for status in STATUS_ORDER}
            observed: Counter[str] = Counter()
            for source_row_number, row in enumerate(reader, 1):
                if row.get("FlightDate", "")[:7] != month:
                    raise ValueError(f"{month}: source contains a flight outside expected month")
                status = status_of(row)
                observed[status] += 1
                quota = quotas[status]
                if quota == 0:
                    continue
                value = {
                    "source_month": month,
                    "source_row_number": str(source_row_number),
                    "sample_status": status,
                    **{field: row.get(field, "") or "" for field in SAMPLE_FIELDS},
                }
                reservoir = reservoirs[status]
                if len(reservoir) < quota:
                    reservoir.append(value)
                else:
                    index = rng[status].randrange(observed[status])
                    if index < quota:
                        reservoir[index] = value

    for status in STATUS_ORDER:
        if len(reservoirs[status]) != quotas[status]:
            raise ValueError(f"{month}: only {len(reservoirs[status])} rows for {status}, need {quotas[status]}")
    rows = [row for status in STATUS_ORDER for row in reservoirs[status]]
    rows.sort(key=lambda row: int(row["source_row_number"]))
    return rows, dict(observed)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_sample(
    source_root: Path,
    acquisition_manifest: dict,
    profile_dir: Path,
    output_csv: Path,
    output_manifest: Path,
    months: list[str],
    sample_size: int = 10_000,
    seed: int = 42,
    min_cancelled: int = 6,
    min_diverted: int = 3,
) -> dict:
    files = {entry["month"]: entry for entry in acquisition_manifest["files"]}
    if any(month not in files for month in months):
        raise ValueError("Acquisition manifest lacks a requested source month")
    quotas = month_quotas(sample_size, len(months), min_cancelled, min_diverted)
    all_rows: list[dict[str, str]] = []
    coverage: list[dict] = []
    for month, requested in zip(months, quotas):
        _, source = source_for(month, source_root)
        actual_sha = file_sha256(source)
        if actual_sha != files[month]["sha256"]:
            raise ValueError(f"{month}: ZIP checksum differs from acquisition manifest")
        rows, observed = sample_month(source, month, requested, seed)
        profile = json.loads((profile_dir / f"{month}.json").read_text(encoding="utf-8"))
        if sum(observed.values()) != profile["dataset"]["rows"]:
            raise ValueError(f"{month}: CSV row count differs from full source profile")
        for status, key in (
            ("completed", "completed"),
            ("cancelled", "cancelled"),
            ("diverted", "diverted_not_cancelled"),
        ):
            if observed.get(status, 0) != profile["dataset"]["status_counts"].get(key, 0):
                raise ValueError(f"{month}: {status} count differs from full source profile")
        all_rows.extend(rows)
        coverage.append({
            "month": month,
            "source_sha256": actual_sha,
            "source_rows": sum(observed.values()),
            "source_status_counts": observed,
            "sample_status_counts": requested,
        })
        print(f"{month}: sampled {len(rows)} of {sum(observed.values()):,} source rows", flush=True)
    if len(all_rows) != sample_size:
        raise ValueError(f"Expected {sample_size} sampled rows, found {len(all_rows)}")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    temporary_csv = output_csv.with_suffix(output_csv.suffix + ".tmp")
    with temporary_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(all_rows)
    temporary_csv.replace(output_csv)
    manifest = {
        "source_dataset": "BTS Reporting Carrier On-Time Performance (1987-present)",
        "sampling_method": "Deterministic reservoir sampling by month and flight outcome; deliberate oversampling of rare outcomes",
        "sampling_warning": "Not a statistically representative sample. Do not compute population KPIs from it.",
        "seed": seed,
        "months": months,
        "rows": sample_size,
        "columns": list(OUTPUT_FIELDS),
        "sample_csv": output_csv.as_posix(),
        "sample_csv_sha256": file_sha256(output_csv),
        "by_month": coverage,
    }
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary_manifest = output_manifest.with_suffix(output_manifest.suffix + ".tmp")
    temporary_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    temporary_manifest.replace(output_manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path("data/raw/bts"))
    parser.add_argument("--acquisition-manifest", type=Path, default=Path("docs/phase1/2024_2025/acquisition_manifest.json"))
    parser.add_argument("--profile-dir", type=Path, default=Path("docs/phase1/2024_2025/profiles"))
    parser.add_argument("--output", type=Path, default=Path("data/sample/bts_flights_2024_2025_sample_10000.csv"))
    parser.add_argument("--sample-manifest", type=Path, default=Path("data/sample/sample_manifest.json"))
    parser.add_argument("--start", default="2024-01")
    parser.add_argument("--end", default="2025-12")
    parser.add_argument("--rows", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    acquisition = json.loads(args.acquisition_manifest.read_text(encoding="utf-8"))
    result = build_sample(
        args.source_root,
        acquisition,
        args.profile_dir,
        args.output,
        args.sample_manifest,
        month_range(args.start, args.end),
        sample_size=args.rows,
        seed=args.seed,
    )
    print(f"Created {result['rows']:,} source-derived rows at {args.output}")
    print(f"SHA-256: {result['sample_csv_sha256']}")


if __name__ == "__main__":
    main()
