# Phase 2 Operational Runbook

All commands below run from the repository root. Python 3.13 was used for the verified Windows run. The Phase 1 downloader requires only the standard library; Phase 2 needs PyArrow, Polars and pytest.

## Prepare the environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-phase2.txt
```

On Linux/macOS, use `.venv/bin/python` instead.

## Restore source data

The source ZIPs must be available under `data/raw/bts/2024/` and `data/raw/bts/2025/`. They can be downloaded from the [verified data Release](https://github.com/thaquan/Flight_Operations_Intelligence/releases/tag/bts-data-2024-2025-v1) or acquired directly:

```bash
python -m src.phase1.download_bts --start 2024-01 --end 2025-12
```

The two GitHub Release downloads contain the original 12 monthly ZIPs for each year; extract the **monthly ZIP files**, not their CSV members, into the corresponding yearly raw directories.

## Inspect planned work

```bash
python -m src.phase2.ingest --start 2024-01 --end 2025-12 --dry-run
```

Dry-run uses the local manifest and Parquet metadata. Actual ingestion additionally verifies source ZIP bytes and integrity.

## Ingest or backfill

One month:

```bash
python -m src.phase2.ingest --month 2024-01
```

The full verified period:

```bash
python -m src.phase2.ingest --start 2024-01 --end 2025-12
```

Re-running the same command is safe. Completed months are skipped.

## Validate the whole period

```bash
python -m src.phase2.validate --deep --report docs/phase2/full_validation.json
python -m pytest -q
```

`--deep` additionally hashes each Parquet output, scans the source filename/hash and continuous row numbers for every record, and checks the two known reviewed source anomalies. The report must show `status: pass`, 24 partitions and 14,080,680 rows.

## Reprocess and recover

To explicitly replace one validated partition (keeping a backup):

```bash
python -m src.phase2.ingest --month 2024-01 --reprocess
```

To recover an incomplete or interrupted partition:

```bash
python -m src.phase2.ingest --month 2024-01 --recover
```

Before using either command:

1. Inspect `data/bronze/_metadata/ingestion_manifest.json`.
2. Check the relevant source SHA-256 against the Phase 1 acquisition manifest.
3. Preserve the contents of `_failed`, `_recovery` and `_backup` until they are no longer needed.
4. Never overwrite a changed official ZIP merely to make ingestion pass. Re-profile and approve source revisions first.

If `data/bronze/_metadata/ingestion.lock` exists after a crash, confirm the previous Python process is no longer running before manually removing the stale lock.

## Extend to a later source month

The Phase 2 pipeline accepts months present in both Phase 1 acquisition and aggregate profiling manifests. To ingest later months, first acquire and profile the new official ZIPs and update the verified source evidence; then run Phase 2 for the new range.

## Version control

Only code, small test fixtures generated during tests, JSON validation summaries and documentation are versioned. The following stay local:

- `data/raw/` — official source ZIP files;
- `data/bronze/` — Parquet partitions, manifest, staging, backups and locks;
- `data/tmp/` — compression benchmark output files;
- `.venv/` — installed environment.
