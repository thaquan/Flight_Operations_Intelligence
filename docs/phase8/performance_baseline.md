# M8.1 - System audit and performance baseline

Measured 28 November 2026 (03:30 UTC), on the accepted local warehouse.
The benchmark reads the existing 24-month, 14,080,680-flight population;
no index, table, database configuration or Power BI change was made.

## Environment and method

- Windows, Intel Core i5-8350U (4 cores / 8 logical processors), approximately
  16 GiB installed RAM, Docker PostgreSQL 17.12, Python 3.13.
- Database: 14,654,338,739 bytes; shared_buffers 128MB, work_mem 4MB,
  effective_cache_size 4GB, max_parallel_workers_per_gather 2, JIT on,
  block size 8192 bytes.
- A repeatable-read, read-only transaction with bounded statement and lock
  timeouts; one unmeasured result comparison/warm-up per variant followed
  by three EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) measurements per variant.
  The order alternates fact/mart, mart/fact, fact/mart.
- Deterministic ordering and exact result equivalence are required before
  timing comparisons. The airline query uses additive counts rather than
  averaging pre-rounded monthly percentages.
- Median server execution time excludes planning and client transfer.
  No cache reset or controlled cold-cache testing was performed. Docker
  had recently started, and local regression tests overlapped the early
  measurement period. Treat these as an observed baseline, not a
  controlled optimization trial or a production SLA.

## Equivalent queries

| Query | Matched rows | Fact samples (ms) | Mart samples (ms) | Fact median (ms) | Mart median (ms) |
| --- | ---: | --- | --- | ---: | ---: |
| Network monthly (scheduled, eligible, late, canceled counts) | 24 | 28178.591, 6111.922, 6032.438 | 0.121, 0.070, 0.083 | 6111.922 | 0.083 |
| Airline 2025 (scheduled, eligible, late counts) | 14 | 4346.734, 3927.646, 3898.975 | 0.454, 0.200, 0.460 | 3927.646 | 0.454 |
| Top 20 origins (scheduled traffic) | 20 | 8172.873, 5394.855, 4454.428 | 287.619, 195.434, 56.241 | 5394.855 | 195.434 |

All paired result sets matched. The network total also independently
matched all 24 months and 14,080,680 scheduled flights. The top-origin
median ratio is 27.60x for this workload. Sub-millisecond network and
airline mart timings are particularly sensitive to measurement noise;
their very large ratios are not meaningful end-to-end speedup claims.

All fact plans included sequential scans and parallel aggregate/gather
operations; they recorded approximately 744,000 shared read blocks per
execution. Each measured mart plan had zero shared read blocks (data
served from PostgreSQL shared buffers). Shared read blocks do not
necessarily represent physical disk reads. No temporary block writes
were observed. The top-origin mart scans more rows than the small
network and airline marts, and its timings varied substantially.

## Storage and index inventory

| Relation | Total bytes (including indexes) | Index bytes |
| --- | ---: | ---: |
| silver.flights | 7902543872 | 537477120 |
| gold.fct_flights | 6613229568 | 511950848 |
| gold.mart_network_monthly | 32768 | 16384 |
| gold.mart_airline_monthly | 114688 | 16384 |
| gold.mart_airport_daily | 102801408 | 20955136 |
| gold.mart_route_monthly | 26558464 | 5545984 |
| gold.mart_delay_causes | 278528 | 81920 |
| Five marts combined | 129785856 | 26681344 |

The five marts occupy approximately 123.8 MiB, about 1.96% of the
materialized fact size. This is additional storage, not a replacement
for the flight-level fact. The inventory records 15 indexes across
Silver and Gold. The fact currently has unique flight_sk and indexes
on flight_date_key and origin_airport_sk, but no source_month index.

## Engineering decisions for M8.2

1. Preserve the existing pre-aggregated marts for compatible workloads.
   They avoid full fact aggregation without changing KPI semantics.
2. Benchmark selective month/date/airport queries in the isolated
   full-scope acceptance database before proposing a new index.
   Compare B-tree and BRIN only where physical ordering and selectivity
   support the experiment; measure storage cost as well as query time.
3. Repeat measurements without concurrent regression and with explicit
   cache-state limitations. Inspect row estimates and execution plans.
4. Do not partition or migrate the production fact solely because
   the database is large. Full-year and full-population scans may be
   appropriate, and indexes can increase load/rebuild cost.
5. Keep incremental Gold experimental until all dependent mart and
   dimension behavior and recovery are validated.

## Reproduce and evidence

From the repository root, with the accepted PostgreSQL warehouse healthy:

```powershell
.\.venv\Scripts\python.exe -m src.phase8.benchmark --repetitions 3
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_phase8_benchmark.py
```

The script writes timestamped summary and full execution-plan JSON
under ignored data/tmp/phase8/. The observed summary is retained in
[baseline_results.json](baseline_results.json); full raw plans remain
local. Six new benchmark tests passed; full ETL regression returned
120 passed, 9 Dagster-only skips, and Ruff passed. The previously
accepted 20-test Dagster suite was not rerun in this milestone (no
Dagster code changed). Main Bronze manifest and the three pre-existing
Power BI file hashes were unchanged.

Earlier observations: [Bronze performance](../phase2/performance_benchmark.md),
[Gold marts](../phase3/m35_performance.md), and
[Phase 7 acceptance](../phase7/acceptance.md). Those timings use
different workloads or conditions and must not be treated as a
controlled before/after comparison.

Power BI refresh timing, new-machine reproduction, full pipeline
resource profiling, and actual database optimization are not completed
by this baseline; they remain later Phase 8 work.
