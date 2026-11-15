# Phase 1 Validation Record

**Status: COMPLETE — source acquisition, full-period profiling and reconciliation verified.**

Date: 2026-11-15 (UTC). This document describes the full 2024–2025 rebuild; the separate January 2025 pilot is retained only as an earlier experiment.

## Acceptance criteria and results

| Criterion | Observed evidence | Result |
| --- | --- | --- |
| Official BTS source | All downloads use the BTS PREZIP path for Reporting Carrier On-Time Performance | PASS |
| Full calendar period | 2024-01 through 2025-12, exactly 24 ZIP files | PASS |
| Archive integrity | One CSV per ZIP; ZIP CRC and SHA-256 recorded for every file | PASS |
| Content completeness | All 24 months cover their first through last calendar day, including leap day 2024-02-29 | PASS |
| Schema coverage | 109 named columns in every month; one trailing unnamed column at header position 109 | PASS |
| Required field presence | All required profiler fields present in all monthly headers | PASS |
| Source-to-profile reconciliation | 24 monthly file hashes and ZIP byte sizes match acquisition manifest | PASS |
| Flight status accounting | Completed + cancelled + diverted-not-cancelled = scheduled rows in every month | PASS |
| Month boundary validation | No invalid `FlightDate` values and no rows outside the expected month | PASS |
| Duplicate detection | No exact duplicate rows or candidate-key collisions observed | PASS |
| Year-over-year readiness | Both full-year counts and weighted arrival delay rates computed | PASS |
| Automated tests | 13 Python standard-library unit/integration-fixture tests pass | PASS |
| Data quality exceptions | Two isolated source anomalies are retained and documented below | REVIEWED |

## Measured dataset size

| Measurement | Verified value |
| --- | ---: |
| Monthly BTS source files | 24 |
| Total compressed ZIP bytes | 709,735,704 |
| Total uncompressed CSV bytes | 6,370,981,019 |
| Total flight observations | **14,080,680** |
| 2024 flight observations | 7,079,061 |
| 2025 flight observations | 7,001,619 |
| Named source columns per month | 109 |
| Distinct origin airports | 358 |
| Distinct reporting airline codes | 15 |
| Distinct directed origin-destination routes | 7,328 |

The originally anticipated 12–14 million records was a planning estimate. **14,080,680** is the observed value from the official files.

## Validated annual KPIs

| KPI | 2024 | 2025 |
| --- | ---: | ---: |
| Scheduled flights | 7,079,061 | 7,001,619 |
| Completed flights | 6,965,247 | 6,879,485 |
| Cancelled flights | 96,315 | 102,876 |
| Diverted (not cancelled) | 17,499 | 19,258 |
| Eligible arrival observations | 6,965,247 | 6,879,484 |
| Arrival delay >=15 minutes | 20.8172% | 22.3075% |
| Arrival on-time rate | 79.1828% | 77.6925% |
| Cancellation rate | 1.3606% | 1.4693% |

2025 had **1.0940% fewer** reported scheduled flights than 2024, while the arrival 15+ minute delay rate increased by **1.4903 percentage points**. These are descriptive results for reported flights, not causal findings.

## Source exceptions retained for Phase 2

1. **2024-08**, CSV line **234,965**: `FlightDate=2024-08-25`, carrier `F9`, `MIA -> ATL`, `CRSDepTime=0600`. `Flight_Number_Reporting_Airline` is blank. The row remains a valid observation for volume KPIs but lacks a complete candidate natural key. Use source filename + CSV line number for lineage.
2. **2025-09**, CSV line **410,707**: `FlightDate=2025-09-06`, carrier `YX`, flight `5859`, `JFK -> MVY`. The record has `Cancelled=0` and `Diverted=0`, but `ArrDel15` and `ArrDelay` are blank. Preserve the row and exclude it from the eligible-arrival denominator.

Other non-blocking special cases:

- Clock values of `2400` occur in source HHMM fields, including two scheduled departure and two scheduled arrival values. Treat midnight rollover deliberately during timestamp modeling.
- 7,486 actual arrival-time and 1,468 actual departure-time values equal `2400`. These are boundary values, not malformed `2460`-style times.
- Most third-, fourth- and fifth-diversion detail columns are almost entirely NULL; this reflects rare conditional events rather than evidence of corrupted archives.

No source rows were deleted or imputed. The complete month-level evidence is in `profiles/`; weighted aggregate measures and all anomaly counts are in `aggregate_profile.json`.

## Local verification commands

```bash
python -m src.phase1.build_report
python -m unittest discover -s tests -v
```

Both were run successfully against the 24 generated profiles. Reproducing the full profiling from ZIPs requires `python -m src.phase1.run_phase1` and the raw source files.

## Completion boundary

This completes **Phase 1 only**: acquisition, assessment, requirements, KPI rules and preliminary modeling. Bronze Parquet, PostgreSQL, dbt, Power BI, NOAA and Dagster have **not** been implemented.
