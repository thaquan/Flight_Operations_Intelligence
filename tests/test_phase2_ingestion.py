"""Small ZIP fixtures exercise Phase 2 without checking in source datasets."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import zipfile

import pyarrow.parquet as pq
import pytest

from src.phase2.bronze_writer import sha256_file, source_header
from src.phase2 import ingest as ingestion_module
from src.phase2.ingest import BronzePipeline
from src.phase2.manifest import ingestion_lock, read_manifest, write_manifest
from src.phase2.validate import validate_period


FIELDS = [
    "FlightDate", "Flight_Number_Reporting_Airline", "CRSDepTime",
    "Cancelled", "Diverted", "ArrDel15", "ArrDelay", "Note",
]
ROWS = [
    ["2024-01-01", "0007", "2400", "0.00", "0.00", "0.00", "-3.00", ""],
    ["2024-01-02", "", "1230", "1.00", "0.00", "", "", ""],
    ["2024-01-03", "0012", "1300", "0.00", "1.00", "", "", ""],
]


def make_zip(path: Path, rows: list[list[str]], fields: list[str] = FIELDS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(fields + [""])
    for row in rows:
        writer.writerow(row + [""])
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("flights.csv", buffer.getvalue().encode("utf-8"))


def make_project(root: Path, rows: list[list[str]] | None = None) -> tuple[BronzePipeline, Path]:
    data = ROWS if rows is None else rows
    source = root / "data/raw/bts/2024/month_2024_01.zip"
    make_zip(source, data)
    acquisition = {
        "files": [{
            "month": "2024-01",
            "source_url": "https://example.test/official/month_2024_01.zip",
            "relative_path": source.relative_to(root).as_posix(),
            "sha256": sha256_file(source),
            "zip_bytes": source.stat().st_size,
            "csv_member": "flights.csv",
        }]
    }
    profile = {
        "monthly": [{"month": "2024-01", "rows": len(data)}],
        "by_year": {"2024": {"scheduled_flights": len(data)}},
        "overall": {"scheduled_flights": len(data)},
    }
    source_doc = root / "docs/phase1/2024_2025"
    source_doc.mkdir(parents=True, exist_ok=True)
    (source_doc / "acquisition_manifest.json").write_text(json.dumps(acquisition), encoding="utf-8")
    (source_doc / "aggregate_profile.json").write_text(json.dumps(profile), encoding="utf-8")
    return BronzePipeline(project_root=root, expected_columns=len(FIELDS)), source


def output_file(pipeline: BronzePipeline) -> Path:
    return pipeline._partition_path("2024-01") / "part-00000.parquet"


def test_bronze_preserves_source_text_nulls_and_lineage(tmp_path: Path) -> None:
    pipeline, source = make_project(tmp_path)
    result = pipeline.ingest_month("2024-01")
    assert result["status"] == "ingested"
    table = pq.ParquetFile(output_file(pipeline)).read()
    assert table.num_rows == 3
    assert table.num_columns == len(FIELDS) + 4
    assert table.column("Flight_Number_Reporting_Airline").to_pylist() == ["0007", None, "0012"]
    assert table.column("CRSDepTime").to_pylist()[0] == "2400"
    assert table.column("ArrDelay").to_pylist() == ["-3.00", None, None]
    assert table.column("source_row_number").to_pylist() == [1, 2, 3]
    assert table.column("source_file").to_pylist() == [source.name] * 3
    assert table.column("source_sha256").to_pylist() == [sha256_file(source)] * 3
    assert validate_period(pipeline, deep=True)["bronze_rows"] == 3


def test_second_run_is_a_no_op(tmp_path: Path) -> None:
    pipeline, _ = make_project(tmp_path)
    pipeline.ingest_month("2024-01")
    path = output_file(pipeline)
    initial_sha = sha256_file(path)
    previous_record = read_manifest(pipeline.state_path)["partitions"]["2024-01"]
    assert pipeline.ingest_month("2024-01") == {"month": "2024-01", "status": "skipped", "rows": 3}
    assert sha256_file(path) == initial_sha
    assert read_manifest(pipeline.state_path)["partitions"]["2024-01"] == previous_record
    assert len(list(path.parent.glob("*.parquet"))) == 1


def test_changed_source_requires_review_without_overwrite(tmp_path: Path) -> None:
    pipeline, source = make_project(tmp_path)
    pipeline.ingest_month("2024-01")
    old_output_sha = sha256_file(output_file(pipeline))
    make_zip(source, ROWS + [ROWS[0]])
    with pytest.raises(ValueError, match="source ZIP changed"):
        pipeline.ingest_month("2024-01")
    state = read_manifest(pipeline.state_path)
    assert state["alerts"]["2024-01"]["status"] == "requires_review"
    assert state["partitions"]["2024-01"]["status"] == "completed"
    assert sha256_file(output_file(pipeline)) == old_output_sha


def test_invalid_month_is_quarantined_and_marked_failed(tmp_path: Path) -> None:
    bad_rows = [ROWS[0], ["2024-02-01", *ROWS[1][1:]]]
    pipeline, _ = make_project(tmp_path, rows=bad_rows)
    with pytest.raises(ValueError, match="out-of-month"):
        pipeline.ingest_month("2024-01")
    assert read_manifest(pipeline.state_path)["partitions"]["2024-01"]["status"] == "failed"
    assert not output_file(pipeline).exists()
    assert len(list((pipeline.bronze_root / "_failed").glob("2024-01-*"))) == 1


def test_populated_trailing_column_is_rejected(tmp_path: Path) -> None:
    pipeline, source = make_project(tmp_path)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(FIELDS + [""])
    writer.writerow(ROWS[0] + ["unexpected data"])
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("flights.csv", buffer.getvalue())
    assert source_header(source, "flights.csv", expected_columns=len(FIELDS)) == FIELDS
    # Refresh the test-only Phase 1 manifest to match the deliberately modified ZIP.
    acquisition_path = tmp_path / "docs/phase1/2024_2025/acquisition_manifest.json"
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    acquisition["files"][0]["sha256"] = sha256_file(source)
    acquisition["files"][0]["zip_bytes"] = source.stat().st_size
    acquisition_path.write_text(json.dumps(acquisition), encoding="utf-8")
    pipeline, _ = make_project_from_existing(tmp_path)
    with pytest.raises(ValueError, match="populated value"):
        pipeline.ingest_month("2024-01")


def make_project_from_existing(root: Path) -> tuple[BronzePipeline, Path]:
    return BronzePipeline(project_root=root, expected_columns=len(FIELDS)), root / "data/raw/bts/2024/month_2024_01.zip"


def test_explicit_reprocess_keeps_previous_backup(tmp_path: Path) -> None:
    pipeline, _ = make_project(tmp_path)
    pipeline.ingest_month("2024-01")
    result = pipeline.ingest_month("2024-01", reprocess=True)
    assert result["status"] == "ingested"
    record = read_manifest(pipeline.state_path)["partitions"]["2024-01"]
    assert record["previous_partition_backup"].startswith("_backup/")
    assert (pipeline.bronze_root / record["previous_partition_backup"]).exists()
    assert validate_period(pipeline, deep=True)["bronze_rows"] == 3


def test_recover_preserves_untracked_partition(tmp_path: Path) -> None:
    pipeline, _ = make_project(tmp_path)
    stray = pipeline._partition_path("2024-01")
    stray.mkdir(parents=True)
    (stray / "incomplete.txt").write_text("interrupted", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Bronze partition exists"):
        pipeline.ingest_month("2024-01")
    assert pipeline.ingest_month("2024-01", recover=True)["status"] == "ingested"
    assert len(list((pipeline.bronze_root / "_recovery").glob("2024-01-*"))) == 1
    assert validate_period(pipeline)["bronze_rows"] == 3


def test_recover_interrupted_replacement_from_backup(tmp_path: Path) -> None:
    pipeline, _ = make_project(tmp_path)
    pipeline.ingest_month("2024-01")
    state = read_manifest(pipeline.state_path)
    completed = state["partitions"]["2024-01"]
    state["partitions"]["2024-01"] = {
        "status": "running", "previous_completed": completed,
        "source_sha256": completed["source_sha256"],
    }
    write_manifest(pipeline.state_path, state)
    backup = pipeline.bronze_root / "_backup" / "2024-01-simulated"
    backup.parent.mkdir(parents=True, exist_ok=True)
    output_file(pipeline).parent.rename(backup)
    assert pipeline.ingest_month("2024-01", recover=True)["status"] == "skipped"
    assert output_file(pipeline).exists()
    assert read_manifest(pipeline.state_path)["partitions"]["2024-01"] == completed


def test_validation_detects_tampered_output(tmp_path: Path) -> None:
    pipeline, _ = make_project(tmp_path)
    pipeline.ingest_month("2024-01")
    record = read_manifest(pipeline.state_path)
    record["partitions"]["2024-01"]["parquet_sha256"] = "0" * 64
    write_manifest(pipeline.state_path, record)
    with pytest.raises(ValueError, match="checksum mismatch"):
        validate_period(pipeline, deep=True)


def test_corrupt_zip_is_reported_without_creating_bronze(tmp_path: Path) -> None:
    pipeline, source = make_project(tmp_path)
    original = source.read_bytes()
    source.write_bytes(original[: len(original) // 2])
    with pytest.raises((ValueError, zipfile.BadZipFile, OSError)):
        pipeline.ingest_month("2024-01")
    state = read_manifest(pipeline.state_path)
    assert state["alerts"]["2024-01"]["status"] == "requires_review"
    assert not output_file(pipeline).exists()


def test_schema_drift_is_rejected(tmp_path: Path) -> None:
    pipeline, source = make_project(tmp_path)
    changed_fields = FIELDS.copy()
    changed_fields[1] = "UnexpectedNewFlightNumber"
    make_zip(source, ROWS, fields=changed_fields)
    with pytest.raises(ValueError, match="field order or names differ"):
        ingestion_module.write_bronze(
            source, "flights.csv", "2024-01", sha256_file(source),
            tmp_path / "drift.parquet", pipeline.source_fields,
            expected_columns=len(FIELDS),
        )


def test_failure_after_publish_quarantines_new_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pipeline, _ = make_project(tmp_path)
    original_write = ingestion_module.write_manifest

    def fail_on_completed(path: Path, state: dict) -> None:
        if state["partitions"].get("2024-01", {}).get("status") == "completed":
            raise OSError("injected manifest commit failure")
        original_write(path, state)

    monkeypatch.setattr(ingestion_module, "write_manifest", fail_on_completed)
    with pytest.raises(OSError, match="injected manifest"):
        pipeline.ingest_month("2024-01")
    assert not output_file(pipeline).exists()
    assert read_manifest(pipeline.state_path)["partitions"]["2024-01"]["status"] == "failed"
    assert len(list((pipeline.bronze_root / "_failed").glob("2024-01-*"))) == 1


def test_concurrent_ingestion_lock_is_respected(tmp_path: Path) -> None:
    pipeline, _ = make_project(tmp_path)
    with ingestion_lock(pipeline.state_path.parent):
        with pytest.raises(RuntimeError, match="Another ingestion"):
            pipeline.ingest_month("2024-01")
    assert pipeline.ingest_month("2024-01")["status"] == "ingested"
