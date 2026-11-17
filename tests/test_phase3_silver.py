"""Silver contracts and batch transformations, without requiring PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timezone
import csv
import io
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.phase2.bronze_writer import sha256_file
from src.phase3.load_silver import Partition, batch_to_csv, inspect_partition, month_range
from src.phase3.silver_contract import BRONZE_COLUMNS, SILVER_COLUMNS


def sample_batch(*, date: str = "2024-01-01", sha: str = "a" * 64,
                 numbers: tuple[int, ...] = (1, 2)) -> pa.RecordBatch:
    length = len(numbers)
    values = {}
    for name in BRONZE_COLUMNS:
        if name == "source_row_number":
            values[name] = pa.array(numbers, type=pa.int64())
        elif name == "ingested_at_utc":
            values[name] = pa.array(
                [datetime(2024, 1, 2, tzinfo=timezone.utc)] * length,
                type=pa.timestamp("us", tz="UTC"),
            )
        else:
            values[name] = pa.array([None] * length, type=pa.string())
    for name, entry in (
        ("FlightDate", [date] * length),
        ("source_file", ["sample.zip"] * length),
        ("source_sha256", [sha] * length),
        ("CRSDepTime", ["0005"] * length),
        ("Cancelled", ["0.00"] * length),
    ):
        values[name] = pa.array(entry, type=pa.string())
    return pa.RecordBatch.from_arrays(
        [values[name] for name in BRONZE_COLUMNS], names=BRONZE_COLUMNS
    )


@pytest.fixture()
def partition(tmp_path: Path) -> Partition:
    return Partition("2024-01", tmp_path / "sample.parquet", 2,
                     "sample.zip", "a" * 64, "b" * 64)


def test_month_range_inclusive_and_invalid() -> None:
    assert month_range("2024-11", "2025-02") == [
        "2024-11", "2024-12", "2025-01", "2025-02"
    ]
    with pytest.raises(ValueError, match="Start month"):
        month_range("2025-01", "2024-12")


def test_contract_matches_versioned_sql() -> None:
    sql = (Path(__file__).resolve().parents[1] /
           "sql/phase3/002_create_silver.sql").read_text(encoding="utf-8")
    assert len(BRONZE_COLUMNS) == len(set(BRONZE_COLUMNS))
    assert len(SILVER_COLUMNS) == len(set(SILVER_COLUMNS))
    for name in SILVER_COLUMNS:
        assert f"    {name} " in sql
    assert "PRIMARY KEY (source_month, source_row_number)" in sql


def test_csv_preserves_hhmm_and_nulls(partition: Partition) -> None:
    contents = batch_to_csv(sample_batch(), partition, 0).decode("utf-8")
    rows = list(csv.reader(io.StringIO(contents)))
    assert len(rows) == 2
    assert rows[0][SILVER_COLUMNS.index("source_month")] == "2024-01-01"
    assert rows[0][SILVER_COLUMNS.index("crs_dep_time")] == "0005"
    assert rows[0][SILVER_COLUMNS.index("cancellation_code")] == r"\N"
    assert rows[0][SILVER_COLUMNS.index("source_row_number")] == "1"


@pytest.mark.parametrize(
    "date,sha,numbers,expected_error",
    [
        ("2024-02-01", "a" * 64, (1, 2), "FlightDate"),
        ("2024-01-01", "b" * 64, (1, 2), "source_sha256"),
        ("2024-01-01", "a" * 64, (1, 3), "source row numbers"),
    ],
)
def test_csv_rejects_bad_lineage(
    partition: Partition, date: str, sha: str,
    numbers: tuple[int, ...], expected_error: str,
) -> None:
    with pytest.raises(ValueError, match=expected_error):
        batch_to_csv(sample_batch(date=date, sha=sha, numbers=numbers), partition, 0)


def test_preflight_checks_parquet_hash_and_rows(tmp_path: Path) -> None:
    folder = tmp_path / "bts/flight_year=2024/flight_month=01"
    folder.mkdir(parents=True)
    path = folder / "part-00000.parquet"
    pq.write_table(pa.Table.from_batches([sample_batch()]), path)
    record = {
        "status": "completed",
        "source_month": "2024-01",
        "partition": "bts/flight_year=2024/flight_month=01",
        "parquet_file": "part-00000.parquet",
        "bronze_row_count": 2,
        "source_file": "sample.zip",
        "source_sha256": "a" * 64,
        "parquet_sha256": sha256_file(path),
    }
    assert inspect_partition("2024-01", record, tmp_path).row_count == 2
    with pytest.raises(ValueError, match="SHA-256"):
        inspect_partition("2024-01", {**record, "parquet_sha256": "b" * 64}, tmp_path)
    with pytest.raises(ValueError, match="row count"):
        inspect_partition("2024-01", {**record, "bronze_row_count": 3}, tmp_path)
