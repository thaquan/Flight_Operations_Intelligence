# Phase 4 — Data Quality & CI

Phase 4 adds reproducible quality gates to the 2024–2025 flight warehouse and a small, fully synthetic CI dataset. The production-size check is **read-only**; CI does **not** download BTS raw files or connect to the local warehouse.

## Deliverables

| Component | Purpose |
| --- | --- |
| `src/phase4/quality_gates.py` | Source-to-mart counts, SHA-256 audit, segment KPIs, eligible-arrival denominators, Phase 1 baseline comparison |
| `src/phase4/ci_fixture.py` | Seed and verify 10 synthetic flights in an isolated `flight_ci` database; test rollback behaviour |
| `sql/phase4/ci_seed.sql` | Reproducible Silver input, including NULL fields, cancellations, diversions, unknown members and a leap day |
| `.github/workflows/ci.yml` | Python lint/tests, PostgreSQL fixture, full dbt build/tests, recovery tests and quality gates |
| `tests/test_phase4_*.py` | Offline quality-gate and CI contract regression tests |
| `quality_report.json` | Captured result from the full two-year local warehouse |

## Validation summary

On November 18, 2026, the local full dataset check returned **6 PASS / 2 REVIEW / 0 FAIL** across all **24 months**. All **14,080,680 scheduled flight rows** reconcile between Silver, Gold and the network mart. The two REVIEW findings are documented source-data exceptions, not failed transformations:

- **August 2024:** one record lacks a component of the candidate business key; preserve the original source-row lineage.
- **September 2025:** one completed flight lacks `ArrDel15`, so it is excluded from the on-time/late arrival denominator.

Python tests: **70 passed**. The isolated PostgreSQL fixture successfully completed **76 dbt nodes** (11 models, 65 data tests), recovered from four intentionally invalid transactions, and passed the fixture quality gates. Ruff lint passed.

These are **local results**; GitHub-hosted workflow execution remains unverified until this commit is pushed. See [validation](validation.md), [CI runbook](ci_runbook.md) and [machine-readable report](quality_report.json).

## Exit criteria

- Production reconciliation checks pass; known source anomalies are visible as REVIEW.
- A clean, tiny synthetic database can build the complete dbt DAG without raw BTS downloads.
- Bad insert/update transactions roll back and do not alter accepted row counts.
- Python and SQL tests run automatically in the workflow once pushed.

**Next:** Phase 5 — Power BI dashboards using the Gold marts and the documented KPI definitions.
