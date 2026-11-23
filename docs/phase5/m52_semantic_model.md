# M5.2 - PostgreSQL Gold semantic-model scaffold

**Status (2026-11-19):** Deterministic TMDL scaffold prepared.
**Not yet verified in Power BI Desktop and not refreshed from PostgreSQL.**
M5.1 design remains proposed for review; do not describe M5.2 as fully
connected or published until the execution checklist below passes.

## Delivered

- Offline validation evidence: docs/phase5/m52_validation.md.
- The generator at src/phase5/build_semantic_model.py creates the full
  semantic-model definition at powerbi/FlightOperations.SemanticModel/.
- The model includes **11 Import-mode tables**: five Gold analytics marts;
  dim_month, dim_date, dim_airline; and three distinct airport role dimensions
  (dim_airport, dim_origin_airport, dim_dest_airport).
- The model defines **11 active one-way many-to-one relationships**.
  There are no direct mart-to-mart or ambiguous many-to-many joins.
- Native Power Query connections use pPgServer (default 127.0.0.1:5433)
  and pPgDatabase (default flight_warehouse), never a stored password.
- Pre-aggregated rate percentages and delay means are excluded. Base counters
  are hidden and have no implicit summation; explicit DAX comes in M5.3.

## Grain and filter contract

| Dimension (one side) | Mart (many side) | Key |
| --- | --- | --- |
| dim_month | All five analytics marts | source_month |
| dim_airline | Airline monthly, delay causes | airline_sk |
| dim_date | Airport daily | date_key -> flight_date_key |
| dim_airport | Airport daily | airport_sk |
| dim_origin_airport | Route monthly | airport_sk -> origin_airport_sk |
| dim_dest_airport | Route monthly | airport_sk -> dest_airport_sk |

dim_month derives its rows from the source months in mart_network_monthly.
mart_airport_daily.source_month is derived using
Date.StartOfMonth(flight_date) in Power Query. This provides a shared
month slicer without an ambiguous date-to-month relationship.

**Critical:** Each airport-daily flight contributes to both origin and
destination roles. Page-level filters or DAX must always select exactly one
airport_role. Routes are directed, so origin and destination selectors must
remain independent. The current route mart has no airline key: never imply
that the airline slicer affects a route ranking. Delay-cause observation
counts represent category entries, not unique delayed flights.

## Offline reproduction

From the repository root:

~~~powershell
.\.venv\Scripts\python.exe -m src.phase5.build_semantic_model
.\.venv\Scripts\python.exe -m pytest tests/test_phase5_semantic_model.py -q -p no:cacheprovider
~~~

The generator produces UTF-8 TMDL files without a BOM, is deterministic
and never reads the local .env file. These tests only validate metadata
and schema contracts, not actual Desktop deserialization or data refresh.

## Ready-to-open Power BI Project

powerbi/FlightOperations.pbip is a minimal PBIP/PBIR project shell wired to
the source-controlled TMDL semantic model by a relative byPath reference.
The report currently contains a blank 1280x720 Executive Overview page; the
static Aviation Command preview is not a working report visual. The project
has not been successfully opened or refreshed inside Desktop.

## Complete M5.2 in Power BI Desktop

1. Start Docker Desktop and ensure the local warehouse is running:

   ~~~powershell
   docker compose up -d
   docker compose ps
   ~~~

   Confirm the existing gold tables are populated using the Phase 3
   runbook. Do not reseed or truncate data just for the BI report.

2. In a recent Power BI Desktop, create an empty local report and save it
   as a Power BI Project (.pbip) with TMDL as its semantic-model format.
3. Close Desktop. Back up the Desktop-generated SemanticModel definition,
   then copy definition.pbism and the definition folder from
   powerbi/FlightOperations.SemanticModel into the Desktop-generated
   *.SemanticModel directory. Never replace an unrelated model.
4. Reopen the .pbip. Resolve any TMDL parse errors reported by Desktop.
   In Power Query, verify pPgServer and pPgDatabase, authenticate via the
   PostgreSQL Database credential prompt, select Import and refresh all
   eleven tables.
5. In Model view, verify every one-side key is unique, 11 relationships
   are active and single-direction, and no relationship becomes many-to-many.
6. Confirm **24 monthly network rows** (Jan 2024-Dec 2025). Compare the
   full-period additive totals against docs/phase4/quality_report.json:

   | Metric | Expected |
   | --- | ---: |
   | Scheduled flights | 14,080,680 |
   | Eligible arrivals | 13,844,731 |
   | Late arrivals 15+ | 2,984,604 |
   | On-time arrivals | 10,860,127 |
   | Cancelled flights | 199,191 |
   | Diverted flights | 36,757 |

7. Validate that summing a single airport_role across the full period
   matches network scheduled flights, that separate directed route selectors
   work, and that the one completed flight missing ArrDel15 is not included
   in the eligible-arrival denominator.
8. After an actual refresh, capture Desktop version, refresh timestamp,
   row counts, relationship screenshots and any errors in a new
   docs/phase5/m52_validation.md. Do not commit cache, credentials or PBIX.

## Next milestones

- M5.2 (pending): successful Power BI Desktop import/refresh and
  reconciliation, followed by design approval.
- M5.3: explicit DAX measures with DIVIDE and role-safe denominators;
  cause-minute shares use the proper all-cause selection denominator.
- M5.4: construct the five dashboard pages from approved wireframes.
- M5.5: validate interactions, accessibility, visuals and screenshots.
- M5.6 (optional): mobile layout and portfolio handoff.

## Technical references

- https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset
- https://learn.microsoft.com/en-us/analysis-services/tmdl/tmdl-overview
- https://learn.microsoft.com/en-us/power-query/connectors/postgresql
