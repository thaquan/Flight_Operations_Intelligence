# Project demonstration and interview guide

## Five-minute demo

| Time | Show | Explain |
| --- | --- | --- |
| 0:00-0:40 | [Repository overview](../../README.md) and [architecture](architecture.md) | Why the fixed BTS scope, batch design and reproducible contracts matter |
| 0:40-1:30 | [Bronze](../phase2/README.md) and [Silver audit](../phase3/m32_silver_pipeline.md) | Checksums, bounded Arrow batches, month-level transactions and retry boundaries |
| 1:30-2:15 | [dbt dimensional design](../phase3/m34_dimensional_model.md) and [mart grains](../phase3/m35_gold_marts_design.md) | Physical flight grain, Unknown keys, distinct airport roles, additive KPIs |
| 2:15-3:00 | [Dagster monitoring](../phase7/monitoring_runbook.md) | 24 partitions, two backfills, read-only audit and isolated recovery |
| 3:00-4:00 | [Power BI showcase](../../README.md#power-bi-dashboard) | 21.56% historical arrival delay rate, carrier volume vs reliability and route drill |
| 4:00-5:00 | [Benchmarks](performance_baseline.md), [clean reproduction](clean_reproduction.md) | Matched outputs, workload-specific timing, trade-offs and limitations |

## Live demo safety

Start the accepted PostgreSQL service and Dagster only if available.
Use the existing [runbook](../phase7/README.md) and
[Power BI guide](../phase5/README.md). Do not reprocess or force a
full rebuild for the interview. In Dagster, select one already loaded
month in ingest_flight_month, inspect source verification and Bronze/Silver
skip messages, and show the resulting run. If a live service is unavailable,
use the existing screenshots and acceptance reports instead.

## Likely interview questions

**Why keep Bronze rather than write directly to PostgreSQL?**
The Bronze layer preserves the original physical source grain, checksum
lineage and reusable compressed files. It separates source handling from
warehouse typing and supports repeatable monthly loads.

**How do you guarantee idempotency?**
Bronze checks the accepted source and output manifest; Silver checks source
and Parquet hashes, audit counts and physical counts. An explicit reprocess
is needed for replacement. Month-level changes and the audit are committed
together under an advisory lock.

**How do you prevent duplicate flights?**
Use a source-month and source-row-number grain. The fact key is deterministic
from those fields, not a guessed unique business-flight combination.
Known missing key components are retained and reviewed, not silently deleted.

**Why use dbt and five marts?**
Keep tested transformations and explicit grain in SQL; expose additive
counts at workload-appropriate grains. A pre-aggregated mart can avoid
scanning the large fact. The trade-off is extra storage and rebuild cost.

**What happens if a source or database fails?**
Source verification may retry once; write steps fail closed. Downstream
assets stop. Silver rolls back the month on failure. Diagnose the error,
restore the dependency and rerun. Isolated drills tested these cases;
Gold publication across all models is not a single atomic transaction.

**Why not deploy incremental Gold or a BRIN index immediately?**
The incremental trial covered only a two-month fact/network workload,
and BRIN depends on physical order/selectivity. The isolated experiments
show potential, not enough evidence to migrate every model or alter the
accepted warehouse.

**How did you measure performance?**
For the SQL baseline, compare equivalent result sets first, then alternate
three EXPLAIN ANALYZE measurements per variant. Report medians and buffer
observations, not dashboard latency. Cache state was not fully controlled.
For ETL, use isolated rollback replacements and process peak memory;
durable commit and total system RAM were not measured.

**How does CI differ from real-data acceptance?**
CI runs Python tests and the entire dbt DAG on a small synthetic fixture,
including recovery assertions. Full historical acceptance is separate.
Azure DevOps is a synchronized Git remote; Azure Pipelines execution has
not been verified.

**What would you change for a production workload?**
Measure workload and freshness requirements first. Add controlled
incremental publication, broader recovery tests, credentials management,
persistent orchestration storage, alerting and deployment only when required.
Do not claim these capabilities already exist.
