# Phase 7 - Operational acceptance

**Status:** Complete for the local-first historical BTS scope (M7.1-M7.5).
**Acceptance date:** 27 November 2026.
**Accepted execution:** 26 November 2026, isolated full Gold run
a4338d96-0de0-43f5-b1d5-f03f08405879.

## Acceptance matrix

| Milestone | Evidence | Result |
| --- | --- | --- |
| M7.1 foundation | Five assets, four jobs, 24 monthly partitions; live monthly and quality runs | Accepted |
| M7.2 UI | Actual browser launch, queued execution and run history | Accepted |
| M7.3 backfill and incremental | Two backfills; 24/24 successful main months; isolated clean load, rerun and new month | Accepted |
| M7.4 recovery | Checksum retry, isolated PostgreSQL outage/restart, Silver transaction rollback, real read-only scheduler tick | Accepted |
| M7.5 monitoring | Run metrics, read-only health checks, real UI evidence | Accepted |
| M7.5 full Gold | Isolated full-population Dagster job, 11 dbt models and 65 data tests | Accepted |

See the [validation history](validation.md) and [monitoring runbook](monitoring_runbook.md)
for actual run IDs, commands, screenshots, evidence and limitations.

## Full Gold acceptance

A consistent dump of the main Silver and audit schemas was restored into
a new database, flight_m75_acceptance, on the isolated PostgreSQL instance
(port 5543). The existing main warehouse (5433) and two-month M7.3
database were not rebuilt. The copied workspace used the tracked
pipeline/dbt source and full Bronze manifest. The new database contained
24 months and 14,080,680 Silver rows before Gold execution.

| Check | Observed result |
| --- | --- |
| Silver reconciliation | PASS; 24 months, 14,080,680 rows |
| Dagster run | SUCCESS; 2/2 steps and materializations |
| dbt build | 11/11 models (9 tables, 2 views), 65/65 data tests |
| dbt node summary | PASS=76, WARN=0, ERROR=0, SKIP=0 |
| dbt build elapsed | 494.093 seconds |
| Dagster run elapsed | 540.684 seconds |
| Quality gates | 6 PASS, 2 documented REVIEW, 0 FAIL |

On 27 November, the saved Dagster events and dbt run_results.json were
read back and the main and acceptance databases independently compared
in read-only repeatable-read transactions.

| Relation | Main and acceptance row counts |
| --- | ---: |
| Silver flights | 14,080,680 |
| Gold fact flights | 14,080,680 |
| dim_airline | 16 |
| dim_airport | 359 |
| dim_date | 731 |
| mart_network_monthly | 24 |
| mart_airline_monthly | 348 |
| mart_airport_daily | 481,262 |
| mart_route_monthly | 139,287 |
| mart_delay_causes | 1,740 |

Monthly Silver and fact counts, audit source/Parquet checksums and row
counts, and the monthly network metrics used by the quality gates
matched exactly. The other seven Gold relations matched by row count.
This comparison does not claim all-column equality of every full-scale
fact or mart row. Existing dbt tests and quality gates provide the
additional validated business constraints.

Main Bronze manifest SHA-256 remained
59f4e17a4b69b65c33a6d5f3c8167dd6076583df9ab04e0e97fbac1300bed4be.
All three pre-existing Power BI working-tree files retained their
previous hashes and were excluded from Phase 7 commits.

## Regression and CI

Final local regression on 27 November: 114 passed and 9 Dagster-only
skips in the ETL environment; 20 passed in the Dagster environment
(123 unique tests across the two suites). Ruff passed.
All eight GitHub Actions runs for the four M7.5 implementation and
monitoring-evidence commits (6dfd538, d91efa4, 112cc31, 36715f7)
completed successfully. The corresponding Git commits were verified on
both GitHub and Azure DevOps. Documentation publication triggers
additional CI runs; see the live
[GitHub Actions history](https://github.com/thaquan/Flight_Operations_Intelligence/actions)
for the latest status. Azure Pipelines execution is not verified.

## Accepted limitations and next phase

- Fixed historical scope, not a streaming pipeline or live flight feed.
- Bronze/Silver use bounded monthly ingestion and idempotent reruns.
  Incremental Gold is a two-month fact/network experiment, not a
  deployed replacement for the existing full dbt rebuild.
- Full Gold acceptance used a complete isolated Silver snapshot, not
  an additional destructive rebuild of the main warehouse. Main
  Dagster Gold assets have no materialization history from this run.
- The weekly warehouse audit is stopped by default. A real isolated
  minute-schedule tick was validated, not a production weekly tick.
- Monitoring is a point-in-time report and the Dagster UI; no production
  uptime SLA, external alerting, or hosted deployment is claimed.
- Full-scale Gold failure recovery and atomic warehouse-wide publication
  are not proven. Two known source-quality REVIEW findings are retained.
- The acceptance database, dump, cloned workspace, credentials and
  runtime logs stay local and ignored; no raw data is committed.

Phase 7 is accepted for the agreed portfolio scope. Phase 8 focuses on
measured optimization and portfolio finalization. NOAA enrichment and
a second risk dashboard remain optional future enhancements.
