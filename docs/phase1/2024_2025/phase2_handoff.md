# Phase 2 Handoff — Ingestion and Bronze Parquet

Phase 1 has already verified all 24 original BTS ZIPs and established a 14,080,680-row source baseline. Phase 2 must build the production-style Bronze pipeline without discarding or changing source observations.

## Required implementation

1. **Incremental monthly entrypoint:** accept a `YYYY-MM` partition and an explicit date range for backfills.
2. **Immutable source provenance:** carry source URL, ZIP SHA-256, ZIP filename, CSV member and ingestion time in the ingest manifest.
3. **Streaming CSV-to-Parquet conversion:** use Polars/PyArrow for memory-bounded processing; remove only the empty final CSV header, not populated BTS attributes.
4. **Partitioning:** `data/bronze/bts/flight_year=YYYY/flight_month=MM/`; compression, schema and row-group settings must be measured rather than guessed.
5. **Lineage:** write `source_file`, `source_sha256`, `source_row_number` and `ingested_at_utc` on every Bronze row.
6. **Idempotency:** repeated processing of unchanged ZIP bytes must not produce duplicate files or rows. If official bytes change, detect the hash mismatch and require a controlled reprocessing decision.
7. **Data-quality handling:** preserve cancelled/diverted rows, report source exceptions and avoid invalid coercions; do not silently drop unparseable records.
8. **Source-to-Bronze reconciliation:** compare monthly source CSV row counts with Parquet row counts and reconcile total volume to **14,080,680**.
9. **Tests:** use small synthetic fixtures for CI and a gated full-data validation script locally.

## Known real-source cases to handle

- Every observed month has 109 named source fields and an unnamed trailing CSV header field.
- Exactly one August 2024 flight record lacks a flight number; `source_file + source_row_number` must still identify it.
- Exactly one September 2025 completed flight lacks `ArrDel15` and `ArrDelay`; keep NULL and exclude it from punctuality denominators.
- `2400` HHMM values need explicit rollover rules if normalized times are introduced.
- Sparse cancellation/diversion/delay-cause attributes must remain nullable.
- Source candidate business keys showed no collisions among complete values in this period, but are not guaranteed unique for future months or revisions.

## Phase 2 acceptance criteria

- All 24 month partitions exist and pass Parquet schema checks.
- Exact source-to-Bronze row count reconciliation across every month and full period.
- The source SHA-256 and record provenance can be traced from any Bronze row.
- A second run of the same source set is a no-op (or atomically replaces only the intended partition without row duplication).
- Failure injection, bad ZIP and changed-content tests pass.
- README and operational runbook explain download, backfill, reprocess, storage size and recovery.

PostgreSQL Silver loading and dbt modeling begin in **Phase 3**, not Phase 2.
