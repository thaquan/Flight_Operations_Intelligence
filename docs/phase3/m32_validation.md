# M3.2 Silver Validation Record

## Observed full-population results

The complete BTS 2024–2025 Bronze dataset was loaded into PostgreSQL `silver.flights` and then reconciled directly against the Phase 2 ingestion manifest.

| Verification | Observed result | Status |
| --- | --- | --- |
| Date range | 2024-01 through 2025-12 | Pass |
| Expected / present partitions | 24 / 24 | Pass |
| Bronze source rows | 14,080,680 | Pass |
| Physical Silver rows | 14,080,680 | Pass |
| Per-month row counts | Every month matched | Pass |
| Physical source row-number ranges | Every month matched 1 through expected count | Pass |
| Source ZIP filenames and SHA-256 values | Every month matched | Pass |
| Monthly load audit | All 24 records matched manifest and physical counts | Pass |
| Unexpected Silver months | None | Pass |
| Unchanged second run | All 24 months skipped | Pass |
| Python test suite | 45 passed | Pass |
| Silver table and indexes | 7,536 MB at verification | Measured |

The generated [reconciliation report](m32_reconciliation.json) provides the exact expected and measured row count for each month, the verification time, and its individual status. All 24 monthly entries have status `pass` and no reported issues.

## Execution details

- The first full load completed without a database type-conversion error.
- Inputs were validated against the Bronze manifest before SQL modification.
- Monthly PostgreSQL `COPY` loads and audit inserts were committed atomically.
- The second full-period run completed successfully without loading a single duplicate month.
- The database remained in the Docker named volume; no local database file was added to Git.
- Silver contains 62 selected Bronze fields, an explicit source-month key and a Silver load timestamp. The original 109 source fields are still retained in Bronze.

## Limitations and next work

This validation confirms source-to-Silver completeness, lineage consistency and repeatable loading. It does not validate dbt transformations, downstream KPI denominators, flight/weather time-zone joins or dashboard outputs. Those checks are scheduled for later milestones and phases.

The explicit `--reprocess` path is implemented transactionally but was not used for the 24-month verification run; no historical month was destructively replaced merely to test that option.
