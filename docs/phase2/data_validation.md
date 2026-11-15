# Phase 2 Data Validation

**Outcome: PASS — full source-to-Bronze reconciliation on 2026-11-15 (UTC).**

The exact machine-readable results are stored in [full_validation.json](full_validation.json). The authoritative baseline is the [Phase 1 aggregate profile](../phase1/2024_2025/aggregate_profile.json).

## Full-period results

| Check | Verified result |
| --- | --- |
| Official monthly source coverage | 24/24 months |
| Published Parquet partitions | 24/24 |
| Source rows, 2024 | 7,079,061 |
| Bronze rows, 2024 | 7,079,061 |
| Source rows, 2025 | 7,001,619 |
| Bronze rows, 2025 | 7,001,619 |
| Source / Bronze rows, entire period | **14,080,680 / 14,080,680** |
| Source + lineage schema | 109 + 4 = 113 columns |
| Parquet SHA-256 against local ingestion manifest | PASS, every partition |
| Row-level source filename and ZIP hash | PASS, all records |
| Continuous one-based source row numbers | PASS, all records |
| FlightDate matches the partition month | PASS, all records |
| Non-null ingestion timestamps | PASS, all records |

## Known source exceptions

The original anomalies from [Phase 1 validation](../phase1/2024_2025/phase1_validation.md) remain present:

1. **2024-08:** One flight without a reporting flight number is retained at `source_row_number=234964` (CSV line 234965), `2024-08-25`, `F9`, `MIA → ATL`.
2. **2025-09:** One completed flight without `ArrDel15` and `ArrDelay` is retained at `source_row_number=410706` (CSV line 410707), `2025-09-06`, `YX 5859`, `JFK → MVY`.

The deep validation code checks these exact source records. Missing values remain NULL; the observations are not deleted or imputed.

## Automated tests

Executed with `python -m pytest -q`:

- **33 passed**: 20 existing Phase 1 tests plus 13 Phase 2 tests.
- Phase 2 fixtures cover preservation of source strings and NULLs, row lineage, no-op reruns, source checksum changes, bad dates, populated unnamed trailing columns, controlled reprocessing, incomplete partition recovery, interrupted replacement recovery, checksum tampering, corrupt ZIPs, schema drift, failure during manifest publication and concurrent writer locks.

The tests use tiny CSVs generated inside temporary directories. No raw BTS archive is committed to Git.

## Validation boundaries

The ingestion and validation checks verify every source ZIP's integrity, Parquet schema and row count, and full row-level provenance. They do not compare each of the 109 source attribute strings against the CSV a second time after publication. CSV-to-Parquet fidelity is enforced by explicit string typing, strict parsing and fixture tests; a second complete cell-by-cell source comparison could be added as an independent audit later.

The Bronze layer does not assert business KPI correctness. Arrival punctuality denominators, timestamp normalization and model-level tests are reserved for later phases.
