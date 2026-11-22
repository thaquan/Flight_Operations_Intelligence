# Power BI reporting

The Flight Operations Intelligence report analyzes U.S. BTS domestic flight
performance from January 2024 through December 2025. Its primary artifact
is the Power BI project at `../../powerbi/FlightOperations.pbip`.

## Project structure

| Path | Purpose |
| --- | --- |
| `powerbi/FlightOperations.pbip` | Desktop entry point |
| `powerbi/FlightOperations.Report/` | Five-page report, native visuals and theme resources |
| `powerbi/FlightOperations.SemanticModel/` | Import-model TMDL, relationships and measures |
| `powerbi/themes/FlightNetworkRiskIntel.json` | Flight Deck source theme |
| `src/phase5/` | Modeling, report templates and targeted maintenance utilities |
| `tests/test_phase5_*.py` | Model and report regression checks |

The model imports PostgreSQL Gold marts. Its connection parameters default
to `127.0.0.1:5433` and database `flight_warehouse`. Credentials are
entered locally in Power BI Desktop and are not stored in this repository.
Run the warehouse before refreshing the model.

## Report pages

| Page | Focus | Main charts |
| --- | --- | --- |
| Executive Overview | Network reliability | 24-month delayed-arrival trend; yearly cancellation and diversion rates |
| Airline Performance | Carrier differences | Airline delay rates and scheduled-flight volumes |
| Airports & Routes | Airport exposure and directed corridors | Busiest origin airports; route-level volume and delay table |
| Delay Causes | Reported delay attribution | Cause-minute ranking and proportional donut |
| Seasonal Trends | Year-over-year patterns | Monthly delay-rate overlay; monthly volume comparison |

The YEAR / PERIOD slicer synchronizes across all five pages. Home and page
tabs use native Power BI PageNavigation actions. Use **Ctrl+click** in
Desktop Edit mode, or an ordinary click in Reading view.

## Metrics and interpretation

- **Scheduled Flights** counts BTS flight records, including cancelled and
  diverted flights.
- **Arrival Delay 15+ Rate** divides qualifying late arrivals by *eligible*
  completed arrivals with known arrival-delay status.
- **Cancellation Rate** and **Diversion Rate** divide their respective
  counts by scheduled flights.
- Airline, origin-airport and route metrics use their own mart grains.
  Origin and destination counts must not be added together.
- Delay-cause minutes are BTS-attributed categories; they do not imply
  observed weather measurements or unique delayed-flight counts.

See [KPI catalog](kpi_catalog.md) for the measurement contract and
[report requirements](report_requirements.md) for scope and limitations.

## Validation

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\ruff.exe check --select E4,E7,E9,F,I src/phase5 tests/test_phase5_*.py
powerbi-report-author validate powerbi/FlightOperations.pbip --no-schema
```

The project was validated locally using Power BI Desktop, including
successful rendering of all five pages. The structural PBIR validator
returned zero errors or warnings, and the Python suite passed 95 tests.
Power BI Desktop is required for actual Import refresh and full visual
interaction testing.

The PBIP stores report definitions and semantic metadata, **not** a
portable snapshot of the imported dataset. Local `.pbi` caches, database
passwords, environment variables and raw flight data are excluded from Git.
No Fabric workspace deployment is part of this checkpoint.
