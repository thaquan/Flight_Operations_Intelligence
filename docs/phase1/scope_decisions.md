# Phase 1 — Scope decisions and Phase 2 handoff

## Agreed project scope

| Decision | Phase 1 choice | Why |
| --- | --- | --- |
| Primary source | BTS **Reporting Carrier** On-Time Performance | Real monthly flight-level operational data, with official definitions. |
| Pilot month | 2025-01 | Manageable, reproducible complete sample. |
| MVP comparison period | Full calendar year 2025 | Annual seasonality and monthly incremental ingestion. |
| Dashboard cohort | Fixed top **20 origin airports by 2025 flight count** | Stable segments for airport comparisons; pilot ranking is provisional. |
| Source retention | Preserve all January raw ZIP bytes; all 2025 original ZIPs in Phase 2 | Auditability and easy reprocessing/backfill. |
| Status grain | One BTS record per reported scheduled flight; never discard cancelled/diverted flights | Cancellation and diversion KPIs remain trustworthy. |
| Arrival on-time base | Noncancelled, nondiverted, valid `ArrDel15` flights | Prevent false perfect on-time ratings from NULL coercion. |
| Flight candidate key | FlightDate, DOT carrier ID, flight number, origin/dest airport IDs, scheduled departure HHMM | Unique in January sample; retest at full-year scope. |
| Time zone | Keep raw local HHMM fields; canonical UTC only after airport-zone mapping | Avoid incorrect weather joins and DST issues. |
| Weather | NOAA GHCNh Phase 6; no weather acquisition claimed in Phase 1 | Defer complexity until operational MVP works. |
| Stack | Python, Polars/PyArrow, PostgreSQL, dbt Core, Power BI Desktop, Docker; Dagster OSS later | Local-first, no paid Fabric or paid cloud requirement. |
| Streaming | Not in MVP | BTS is released monthly; do not misrepresent a batch feed as streaming. |

## Out of scope for initial MVP

1. Realtime radar / live aircraft trajectories and Kafka architecture.
2. Ticket prices, revenue, profit, seat occupancy and passenger-specific outcomes.
3. Predictive ML model and weather **causation** claims.
4. Entire 1987–present history, multi-cloud infrastructure and paid Microsoft Fabric capacities.
5. Downloading 2026 historical months before validating the 2025 ingestion baseline.

## Phase 2 implementation backlog

| Priority | Task | Definition of done |
| --- | --- | --- |
| P0 | Configurable monthly BTS downloader | Accepts `--year`, `--month`; obtains official ZIP; handles retries and temporary incomplete downloads. |
| P0 | Immutable source files and manifest | Records month, URL, source SHA-256, byte count, load status, rows, ingestion time. |
| P0 | Repeatable CSV → partitioned Parquet | Read ZIP without manually extracting to a permanent CSV, remove only unnamed trailing header, preserve typed fields and raw lineage. |
| P0 | PostgreSQL landing schema | Load a month in transactions and reconcile source/warehouse counts. |
| P0 | Idempotency | Re-running the same month does **not** double the rows; corrected month data can be safely reprocessed. |
| P0 | Status and key validation | Check `Cancelled/Diverted`, date, `ArrDel15`, candidate-key collisions and expected dimensions each month. |
| P1 | Full 2025 backfill | Download months Jan–Dec in batches; log actual total rows/storage and choose top 20 by full-year airport ID. |
| P1 | Automated smoke tests | Small fixture ZIP and a database integration test; CI does not require a 243 MB CSV. |

## Acceptance criteria to start Phase 3

- A single documented command initializes dependencies and ingests January 2025 into PostgreSQL.
- The pipeline rerun is idempotent and preserves a SHA-256-based source manifest.
- Every parsed source row has a traceable source file and original row position.
- Real January source count **539,747** reconciles with the month landing count (unless explicit, justified quarantine rows are recorded).
- Cancellation/diversion NULL logic is preserved; no made-up arrival delay for non-arrivals.
- Source format anomaly (unnamed final column) handled without shifting real columns.
- Monthly tests and a minimal CI job pass on tiny test data.

## Suggested Phase 2 Git milestones (after a repository has been configured)

1. `Initialize flight operations project and data profiling`
2. `Add monthly BTS downloader and source manifest`
3. `Convert raw flight data into partitioned Parquet`
4. `Load flight records into PostgreSQL with validation`
5. `Document ingestion checks and reproducible setup`

No remote GitHub repository was provided for this project at Phase 1. Nothing has been pushed; the separate existing HR Workforce repository is untouched.
