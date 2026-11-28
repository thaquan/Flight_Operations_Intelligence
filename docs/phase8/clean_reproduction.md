# M8.4 - Clean-checkout reproduction

Verified on Windows on 28 November 2026 using a fresh GitHub clone on
the existing host, not a different physical machine. The trial started
from commit 33b034e and installed the two Python environments from
their pinned top-level requirements. Installed packages, database
files and generated Bronze data were not copied.

## Acceptance results

| Check | Observed result |
| --- | --- |
| Clean GitHub clone | PASS; no tracked local credentials or generated Bronze |
| Fresh ETL and Dagster virtual environments | PASS; both pip check commands clean |
| Initial ETL regression | 123 passed, 1 failed, 9 skipped |
| Theme checkout fix | 2ec5bd1; LF/CRLF hash normalization |
| ETL regression after fast-forward | 125 passed, 9 skipped |
| Dagster regression | 20 passed |
| Ruff | PASS |
| New PostgreSQL Compose project | Healthy; PostgreSQL 17.12 |
| Synthetic fixture | 10 flights, 3 months; 76/76 dbt nodes PASS |
| Fixture quality and recovery | 6 PASS, 0 REVIEW, 0 FAIL; recovery PASS |
| Actual January 2024 ingestion | 547,271 rows from verified ZIP |
| Identical January rerun | Bronze and Silver both skipped |
| Actual January Gold build | 11/11 dbt models PASS, 13.45 s |
| January reconciliation | All 7 network metrics and five mart row counts matched main |

Git converted the theme source from LF to CRLF in the fresh checkout.
A raw-byte resource hash consequently differed. Commit 2ec5bd1
normalizes line endings before hashing in the two theme scripts and
adds a regression test for both line endings. The existing report
and registered resource were not modified.

## Fresh environment and isolation

Use the [full reproduction guide](../reproduction.md). The following
Windows setup describes the tested workflow. Choose an unused directory,
Compose project name and host port when an accepted warehouse already
exists. Changing the directory alone does not isolate Compose because
the versioned compose file has a fixed default project name.

```powershell
git clone https://github.com/thaquan/Flight_Operations_Intelligence.git
Set-Location Flight_Operations_Intelligence
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-phase2.txt -r requirements-phase3.txt -r requirements-phase4.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m venv data/tmp/dagster-venv
.\data\tmp\dagster-venv\Scripts\python.exe -m pip install -r requirements-phase7.txt
.\data\tmp\dagster-venv\Scripts\python.exe -m pip check
.\data\tmp\dagster-venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_phase7_orchestration.py
.\.venv\Scripts\python.exe -m src.phase3.bootstrap_env
```

For a second checkout, edit only its private .env to set an unused
port and distinct database name. This trial used POSTGRES_PORT=5643,
POSTGRES_DB=flight_m84_real and the unique project flight_m84_clean,
with a newly generated password. Check that port, project and volume
are unused before startup.

```powershell
docker compose -p flight_m84_clean up -d --wait postgres
.\.venv\Scripts\python.exe -m src.phase3.check_database
```

The trial created a separate flight_ci database in that new container
for the synthetic fixture. Follow the [CI runbook](../phase4/ci_runbook.md)
and [workflow](../../.github/workflows/ci.yml) for the fixture setup.
The fixture requires FLIGHT_CI_FIXTURE=1 and POSTGRES_DB=flight_ci.
Never point it at the real warehouse. The fixture and real databases
had distinct names and no original project volume was reused.

## Real-data trial

The official January ZIP was copied from the previously verified
local source archive to the path in the versioned acquisition
manifest; no raw file was downloaded during this trial. The ZIP
SHA-256 matched the manifest:

```text
fe089b45523f9d4ac0ccd0e176a543d274e914ee5ae5bd384dbaafc7dc06ebfd
```

Use the [acquisition guide](../reproduction.md#phase-1-reproduce-the-full-assessment)
or [source release](https://github.com/thaquan/Flight_Operations_Intelligence/releases/tag/bts-data-2024-2025-v1)
to obtain the matching ZIPs on another machine.

From the clean repository root, initialize its own Dagster instance:

```powershell
$env:DAGSTER_HOME = Join-Path (Get-Location).Path 'data/tmp/dagster-home'
$env:FLIGHT_PIPELINE_PYTHON = Join-Path (Get-Location).Path '.venv/Scripts/python.exe'
New-Item -ItemType Directory -Force -Path $env:DAGSTER_HOME | Out-Null
Copy-Item orchestration/dagster.yaml (Join-Path $env:DAGSTER_HOME 'dagster.yaml')
```

Use the [Dagster runbook](../phase7/README.md) to launch the
ingest_flight_month job with partition 2024-01 twice. The actual trial
used execute_in_process in the new Dagster environment, with persistent
local instance storage.

| Run | ID | Engine duration |
| --- | --- | ---: |
| New load | ac8e00b5-5e44-4138-b413-626ea518439c | 52.23 s |
| Idempotent rerun | 1bd2aa96-e71e-4b43-8952-3f89c85bb8e1 | 4.95 s |

Bronze produced 17,833,166 Parquet bytes. The first run loaded
547,271 Silver rows and the second skipped all rows at both layers.
One audit row remained. A direct dbt run then created nine tables
and two views:

```powershell
$env:POSTGRES_HOST = '127.0.0.1'
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli run --threads 2
```

The sample used direct dbt run, not the full-scope Dagster Gold
job or full quality gates, which require 24 months. All 65 dbt data
tests passed on the separate synthetic fixture; they were not
rerun on the actual one-month sample. Full-scope acceptance remains
in [Phase 7](../phase7/acceptance.md).

## Reconciled January results

Read-only repeatable-read queries returned identical January counts
in the accepted and clean warehouses. The daily airport mart is
scoped by flight_date; monthly marts use source_month.

| Relation | January rows in both warehouses |
| --- | ---: |
| Silver flights | 547,271 |
| Gold flight fact | 547,271 |
| Network monthly | 1 |
| Airline monthly | 15 |
| Airport daily | 20,059 |
| Route monthly | 5,666 |
| Delay causes | 75 |

| Network KPI | January value in both warehouses |
| --- | ---: |
| Scheduled | 547,271 |
| Completed | 525,370 |
| Cancelled | 20,389 |
| Diverted | 1,512 |
| Eligible arrivals | 525,370 |
| Late arrivals 15+ | 126,410 |
| On-time arrivals | 398,960 |

The main Bronze manifest and three pre-existing Power BI file hashes
were unchanged. Counts and seven network metrics matched; all-column
equality of every flight or mart row was not tested. The clean clone
remained Git-clean (generated artifacts ignored).

## Scope and cleanup

A different physical machine, fresh acquisition and ingestion of
all 24 months, Power BI Desktop refresh in the new clone and Azure
Pipelines execution were not tested. Top-level dependency versions
are pinned, but transitive dependencies are not fully locked. The
observed installation proves this resolved environment, not identical
future dependency resolution.

Keep the test database and its run history for evidence, or stop
only the test project from its checkout, using its explicit name:

```powershell
docker compose -p flight_m84_clean stop postgres
```

For full historical operation, complete all 24 partitions before
launching rebuild_gold_and_validate, retain documented REVIEW
findings and use the accepted PBIP without regenerating it.
