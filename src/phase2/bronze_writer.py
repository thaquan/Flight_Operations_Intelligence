"""Convert one verified BTS ZIP member to a lineage-aware Parquet file."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import zipfile

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.parquet as pq


SOURCE_COLUMNS = 109
TRAILING_COLUMN = "__bts_unnamed_trailing_column"
LINEAGE_COLUMNS = (
    "source_file",
    "source_sha256",
    "source_row_number",
    "ingested_at_utc",
)
BLOCK_SIZE = 8 * 1024 * 1024
ROW_GROUP_SIZE = 100_000
COMPRESSION = "zstd"


def source_header(zip_path: Path, csv_member: str, expected_columns: int = SOURCE_COLUMNS) -> list[str]:
    """Read the original header without materializing the CSV."""
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(csv_member) as binary:
            with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as text:
                fields = next(csv.reader(text))
    if len(fields) != expected_columns + 1 or fields[-1] != "":
        raise ValueError(
            f"{zip_path.name}: expected {expected_columns} named fields and one empty trailing header; "
            f"found {len(fields)} fields"
        )
    names = fields[:-1]
    if any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError(f"{zip_path.name}: empty or duplicate source field names")
    if any(name in LINEAGE_COLUMNS or name == TRAILING_COLUMN for name in names):
        raise ValueError(f"{zip_path.name}: source field conflicts with lineage fields")
    return names


def bronze_schema(source_fields: list[str]) -> pa.Schema:
    return pa.schema(
        [pa.field(name, pa.string()) for name in source_fields]
        + [
            pa.field("source_file", pa.string()),
            pa.field("source_sha256", pa.string()),
            pa.field("source_row_number", pa.int64()),
            pa.field("ingested_at_utc", pa.timestamp("us", tz="UTC")),
        ]
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_bronze(
    source_zip: Path,
    csv_member: str,
    month: str,
    source_sha256: str,
    destination: Path,
    source_fields: list[str],
    *,
    expected_columns: int = SOURCE_COLUMNS,
    compression: str = COMPRESSION,
) -> dict:
    """Write one month in batches, preserving all named source text fields.

    Empty CSV fields become Parquet NULL; nonempty text is never type-inferred.
    The ZIP's last unnamed field must be empty on every record.
    """
    current_header = source_header(source_zip, csv_member, expected_columns=expected_columns)
    if current_header != source_fields:
        raise ValueError(f"{month}: source field order or names differ from the reference schema")
    if "FlightDate" not in source_fields:
        raise ValueError("FlightDate is required to verify monthly partition membership")

    destination.parent.mkdir(parents=True, exist_ok=True)
    schema = bronze_schema(source_fields)
    ingest_time = datetime.now(timezone.utc)
    row_count = 0
    batch_count = 0

    with zipfile.ZipFile(source_zip) as archive:
        with archive.open(csv_member) as binary:
            reader = pacsv.open_csv(
                binary,
                read_options=pacsv.ReadOptions(
                    column_names=source_fields + [TRAILING_COLUMN],
                    skip_rows=1,
                    block_size=BLOCK_SIZE,
                ),
                convert_options=pacsv.ConvertOptions(
                    default_column_type=pa.string(),
                    strings_can_be_null=True,
                    null_values=[""],
                ),
            )
            with pq.ParquetWriter(
                destination,
                schema=schema,
                compression=compression,
                use_dictionary=True,
                write_statistics=True,
            ) as writer:
                for batch in reader:
                    if batch.num_rows == 0:
                        continue
                    unused = batch.column(batch.schema.get_field_index(TRAILING_COLUMN))
                    if pc.any(pc.is_valid(unused)).as_py():
                        raise ValueError(f"{month}: populated value in unnamed trailing CSV field")

                    flight_dates = batch.column(batch.schema.get_field_index("FlightDate"))
                    in_month = pc.fill_null(pc.starts_with(flight_dates, month), False)
                    if pc.all(in_month).as_py() is not True:
                        raise ValueError(f"{month}: CSV contains a missing or out-of-month FlightDate")

                    start = row_count + 1
                    end = row_count + batch.num_rows + 1
                    values = [
                        batch.column(batch.schema.get_field_index(name))
                        for name in source_fields
                    ]
                    values.extend(
                        [
                            pa.array([source_zip.name] * batch.num_rows, type=pa.string()),
                            pa.array([source_sha256] * batch.num_rows, type=pa.string()),
                            pa.array(range(start, end), type=pa.int64()),
                            pa.array([ingest_time] * batch.num_rows, type=pa.timestamp("us", tz="UTC")),
                        ]
                    )
                    writer.write_table(pa.Table.from_arrays(values, schema=schema), row_group_size=ROW_GROUP_SIZE)
                    row_count += batch.num_rows
                    batch_count += 1

    if row_count == 0:
        raise ValueError(f"{month}: no source observations found")
    return {
        "source_row_count": row_count,
        "bronze_row_count": row_count,
        "batches": batch_count,
        "parquet_file": destination.name,
        "parquet_bytes": destination.stat().st_size,
        "parquet_sha256": sha256_file(destination),
        "schema_fields": len(schema),
        "compression": compression,
        "row_group_size_target": ROW_GROUP_SIZE,
        "ingested_at_utc": ingest_time.isoformat(timespec="seconds"),
    }
