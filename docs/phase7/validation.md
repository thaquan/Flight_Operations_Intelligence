# M7.1 - Orchestration foundation validation

Verified locally on 24 November 2026 with Windows, Python 3.13.15,
Dagster 1.13.31 and PostgreSQL 17.12. The accepted report baseline remains
93cf3dd; no PBIP, PBIR, semantic model, existing ETL or dbt source changes
were made by this milestone.

## Verification

| Check | Observed result |
| --- | --- |
| Dagster isolated environment | Installed; pip check passed |
| Pipeline environment tests | 108 passed, 8 Dagster-only skips (103 existing + 5 new) |
| Orchestration environment tests | 13 passed, no warnings on final run |
| Ruff | Passed for Phase 4, 5 and new Phase 7 code/tests |
| Definitions/workspace | CLI validation passed after correcting working directory |
| Instance configuration | QueuedRunCoordinator; max concurrent runs = 1 |
| Local PostgreSQL | Docker service healthy; database check passed |
| Bronze manifest | 24 completed partitions |
| Silver load audit and Gold network mart | 24 months, 14,080,680 rows/flights |

## Actual Dagster executions

- Monthly job ingest_flight_month, partition 2024-01:
  run 5586673a-4707-4b97-a0d2-565dee262d0c, SUCCESS.
  Source hash verified; Bronze and Silver both skipped 547,271 existing
  records; three materializations; Bronze manifest SHA-256 unchanged.
  Engine duration 9.18 s.
- audit_job:
  run 11d5b115-3578-4c60-99d5-6919208041b0, SUCCESS.
  Full-scope quality gate status REVIEW: 6 PASS, 2 REVIEW, 0 FAIL.
  All 24 months and 14,080,680 scheduled flights reconcile. The two
  reviewed exceptions are the previously documented August 2024 missing
  business-key component and September 2025 missing ArrDel15.
  Engine duration 1m41s.

Run history and compute logs are retained in ignored local data/tmp/dagster-home.
The audit job's successful exit means no failing gates, not that all
findings have PASS status.

## Remaining scope at M7.1 (historical)

- Full Gold rebuild ordering and failure propagation were verified with
  a simulated runner; a live full dbt rebuild was deliberately not
  repeated against the accepted warehouse.
- Existing partition skip behavior was demonstrated for two actual months (M7.1 and M7.2).
  A clean load and multi-month Dagster backfill need an isolated database
  acceptance run; existing Bronze/Silver unit tests cover lower-level
  ingestion and recovery contracts.
- Weekly read-only audit schedule is configured but STOPPED by default;
  no real daemon-triggered schedule tick or external
  alert delivery has been verified.
- Gold remains full-rebuild; incremental Gold models, deployment and
  operational recovery drills are follow-up work.
- The dedicated GitHub Actions workflow is authored but has not run
  remotely yet. No Git commit or push is part of this validation.

## M7.2 - Dagster UI and queued execution

Verified locally on 24 November 2026 using the persistent Dagster
instance and a real Chromium browser controlled by Playwright. The
webserver was bound to 127.0.0.1:3000, returned HTTP 200, and the daemon
processed the run queue. Playwright was installed only as a local
acceptance tool, not a new pipeline dependency.

- Asset Catalog displayed all five assets; the global lineage view
  displayed the flight_ingestion and warehouse groups.
- Run history displayed both M7.1 runs and the new M7.2 run as Success.
- In ingest_flight_month, the browser opened Materialize all, filtered
  the partition picker to 2025-12, selected exactly one partition and
  clicked Launch 1 run. No all-month materialization was requested.
- Run 4b8913ef-f46f-4539-b161-0efa63637941 moved from Queued to Started
  to Success. Three asset materializations and three successful steps
  were verified in stored events and the browser run-detail view.
  UI-reported duration: 9 seconds. Bronze and Silver both skipped the
  existing 582,304 rows after source verification.
- Bronze manifest SHA-256 was unchanged:
  59f4e17a4b69b65c33a6d5f3c8167dd6076583df9ab04e0e97fbac1300bed4be.
- Read-only SQL confirmed 24 Silver audit months and 24 Gold network
  months, both totaling 14,080,680 flights.
- Silver partition view showed 2 materialized, 22 missing, 0 failed.
  This is Dagster event history, not missing warehouse data.
- Automation view displayed the Monday 02:00 UTC audit schedule.
  It remains stopped; no scheduled tick was tested.
- Three pre-existing Power BI working-tree files retained their exact
  SHA-256 hashes. No report or semantic model edits were made.

Local browser captures are retained under ignored data/tmp/dagster-ui.
The browser automation initially encountered navigation/locator timeouts;
the final direct job and run views and single-partition launch succeeded.
A clean load, multi-month backfill, full Gold rebuild, failure recovery
and a real scheduler tick remain outside this acceptance scope.

