# Phase 4 validation record

Date: November 18, 2026 (local and hosted verification). GitHub-hosted run: **[passed](https://github.com/thaquan/Flight_Operations_Intelligence/actions/runs/44340972773)** for commit `09d3b1a`.

## Full-size data quality

Command from the repository root (after starting the existing PostgreSQL warehouse and configuring `.env`):

```powershell
.\.venv\Scripts\python.exe -m src.phase4.quality_gates --mode full --report docs/phase4/quality_report.json
```

Status: **REVIEW — 6 PASS, 2 REVIEW, 0 FAIL**. This mode queries the existing warehouse without rebuilding or writing it.

| Reconciled KPI | Count |
| --- | ---: |
| Source months | 24 |
| Scheduled flights | 14,080,680 |
| Completed flights | 13,844,732 |
| Cancelled flights | 199,191 |
| Diverted flights | 36,757 |
| Eligible arrivals | 13,844,731 |
| Late arrivals (15+ minutes) | 2,984,604 |
| On-time arrivals | 10,860,127 |

Passing checks cover month completeness, Silver/Gold row parity, Bronze-to-Silver audit counts and source SHA-256 hashes, airline/route/airport segment aggregates, eligible arrival denominators, and seven Phase 1 population baselines.

Two transparent exceptions remain for upstream data quality:

1. **2024-08** — a record with an incomplete candidate business key. It is retained rather than silently deleted.
2. **2025-09** — a completed record with unknown `ArrDel15`. It is not incorrectly counted as on-time or late.

An explicit **FAIL** makes the quality command exit nonzero; source exceptions classified **REVIEW** remain visible in the JSON output without failing the job.

## Regression and CI fixture

- `python -m pytest -q -p no:cacheprovider`: **70/70 passed** (Phase 1–4 tests).
- `ruff check --select E4,E7,E9,F,I src/phase4 tests/test_phase4_quality_gates.py tests/test_phase4_ci_workflow.py`: **passed**.
- PostgreSQL 17 test container with DB `flight_ci`: **10** synthetic Silver records across three months.
- `dbt build --project-dir dbt --profiles-dir dbt --threads 2`: **76/76 nodes passed** (11 models and 65 tests).
- `python -m src.phase4.ci_fixture verify`: fixture KPIs/unknown dimension correct and **4/4** bad-transaction rollback cases passed.
- `python -m src.phase4.quality_gates --mode fixture`: **6 PASS / 0 REVIEW / 0 FAIL**.
- Re-running the seed kept the synthetic Silver population at exactly **10 rows** (idempotent).

The local fixture runs against its own isolated database/port and never replaces the real warehouse. The GitHub-hosted workflow independently passed its Python lint/tests, synthetic PostgreSQL seed, dbt DAG, rollback checks and fixture quality gates. The **full 24-month reconciliation remains a separate local warehouse check**, not part of the lightweight hosted CI job.
