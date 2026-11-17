# Phase 3 / M3.1: PostgreSQL Infrastructure

## Purpose and boundary

Milestone M3.1 establishes a reproducible local PostgreSQL warehouse and a working dbt Core connection. The database is intentionally empty of flight records at this stage. Bronze-to-Silver ingestion, dimensional models, incremental transformations, and Gold data marts will be implemented in later Phase 3 milestones.

The design is suitable for a local student portfolio and does not require a cloud subscription or a paid Microsoft Fabric capacity.

## Components

| Component | Configuration | Responsibility |
| --- | --- | --- |
| PostgreSQL | Docker image `postgres:17` | Local relational warehouse |
| Docker Compose | `docker-compose.yml` | Service lifecycle, health checks, host port and storage |
| Database volume | `flight_operations_intelligence_postgres_data` | Retain data across container restarts |
| Initial SQL | `docker/postgres/init/001_create_schemas.sql` | Create namespace boundaries and a bootstrap marker |
| Credentials | Local ignored `.env` | Database name, username, password and host port |
| dbt Core | `dbt/dbt_project.yml` and `dbt/profiles.yml` | Project configuration and PostgreSQL connection |
| Diagnostics | `src/phase3/check_database.py` | Verify database properties and initial schemas |

The Compose port binding uses `127.0.0.1` rather than all interfaces. Its default host port is **5433**, avoiding the common locally installed PostgreSQL service on port 5432. Internal container traffic still uses port 5432. The Docker health check uses `pg_isready`.

## Initial schema ownership

The initialization script creates six schemas:

| Schema | Intended use |
| --- | --- |
| `silver` | Validated flight records loaded from Bronze |
| `staging` | dbt source-aligned staging models |
| `intermediate` | Shared transformation logic |
| `gold` | Curated analytical fact and dimension models |
| `marts` | BI-oriented aggregates and reporting views |
| `audit` | Pipeline and warehouse metadata |

The `audit.bootstrap_info` table records one initialization marker with a schema version and a timestamp. It is used to verify that the same database survives a container restart, not as a source of business metrics.

PostgreSQL's entrypoint applies `docker/postgres/init/*.sql` **only when the data directory is first initialized**. Editing this script later will not automatically migrate a populated database. Subsequent schema changes need explicit, versioned migrations.

## Prerequisites

- Docker Desktop with the Linux container engine running.
- Python 3.10+ and a local virtual environment.
- Free local storage for the Docker image and named volume.
- Port 5433 free on the Windows host, or an alternate `POSTGRES_PORT` in the ignored `.env`.

## First-time setup

Execute commands from the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-phase2.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-phase3.txt
.\.venv\Scripts\python.exe -m src.phase3.bootstrap_env
docker compose config --quiet
docker compose up -d --wait
.\.venv\Scripts\python.exe -m src.phase3.check_database
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli debug
```

The bootstrap command creates `.env` with a cryptographically random password only if the file is absent. If an existing `.env` is found, the script does not modify it. Do not commit this file or paste credentials into logs, tickets, or screenshots. `.env.example` contains configuration names and a nonfunctional placeholder only.

The dbt wrapper loads the local settings into the dbt process environment; `dbt/profiles.yml` references them with `env_var`. No password is hard-coded into the profile.

## Daily operations

```powershell
docker compose up -d --wait
docker compose ps
.\.venv\Scripts\python.exe -m src.phase3.check_database
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli debug
docker compose stop
```

Use `docker compose restart postgres` to restart the single service. Both `stop` and `down` preserve the named volume; **do not use `docker compose down -v`**, which deletes the database volume. Keep database files and dumps outside the Git repository.

## Troubleshooting

| Symptom | Check or action |
| --- | --- |
| Docker daemon unavailable | Start Docker Desktop and wait for its engine to become ready. |
| `POSTGRES_PASSWORD` not set | Run `python -m src.phase3.bootstrap_env` or populate `.env` privately. |
| Port 5433 already in use | Choose an unused `POSTGRES_PORT` in `.env` and restart the Compose service. |
| Container unhealthy | Inspect `docker compose ps` and `docker compose logs postgres`. Avoid exposing credential values. |
| dbt connection fails | Verify the container is healthy, `.env` exists, and dbt is run through `src.phase3.dbt_cli`. |
| SQL changes do not appear | Initialization scripts run only once on empty database volumes. Use migrations for existing volumes. |

## Next milestone

M3.2 will implement the controlled Bronze Parquet to PostgreSQL Silver load, including schemas, row-level typing, batch loading, source lineage and reconciliation. It must preserve all 24 months and the complete BTS flight population. Subsequent milestones will build dbt staging, intermediate models, dimensional facts and marts.
