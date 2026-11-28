# M8.2 - Isolated PostgreSQL index optimization

Measured on 28 November 2026, starting 13:24 UTC, on the full-scope
M7.5 acceptance database `flight_m75_acceptance` (loopback port 5543).
PostgreSQL 17.12, 24 months and 14,080,680 scheduled flights.

## Method and safety

The guarded [experiment](../../src/phase8/index_experiment.py) compares
the original three fact indexes with a temporary BRIN or B-tree on
`source_month`. It refuses the main warehouse and other database names,
checks the historical scope and existing index inventory, and requires
an idle acceptance database. The experiment creates each candidate in
a savepoint inside a repeatable-read transaction, rolls back the candidate
after measurement, and rolls back the whole transaction on exit. No
candidate index is deployed to the accepted warehouse or dbt models.

Each stage compares three fact-query results with their existing Gold
mart equivalents, then performs three EXPLAIN ANALYZE BUFFERS runs per
query with alternating query order. The four stages are baseline, BRIN,
B-tree, and baseline after rollback. Planner settings are unchanged;
no scan type is forced. There is no cache flush, independent index-build
replication or controlled cold-cache comparison. No regression tests
were run concurrently during these measurements.

## Exact result checks

All four stages matched the same three additive KPI counts (scheduled,
eligible, late arrivals) from Gold marts:

| Scope | Scheduled | Eligible | Late |
| --- | ---: | ---: | ---: |
| December 2025 | 582304 | 571924 | 153113 |
| December 2025, origin airport key 1013930 | 27790 | 27007 | 10531 |
| Full year 2025 | 7001619 | 6879484 | 1534638 |

## Observed execution times

Median PostgreSQL server execution time, milliseconds, three samples
per query per stage (not dashboard or client latency).

| Workload | Baseline | BRIN | B-tree | Baseline after rollback |
| --- | ---: | ---: | ---: | ---: |
| Single month | 2386.193 | 834.940 | 952.343 | 2426.666 |
| Origin and month | 2271.378 | 261.962 | 261.381 | 1964.984 |
| Full year | 3546.749 | 3566.933 | 3623.463 | 3343.274 |

The BRIN candidate reduced observed median time by about 2.86x for
one month and 8.67x for origin/month versus the first baseline. Against
the post-rollback baseline, the corresponding ratios are about 2.91x
and 7.50x. The full-year query showed no material benefit; its plan
remained a sequential scan. The spread in repeated baselines is a
reminder that these are local observations, not guaranteed speedups.

| Candidate | Build time (seconds) | Index bytes |
| --- | ---: | ---: |
| BRIN (default pages_per_range) | 4.989 | 172032 |
| B-tree | 18.386 | 97607680 |

BRIN occupied 168 KiB versus approximately 93.09 MiB for B-tree, about
567 times less space for this particular snapshot. Build time is one
observation per candidate, not a replicated build benchmark.

## Plan observations and decision

- Single-month baseline used a sequential scan; both candidates used
  bitmap index and bitmap heap scans. Shared read blocks declined from
  roughly 728,000 to 30,000-36,000.
- Origin/month baseline used the existing origin index; both candidates
  combined the month and origin indexes with BitmapAnd. Shared read
  blocks declined from roughly 180,000 to at most 7,009 in the candidate
  samples. Cache state differs between samples; shared reads do not
  necessarily mean physical disk reads.
- Full-year plans did not use either new month index.
- The global source_month correlation statistic was -0.14193362.
  Despite that modest correlation, the measured BRIN candidate was
  effective for the chosen December predicate; a single statistic does
  not establish all block-range selectivity. Different months or future
  rebuild ordering may produce different results.

Prefer BRIN as a candidate for selective fact-level month predicates
on this snapshot. Preserve existing indexes and use the pre-aggregated
marts for compatible analytical queries. No production change is made:
test other months/selectivities, rebuild overhead and repeatability
before accepting a dbt index change. A large table alone does not justify
partitioning or incremental migration.

## Reproduce

With the M7.5 isolated acceptance database restored and idle, run from
the repository root:

```powershell
.\.venv\Scripts\python.exe -m src.phase8.index_experiment --repetitions 3
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_phase8_benchmark.py
```

The script retains timestamped summary and full plans under ignored
`data/tmp/phase8/`. The observed summary is published as
[index_results.json](index_results.json); raw execution plans stay local.

Final read-only checks verified both main and acceptance audit/network
totals (24 months, 14,080,680 flights), the original three fact indexes
on both databases and exact original acceptance index definitions.
No experimental index remains. Bronze manifest and all three pre-existing
Power BI file SHA-256 hashes were unchanged. Ruff passed, benchmark
tests 8/8 passed, and ETL regression returned 122 passed, 9 Dagster-only
skips. No Dagster code changed. No production query/index migration,
Power BI refresh benchmark or full pipeline profiling is claimed.
