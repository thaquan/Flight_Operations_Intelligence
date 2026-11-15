# Phase 1 — Dataset assessment / Đánh giá bộ dữ liệu

**Status:** Real source file downloaded and all records profiled on 2026-11-14. Assessment based on **January 2025 only**, not all of 2025.

## 1. Dataset selection

| Item | Assessment |
| --- | --- |
| Project | Flight Operations Intelligence — Data Engineering + Data Analytics |
| Owner/publisher | U.S. Department of Transportation — Bureau of Transportation Statistics (BTS) |
| Source dataset | Reporting Carrier On-Time Performance (1987–present) |
| Pilot sample | January 2025, official monthly pre-zipped CSV |
| Geography | BTS-reported U.S. domestic non-stop flights; **not worldwide flight tracking** |
| Reporting frequency | Monthly publication, not live or event streaming |
| ZIP size | 27,108,664 bytes (25.85 MiB) |
| CSV uncompressed size | 243,177,378 bytes (231.91 MiB) |
| Rows inspected | **539,747** |
| Columns | 109 named columns plus one empty trailing header |
| Period observed | 2025-01-01 through 2025-01-31, full 31 calendar days |
| Coverage | 329 origin airports; 329 destination airports; 14 reporting-airline codes |
| SHA-256 | `868387dcedaef1b8d8392e608e642219fde50d594c3cf2094aec858167629ccf` |
| Source download | [January 2025 official BTS ZIP](https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_1.zip) |

## 2. Suitability for DE and DA

**Data Engineering suitability — high:** Monthly source ZIPs support independently verifiable ingestion, source hashing, incremental loads, partitioned Parquet, Postgres warehouse modeling, dbt tests, DAG orchestration and reprocessing/backfills. Each row includes flight identifiers, multiple airport keys, time fields, status indicators and many legitimate optional columns.

**Data Analytics suitability — high:** Measurable arrival lateness, cancellations, diversions and segmentation by airline, origin/destination, routes and time periods. The data provides multiple analytical questions beyond a generic sales dashboard. It cannot support airfare or profitability analysis.

**Distinctive extension:** NOAA GHCNh hourly/synoptic weather permits airport/station mapping, UTC/local-time conversion and a **point-in-time join**. This adds a credible real-world temporal data-engineering challenge but is deferred until the BTS MVP is stable.

## 3. Initial findings from the complete January file

| Flight outcome | Rows | Share of all 539,747 scheduled flights |
| --- | ---: | ---: |
| Completed (`Cancelled=0`, `Diverted=0`) | 522,269 | 96.7618% |
| Cancelled | 16,312 | 3.0222% |
| Diverted but not cancelled | 1,166 | 0.2160% |
| Total | **539,747** | **100%** |

Among completed flights with an `ArrDel15` value (522,269 valid records):

- **424,139** arrived less than 15 minutes late; arrival on-time rate **81.2108%**.
- **98,130** arrived at least 15 minutes late; 15+ arrival delay rate **18.7892%**.
- These percentages exclude cancelled/diverted flights by design. The 3.0222% cancellation rate uses **all scheduled flights** as the denominator.

## 4. Pilot airport cohort

January 2025's 20 highest-volume **origin** airports (descriptive pilot sample):

`DFW, DEN, ATL, ORD, CLT, PHX, LAX, LAS, MCO, SEA, DCA, LGA, SFO, BOS, MIA, EWR, SLC, DTW, IAH, MSP`.

These airports account for **284,081** January origin flight records (**52.63%** of the monthly total). This list is useful for the pilot, **not yet the final 2025 cohort**. In Phase 2, rank by **full-year 2025 origin departures**, choose and freeze the top 20 airport IDs, then apply the fixed cohort consistently across 2025 and any comparison period. Keeping the raw data complete prevents selection bias from destructive source filtering.

## 5. Scalability estimate, not an observed fact

Naively multiplying January by 12 gives about **6.48 million flight records**, **310 MiB** of compressed ZIP files and **2.72 GiB** uncompressed CSV per year. Actual 2025 totals, row widths, monthly volumes and warehouse size can differ seasonally; **these are capacity-planning approximations, not measurements of 2025**.

For an intern portfolio, ingest one January batch first, then the 2025 months once source-level reconciliation is reliable. For a resource-constrained machine, test 3 months and store only selected analytics fields in PostgreSQL, while keeping immutable originals.

## 6. Decision

**Proceed (GO)**. January data contains enough populated flight statuses, scheduled time, airports and delay fields for the planned warehouse and dashboard. Risks are manageable but must be addressed rather than hidden:

- The source has a blank trailing CSV header; 109 **named** fields are canonical.
- Sparse diversion/cancellation/delay-cause columns reflect conditional applicability, not automatically bad records.
- Natural-key uniqueness is observed in January only; validate again across months before database constraints.
- Airport-local HHMM fields require robust time-zone/DST logic before NOAA joins.
- Published historical data is monthly and delayed, not a real-time stream.
- Weather and causal inference are outside the Phase 1 validation scope.

## References

- [BTS dataset page](https://transtats.bts.gov/TableInfo.asp?QO_fu146_anzr=b0-gvzr&V0s1_b0yB=D&gnoyr_VQ=FGJ)
- [BTS field definitions](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ)
- [BTS pre-zipped monthly downloads](https://transtats.bts.gov/PREZIP/)
- [NOAA GHCNh weather dataset](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly)
- [Reproducible machine-readable profiling output](profile_2025_01.json)
