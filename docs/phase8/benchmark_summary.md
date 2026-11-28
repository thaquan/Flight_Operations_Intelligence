# Performance evidence summary

All timings are measured on the local Windows environment, not a
production SLA. The following concise results are linked to full
methods and raw summaries. Different experiments have different
scopes; they must not be combined into a single end-to-end speedup.

| Experiment | Observed result | Interpretation |
| --- | --- | --- |
| Bronze storage | 445,109,486 Parquet bytes for 14,080,680 rows | Compact persisted source-derived layer; [Phase 2](../phase2/performance_benchmark.md) |
| Fact vs mart, top-20 origins | 5,394.855 ms vs 195.434 ms median, 27.60x ratio | Equivalent result sets; three measured runs each, not report latency |
| Five Gold marts | 129,785,856 bytes vs 6,613,229,568-byte fact (1.96%) | Additional aggregate storage including indexes |
| Isolated month BRIN | 2,386.193 ms to 834.940 ms median | Observed 2.86x ratio; candidate not deployed |
| Isolated origin/month BRIN | 2,271.378 ms to 261.962 ms median | Observed 8.67x ratio; no material full-year gain |
| Index size | BRIN 172,032 bytes vs B-tree 97,607,680 bytes | Candidate DDL rolled back; physical order matters |
| Silver replacement, 25k vs 50k | 30.416 vs 40.376 seconds in final pass | One sample per configuration; earlier timings nearly tied |
| Python peak memory, 25k vs 50k | 241,713,152 vs 267,984,896 bytes | Smaller batch promising; default unchanged |
| Full isolated Gold acceptance | 494.093 s dbt build; 540.684 s Dagster run | 11 models, 65 tests; previous full-scope run |
| Clean real-month ingestion | 52.23 s load; 4.95 s unchanged rerun | 547,271 rows on new clone; rerun skipped both layers |

## Method and raw evidence

- [M8.1 baseline](performance_baseline.md) / [JSON](baseline_results.json)
- [M8.2 index comparison](index_optimization.md) / [JSON](index_results.json)
- [M8.3 pipeline evaluation](pipeline_performance.md) / [JSON](pipeline_results.json)
- [M8.4 clean reproduction](clean_reproduction.md)
- [Full Gold acceptance](../phase7/acceptance.md)

Cache state and local machine load were not fully controlled. M8.1
included concurrent regression activity early in the measurement; M8.2
included an original-index baseline after rollback. M8.3 measured
rolled-back replacements, not durable commits, and process memory,
not total database/VM memory. No production index migration or batch
default change was accepted. Power BI refresh time was not measured.
