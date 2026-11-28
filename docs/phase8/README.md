# Phase 8 - Performance and portfolio finalization

| Milestone | Scope | Status |
| --- | --- | --- |
| M8.1 | System audit and repeated read-only query baseline | Verified locally |
| M8.2 | Selective query/index optimization experiments | Verified locally; no production index migration |
| M8.3 | Pipeline performance evaluation | Verified locally; retain production defaults |
| M8.4 | Architecture and reproducibility | Planned |
| M8.5 | Portfolio and final acceptance | Planned |

Start with [M8.1 performance baseline](performance_baseline.md) and
[measured summary](baseline_results.json). Existing Phase 7 acceptance
is preserved. Production changes require measured benefit, equivalent
results, regression checks and explicit acceptance. No new technology
or separate Power BI report is required for this phase.

See [M8.2 index optimization](index_optimization.md) and [measured results](index_results.json) for the isolated BRIN/B-tree comparison. See [M8.3 pipeline performance](pipeline_performance.md) and [measured results](pipeline_results.json) for the isolated batch-size and memory comparison. M8.4 is next.
