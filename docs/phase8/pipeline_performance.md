# M8.3 - Pipeline throughput and memory evaluation

Measured on 28 November 2026, using the isolated January 2024 Bronze
partition from M7.3 and its two-month PostgreSQL database
(flight_m73_test, loopback port 5543). The measured month has 547,271
rows. The accepted main warehouse and production ETL configuration
are unchanged.

## Method

The [benchmark](../../src/phase8/pipeline_benchmark.py) verifies the
isolated Parquet checksum and schema against its own Bronze manifest.
Each configuration uses a fresh Python process. For reads, one warm-up
and three timed Arrow batch scans check row count and source-row-number
sum; the Silver projection includes 62 of 113 Bronze columns. This
check is not a proof of every individual value. The existing loader
validates full batch lineage when copying rows.

The three timed replacement workloads call the actual existing
load_month function with reprocess=True and the selected batch size.
They include reading, validation, CSV conversion, DELETE, PostgreSQL
COPY, row-count and audit checks, but exclude the final outer rollback
and exclude a durable transaction commit. The inner loader transaction
is a savepoint inside an outer transaction forced to roll back. One
full replacement sample per configuration is retained in the final
verified pass. A session-level advisory lock and local database guard
protect the isolated scope. No other client may use that database
during the experiment; internal maintenance workers are allowed.

Memory is the fresh Python process lifetime peak working set (Windows),
and the Arrow default memory pool peak allocation. These overlap and
must not be added. Neither metric measures the PostgreSQL backend,
Docker VM, OS cache or total system memory.

## Parquet scans

Median seconds from three measurements after warm-up. Memory in bytes.

| Batch rows | Projection | Samples (s) | Median (s) | Python peak bytes | Arrow peak bytes |
| ---: | --- | --- | ---: | ---: | ---: |
| 25000 | Silver (62) | 0.557446, 0.620008, 0.663315 | 0.620008 | 205398016 | 53703744 |
| 50000 | Silver (62) | 0.788135, 0.811556, 0.700044 | 0.788135 | 273801216 | 88683520 |
| 100000 | Silver (62) | 0.761560, 0.752137, 0.546557 | 0.752137 | 406458368 | 160639872 |
| 50000 | All (113) | 0.668198, 0.660799, 1.147605 | 0.668198 | 316416000 | 122481984 |

Projection reduced the measured peak memory at 50,000 rows, but did
not consistently reduce elapsed time. The scan work is much smaller
than the replacement workload; these are different operations and
their times should not be directly subtracted to estimate COPY cost.

## Silver replacement

| Batch rows | Wall seconds | Rows/s | Python peak bytes | Arrow peak bytes | Rollback seconds |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 25000 | 30.416 | 17993.0 | 241713152 | 55248192 | 0.002 |
| 50000 (current default) | 40.376 | 13554.5 | 267984896 | 91054016 | 0.003 |
| 100000 | 37.802 | 14477.1 | 394485760 | 164805248 | 0.002 |

All three runs processed exactly 547,271 rows. The final verified
pass compared monthly row counts, aggregate row hashes and complete
audit records before and after; the fingerprint matched. Both months
(1,066,492 rows) were preserved. The hash comparison is not a formal
collision-free row-by-row proof.

An earlier attempt was blocked by the checksum guard before loading:
the main and isolated Parquet artifacts came from the same source ZIP
but were independently generated. The benchmark was corrected to
use the isolated artifact. A subsequent pass completed all three
replacement calls and their individual rollback checks, with 46.306,
46.271 and 47.747 seconds for 25k, 50k and 100k respectively, but the
final fingerprint check stopped at a conservative peer guard. A later
read-only inspection found no client peers and observed a recent
autovacuum. The guard was refined to distinguish client backends
from maintenance workers, and the final complete pass above succeeded.
The earlier timing observations are not treated as a second complete
fingerprint-verified benchmark.

No cache flush or randomized load-order experiment was performed;
internal maintenance can affect timing. Rolled-back writes can
still generate WAL, dead tuples and physical space changes in the
isolated database, so this is not a zero-I/O workload. The main
warehouse was read only for final reconciliation.

## Historical dbt and Dagster evidence

Re-read the saved full-scope M7.5 dbt run_results.json and the persisted
Dagster run records. No new full Gold build was executed for M8.3.

| Stage or node | Observed time (s) |
| --- | ---: |
| Full Dagster Gold acceptance | 540.684 |
| dbt build (11 models, 65 tests) | 494.093 |
| fct_flights model | 156.638 |
| dim_airport model | 82.255 |
| assert_fact_kpi_totals test | 75.182 |
| mart_airport_daily model | 67.859 |
| assert_arrival_kpi_flags test | 62.555 |
| unique_fct_flights_flight_sk test | 44.615 |
| mart_delay_causes model | 43.435 |
| warehouse_quality Dagster step | 8.15 |

dbt node execution times overlap with two threads and must not be summed
to obtain wall time. The full Gold run was SUCCESS (76/76 nodes);
quality was 6 PASS, 2 documented REVIEW and 0 FAIL. The 25 main runs
(24 ingestion and one audit) remain SUCCESS, median 6.861 s, maximum
103.040 s; those ingestion runs skipped existing months. Three
isolated monthly runs were SUCCESS, median 80.978 s, maximum 81.736 s
(two clean loads and one skip). These scopes are not directly comparable
to the rolled-back replacement measurements.

## Decisions

- Keep the current default batch of 50,000 for now. A 25,000-row batch
  is a promising lower-memory option on constrained machines; it was
  faster in the final pass and essentially tied in the earlier pass.
  The 100,000-row variant consumed substantially more Python/Arrow
  memory without a consistent speed advantage.
- Preserve column projection, bounded batches, lineage validation,
  transactional COPY and audit checks. Do not remove correctness
  tests to reduce runtime.
- Prioritize fact construction and expensive full-population dbt
  validation/aggregation when future throughput requires optimization.
  Do not deploy incremental Gold until all marts, dimensions, corrections
  and recovery have been validated. Existing historical scope does not
  justify a risky migration solely for portfolio claims.
- Power BI refresh/memory and clean-machine deployment have not been
  benchmarked here. Full-load throughput under durable commit, broader
  month coverage, peak database memory and controlled repeatability
  remain limitations.

## Reproduce and verify

With the original M7.3 isolated database available and idle, the
isolated Bronze artifact intact, and the M7.5 dbt result artifact
available, run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m src.phase8.pipeline_benchmark
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_phase8_benchmark.py
```

The script checkpoints results under ignored data/tmp/phase8/ after
each successful configuration. Only a result with
isolated_fingerprint_restored=true is a complete run. The verified
summary and historical node timings are published in
[pipeline_results.json](pipeline_results.json). No source data,
credentials or raw runtime logs are published.

Final read-only main and isolated audit/network totals were 24 months /
14,080,680 flights and two months / 1,066,492 flights respectively.
Bronze manifest and three existing Power BI file hashes were unchanged.
Ruff passed, benchmark tests 10/10 passed, and full ETL regression
returned 124 passed and 9 Dagster-only skips. No Dagster implementation
changed. M8.3 is accepted as a performance evaluation, not a claim
of a deployed production speedup.
