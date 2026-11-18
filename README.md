# Flight Operations Intelligence

**End-to-End Aviation Data Engineering & Analytics Platform**

A reproducible, local-first student portfolio project combining data engineering and business intelligence with real U.S. Department of Transportation flight records. The target audience is Data Engineer Intern and Data Analyst Intern positions.

**Current status:** Phases 1-3 and Phase 4 local data-quality/CI verification are complete. All 24 BTS months and 14,080,680 observations reconcile from PostgreSQL Silver through dbt staging, the Gold fact and five analytics marts. GitHub-hosted CI awaits the next push; Power BI is planned for Phase 5.

## Business questions

1. How often do reported domestic flights arrive at least 15 minutes late?
2. Which airlines, origin airports, routes and time periods have the highest arrival delay rates?
3. How often are flights cancelled or diverted, and how do those rates differ by segment?
4. How do measured weather conditions relate to delays? *(Planned for Phase 6; association is not causation.)*
5. Is there evidence of downstream delay propagation across successive flights of the same aircraft? *(Optional extension.)*

## Data sources

- **BTS Reporting Carrier On-Time Performance (1987–present)**, official U.S. DOT dataset. [Download](https://transtats.bts.gov/DL_SelectFields.aspx?QO_fu146_anzr=&gnoyr_VQ=FGJ), [pre-zipped monthly files](https://transtats.bts.gov/PREZIP/), [field descriptions](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ).
- **NOAA GHCNh hourly meteorological observations**, planned for Phase 6. [Dataset and bulk-download guidance](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly).

## Explore the data

- **[Download the complete BTS 2024–2025 dataset (GitHub Release)](https://github.com/thaquan/Flight_Operations_Intelligence/releases/tag/bts-data-2024-2025-v1)**: all 24 verified official monthly ZIPs, packaged into [2024](https://github.com/thaquan/Flight_Operations_Intelligence/releases/download/bts-data-2024-2025-v1/BTS_Reporting_Carrier_2024_Official_ZIPs.zip) and [2025](https://github.com/thaquan/Flight_Operations_Intelligence/releases/download/bts-data-2024-2025-v1/BTS_Reporting_Carrier_2025_Official_ZIPs.zip) archives. Each yearly archive includes a source-file checksum list.
- [Open a compact 1,200-row BTS preview](data/sample/bts_flights_preview_1200.csv) directly on GitHub.
- [Download the 10,000-row sample](data/sample/bts_flights_2024_2025_sample_10000.csv) for local inspection.
- [Read the sampling method and limitations](data/sample/README.md).
- [Inspect the verified source manifest](docs/phase1/2024_2025/acquisition_manifest.json) for all 24 official monthly downloads and SHA-256 values.

Both samples contain actual BTS records from all 24 months, with a deliberate minimum number of cancellations and diversions for inspection. **They are not representative datasets and must not be used to estimate population KPIs.** For population analysis, use the complete 2024–2025 Release archives or the Phase 1 downloader below.

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

Raw ZIPs stay in `data/raw/bts/<YEAR>/` and are **never committed to Git history**. Instead, the two verified yearly archives are downloadable as [GitHub Release assets](https://github.com/thaquan/Flight_Operations_Intelligence/releases/tag/bts-data-2024-2025-v1). The acquisition manifest and 24 JSON profiles provide reproducible evidence without bundling the source data in the repository.

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

## Phase 2: build the Bronze Parquet layer

The Phase 2 pipeline reads the official BTS monthly ZIPs in bounded PyArrow CSV batches, validates each source against Phase 1 checksums, and writes partitioned, ZSTD-compressed Parquet with row-level lineage. It supports month-range backfills, idempotent reruns, explicit reprocessing, and recovery of interrupted local outputs.

Install the tested local dependencies in a virtual environment (Python 3.13 on Windows was used for the verified run):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-phase2.txt
```

Activate the environment first, or call its Python executable directly. Run from the project root with the 24 raw ZIPs already downloaded:

```bash
python -m src.phase2.ingest --start 2024-01 --end 2025-12 --dry-run
python -m src.phase2.ingest --start 2024-01 --end 2025-12
python -m src.phase2.validate --deep --report docs/phase2/full_validation.json
python -m pytest -q
```

**Verified local result:** 24/24 Parquet partitions, **14,080,680/14,080,680** rows reconciled, 113 fields per Bronze record (109 source + 4 lineage), and 445,109,486 Parquet bytes. The 24-month rerun skipped every partition without changing the ingestion manifest; 33 Python tests passed. Two reviewed Phase 1 source exceptions were preserved and checked.

- [Phase 2 overview and documentation](docs/phase2/README.md)
- [Bronze schema](docs/phase2/bronze_schema.md)
- [Operations and recovery runbook](docs/phase2/runbook.md)
- [Deep validation report](docs/phase2/full_validation.json)
- [Measured performance](docs/phase2/performance_benchmark.md)

The generated `data/bronze/` tree and its ingestion manifest are deliberately Git-ignored. Reproduce them locally from the official raw ZIPs; PostgreSQL and dbt modeling begin in Phase 3.

## Phase 3, M3.1: local PostgreSQL foundation

M3.1 provides a containerized PostgreSQL 17 warehouse, persistent Docker storage, versioned schema initialization, environment-based credentials and a dbt Core connection. It **does not yet load Bronze data** or publish Silver/Gold models; those belong to subsequent Phase 3 milestones.

Install Phase 3 dependencies into the existing virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-phase3.txt
.\.venv\Scripts\python.exe -m src.phase3.bootstrap_env
docker compose up -d --wait
.\.venv\Scripts\python.exe -m src.phase3.check_database
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli debug
```

The bootstrap command generates a private `.env` with a random database password and refuses to overwrite an existing one. Docker publishes PostgreSQL to **127.0.0.1:5433** by default; the database is kept in a named volume. Start Docker Desktop before running Compose. To stop the service without removing data, run `docker compose stop`.

- [M3.1 infrastructure and operation guide](docs/phase3/m31_infrastructure.md)
- [M3.1 verification record](docs/phase3/m31_validation.md)

## Phase 3, M3.2: Bronze to Silver

M3.2 loads the 2024–2025 Bronze population into `silver.flights` using checksum-verified Parquet inputs, bounded Arrow batches and PostgreSQL `COPY`. Each monthly load is transactional and recorded in `audit.silver_loads`. Unchanged months are skipped; an explicit `--reprocess` is required for a replacement.

```powershell
.\.venv\Scripts\python.exe -m src.phase3.load_silver --start 2024-01 --end 2025-12 --dry-run
.\.venv\Scripts\python.exe -m src.phase3.load_silver --start 2024-01 --end 2025-12
.\.venv\Scripts\python.exe -m src.phase3.validate_silver --report docs/phase3/m32_reconciliation.json
.\.venv\Scripts\python.exe -m pytest -q
```

**Verified local result:** all **24/24 months and 14,080,680/14,080,680 rows** reconciled between Bronze and Silver. All 24 partitions were skipped on an unchanged rerun. Silver maps 62 Bronze fields into typed columns, adds the source month and a load timestamp, and preserves the complete source population. The local PostgreSQL table and indexes occupied **7,536 MB** at verification. The full Python suite passed **45 tests**.

- [M3.2 pipeline architecture and runbook](docs/phase3/m32_silver_pipeline.md)
- [M3.2 source-to-Silver reconciliation](docs/phase3/m32_reconciliation.json)
- [M3.2 validation record](docs/phase3/m32_validation.md)

## Phase 3, M3.3: dbt Source and Staging Models

M3.3 declares `silver.flights` as a dbt source and builds two PostgreSQL views:
`staging.stg_flights` (all typed Silver fields plus normalized airline/airport
codes) and `staging.stg_flight_outcomes` (mutually exclusive flight statuses
and additive KPI numerators/denominators). Neither view filters, deduplicates,
or physically copies source flights.

```powershell
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli parse
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli build
.\.venv\Scripts\python.exe -m pytest -q
```

**Verified local result:** dbt built 2 views and passed 9 data tests
(**11/11 PASS**; no warnings or errors). All monthly Silver-to-staging row
counts matched. The Python suite passed **48 tests**. Annual dbt staging
arrival delay rates match Phase 1: **20.82% in 2024** and **22.31% in 2025**,
using completed flights with a valid `ArrDel15` as the denominator.

- [M3.3 staging design and runbook](docs/phase3/m33_staging_models.md)
- [M3.3 verification record](docs/phase3/m33_validation.md)

## Phase 3, M3.4: Dimensional Modeling

M3.4 builds the physical PostgreSQL Star Schema in `gold` using dbt:
`fct_flights`, `dim_airline`, `dim_airport` and `dim_date`. The airport
dimension is used for both origin and destination roles. Stable numeric
keys, unknown members and source lineage preserve every observation.

```powershell
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli run --select path:models/marts/dimensions path:models/marts/facts
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli test --select path:models/marts/dimensions path:models/marts/facts
.\.venv\Scripts\python.exe -m pytest -q
```

**Verified local result:** 15 airlines plus Unknown, 358 airports plus
Unknown, 731 calendar dates, and **14,080,680 fact rows**. All **24
M3.4 dbt tests passed**, including fact-to-dimension relationships,
monthly Silver-to-Fact reconciliation and annual KPI consistency.
The materialized fact and indexes occupied approximately **6,307 MB**.
The fact is currently a fully rebuilt table, not an incremental merge.

- [M3.4 dimensional design and runbook](docs/phase3/m34_dimensional_model.md)
- [M3.4 Star Schema ERD](docs/phase3/m34_erd.md)
- [M3.4 validation record](docs/phase3/m34_validation.md)

## Phase 3, M3.5: Gold Analytics Data Marts

M3.5 materializes five BI-ready aggregate tables from the complete Gold
flight fact: `mart_network_monthly`, `mart_airline_monthly`,
`mart_airport_daily`, `mart_route_monthly`, and `mart_delay_causes`.
The airport mart retains separate origin/destination roles, routes are
directed, and the cause mart distinguishes non-NULL observations from
positive reported minutes. All flight-rate KPIs reuse a shared dbt macro.

```powershell
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli parse
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli run --select path:models/marts/analytics --threads 2
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli test --select path:models/marts/analytics tag:m35 --threads 2
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

**Verified local result:** **24** network-month rows, **348** airline-months,
**481,262** airport/role/days, **139,287** directed route-months and **1,740**
airline/month/cause groups. An unchanged rebuild and a final indexed rebuild
reproduced all row counts. **32/32 selected dbt tests** and **57/57 Python
tests** passed; the full dbt regression suite passed **65/65 data tests**.
Network delay 15+ rates remain **20.82% (2024)** and **22.31% (2025)**.
PostgreSQL aggregate tables are currently full-rebuild, not incremental.

- [M3.5 Gold marts design and SQL examples](docs/phase3/m35_gold_marts_design.md)
- [M3.5 KPI and dimension mapping](docs/phase3/m35_kpi_mapping.md)
- [M3.5 source-to-mart reconciliation](docs/phase3/m35_reconciliation.md)
- [M3.5 measured performance](docs/phase3/m35_performance.md)
- [M3.5 validation record](docs/phase3/m35_validation.md)

## Phase 4: Data Quality & CI

Phase 4 checks the complete two-year source-to-mart lineage using a read-only quality runner. It validates monthly source counts and hashes, KPI denominators, segment aggregations and the Phase 1 population baseline. A separate synthetic PostgreSQL fixture runs the full dbt project in CI without downloading raw BTS records.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\ruff.exe check --select E4,E7,E9,F,I src/phase4 tests/test_phase4_quality_gates.py tests/test_phase4_ci_workflow.py
.\.venv\Scripts\python.exe -m src.phase4.quality_gates --mode full --report docs/phase4/quality_report.json
```

**Verified locally:** **70/70 Python tests**, Ruff lint, and **76/76 dbt nodes** (11 models, 65 tests) on a throwaway PostgreSQL 17 fixture. Full 24-month quality gates returned **6 PASS, 2 REVIEW, 0 FAIL**; the two REVIEW findings are transparent BTS source exceptions. The Actions workflow is committed locally but **has not yet been executed on GitHub**.

- [Phase 4 scope and findings](docs/phase4/README.md)
- [CI and recovery runbook](docs/phase4/ci_runbook.md)
- [Verification results](docs/phase4/validation.md)
- [Full dataset quality report (JSON)](docs/phase4/quality_report.json)

## Planned stack and scope

| Layer | Planned technology | Status |
| --- | --- | --- |
| Source acquisition / profiling | Python | Phase 1 |
| Bronze storage | Python, PyArrow, Polars and partitioned Parquet | Phase 2 complete |
| Silver warehouse | PostgreSQL + Docker Compose | M3.2 complete; 24 months loaded and reconciled |
| Transformations | dbt Core | M3.5 Gold fact, dimensions and five aggregate marts complete |
| Tests and CI | pytest, Ruff, 65 dbt data tests, synthetic PostgreSQL fixture and GitHub Actions | Phase 4 locally verified; hosted run pending push |
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

GitHub repository: [thaquan/Flight_Operations_Intelligence](https://github.com/thaquan/Flight_Operations_Intelligence). Phases 1-3 are published on `main`; Phase 4 has been verified locally and will appear on GitHub after the next push. Public raw BTS ZIPs are available via the [data Release](https://github.com/thaquan/Flight_Operations_Intelligence/releases/tag/bts-data-2024-2025-v1), while raw files, Bronze outputs, local databases and credentials remain excluded from version control.
