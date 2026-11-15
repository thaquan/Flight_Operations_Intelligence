"""Incremental, resumable ingestion of official BTS ZIP files to Bronze Parquet.

Run from the repository root, for example:
    python -m src.phase2.ingest --month 2024-01
    python -m src.phase2.ingest --start 2024-01 --end 2025-12
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import time
import uuid

import pyarrow.parquet as pq

from src.phase1.download_bts import month_range, verify_zip
from .bronze_writer import bronze_schema, sha256_file, source_header, write_bronze
from .manifest import ingestion_lock, read_manifest, utc_now, write_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACQUISITION_MANIFEST = Path("docs/phase1/2024_2025/acquisition_manifest.json")
PHASE1_PROFILE = Path("docs/phase1/2024_2025/aggregate_profile.json")


class BronzePipeline:
    def __init__(
        self,
        project_root: Path = PROJECT_ROOT,
        *,
        source_manifest: Path | None = None,
        aggregate_profile: Path | None = None,
        bronze_root: Path | None = None,
        expected_columns: int = 109,
    ) -> None:
        self.project_root = project_root.resolve()
        self.bronze_root = (bronze_root or self.project_root / "data/bronze").resolve()
        acquisition_path = source_manifest or self.project_root / ACQUISITION_MANIFEST
        profile_path = aggregate_profile or self.project_root / PHASE1_PROFILE
        acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        self.sources = {entry["month"]: entry for entry in acquisition["files"]}
        self.expected_rows = {entry["month"]: entry["rows"] for entry in profile["monthly"]}
        self.expected_columns = expected_columns
        if len(self.sources) != len(acquisition["files"]):
            raise ValueError("Duplicate month in acquisition manifest")
        if set(self.sources) != set(self.expected_rows):
            raise ValueError("Acquisition and Phase 1 profiling months do not match")
        if not self.sources:
            raise ValueError("Acquisition manifest contains no source files")
        first_month = min(self.sources)
        first_source = self._source_path(self.sources[first_month])
        self.source_fields = source_header(
            first_source, self.sources[first_month]["csv_member"], expected_columns
        )
        self.schema = bronze_schema(self.source_fields)
        self.state_path = self.bronze_root / "_metadata" / "ingestion_manifest.json"

    def _source_path(self, source: dict) -> Path:
        path = (self.project_root / source["relative_path"]).resolve()
        allowed = (self.project_root / "data/raw/bts").resolve()
        if not path.is_relative_to(allowed):
            raise ValueError(f"Source file lies outside data/raw/bts: {path}")
        return path

    def _partition_path(self, month: str) -> Path:
        year, month_number = month.split("-")
        return self.bronze_root / "bts" / f"flight_year={year}" / f"flight_month={month_number}"

    def _check_current(self, record: dict | None, source: dict, month: str) -> bool:
        if not record or record.get("status") != "completed":
            return False
        if record.get("source_sha256") != source["sha256"]:
            return False
        if record.get("bronze_row_count") != self.expected_rows[month]:
            return False
        output_file = self._partition_path(month) / "part-00000.parquet"
        if not output_file.is_file() or output_file.stat().st_size != record.get("parquet_bytes"):
            return False
        try:
            metadata = pq.read_metadata(output_file)
            actual_schema = pq.ParquetFile(output_file).schema_arrow
        except Exception:
            return False
        return metadata.num_rows == self.expected_rows[month] and actual_schema == self.schema

    def _quarantine(self, path: Path, folder: str, month: str) -> Path:
        target = self.bronze_root / folder / f"{month}-{uuid.uuid4().hex}"
        target.parent.mkdir(parents=True, exist_ok=True)
        path.rename(target)
        return target

    def _restore_interrupted_backup(self, month: str, record: dict | None, destination: Path) -> None:
        if destination.exists() or not record or record.get("status") != "completed":
            return
        backup_root = self.bronze_root / "_backup"
        backups = sorted(backup_root.glob(f"{month}-*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if backups:
            destination.parent.mkdir(parents=True, exist_ok=True)
            backups[0].rename(destination)
            print(f"{month}: restored previous partition from backup", flush=True)

    def ingest_month(
        self,
        month: str,
        *,
        reprocess: bool = False,
        recover: bool = False,
        dry_run: bool = False,
    ) -> dict:
        if month not in self.sources:
            raise ValueError(f"Month {month} is absent from the Phase 1 acquisition manifest")
        source = self.sources[month]
        source_path = self._source_path(source)
        destination = self._partition_path(month)
        if dry_run:
            state = read_manifest(self.state_path)
            current = self._check_current(state["partitions"].get(month), source, month)
            return {"month": month, "status": "would_skip" if current and not reprocess else "would_ingest"}

        with ingestion_lock(self.state_path.parent):
            state = read_manifest(self.state_path)
            previous = deepcopy(state["partitions"].get(month))
            if recover:
                if previous and previous.get("status") == "running" and previous.get("previous_completed"):
                    # An interrupted replacement may have moved the old partition
                    # into _backup before publishing or committing the new version.
                    if destination.exists():
                        self._quarantine(destination, "_recovery", month)
                    self._restore_interrupted_backup(
                        month, previous["previous_completed"], destination
                    )
                    if not destination.exists():
                        raise RuntimeError(f"{month}: previous partition backup is missing")
                    state["partitions"][month] = previous["previous_completed"]
                    write_manifest(self.state_path, state)
                    previous = deepcopy(state["partitions"][month])
                self._restore_interrupted_backup(month, previous, destination)

            if self._check_current(previous, source, month) and not reprocess:
                # Recheck source bytes; matching filenames alone are not proof.
                actual_sha = sha256_file(source_path)
                if actual_sha != source["sha256"]:
                    state["alerts"][month] = {
                        "status": "requires_review",
                        "detected_at_utc": utc_now(),
                        "expected_sha256": source["sha256"],
                        "actual_sha256": actual_sha,
                    }
                    write_manifest(self.state_path, state)
                    raise ValueError(f"{month}: source ZIP changed; refresh Phase 1 evidence before reprocessing")
                return {"month": month, "status": "skipped", "rows": previous["bronze_row_count"]}

            if destination.exists() and not reprocess:
                if not recover or (previous and previous.get("status") == "completed"):
                    raise RuntimeError(
                        f"{month}: Bronze partition exists but is not a validated current output; "
                        "inspect it and use --recover or --reprocess explicitly"
                    )
                recovery_path = self._quarantine(destination, "_recovery", month)
                print(f"{month}: preserved incomplete partition at {recovery_path}", flush=True)

            if not source_path.is_file():
                raise FileNotFoundError(source_path)
            try:
                source_check = verify_zip(source_path)
                if source_check["sha256"] != source["sha256"]:
                    raise ValueError("source ZIP SHA-256 differs from Phase 1")
                if source_check["zip_bytes"] != source["zip_bytes"]:
                    raise ValueError("source ZIP byte count differs from Phase 1")
                if source_check["csv_member"] != source["csv_member"]:
                    raise ValueError("source CSV member differs from Phase 1")
            except Exception as exc:
                state["alerts"][month] = {
                    "status": "requires_review",
                    "detected_at_utc": utc_now(),
                    "error": str(exc),
                }
                write_manifest(self.state_path, state)
                raise

            started = time.monotonic()
            state["partitions"][month] = {
                "status": "running",
                "source_month": month,
                "source_sha256": source["sha256"],
                "started_at_utc": utc_now(),
            }
            if previous and previous.get("status") == "completed":
                state["partitions"][month]["previous_completed"] = previous
            write_manifest(self.state_path, state)

            staging = self.bronze_root / "_staging" / f"{month}-{uuid.uuid4().hex}"
            staging.mkdir(parents=True, exist_ok=False)
            output_file = staging / "part-00000.parquet"
            backup: Path | None = None
            published = False
            try:
                result = write_bronze(
                    source_path,
                    source["csv_member"],
                    month,
                    source["sha256"],
                    output_file,
                    self.source_fields,
                    expected_columns=self.expected_columns,
                )
                if result["bronze_row_count"] != self.expected_rows[month]:
                    raise ValueError(
                        f"{month}: source-to-Bronze row mismatch: "
                        f"{result['bronze_row_count']} vs Phase 1 {self.expected_rows[month]}"
                    )
                if pq.read_metadata(output_file).num_rows != self.expected_rows[month]:
                    raise ValueError(f"{month}: Parquet metadata row count mismatch")
                if pq.ParquetFile(output_file).schema_arrow != self.schema:
                    raise ValueError(f"{month}: Parquet schema mismatch")

                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    if not reprocess:
                        raise FileExistsError(destination)
                    backup = self._quarantine(destination, "_backup", month)
                staging.rename(destination)
                published = True
                state["partitions"][month] = {
                    "status": "completed",
                    "source_month": month,
                    "source_url": source["source_url"],
                    "source_file": source_path.name,
                    "source_relative_path": source["relative_path"],
                    "csv_member": source["csv_member"],
                    "source_sha256": source["sha256"],
                    "source_zip_bytes": source["zip_bytes"],
                    "partition": destination.relative_to(self.bronze_root).as_posix(),
                    "completed_at_utc": utc_now(),
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    **result,
                }
                if backup is not None:
                    state["partitions"][month]["previous_partition_backup"] = backup.relative_to(
                        self.bronze_root
                    ).as_posix()
                state["alerts"].pop(month, None)
                write_manifest(self.state_path, state)
                return {
                    "month": month,
                    "status": "ingested",
                    "rows": result["bronze_row_count"],
                    "bytes": result["parquet_bytes"],
                    "elapsed_seconds": state["partitions"][month]["elapsed_seconds"],
                }
            except Exception as exc:
                if published and destination.exists():
                    self._quarantine(destination, "_failed", month)
                if backup is not None and backup.exists():
                    backup.rename(destination)
                if staging.exists():
                    self._quarantine(staging, "_failed", month)
                if previous and previous.get("status") == "completed":
                    state["partitions"][month] = previous
                    state["partitions"][month]["last_error"] = str(exc)
                else:
                    state["partitions"][month] = {
                        "status": "failed",
                        "source_month": month,
                        "source_sha256": source["sha256"],
                        "failed_at_utc": utc_now(),
                        "error": str(exc),
                    }
                write_manifest(self.state_path, state)
                raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", help="Ingest one YYYY-MM month")
    parser.add_argument("--start", help="Start of inclusive backfill range")
    parser.add_argument("--end", help="End of inclusive backfill range")
    parser.add_argument("--dry-run", action="store_true", help="Show intended work without writes")
    parser.add_argument("--reprocess", action="store_true", help="Replace existing partitions after validation")
    parser.add_argument("--recover", action="store_true", help="Preserve incomplete output and retry")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args()
    if args.month and (args.start or args.end):
        parser.error("--month cannot be combined with --start or --end")
    if args.month:
        months = month_range(args.month, args.month)
    else:
        months = month_range(args.start or "2024-01", args.end or "2025-12")

    pipeline = BronzePipeline(project_root=args.project_root)
    print(f"Selected {len(months)} month(s); Bronze root: {pipeline.bronze_root}", flush=True)
    for month in months:
        result = pipeline.ingest_month(
            month, reprocess=args.reprocess, recover=args.recover, dry_run=args.dry_run
        )
        print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
