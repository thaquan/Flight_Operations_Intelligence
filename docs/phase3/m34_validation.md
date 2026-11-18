# M3.4 Dimensional Modeling Validation

## Verified environment and source

Verification performed locally on 2026-11-18 using PostgreSQL 17.12,
dbt Core 1.11.17 and dbt-postgres 1.11.0. The source remained the
unfiltered 2024-01 through 2025-12 BTS reporting-carrier population.

| Source verification | Observed result | Status |
| --- | ---: | --- |
| Silver flight rows | 14,080,680 | Pass |
| Months | 24 | Pass |
| Distinct airline DOT IDs | 15 | Measured |
| Distinct origin/destination airport IDs | 358 / 358 | Measured |
| Missing airline/origin/destination IDs | 0 / 0 / 0 | Measured |
| Maximum monthly source-row position | 634,613 | Within key range |

## Gold model materialization

| Relation | Actual rows | Result |
| --- | ---: | --- |
| `gold.dim_airline` | 16 | 15 reporting carriers + Unknown |
| `gold.dim_airport` | 359 | 358 airports + Unknown |
| `gold.dim_date` | 731 | All calendar dates in 2024-2025 |
| `gold.fct_flights` | 14,080,680 | Complete source observation population |

All four table materializations completed successfully in PostgreSQL.
First-time dimension creation took **98.25 seconds**; fact creation
with indexes took **195.30 seconds**. The physical fact and its indexes
occupied **6,307 MB** when measured using
`pg_total_relation_size`. These are local observations, not storage or
speed guarantees for other machines.

## Test results

| Test | Actual result | Status |
| --- | --- | --- |
| dbt parse | 6 models, 33 data tests, 1 source | Pass |
| dbt M3.4 data tests | 24 / 24 | Pass |
| Surrogate key uniqueness and non-NULL | Checked on fact/dimensions | Pass |
| All four fact-to-dimension relationships | No orphan keys | Pass |
| Unknown members | Exactly one for carrier/airport | Pass |
| Monthly Silver-to-Fact counts | Every month matched | Pass |
| Yearly staging-to-Fact KPI numerators/denominators | Matched | Pass |
| Flight source position range | No rows outside 1..9,999,999 | Pass |
| Python regression suite | 52 / 52 | Pass |

The M3.4 dbt test run finished in **144.62 seconds**, with no warnings,
errors or skipped tests. The new Python tests run without needing dbt
or a live PostgreSQL connection.

### Direct Fact KPI query

| Year | Scheduled | Eligible arrivals | Arrivals >=15 minutes late | Late arrival rate |
| --- | ---: | ---: | ---: | ---: |
| 2024 | 7,079,061 | 6,965,247 | 1,449,966 | 20.82% |
| 2025 | 7,001,619 | 6,879,484 | 1,534,638 | 22.31% |

These are directly observed from `gold.fct_flights`, consistent with
the independently generated Phase 1 population report and M3.3 staging.
No flight is dropped during a dimension join because the Fact keys
are derived before any dimension lookup.

## Rebuild/idempotency verification

A second `dbt run --select fct_flights` completed successfully in
**179.55 seconds** (same 14,080,680 rows). After the rebuild, a
direct read returned:

- 14,080,680 Fact rows;
- 24 distinct source months;
- first month 2024-01-01, last month 2025-12-01.

This verifies repeatable **full-table rebuild** behavior, not
incremental upserts. The original Silver, Bronze and monthly load
audit were not rewritten by the dbt runs.

## Remaining limitations

- The dimensions are representative lookups, not time-versioned SCD2
  snapshots. Source attributes can change over time.
- PostgreSQL fact/dimension tables have key indexes and dbt tests;
  physical FK constraints are not installed.
- Full Fact rebuilds duplicate source storage and take several
  minutes; an atomic month-replacement incremental strategy requires
  separate design and performance verification.
- Reporting-level Gold aggregation and source-to-mart KPI validation
  remain for M3.5 and M3.6.