## M7.3 - Backfill and incremental processing

Verified locally across 24-25 November 2026, using the persisted Dagster
run history and read-only warehouse reconciliation after reconnecting.

### Accepted warehouse: 24 monthly partitions

- UI backfill xadpzmsy (2024-02 through 2024-03): COMPLETED_SUCCESS.
- UI backfill fncvwkbc (2024-04 through 2025-11): COMPLETED_SUCCESS.
- Together with the M7.1 and M7.2 runs, the stored main instance contains
  24 distinct successful monthly ingestion runs and one successful audit
  run. No monthly run failed.
- Bronze and Silver skip logs independently sum to 14,080,680 rows across
  the 24 months. No source month was rewritten.
- Main Silver contains 14,080,680 rows; its audit and Gold network mart
  each cover 24 months and reconcile to the same population.
- Main Bronze manifest SHA-256 remains
  59f4e17a4b69b65c33a6d5f3c8167dd6076583df9ab04e0e97fbac1300bed4be.

### Isolated clean load and idempotent rerun

The test workspace is under ignored data/tmp/m73-isolated, with copies
of the two official ZIPs, pipeline/dbt source and reference manifests,
a separate local .env and Dagster instance. The dedicated Docker Compose
project flight_m73_isolated uses its own volume, database flight_m73_test
and loopback port 5543. The accepted warehouse stays on port 5433.

| Month / operation | Dagster run ID | Bronze | Silver | Rows | Engine |
| --- | --- | --- | --- | ---: | ---: |
| 2024-01 clean load | beac8e27-6354-4a20-9fc0-840af08a59d8 | Ingested | Loaded | 547,271 | 81 s |
| 2024-01 rerun | 9b1deea5-d6c3-4608-9a69-f8ed48cf162b | Skipped | Skipped | 547,271 | 8.01 s |
| 2024-02 new month | dcb5287a-2113-41db-a686-98e15208faab | Ingested | Loaded | 519,221 | 80 s |

All three runs succeeded. Isolated Silver has exactly two audit months
and 1,066,492 rows, matching the sum of the two distinct source months.
The rerun did not increase the population. The 24-month reference
quality gate is intentionally not used to judge this partial warehouse.

### Gold strategy experiment (not a production migration)

On the isolated database, dbt run --threads 2 completed all 11 models
(9 tables, 2 views) in 40.58 seconds, with 0 model errors. This was a
model build, not an execution of the 65 dbt data tests.

The reproducible experiment in src/phase7/benchmark_incremental.py
requires the isolated database and its compiled dbt SQL. It compares
identically indexed PostgreSQL temporary fact tables populated from the
actual compiled staging-to-fact query, and computes the network mart
from the monthly fact. It cannot run against the main database settings.

| Operation | Rows | Elapsed |
| --- | ---: | ---: |
| Full fact insert (two months) | 1,066,492 | 33.150 s |
| January fact insert | 547,271 | 24.098 s |
| February fact insert | 519,221 | 17.599 s |
| January network insert | 1 | 1.042 s |
| February network insert | 1 | 2.277 s |
| February transactional replacement (fact + network) | 519,221 deleted and inserted; 1 network row replaced | 24.226 s |

The experiment deliberately changed one temporary February fact key and
one temporary network metric to represent stale target data, then deleted
and recomputed the affected month in a single transaction. Exact
all-column, key-aligned comparisons against the isolated dbt full-build
returned zero mismatches for the full fact, monthly fact and monthly
network mart. Obsolete fact key count after replacement: zero.

Timings are single local observations on a two-month dataset, including
different operations and cache states. They are not a production SLA or
proof that every incremental model is faster. February-only fact insert
processed about 48.7% of the two-month row population. The accepted Gold
materializations are unchanged. No persistent production incremental
model or production source-update mechanism is claimed.

### Engineering decision and remaining work

- Use bounded monthly ingestion/backfill for Bronze and Silver; existing
  checksum and transactional contracts remain in force.
- Candidate future Gold method: replace the complete changed month
  transactionally, not append-only or key-only upsert, so obsolete keys
  and aggregate groups disappear as well.
- Retain full rebuild for dimensions whose winning attributes depend on
  observations across months. Evaluate the four remaining analytics
  marts independently (including airport/day/role grain and delay-cause
  group share); the proof here covers only fact and network.
- Keep the accepted production dbt build unchanged until all affected
  models, source-change semantics, audit behavior and recovery have been
  verified. Full-scale performance and concurrent readers are untested.
- Next: M7.4 scheduling and failure recovery, then M7.5 observability,
  CI acceptance and portfolio evidence. The weekly audit remains
  disabled until explicitly tested and enabled.
