# Engineering decisions and trade-offs

The decisions below describe the accepted historical portfolio scope,
not generic recommendations for every flight-data system.

| Decision | Reason | Trade-off / evidence |
| --- | --- | --- |
| Fixed 24-month official BTS scope | Reproducible baseline and known source exceptions | No live feed; new months need manifest/profile acceptance |
| Local Parquet Bronze, ZSTD, bounded Arrow batches | Compact immutable source-derived layer; lineage and bounded memory | Local disk and manifest are operational dependencies; [Bronze evidence](../phase2/performance_benchmark.md) |
| PostgreSQL 17 and transactional COPY | Relational integrity, auditable month-level recovery | Fact and Silver consume significant disk space; [Silver pipeline](../phase3/m32_silver_pipeline.md) |
| Preserve source row grain | Candidate business identifiers may be missing or nonunique | Surrogate key tied to accepted source order; [dimensional model](../phase3/m34_dimensional_model.md) |
| dbt dimensions and five marts | Explicit grain and tested business logic; inexpensive BI queries | Extra storage, rebuild time, need for reconciliation; [baseline](performance_baseline.md) |
| Gold full rebuild | Simpler dependency consistency for fixed historical scope | Full rebuild is expensive; isolated incremental trial is not production migration |
| BRIN candidate, no index deployment | Selective workload benefit and small observed index | Physical ordering and cache variability require broader tests; [index experiment](index_optimization.md) |
| Retain default Silver batch 50,000 | Existing accepted loader; smaller batch promising for memory | Single-load observations and rollback are not controlled durable-commit benchmarks; [pipeline evidence](pipeline_performance.md) |
| Dagster separate environment | Reuse tested CLIs and isolate dependency sets | Two environments and local run storage to operate; [runbook](../phase7/README.md) |
| Read-only audit, controlled retries | Fail closed and avoid automatic write replacement | Operator inspects errors and reruns; no external alerting SLA |
| Import marts into one Power BI project | Report responsiveness and clear metric definitions | Manual credential setup and refresh; no hosted semantic service |
| Synthetic fixture in CI | Full dbt graph, regression and recovery without downloading BTS | Fixture does not prove full-population correctness; full historical acceptance remains separate |
| No NOAA, Spark, Kafka or Kubernetes in v1 scope | Avoid scope without demonstrated need | Weather enrichment, distributed processing and hosted operations are future decisions |

Two known BTS REVIEW exceptions remain visible rather than silently
removing observations. The pipeline has month-level Silver atomicity,
not an atomic all-model Gold publication transaction. The weekly audit
is STOPPED by default. Production migration decisions require
measured improvement, equivalent results, regression and acceptance.

The clean-checkout trial exposed newline-dependent theme resource
hashes: Git's CRLF checkout changed a raw-byte hash despite identical
theme content. Commit `2ec5bd1` normalizes CRLF to LF before hashing
in both theme scripts, with an LF/CRLF regression test. The accepted
Power BI report and registered resource are unchanged.
