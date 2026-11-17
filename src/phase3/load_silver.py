"""Load verified BTS Bronze Parquet partitions into PostgreSQL Silver.

Each month is an atomic transaction: a failure rolls back its rows and audit
record together. Re-running an unchanged month skips it; replacement requires
an explicit --reprocess flag.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import time

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
import psycopg

from src.phase2.bronze_writer import sha256_file
from .config import PROJECT_ROOT, read_env
from .silver_contract import BRONZE_COLUMNS, SILVER_COLUMNS


BRONZE_ROOT = PROJECT_ROOT / "data/bronze"
MANIFEST_PATH = BRONZE_ROOT / "_metadata/ingestion_manifest.json"
MIGRATION_PATH = PROJECT_ROOT / "sql/phase3/002_create_silver.sql"
COPY_SQL = (
    f"COPY silver.flights ({', '.join(SILVER_COLUMNS)}) "
    "FROM STDIN WITH (FORMAT CSV, NULL '\\N')"
)
LOCK_ID = 81032002


@dataclass(frozen=True)
class Partition:
    month: str
    path: Path
    row_count: int
    source_file: str
    source_sha256: str
    parquet_sha256: str

    @property
    def month_date(self) -> date:
        return date.fromisoformat(f"{self.month}-01")


def month_range(start: str, end: str) -> list[str]:
    first = date.fromisoformat(f"{start}-01")
    last = date.fromisoformat(f"{end}-01")
    if first > last:
        raise ValueError("Start month must be on or before end month")
    result: list[str] = []
    year, month = first.year, first.month
    while (year, month) <= (last.year, last.month):
        result.append(f"{year:04d}-{month:02d}")
        year, month = year + (month == 12), (month % 12) + 1
    return result


def inspect_partition(month: str, record: dict, bronze_root: Path = BRONZE_ROOT) -> Partition:
    """Verify checksum, manifest and Parquet metadata before any SQL writes."""
    if record.get("status") != "completed":
        raise ValueError(f"{month}: Bronze partition is not completed")
    root = bronze_root.resolve()
    path = (root / record["partition"] / record["parquet_file"]).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"{month}: missing or unsafe Bronze Parquet path")
    if record.get("source_month") != month:
        raise ValueError(f"{month}: source month differs from manifest key")
    expected_rows = record["bronze_row_count"]
    if not isinstance(expected_rows, int) or expected_rows <= 0:
        raise ValueError(f"{month}: invalid Bronze row count")
    parquet = pq.ParquetFile(path)
    if parquet.metadata.num_rows != expected_rows:
        raise ValueError(f"{month}: Parquet row count differs from manifest")
    if parquet.schema_arrow.names != list(dict.fromkeys(parquet.schema_arrow.names)):
        raise ValueError(f"{month}: duplicate Parquet columns")
    missing = set(BRONZE_COLUMNS) - set(parquet.schema_arrow.names)
    if missing:
        raise ValueError(f"{month}: missing Silver source columns: {sorted(missing)}")
    actual_hash = sha256_file(path)
    if actual_hash != record["parquet_sha256"]:
        raise ValueError(f"{month}: Parquet SHA-256 differs from manifest")
    return Partition(
        month=month,
        path=path,
        row_count=expected_rows,
        source_file=record["source_file"],
        source_sha256=record["source_sha256"],
        parquet_sha256=actual_hash,
    )


def batch_to_csv(batch: pa.RecordBatch, partition: Partition, offset: int) -> bytes:
    """Validate lineage and render one bounded Arrow batch for PostgreSQL COPY."""
    if batch.num_rows == 0:
        return b""
    columns = batch.schema.names
    flight_dates = batch.column(columns.index("FlightDate"))
    in_month = pc.fill_null(pc.starts_with(flight_dates, partition.month), False)
    if pc.all(in_month).as_py() is not True:
        raise ValueError(f"{partition.month}: out-of-month or NULL FlightDate")
    for name, expected in (
        ("source_file", partition.source_file),
        ("source_sha256", partition.source_sha256),
    ):
        matches = pc.fill_null(pc.equal(batch.column(columns.index(name)), expected), False)
        if pc.all(matches).as_py() is not True:
            raise ValueError(f"{partition.month}: invalid {name} in Bronze batch")
    row_numbers = batch.column(columns.index("source_row_number"))
    if (
        pc.min(row_numbers).as_py() != offset + 1
        or pc.max(row_numbers).as_py() != offset + batch.num_rows
        or pc.count_distinct(row_numbers).as_py() != batch.num_rows
    ):
        raise ValueError(f"{partition.month}: noncontiguous source row numbers")

    arrow_table = pa.Table.from_batches([batch])
    month_values = pa.array([partition.month + "-01"] * batch.num_rows, type=pa.string())
    export = pa.Table.from_arrays(
        [month_values] + [arrow_table[name] for name in BRONZE_COLUMNS],
        names=SILVER_COLUMNS,
    )
    sink = pa.BufferOutputStream()
    pacsv.write_csv(
        export,
        sink,
        write_options=pacsv.WriteOptions(include_header=False, null_string="\\N"),
    )
    return sink.getvalue().to_pybytes()


def connect(settings: dict[str, str]) -> psycopg.Connection:
    return psycopg.connect(
        host="127.0.0.1",
        port=int(settings["POSTGRES_PORT"]),
        dbname=settings["POSTGRES_DB"],
        user=settings["POSTGRES_USER"],
        password=settings["POSTGRES_PASSWORD"],
        connect_timeout=10,
        autocommit=True,
    )


def ensure_schema(connection: psycopg.Connection) -> None:
    connection.execute(MIGRATION_PATH.read_text(encoding="utf-8"))


def current_load(connection: psycopg.Connection, partition: Partition) -> tuple | None:
    return connection.execute(
        "SELECT source_sha256, parquet_sha256, bronze_row_count, silver_row_count "
        "FROM audit.silver_loads WHERE source_month = %s",
        (partition.month_date,),
    ).fetchone()


def physical_count(connection: psycopg.Connection, partition: Partition) -> int:
    return connection.execute(
        "SELECT COUNT(*) FROM silver.flights WHERE source_month = %s",
        (partition.month_date,),
    ).fetchone()[0]


def load_month(
    connection: psycopg.Connection,
    partition: Partition,
    *,
    reprocess: bool = False,
    batch_size: int = 50_000,
) -> dict:
    """Compare warehouse state, then commit exactly one complete month."""
    existing = current_load(connection, partition)
    existing_rows = physical_count(connection, partition)
    matches = (
        existing == (
            partition.source_sha256,
            partition.parquet_sha256,
            partition.row_count,
            partition.row_count,
        )
        and existing_rows == partition.row_count
    )
    if matches and not reprocess:
        return {"month": partition.month, "status": "skipped", "rows": existing_rows}
    if (existing is not None or existing_rows > 0) and not reprocess:
        raise RuntimeError(
            f"{partition.month}: Silver differs from Bronze; review before --reprocess"
        )

    started = time.perf_counter()
    written = 0
    # COPY and audit update are protected by the same month-sized transaction.
    with connection.transaction():
        if existing is not None or existing_rows > 0:
            connection.execute(
                "DELETE FROM silver.flights WHERE source_month = %s",
                (partition.month_date,),
            )
            connection.execute(
                "DELETE FROM audit.silver_loads WHERE source_month = %s",
                (partition.month_date,),
            )
        parquet = pq.ParquetFile(partition.path)
        with connection.cursor() as cursor:
            with cursor.copy(COPY_SQL) as copy:
                for batch in parquet.iter_batches(batch_size=batch_size, columns=list(BRONZE_COLUMNS)):
                    copy.write(batch_to_csv(batch, partition, written))
                    written += batch.num_rows
        if written != partition.row_count:
            raise ValueError(
                f"{partition.month}: COPY input has {written} rows, expected {partition.row_count}"
            )
        stored = physical_count(connection, partition)
        if stored != partition.row_count:
            raise ValueError(
                f"{partition.month}: PostgreSQL has {stored} rows, expected {partition.row_count}"
            )
        connection.execute(
            "INSERT INTO audit.silver_loads "
            "(source_month, source_sha256, parquet_sha256, bronze_row_count, silver_row_count) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                partition.month_date,
                partition.source_sha256,
                partition.parquet_sha256,
                partition.row_count,
                stored,
            ),
        )
    return {
        "month": partition.month,
        "status": "reprocessed" if existing is not None else "loaded",
        "rows": written,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2024-01", help="First YYYY-MM")
    parser.add_argument("--end", default="2025-12", help="Last YYYY-MM")
    parser.add_argument("--month", help="Process one YYYY-MM, overriding the range")
    parser.add_argument("--batch-size", type=int, default=50_000)
    parser.add_argument("--reprocess", action="store_true", help="Atomically replace existing months")
    parser.add_argument("--dry-run", action="store_true", help="Verify Bronze only; do not write SQL")
    args = parser.parse_args()
    if args.batch_size < 1 or args.batch_size > 200_000:
        parser.error("--batch-size must be between 1 and 200000")

    requested = [args.month] if args.month else month_range(args.start, args.end)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    records = manifest["partitions"]
    absent = sorted(set(requested) - set(records))
    if absent:
        raise ValueError(f"Missing Bronze months: {absent}")

    # Complete checksum preflight precedes all database changes.
    partitions = [inspect_partition(month, records[month]) for month in requested]
    print(f"Preflight passed: {len(partitions)} Bronze partitions, "
          f"{sum(p.row_count for p in partitions):,} rows", flush=True)
    if args.dry_run:
        return

    settings = read_env(PROJECT_ROOT / ".env")
    with connect(settings) as connection:
        ensure_schema(connection)
        locked = connection.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_ID,)).fetchone()[0]
        if not locked:
            raise RuntimeError("Another Silver load is already running")
        try:
            for partition in partitions:
                result = load_month(
                    connection,
                    partition,
                    reprocess=args.reprocess,
                    batch_size=args.batch_size,
                )
                print(json.dumps(result), flush=True)
        finally:
            connection.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))


if __name__ == "__main__":
    main()
