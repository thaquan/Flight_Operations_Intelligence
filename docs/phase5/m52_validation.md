# M5.2 validation checkpoint - 2026-11-19

## Confirmed results

- Local branch and GitHub main both resolved to ea966cb before M5.2 work.
- No existing M5.1 design artifact was deleted, reverted or committed.
- Generated semantic model definition contains 11 Import tables, 11 active
  one-direction relationships and 2 Power Query connection parameters.
- The locally installed Microsoft Analysis Services Tabular library
  (version 19.87.7.0) deserialized the entire TMDL folder successfully
  using TmdlSerializer.DeserializeDatabaseFromFolder.
- Full Python regression: **77 passed**.
- New-file Ruff lint (E4,E7,E9,F,I): **PASS**.
- Git whitespace diff check: **PASS**.
- Offline contract suite for M5.2: **7 passed** (included in the 77).

## Still to validate

- A Power BI Desktop installation was not detected in standard install
  locations or the uninstall registry during this session.
- Docker Desktop PostgreSQL engine was unavailable; localhost:5433
  was not listening. Live Gold-query execution was not attempted.
- The TMDL parse success proves the definition is syntactically readable
  by the local TOM library. It does **not** prove Power BI Desktop can
  load tables, authenticate, refresh, validate relationships against
  real data, or render visuals.
- M5.1 design approval is still pending; no report has been published.
- No git commit or push was performed.

## Exit criteria for actual M5.2 completion

1. Open the semantic model in Power BI Desktop as a PBIP TMDL project.
2. Authenticate to the local PostgreSQL Gold database with Import mode.
3. Refresh all 11 model tables without errors.
4. Confirm 24 months and reference counts in
   docs/phase4/quality_report.json.
5. Validate role-safe airport totals and both directed-route selectors.
6. Save the Desktop project and record a refresh timestamp/version
   with no credentials or local data cache in Git.

See m52_semantic_model.md for exact steps and modeling cautions.

## Live follow-up: Docker running, warehouse verified (2026-11-19)

- Docker Desktop started from D:/Docker/Desktop/Docker Desktop.exe.
- Docker Engine 29.6.2 operational; PostgreSQL 17 container
  flight_operations_intelligence-postgres-1 became healthy.
- The existing flight_warehouse connected successfully at 127.0.0.1:5433.
- Gold contains nine tables (three dimensions, one fact, five analytics marts).
- Direct SQL against gold.mart_network_monthly returned **24 rows**,
  2024-01-01 through 2025-12-01, and exact additive totals:

  | Metric | SQL sum |
  | --- | ---: |
  | scheduled_flights | 14,080,680 |
  | eligible_arrivals | 13,844,731 |
  | late_arrivals_15 | 2,984,604 |
  | on_time_arrivals | 10,860,127 |
  | cancelled_flights | 199,191 |
  | diverted_flights | 36,757 |

- gold.mart_airport_daily contained **481,262 rows**.
- A source-controlled Power BI project shell was written at
  powerbi/FlightOperations.pbip; report metadata is at
  powerbi/FlightOperations.Report and its definition.pbir uses byPath
  to the TMDL semantic model. It has one empty Executive Overview page.
- **Import not completed:** WinGet lists Power BI Desktop as an
  MS Store package, but the active Windows session exposes neither
  the PBIDesktop executable nor a running PBIDesktop process. Both
  a shell AppsFolder launch request and a .pbip launch request failed
  to produce a Power BI Desktop process; .pbip has no registered
  Windows file association in this session. No authentication prompt,
  refresh, in-memory Power BI import, or report render was verified.
  Data is accessible from PostgreSQL but not yet imported into Power BI.
- The original M5.1 demo can be opened at
  docs/phase5/dashboard_preview.png. The theme JSON is at
  powerbi/themes/FlightOperationsIntelligence.json.
- Keep Power BI import credentials exclusively in Desktop; do not
  place the local .env credentials into report files.

**Next user-visible action:** Open Power BI Desktop in the interactive
Windows desktop session, then use File > Open to select
D:/Flight_Operations_Intelligence/powerbi/FlightOperations.pbip.
Use Power Query to authenticate and refresh all tables with the
existing locally running PostgreSQL instance, then compare the
Power BI totals with the SQL results above. Report PBIR/TMDL metadata
may require compatibility adjustments in Desktop.
