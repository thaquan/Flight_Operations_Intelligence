# Portfolio case study - Flight Operations Intelligence

## Project in one paragraph

Flight Operations Intelligence is a local-first batch data engineering and
analytics platform for 14,080,680 U.S. BTS flight observations across 24 months
(2024-2025). It preserves source lineage in Parquet, loads a PostgreSQL warehouse
with transactional monthly COPY and audit records, builds a dbt dimensional
model and five analytics marts, and orchestrates historical ingestion with
Dagster. A five-page Power BI report presents network, airline, airport,
route, delay-cause and seasonal performance. GitHub Actions verifies Python,
dbt fixture and orchestration contracts; Azure DevOps is a second Git remote.

## Evidence for a reviewer

| Capability | Demonstrated result | Evidence |
| --- | --- | --- |
| Data acquisition and ingestion | 24 checksum-verified ZIPs; 14,080,680 Bronze/Silver records | [Bronze](../phase2/README.md), [Silver](../phase3/m32_validation.md) |
| Warehouse modeling | Flight-grain fact, three dimensions and five marts; 65 dbt data tests | [ERD](../phase3/m34_erd.md), [Gold design](../phase3/m35_gold_marts_design.md) |
| Operational reliability | 24 monthly Dagster partitions, two successful backfills, idempotent reruns, isolated recovery drills | [Orchestration acceptance](../phase7/acceptance.md) |
| Data quality | 6 PASS, 2 documented source REVIEW, 0 FAIL on full scope | [Quality validation](../phase4/validation.md) |
| BI | Five pages; 11 tables, 11 relationships, 49 measures; 254 historical SQL/DAX integer comparisons | [BI acceptance](../phase5/m55_acceptance.md) |
| Query design | 5,394.855 ms fact vs 195.434 ms mart median for top-20 origin workload | [Measured baseline](performance_baseline.md) |
| Trade-offs | BRIN/B-tree and batch/memory tests, isolated and rolled back | [Index experiment](index_optimization.md), [Pipeline experiment](pipeline_performance.md) |
| Reproducibility | Fresh Git checkout, new environments, 76-node synthetic dbt build, real one-month Dagster-to-Gold trial | [Clean reproduction](clean_reproduction.md) |

## CV-ready entry (English)

**Flight Operations Intelligence | Personal Data Engineering Project**

Python, PyArrow, PostgreSQL, dbt, Dagster, Docker, GitHub Actions, Power BI

- Built a batch data pipeline processing 14.08M BTS flight records across
  24 months, using checksum-verified Parquet ingestion, transactional PostgreSQL
  COPY, source lineage and idempotent monthly loads.
- Designed a dbt star schema and five Gold marts with 65 data tests; validated
  equivalent top-origin queries and observed a 27.6x median SQL execution-time
  improvement using a pre-aggregated mart versus the flight fact.
- Orchestrated monthly ingestion and backfills with Dagster, verified failure
  recovery and rollback in isolated databases, and automated Python/dbt
  fixture checks through GitHub Actions.
- Delivered a five-page Power BI report with 49 DAX measures and documented
  architecture, quality exceptions, performance trade-offs and clean-checkout
  reproduction.

For a shorter CV, retain the first three bullets and link the repository.
These bullets are project claims, not employment experience or production SLAs.

## Business interpretation

The accepted population contains 14,080,680 scheduled flights, 13,844,731
eligible arrivals and 2,984,604 arrivals delayed by 15+ minutes. The eligible
arrival delay rate was 21.56%, rising from 20.82% in 2024 to 22.31% in 2025.
These are historical descriptive findings, not predictions or causal estimates.

## Demonstration

See [demo and interview guide](demo_interview.md). Show the accepted report
and recorded operational evidence before any live operation. Use an
unchanged month to demonstrate idempotency; do not rebuild the full
warehouse just for a short interview. The main report is already accepted.

## Boundaries

Gold remains a full dbt rebuild. The BRIN experiment and two-month
incremental trial are not deployed production changes; the Silver batch
default stays at 50,000. The weekly audit is stopped by default. The clean
reproduction trial was performed on the same physical host and did not
rerun the full 24-month pipeline or refresh the report from the new clone.
NOAA, a second dashboard, hosted deployment and Azure Pipelines execution
are outside the verified scope.
