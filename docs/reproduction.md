# Full reproduction guide

Run from the repository root. This guide preserves milestone commands, measured results and evidence from the accepted baseline. See the [project overview](../README.md) for current status. Earlier milestone test counts are historical, not current regression totals.

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

- [Source, scope and acquisition](../docs/phase1/2024_2025/source_and_scope.md)
- [Business requirements](../docs/phase1/2024_2025/business_requirements.md)
- [Business data dictionary](../docs/phase1/2024_2025/data_dictionary.md)
- [KPI definitions](../docs/phase1/2024_2025/kpi_definitions.md)
- [Preliminary data model](../docs/phase1/2024_2025/preliminary_data_model.md)
- [Measured full-period data-quality report](../docs/phase1/2024_2025/data_quality_assessment.md)
- [Complete source field catalog](../docs/phase1/2024_2025/field_catalog.md)
- [Phase 1 validation and source exceptions](../docs/phase1/2024_2025/phase1_validation.md)
- [Phase 2 implementation handoff](../docs/phase1/2024_2025/phase2_handoff.md)
- [Acquisition manifest](../docs/phase1/2024_2025/acquisition_manifest.json)
- [Aggregate machine-readable profile](../docs/phase1/2024_2025/aggregate_profile.json)
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

- [Phase 2 overview and documentation](../docs/phase2/README.md)
- [Bronze schema](../docs/phase2/bronze_schema.md)
- [Operations and recovery runbook](../docs/phase2/runbook.md)
- [Deep validation report](../docs/phase2/full_validation.json)
- [Measured performance](../docs/phase2/performance_benchmark.md)

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

- [M3.1 infrastructure and operation guide](../docs/phase3/m31_infrastructure.md)
- [M3.1 verification record](../docs/phase3/m31_validation.md)

## Phase 3, M3.2: Bronze to Silver

M3.2 loads the 2024–2025 Bronze population into `silver.flights` using checksum-verified Parquet inputs, bounded Arrow batches and PostgreSQL `COPY`. Each monthly load is transactional and recorded in `audit.silver_loads`. Unchanged months are skipped; an explicit `--reprocess` is required for a replacement.

```powershell
.\.venv\Scripts\python.exe -m src.phase3.load_silver --start 2024-01 --end 2025-12 --dry-run
.\.venv\Scripts\python.exe -m src.phase3.load_silver --start 2024-01 --end 2025-12
.\.venv\Scripts\python.exe -m src.phase3.validate_silver --report docs/phase3/m32_reconciliation.json
.\.venv\Scripts\python.exe -m pytest -q
```

**Verified local result:** all **24/24 months and 14,080,680/14,080,680 rows** reconciled between Bronze and Silver. All 24 partitions were skipped on an unchanged rerun. Silver maps 62 Bronze fields into typed columns, adds the source month and a load timestamp, and preserves the complete source population. The local PostgreSQL table and indexes occupied **7,536 MB** at verification. The full Python suite passed **45 tests**.

- [M3.2 pipeline architecture and runbook](../docs/phase3/m32_silver_pipeline.md)
- [M3.2 source-to-Silver reconciliation](../docs/phase3/m32_reconciliation.json)
- [M3.2 validation record](../docs/phase3/m32_validation.md)

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

- [M3.3 staging design and runbook](../docs/phase3/m33_staging_models.md)
- [M3.3 verification record](../docs/phase3/m33_validation.md)

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

- [M3.4 dimensional design and runbook](../docs/phase3/m34_dimensional_model.md)
- [M3.4 Star Schema ERD](../docs/phase3/m34_erd.md)
- [M3.4 validation record](../docs/phase3/m34_validation.md)

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

- [M3.5 Gold marts design and SQL examples](../docs/phase3/m35_gold_marts_design.md)
- [M3.5 KPI and dimension mapping](../docs/phase3/m35_kpi_mapping.md)
- [M3.5 source-to-mart reconciliation](../docs/phase3/m35_reconciliation.md)
- [M3.5 measured performance](../docs/phase3/m35_performance.md)
- [M3.5 validation record](../docs/phase3/m35_validation.md)

## Phase 4: Data Quality & CI

Phase 4 checks the complete two-year source-to-mart lineage using a read-only quality runner. It validates monthly source counts and hashes, KPI denominators, segment aggregations and the Phase 1 population baseline. A separate synthetic PostgreSQL fixture runs the full dbt project in CI without downloading raw BTS records.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\ruff.exe check --select E4,E7,E9,F,I src/phase4 tests/test_phase4_quality_gates.py tests/test_phase4_ci_workflow.py
.\.venv\Scripts\python.exe -m src.phase4.quality_gates --mode full --report docs/phase4/quality_report.json
```

**Verified locally:** **70/70 Python tests**, Ruff lint, and **76/76 dbt nodes** (11 models, 65 tests) on a throwaway PostgreSQL 17 fixture. Full 24-month quality gates returned **6 PASS, 2 REVIEW, 0 FAIL**; the two REVIEW findings are transparent BTS source exceptions. **Verified on GitHub:** the [Data quality CI workflow](https://github.com/thaquan/Flight_Operations_Intelligence/actions/runs/44340972773) passed on commit `09d3b1a`, including lint, Python tests, the synthetic PostgreSQL/dbt build, rollback checks and fixture quality gates.

- [Phase 4 scope and findings](../docs/phase4/README.md)
- [CI and recovery runbook](../docs/phase4/ci_runbook.md)
- [Verification results](../docs/phase4/validation.md)
- [Full dataset quality report (JSON)](../docs/phase4/quality_report.json)

## Phase 5: Power BI report

After completing the warehouse and Gold marts, open the canonical
[PBIP](../powerbi/FlightOperations.pbip) in Power BI Desktop. Use the
[setup guide](phase5/README.md) for connection parameters and refresh,
and the [acceptance report](phase5/m55_acceptance.md) for validation commands,
SQL/DAX reconciliation and actual Desktop interaction checks. The accepted
report has five pages, 11 tables, 11 relationships and 49 measures. The final
local regression recorded 103 tests passed, Ruff PASS and zero PBIR errors
or warnings. The PBIP is already source controlled; do not regenerate it
merely to open the existing report.

## Phase 7: orchestration and operational validation

After installing Phase 2-4 dependencies, follow the
[Dagster setup and operations runbook](phase7/README.md). Use a separate
virtual environment from requirements-phase7.txt and a dedicated local
DAGSTER_HOME. Run all 24 supported monthly partitions before
rebuild_gold_and_validate. The weekly audit is stopped by default;
do not enable it until the warehouse and daemon are available.

See the [monitoring runbook](phase7/monitoring_runbook.md) and
[full-population acceptance](phase7/acceptance.md) for actual
scheduler/recovery evidence and the successful isolated full Gold
build (11 models and 65 tests).

## Phase 8: performance and reproducibility

Use the [Phase 8 plan](phase8/README.md), [performance baseline](phase8/performance_baseline.md),
[index experiments](phase8/index_optimization.md) and
[pipeline measurements](phase8/pipeline_performance.md). The latter
two require their documented isolated databases and are not steps
for normal initial deployment.

The [final architecture](phase8/architecture.md),
[engineering decisions](phase8/engineering_decisions.md) and
[clean-checkout trial](phase8/clean_reproduction.md) explain the
implemented scope and verified fresh-install procedure.

**Important isolation warning:** the Compose file uses a fixed default
project name. A second clone on the same machine must use a different
project name (docker compose -p UNIQUE_NAME), unused host port and
independent credentials/volume. Verify the target database before
any fixture, benchmark or rebuild. Never run docker compose down -v
against the accepted warehouse.
