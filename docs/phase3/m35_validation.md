# M3.5 - Verification record

**Date:** 2026-11-18. **Status:** Completed and verified locally.
**Input:** M3.4 `gold.fct_flights` (14,080,680 rows), three dimensions,
and the 24 BTS 2024-2025 monthly source partitions.

## Commands and outcomes

| Verification | Result |
| --- | --- |
| dbt `parse` | PASS |
| dbt `run --select path:models/marts/analytics --threads 2` | PASS, five tables |
| Unchanged mart rebuild | PASS, identical counts |
| Final indexed mart rebuild | PASS, identical counts |
| dbt `test --select path:models/marts/analytics tag:m35 --threads 2` | **32 PASS, 0 WARN, 0 ERROR** |
| Full dbt `test --threads 2` across staging, fact, dimensions and marts | **65 PASS, 0 WARN, 0 ERROR** |
| Python `pytest -q -p no:cacheprovider` | **57 PASS** |
| Fact/network, all four segment rollups and source delay causes | PASS |
| Composite key uniqueness and dimension relationships | PASS |
| 2024 and 2025 annual delay KPI baselines | Match |

The scoped dbt test suite contains generic null/relationship/value tests,
the network unique-key test and five independent SQL assertions. It checks
source-to-mart totals and non-NULL/positive delay cause semantics.

## Acceptance evidence

- Materialized row counts: network **24**, airline **348**, airport daily
  **481,262**, directed route **139,287**, cause **1,740**.
- Two-year scheduled network volume: **14,080,680**.
- Annual delay 15+ rates: **20.82%** (2024), **22.31%** (2025),
  recomputed from additive totals.
- Attributed-minute categories preserve zero/non-NULL distinction.
- All unique composite indexes created by dbt without errors.
- Measured table sizes and illustrative route-vs-fact query are recorded
  in [M3.5 performance](m35_performance.md).

## Limitations / follow-up

- dbt Gold tables use full rebuilds rather than incrementally updating
  only new months; no automation or SLA is claimed.
- Air/route rankings may be misleading for tiny denominator groups:
  Power BI should expose flight-volume filters and denominators.
- An airport observation has two valid location roles. Add only
  origin **or** destination totals for network-wide visualizations.
- Reported `weather_delay` is a BTS cause category, **not NOAA weather**.
- Power BI report pages, semantic measures and scheduled CI are separate
  future phases, not included in this milestone.

See [M3.5 design](m35_gold_marts_design.md),
[KPI mapping](m35_kpi_mapping.md),
[reconciliation](m35_reconciliation.md) and
[performance](m35_performance.md).
