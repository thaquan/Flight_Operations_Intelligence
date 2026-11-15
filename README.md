# Flight Operations Intelligence

**End-to-End Aviation Data Engineering & Analytics Platform**

A reproducible, local-first student portfolio project combining data engineering and business intelligence with real U.S. Department of Transportation flight records. The target audience is Data Engineer Intern and Data Analyst Intern positions.

**Current status:** Phase 1 complete and verified (24/24 months; 14,080,680 real flight observations). Phases 2–8 are planned, not implemented.

## Business questions

1. How often do reported domestic flights arrive at least 15 minutes late?
2. Which airlines, origin airports, routes and time periods have the highest arrival delay rates?
3. How often are flights cancelled or diverted, and how do those rates differ by segment?
4. How do measured weather conditions relate to delays? *(Planned for Phase 6; association is not causation.)*
5. Is there evidence of downstream delay propagation across successive flights of the same aircraft? *(Optional extension.)*

## Data sources

- **BTS Reporting Carrier On-Time Performance (1987–present)**, official U.S. DOT dataset. [Download](https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=&gnoyr_VQ=FGJ), [pre-zipped monthly files](https://transtats.bts.gov/PREZIP/), [field descriptions](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ).
- **NOAA GHCNh hourly meteorological observations**, planned for Phase 6. [Dataset and bulk-download guidance](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly).

**Data ethics / limitations:** This project contains domestic flights reported by U.S. carriers, not all flights worldwide. The BTS feed is published monthly, **not a real-time stream**. BTS does not include flight-level ticket prices or airline profit.

## Dataset scope

- **Primary:** BTS Reporting Carrier On-Time Performance, all 24 complete calendar months from January 2024 through December 2025.
- **Population:** all reporting carriers, airports and flight outcomes in the official monthly files; no source-level top-airport filtering.
- **BI focus:** approximately 20 highest-volume origin airports, ranked over the entire two-year period.
- **Secondary (Phase 6):** NOAA GHCNh hourly weather records, joined with validated airport/station and timezone mappings.

The original January 2025-only pilot is preserved under `docs/phase1/` for historical reference. It is **not** accepted as evidence of 24-month coverage.

## Phase 1: reproduce the full assessment

Requires Python 3.10+. The Phase 1 acquisition, profiler and tests use the Python standard library.

```bash
python -m src.phase1.download_bts --start 2024-01 --end 2025-12 --workers 3
python -m src.phase1.run_phase1 --workers 4
python -m src.phase1.build_report
python -m unittest discover -s tests -v
```

These commands download official source ZIP files (approximately several hundred MB in total), verify each archive's CRC and SHA-256, profile every source row, and reconcile all 24 monthly reports. Use `python -m src.phase1.run_phase1 --resume` only when previously generated monthly profiles and matching source checksums are available.

Raw ZIPs stay in `data/raw/bts/<YEAR>/` and are **never committed**. The acquisition manifest and 24 JSON profiles provide reproducible evidence without bundling the source data in the repository.

Phase 1 deliverables:

- [Source, scope and acquisition](docs/phase1/2024_2025/source_and_scope.md)
- [Business requirements](docs/phase1/2024_2025/business_requirements.md)
- [Business data dictionary](docs/phase1/2024_2025/data_dictionary.md)
- [KPI definitions](docs/phase1/2024_2025/kpi_definitions.md)
- [Preliminary data model](docs/phase1/2024_2025/preliminary_data_model.md)
- [Measured full-period data-quality report](docs/phase1/2024_2025/data_quality_assessment.md)
- [Complete source field catalog](docs/phase1/2024_2025/field_catalog.md)
- [Phase 1 validation and source exceptions](docs/phase1/2024_2025/phase1_validation.md)
- [Phase 2 implementation handoff](docs/phase1/2024_2025/phase2_handoff.md)
- [Acquisition manifest](docs/phase1/2024_2025/acquisition_manifest.json)
- [Aggregate machine-readable profile](docs/phase1/2024_2025/aggregate_profile.json)
- Monthly machine-readable profiles in `docs/phase1/2024_2025/profiles/`

## Planned stack and scope

| Layer | Planned technology | Status |
| --- | --- | --- |
| Source acquisition / profiling | Python | Phase 1 |
| Bronze storage | Source ZIP + partitioned Parquet (Polars/PyArrow) | Phase 2 |
| Silver warehouse | PostgreSQL + Docker Compose | Phase 3 |
| Transformations | dbt Core | Phase 3 |
| Tests and CI | pytest, dbt tests, GitHub Actions | Phase 4 |
| BI | Power BI Desktop (Import) | Phase 5 |
| Weather integration | NOAA GHCNh, station mapping, IANA time zones | Phase 6 |
| Orchestration | Dagster OSS | Phase 7 |

The MVP includes **two complete years (2024–2025)** for year-over-year and seasonal comparisons. Spark, Kafka and paid Microsoft Fabric capacities are intentionally excluded until there is a demonstrated technical need. Credentials, raw datasets and local databases are not checked in.

## Phase roadmap

1. **Data Acquisition, Exploration & Business Requirements:** verify and profile all 24 monthly BTS files, document KPI rules and initial star schema.
2. **Data Ingestion & Bronze:** repeatable ZIP ingestion, manifest, checksum, partitioned Parquet, backfill and idempotency.
3. **PostgreSQL Warehouse & dbt Core:** Silver staging/intermediate models, fact/dimension tables and Gold data marts.
4. **Data Quality & CI:** pytest, dbt tests, source-to-mart reconciliation and GitHub Actions.
5. **Power BI Analytics:** Executive Overview, Airline Performance, Airport & Route Analytics, Delay Causes & Seasonal Trends.
6. **NOAA Weather Integration:** airport-station mapping, timezone conversion, point-in-time weather joins and Weather Impact page.
7. **Dagster OSS:** scheduling, retries, logging, monitoring, incremental updates and backfills.
8. **Performance & Portfolio:** measured benchmarks, optimizations, architecture docs, screenshots, evidence-based insights and CV-ready presentation.

## Data integrity principles

- Every published statistic must be calculated from downloaded source records; capacity estimates are explicitly labeled as estimates.
- Flight delay percentages use documented eligible-arrival denominators, not all scheduled flights.
- Cancelled and diverted flights remain in the source population.
- High NULL rates in conditional delay and diversion fields are interpreted in context.
- The candidate natural key is checked for collisions; no silent deduplication is performed.
- Flight- and weather-time joins must account for local time, UTC, daylight saving and arrival-date rollover.

## Repository status

There is no configured GitHub remote for this project. Source files can be committed locally once validated; no push is performed without an explicit repository target and instruction.
