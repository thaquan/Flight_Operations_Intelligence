"""Validate all Bronze partitions against the verified Phase 1 source baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import polars as pl

from .bronze_writer import sha256_file
from .ingest import BronzePipeline, PROJECT_ROOT
from .manifest import read_manifest, utc_now


def _all_true(values: pa.Array) -> bool:
    return pc.all(pc.fill_null(values, False)).as_py() is True


def _check_lineage(file: pq.ParquetFile, month: str, source_file: str, source_hash: str) -> int:
    """Read only lineage/date columns and verify their values for every row."""
    columns = ["FlightDate", "source_file", "source_sha256", "source_row_number", "ingested_at_utc"]
    row_count = 0
    for batch in file.iter_batches(batch_size=65_536, columns=columns):
        n = batch.num_rows
        values = {name: batch.column(batch.schema.get_field_index(name)) for name in columns}
        if not _all_true(pc.starts_with(values["FlightDate"], month)):
            raise ValueError(f"{month}: out-of-period FlightDate in Bronze")
        if not _all_true(pc.equal(values["source_file"], source_file)):
            raise ValueError(f"{month}: source_file lineage mismatch")
        if not _all_true(pc.equal(values["source_sha256"], source_hash)):
            raise ValueError(f"{month}: source_sha256 lineage mismatch")
        expected_numbers = pa.array(range(row_count + 1, row_count + n + 1), type=pa.int64())
        if not _all_true(pc.equal(values["source_row_number"], expected_numbers)):
            raise ValueError(f"{month}: source_row_number is not continuous and ordered")
        if pc.any(pc.is_null(values["ingested_at_utc"])).as_py():
            raise ValueError(f"{month}: null ingestion timestamp")
        row_count += n
    return row_count


def _check_known_source_exceptions(pipeline: BronzePipeline) -> dict:
    """Ensure the two reviewed Phase 1 anomalies survived Bronze conversion."""
    august = pipeline._partition_path("2024-08") / "part-00000.parquet"
    missing_number = (
        pl.scan_parquet(august)
        .filter(pl.col("Flight_Number_Reporting_Airline").is_null())
        .select(["FlightDate", "Reporting_Airline", "Origin", "Dest", "source_row_number"])
        .collect()
        .to_dicts()
    )
    expected_august = {
        "FlightDate": "2024-08-25", "Reporting_Airline": "F9",
        "Origin": "MIA", "Dest": "ATL", "source_row_number": 234964,
    }
    if missing_number != [expected_august]:
        raise ValueError("2024-08: the reviewed missing flight-number source row was not preserved")

    september = pipeline._partition_path("2025-09") / "part-00000.parquet"
    missing_arrival_flag = (
        pl.scan_parquet(september)
        .filter(
            (pl.col("Cancelled") == "0.00")
            & (pl.col("Diverted") == "0.00")
            & pl.col("ArrDel15").is_null()
        )
        .select([
            "FlightDate", "Reporting_Airline", "Flight_Number_Reporting_Airline",
            "Origin", "Dest", "ArrDelay", "source_row_number",
        ])
        .collect()
        .to_dicts()
    )
    expected_september = {
        "FlightDate": "2025-09-06", "Reporting_Airline": "YX",
        "Flight_Number_Reporting_Airline": "5859",
        "Origin": "JFK", "Dest": "MVY", "ArrDelay": None,
        "source_row_number": 410706,
    }
    if missing_arrival_flag != [expected_september]:
        raise ValueError("2025-09: the reviewed missing arrival-delay source row was not preserved")
    return {
        "2024-08_missing_flight_number": 1,
        "2025-09_completed_missing_arrdel15": 1,
    }


def validate_period(pipeline: BronzePipeline, *, deep: bool = False) -> dict:
    state = read_manifest(pipeline.state_path)
    monthly = []
    by_year: dict[str, int] = {}
    output_bytes = 0
    for month in sorted(pipeline.sources):
        record = state["partitions"].get(month)
        if not record or record.get("status") != "completed":
            raise ValueError(f"{month}: Bronze partition not completed")
        source = pipeline.sources[month]
        if record.get("source_sha256") != source["sha256"]:
            raise ValueError(f"{month}: recorded source hash differs from Phase 1")
        if record.get("source_file") != Path(source["relative_path"]).name:
            raise ValueError(f"{month}: source filename differs from Phase 1")
        if deep and sha256_file(pipeline._source_path(source)) != source["sha256"]:
            raise ValueError(f"{month}: current raw ZIP checksum differs from Phase 1")

        partition = pipeline._partition_path(month)
        output_file = partition / "part-00000.parquet"
        if not output_file.is_file():
            raise FileNotFoundError(output_file)
        byte_size = output_file.stat().st_size
        if byte_size != record["parquet_bytes"]:
            raise ValueError(f"{month}: Parquet byte size differs from ingestion manifest")
        file = pq.ParquetFile(output_file)
        if file.schema_arrow != pipeline.schema:
            raise ValueError(f"{month}: Parquet schema differs from the canonical schema")
        rows = file.metadata.num_rows
        if rows != pipeline.expected_rows[month] or rows != record["bronze_row_count"]:
            raise ValueError(f"{month}: source-to-Bronze record count mismatch")
        if deep:
            if sha256_file(output_file) != record["parquet_sha256"]:
                raise ValueError(f"{month}: Parquet checksum mismatch")
            if _check_lineage(file, month, record["source_file"], source["sha256"]) != rows:
                raise ValueError(f"{month}: lineage scan count differs from Parquet metadata")
        monthly.append({"month": month, "source_rows": pipeline.expected_rows[month],
                        "bronze_rows": rows, "parquet_bytes": byte_size,
                        "row_groups": file.metadata.num_row_groups})
        by_year[month[:4]] = by_year.get(month[:4], 0) + rows
        output_bytes += byte_size

    profile = json.loads((pipeline.project_root / "docs/phase1/2024_2025/aggregate_profile.json").read_text(encoding="utf-8"))
    for year, rows in by_year.items():
        if rows != profile["by_year"][year]["scheduled_flights"]:
            raise ValueError(f"{year}: annual count mismatch vs Phase 1")
    total = sum(by_year.values())
    if total != profile["overall"]["scheduled_flights"]:
        raise ValueError("Full-period row count differs from Phase 1")
    if len(monthly) != len(pipeline.sources):
        raise ValueError("Unexpected number of monthly partitions")
    report = {
        "generated_at_utc": utc_now(),
        "validation_mode": "deep" if deep else "metadata",
        "status": "pass",
        "source_months": len(pipeline.sources),
        "bronze_partitions": len(monthly),
        "bronze_columns": len(pipeline.schema),
        "bronze_rows": total,
        "by_year": by_year,
        "bronze_parquet_bytes": output_bytes,
        "monthly": monthly,
    }
    if deep and {"2024-08", "2025-09"}.issubset(pipeline.sources):
        report["known_source_exceptions"] = _check_known_source_exceptions(pipeline)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--deep", action="store_true", help="Hash Parquet and inspect every lineage row")
    parser.add_argument("--report", type=Path, help="Write a JSON validation report")
    args = parser.parse_args()
    result = validate_period(BronzePipeline(project_root=args.project_root), deep=args.deep)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: val for key, val in result.items() if key != "monthly"}, indent=2))


if __name__ == "__main__":
    main()
