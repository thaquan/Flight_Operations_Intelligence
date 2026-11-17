# M3.2: Bronze-to-PostgreSQL Silver Pipeline

## Goal

Load the complete BTS 2024–2025 flight population from the verified Bronze Parquet partitions into a typed PostgreSQL Silver table. The unit of delivery is **one official monthly source observation**. No airline, airport, route, cancelled flight or diverted flight is filtered out.

This milestone covers warehouse loading and source-to-Silver reconciliation. It does not implement dbt staging, dimensional models or business KPI calculations; those are later Phase 3 milestones.

## Inputs and outputs

| Item | Location | Purpose |
| --- | --- | --- |
| Bronze partitions | `data/bronze/bts/flight_year=YYYY/flight_month=MM/part-00000.parquet` | Full 113-field Parquet observations |
| Bronze manifest | `data/bronze/_metadata/ingestion_manifest.json` | Expected rows, file paths and SHA-256 checksums |
| Silver migration | `sql/phase3/002_create_silver.sql` | Version-controlled table definition and indexes |
| Silver contract | `src/phase3/silver_contract.py` | Explicit source-to-target field mapping |
| Silver loader | `src/phase3/load_silver.py` | Preflight, transactional COPY and incremental control |
| Silver table | `silver.flights` | Typed analytical flight records and physical lineage |
| Load audit | `audit.silver_loads` | One committed record per loaded month |
| Reconciliation | `src/phase3/validate_silver.py` | Physical month, row-key and source-hash checks |

## Silver data contract

Bronze retains **all 109 official fields plus four lineage fields** as the source-of-truth landing layer. Silver selects the fields required by the planned dashboards: flight date, airline and flight identifiers, airports, scheduled and actual times, delays, cancellation/diversion indicators, duration, distance and reported delay causes. Source fields not selected for Silver remain available in Bronze and may be added through a later versioned migration.

Silver uses:

- `DATE` for flight and source months;
- `SMALLINT`/`INTEGER` for numeric calendar and airport identifiers;
- `DOUBLE PRECISION` for delay, time-duration and distance measures;
- constrained `NUMERIC(3,2)` for reported 0/1 indicators;
- `TEXT` for airline/airport codes, tail numbers, cancellation codes and all HHMM clock fields;
- `TIMESTAMPTZ` for the Bronze ingestion timestamp.

**HHMM source fields remain text on purpose.** Values such as `0005` and `2400` must not be naively parsed as local timestamps. UTC conversion and midnight/daylight-saving handling will be designed separately where needed.

The physical source observation is identified by `(source_month, source_row_number)`, which is the Silver primary key. The original source ZIP filename and SHA-256 are also preserved. This identity does not assume BTS flight numbers or tail numbers are globally unique.

## Processing and data integrity

1. Resolve the requested month or inclusive month range.
2. Verify that each Bronze partition is completed and its Parquet file matches the manifest SHA-256, row count and required columns.
3. Compare the committed Silver audit record and physical row count with the current Bronze signature.
4. Skip unchanged completed months automatically.
5. For a new month, stream bounded Arrow record batches through PostgreSQL `COPY`. A transaction contains the entire month and its audit record.
6. Validate the copied row count before committing. PostgreSQL constraints enforce unique physical row identity, valid flight-month membership and valid reported cancellation/diversion flags.
7. If a replacement is explicitly requested, remove and reload only that month **inside the same transaction**. A failed load rolls back to the previous committed month.
8. Independently reconcile all 24 physical months, source-row-number ranges, source hashes, filenames and load audit records.

The loader uses a database advisory lock to prevent concurrent runs of this pipeline. A changed file or mismatched Silver state requires inspection and an explicit `--reprocess`; it is never silently overwritten.

## Run commands

Start Docker Desktop, then from the repository root:

```powershell
docker compose up -d --wait
.\.venv\Scripts\python.exe -m src.phase3.load_silver --start 2024-01 --end 2025-12 --dry-run
.\.venv\Scripts\python.exe -m src.phase3.load_silver --start 2024-01 --end 2025-12
.\.venv\Scripts\python.exe -m src.phase3.validate_silver --report docs/phase3/m32_reconciliation.json
.\.venv\Scripts\python.exe -m pytest -q
```

Load or backfill one month:

```powershell
.\.venv\Scripts\python.exe -m src.phase3.load_silver --month 2025-06
```

If the source Parquet or Silver rows have changed, investigate first and only then authorize replacement:

```powershell
.\.venv\Scripts\python.exe -m src.phase3.load_silver --month 2025-06 --reprocess
```

The default Arrow batch size is 50,000 rows. `--batch-size` accepts values from 1 through 200,000 for local tuning. Full-population statistics and runtime measurements must come from actual execution, not estimates.

## Failure and recovery

- A failed month transaction rolls back both data rows and the audit record; earlier committed months remain usable.
- Restarting the same inclusive range skips complete, matching months and continues with missing ones.
- If PostgreSQL contains rows that do not match the Bronze signature, the loader stops and requires explicit review; it will not silently merge or delete them.
- Never delete the Docker named volume to recover from a load error. Use the recorded audit state and targeted, transactional reprocessing.
- Raw ZIP files, Bronze Parquet, local database files and credentials stay out of Git.

## Deferred work

M3.3 will add dbt source declarations and staging models. Later Phase 3 milestones will define fact/dimension grain, surrogate keys and Gold marts, with KPI logic grounded in the Phase 1 business definitions.
