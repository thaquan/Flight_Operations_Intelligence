# M3.1 Infrastructure Validation

## Scope

This record covers the PostgreSQL and dbt foundation only. It is not a certification of Silver/Gold data models, dashboard metrics, or Phase 3 completion.

## Local verification

| Check | Observed result | Status |
| --- | --- | --- |
| Compose configuration | `docker compose config --quiet` returned successfully | Pass |
| Container startup | PostgreSQL service became `healthy` | Pass |
| Network exposure | Host `127.0.0.1:5433` mapped to container port `5432` | Pass |
| PostgreSQL version | `17.12 (Debian 17.12-1.pgdg13+1)` | Pass |
| Database and role | `flight_warehouse` / `flight_app` | Pass |
| Database encoding | `UTF8` | Pass |
| Initial namespaces | `audit`, `gold`, `intermediate`, `marts`, `silver`, `staging` | Pass |
| Bootstrap metadata | `audit.bootstrap_info` contained schema version `1` | Pass |
| dbt Core | `1.11.17` with PostgreSQL adapter `1.11.0` | Pass |
| dbt connection | `dbt debug` reported `All checks passed!` | Pass |
| Container restart | Bootstrap timestamp matched before and after restart | Pass |
| Named volume | `flight_operations_intelligence_postgres_data` retained database state | Pass |
| Python tests | `38 passed` (Phase 1/2 regression and M3.1 tests) | Pass |

The persistence check compared the stored `audit.bootstrap_info.initialized_at_utc` value before and after restarting the PostgreSQL container. The value was unchanged; the named volume remained attached. This verifies preservation over a restart, not backup or disaster recovery.

## Security and repository hygiene

- The local `.env` is ignored; `.env.example` contains only placeholders.
- No raw BTS ZIPs, Bronze Parquet partitions, database files, or Docker volumes are tracked.
- dbt-generated logs, targets and user identifiers are excluded from Git.
- PostgreSQL binds only to the loopback interface by default.

## Outstanding work

M3.1 does **not** claim to have loaded the 14,080,680 Bronze flight rows into PostgreSQL. That load and its reconciliation belong to M3.2. dbt business models and automated data tests are also pending.
