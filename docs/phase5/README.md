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
| Executive Overview | Network reliability | Full-width 24-month line with monthly markers and sparse quarter ticks; compact annual-risk delta strip |
| Airline Performance | Exposure versus reliability | Carrier scatter: flights vs delay rate, cancellation-sized bubbles; traffic-share treemap |
| Airports & Routes | State-to-airport-to-route analysis | Drillable origin traffic by state then airport; linked directed-route table |
| Delay Causes | Cause mix over time | 24-month stacked area by cause; proportional donut for the same reported-minute total |
| Seasonal Trends | Year-over-year patterns | 2024/2025 monthly delay-rate heatmap and diverging percentage-point differences |

The three analysis pages use deliberately different chart grammars:
**Airline Performance** compares rate against exposure rather than ranking
each measure independently; the treemap encodes each carrier's share of
flights. **Airports & Routes** starts at state level, then drills to an origin
airport; selecting a bar filters the adjacent route table through their
shared directed-route mart. Use the bar visual's native drill controls to
change levels. **Delay Causes** separates change over time (stacked area)
from composition (donut), with the same reported-minute measure in both.
Cause-minute totals are not counts of unique delayed flights.

The Executive Overview reserves full horizontal space for the monthly
delayed-arrival trend, plotted with direct calendar dates, unsmoothed
segments and individual observations. A compact strip highlights changes
in operational risk: **+1.49 pp** late arrivals, **+0.11 pp**
cancellations and **+0.03 pp** diversions for 2025 versus 2024.
Positive percentage-point change means operational risk worsened.
The five top-level KPIs retain their original definitions; total flight
volume displays two decimals in millions (14.08M for the full period).
The YoY strip does not repeat the individual 2024/2025 rate values,
and it does not respond to the synced YEAR filter.

Executive comparison measures summarize complete 2024 and 2025 periods
even when the YEAR slicer is set to one year. Seasonal heatmap rates
preserve the calendar-month context but ignore YEAR, so the two columns
remain comparable under either filter setting. The diverging bar is
2025 minus 2024 in percentage points (coral: greater delay risk;
cyan: less delay risk). These are ratios of aggregated counts, not
averages of monthly percentages. The model now includes **49 measures**,
six of which support the new year-over-year comparisons.

The YEAR / PERIOD slicer synchronizes across all five pages. Home and page
tabs use native Power BI PageNavigation actions. Use **Ctrl+click** in
Desktop Edit mode, or an ordinary click in Reading view.

## Final dashboard usability and accessibility (23 November 2026)

All five pages were re-rendered from the canonical PBIP after a scoped
visual-quality pass. Selected navigation tabs use dark text on cyan to
satisfy WCAG AA normal-text contrast; 12 data visuals have descriptive
native Power BI alt text, and the KPI row on each page displays two
decimal places for large compact numbers where applicable.

Airline scatter bubbles are labeled on hover rather than with overlapping
static carrier codes; the treemap legend is suppressed because the tile
labels already identify the categories. Colors in the treemap denote
categories, **not** delay risk. Airport route delay-rate cells use a fixed
10-40% color scale; route rows remain ranked by scheduled volume. The
origin chart drills between state and origin airport levels and filters
the linked route table. Delay Causes now has a scalar month axis; its
observation count is not a count of unique delayed flights and cause
minutes are not normalized for traffic. Seasonal heatmap columns share
a fixed 10-35% scale so 2024 and 2025 shading is comparable. Top KPI
values follow YEAR while both seasonal comparison columns stay fixed.

The live Power BI Desktop validation confirmed native Home navigation,
state-to-airport level change and Drill up, and a Texas bar selection
filtered the route table to **1,506,108 flights / 24.19% delay rate**;
clearing it restored the full-period total. YEAR = 2024 returned
**7.08M flights / 20.82% delay rate**, then All restored **14.08M /
21.56%**. The report was saved at Executive Overview with YEAR = All.

**Remaining scope:** a separate mobile-specific layout has not been
implemented; airline dimension data does not include full carrier names,
and the dashboard has no user-agreed SLA thresholds. The five top-tab
links and Home were subsequently verified using actual Ctrl+mouse clicks
in Desktop Edit mode, with each destination page checked after navigation.

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

See the [Phase 5 acceptance report](m55_acceptance.md) for direct Gold/DAX reconciliation and Desktop interaction status.

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
returned zero errors or warnings, and the Python suite passed 103 tests.
Power BI Desktop is required for actual Import refresh and full visual
interaction testing.

The PBIP stores report definitions and semantic metadata, **not** a
portable snapshot of the imported dataset. Local `.pbi` caches, database
passwords, environment variables and raw flight data are excluded from Git.
No Fabric workspace deployment is part of this checkpoint.
