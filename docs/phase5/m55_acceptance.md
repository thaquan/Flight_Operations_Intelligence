# Phase 5 acceptance: data reconciliation and report interactions

**Date:** 22 November 2026

**Project:** `powerbi/FlightOperations.pbip`
**Result:** Data and structural checks passed. One navigation click-through check requires a manual Desktop pass.

## Scope

The review covers the five-page Flight Deck report and its 43 DAX measures using the 2024–2025 U.S. Bureau of Transportation Statistics flight dataset. Power BI Desktop uses an Import semantic model sourced from PostgreSQL Gold marts; this is historical analysis, not live flight tracking.

## Gold versus Power BI

PostgreSQL 17 was verified healthy on `127.0.0.1:5433`. A read-only Power BI Modeling MCP session queried the currently open Desktop model (11 tables, 43 measures). **254 integer observations matched exactly** between Gold SQL aggregates and live DAX query results.

| Check | Scope | Result |
| --- | --- | --- |
| Network totals | Scheduled, eligible, late, on-time, cancelled and diverted | PASS — 6 comparisons |
| Annual totals | Five measures for each of 2024 and 2025 | PASS — 10 comparisons |
| Monthly totals | Five measures across 24 month/year pairs | PASS — 120 comparisons |
| Airline comparisons | Scheduled, eligible and late arrivals for 12 selected carriers | PASS — 36 comparisons |
| Origin airports | Scheduled, eligible and late arrivals for 12 high-volume airports | PASS — 36 comparisons |
| Directed routes | Scheduled, eligible and late arrivals for 12 corridors | PASS — 36 comparisons |
| Delay attribution | Reported cause minutes for the five BTS categories | PASS — 5 comparisons |
| Mart reconciliation | Airline, origin, destination and route scheduled totals, plus cause-minute total | PASS — 5 comparisons |
| **Total** | | **254/254 exact matches** |

The network results reconcile as follows:

| Metric | 2024 | 2025 | All 24 months |
| --- | ---: | ---: | ---: |
| Scheduled flights | 7,079,061 | 7,001,619 | 14,080,680 |
| Eligible arrivals | 6,965,247 | 6,879,484 | 13,844,731 |
| Arrivals delayed 15+ minutes | 1,449,966 | 1,534,638 | 2,984,604 |
| Cancelled flights | 96,315 | 102,876 | 199,191 |
| Diverted flights | 17,499 | 19,258 | 36,757 |
| Arrival delay 15+ rate | 20.82% | 22.31% | 21.56% |

Arrival delay rates use **eligible arrivals** as the denominator; cancellation and diversion rates use **scheduled flights**. The cause marts sum to **215,729,337 attributed minutes**, which must not be interpreted as a count of unique delayed flights. Airline totals, directed-route totals, and the *separate* airport origin/destination totals each reconcile to network totals; origin plus destination is not an additive flight metric.

**Airport dimension rule:** The original airport-volume visual was tested using `mart_airport_daily` with `dim_airport[airport_code]`; using the route-origin dimension against that airport-daily measure would incorrectly repeat network totals. The later chart redesign instead groups `mart_route_monthly` by `dim_origin_airport[state_code]` then `dim_origin_airport[airport_code]`, so the origin bar and adjacent directed-route table share the same grain and filter path. These separate correct combinations are covered by report regression tests.

## Desktop interaction tests

| Scenario | Result | Evidence |
| --- | --- | --- |
| Open the canonical project | PASS | One PBIP, five report pages; saved Desktop instance |
| Select YEAR = 2024 in Executive Overview | PASS | Cards changed to approximately 7M scheduled flights and 20.82% late-arrival rate |
| Switch to Airports & Routes with YEAR still selected | PASS | Year selection persisted; route scheduled flights and delay rate changed to the same 2024 figures |
| Select YEAR = 2025 in Executive Overview | PASS | Cards changed to approximately 7M scheduled flights and 22.31% late-arrival rate |
| Restore Executive Overview and save | PASS | Executive page selected; Desktop reports no unsaved changes |
| Home/PageNavigation actions | **PASS** | Real Ctrl+mouse clicks on OVERVIEW, AIRLINES, AIRPORTS, CAUSES, TRENDS and Home moved to their expected selected pages in Desktop Edit mode |
| Chart-to-card filtering | PASS | Selecting the Jan 2024 delay-rate data point filtered network KPI cards to approximately 547K scheduled flights and 24.06% late arrivals; removing the selection restored full-period KPIs |

The final navigation audit used direct Ctrl+mouse clicks rather than UI Automation's hyperlink Invoke method, which does not perform Desktop Edit-mode navigation. Every transition was checked against Power BI Desktop's selected report page: Airline to OVERVIEW, Overview to AIRLINES, Airlines to AIRPORTS, Airports to CAUSES, Causes to TRENDS, and Seasonal to Home (Executive Overview). All six transitions passed; Desktop reported no unsaved changes after the clicks.

## Chart interactions rework (22 November 2026)

Three analysis pages were rebuilt with a purpose-specific chart language:
carrier traffic versus late-arrival rate is now a bubble scatter (bubble size
represents cancelled flights), carrier traffic share is a treemap, the origin
flight-volume bar drills from state to airport and filters the directed-route
table using the same route mart, and the reported cause-minute ranking is
replaced by a 24-month stacked area paired with the original cause-share donut.

Desktop screenshot review confirmed all chart types render data, the
scatter has a distinct data point for each of 15 carriers, and the stacked
area displays five BTS cause categories across 24 months. Selecting **Texas**
on the origin-state bar filtered the adjacent directed-route table and the
route KPIs to **1,506,108 scheduled flights** with **24.19% delayed arrivals**.
Removing the selection restored the full 14,080,680-flight context.

The two-level state-to-airport hierarchy is configured natively in PBIR.
Clicking the Power BI drill control itself remains a manual check; a positive
bar-to-table cross-filter test does not prove that a GUI drill click worked.
The model and DAX measures were left unchanged. After the chart rework,
the full Python regression passed **97 tests**, Ruff passed, and the PBIR
validator again reported zero errors and zero warnings.

## Executive and seasonal visualization trial (22 November 2026)

The Executive Overview now uses a 24-month reliability line and three
2024-to-2025 risk scorecards (delayed arrivals, cancellations and
diversions). Seasonal Trends uses a two-column month-by-year heatmap
and diverging month-by-month bars for the **2025 minus 2024 delay-rate
change in percentage points**. The semantic model has six additional
DAX measures, bringing it to **49 measures**; historical Gold mart data
and relationships remain unchanged.

DAX was checked against the Gold year-level ratios: delayed-arrival
risk increased by **1.49 pp**, cancellation rate by **0.11 pp** and
diversion rate by **0.03 pp**. Of twelve month-level delay-rate
comparisons, **seven increased and five decreased**. A read-only DAX
query under YEAR = 2024 returned both the 2024 and the 2025 heatmap
rates in all twelve rows. Only the period-specific KPI cards and trend
are affected by the YEAR filter; fixed-comparison visual measures
retain both years.

The final local regression passed **98 Python tests**, Ruff lint passed,
and PBIR validation reported **zero errors and zero warnings**.
The year-on-year authoring utilities are idempotent; the generator can
construct all five page designs in a scratch report without overwriting
the saved canonical PBIP. Native month-level drillthrough to a separate
analysis page was deferred: the trial intentionally keeps the existing
five-page navigation and its synchronized YEAR filter.

Both pages were opened and reviewed as rendered in Power BI Desktop.
Initial missing-field errors were resolved by synchronizing six new
measures to the live model, followed by a saved and reopened PBIP.
Executive scorecards now fit their labels and complete rate changes.
Seasonal heatmap displays twelve months simultaneously, together with
yearly total rates; signed bars use coral for worsening months and
cyan for improving months.

The three previously approved pages (Airline Performance, Airports &
Routes and Delay Causes) were audited against a pre-change snapshot:
**all 60 page-definition files remained byte-identical**. The PBIP
remains the only report artifact; no Git commit, push or publication
was performed for this trial.

## Executive Overview layout refinement (23 November 2026)

The stacked comparison cards were reduced to a single horizontal
risk-change strip. The three existing DAX measures now return signed
percentage-point deltas only; network totals and the other year-
comparison measures remain unchanged. The 24-month trend now uses a
scalar date axis with quarterly ticks, individual monthly markers and
straight-line interpolation rather than smoothing. The scheduled-flight
KPI shows 14.08M instead of rounding to 14M.

Live Desktop verification confirmed YEAR = 2024 reduces headline
scheduled flights to 7.08M and the late-arrival rate to 20.82% while
the +1.49 pp comparison stays fixed. YEAR was reset to All and the
Desktop report saved with 14.08M flights and 21.56% late arrivals.
The same single PBIP was used. A pre-edit ZIP backup was retained
outside the repository, and the other four page definitions were
fingerprinted to confirm no changes. The PBIR validator returned
0 errors and 0 warnings; all five authoring utilities reported
zero pending edits on rerun. No commit or remote push was made.

## Five-page visual-quality remediation (23 November 2026)

The desktop-authored canonical report was backed up outside the repository
before editing. All five pages received intentional readability and
accessibility fixes without adding or renaming a PBIP: selected tabs use
legible dark text on cyan; network/carrier/airport/cause/seasonal KPI cards
show two-decimal compact values where appropriate; airline scatter static
codes no longer overlap; redundant treemap legend is removed. The route
table now shades the delay rate with a fixed 10-40% scale, and the cause
history uses a continuous month axis. Seasonal's two year columns now
share an explicitly bounded 10-35% delayed-arrival color scale.

Twelve analytical visuals received native Power BI container AltText.
The PBIR validator returned zero errors and warnings after the final
Save. The full Python regression passed **103 tests** and Ruff passed.
All six existing authoring/quality scripts returned zero pending edits.
Five fresh page screenshots were examined; no blank charts or missing
measures appeared.

Functional Desktop checks: Ctrl+click Home navigated from Airports to
Executive Overview; the origin chart's Next Level action displayed
airport-level values and Drill up restored the state-level view.
Selecting Texas filtered the route table and cards to 1,506,108
scheduled flights and 24.19% delayed arrivals. Clearing the state
selection restored 14.08M. Selecting YEAR = 2024 displayed 7.08M
scheduled flights and 20.82% late arrivals, and selecting All restored
14.08M and 21.56%. The Desktop report was saved on Executive Overview.

Still not covered by a release gate: dedicated Power BI mobile layout,
formal accessibility inspection in an assistive screen reader, and a signed-off
SLA/risk threshold policy. All five top navigation tabs and Home now have
separate direct-click evidence; PBIR validation alone would not prove this.
Publishing to Fabric and Azure DevOps pipeline execution were not part of
this report validation.

## Build, CI and report validation

- Python regression: **103 passed** on the latest local five-page remediation.
- Ruff lint: **PASS**.
- PBIR structural validation: **0 errors, 0 warnings** (`powerbi-report-author validate powerbi/FlightOperations.pbip --no-schema`).
- GitHub Actions — [Data quality CI run 45022192579](https://github.com/thaquan/Flight_Operations_Intelligence/actions/runs/45022192579): **completed successfully** for commit `aa4037c`.
- Azure DevOps: Git synchronization was verified previously. The pipelines API is not publicly accessible without sign-in; no tracked Azure Pipelines YAML definition was found. **Pipeline execution is not verified**.
- No refresh, publish, Git commit or push was performed as part of this acceptance pass.

## Reproduction

Run PostgreSQL from the project root, then validate the local source:

```powershell
docker compose up -d postgres
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\ruff.exe check --select E4,E7,E9,F,I src/phase5 tests/test_phase5_*.py
powerbi-report-author validate powerbi/FlightOperations.pbip --no-schema
```

A representative network reconciliation compares this Gold query:

```sql
SELECT calendar_year,
       SUM(scheduled_flights) AS scheduled,
       SUM(eligible_arrivals) AS eligible,
       SUM(late_arrivals_15) AS late
FROM gold.mart_network_monthly
GROUP BY calendar_year
ORDER BY calendar_year;
```

With these DAX measures grouped by `dim_month[calendar_year]`:

```dax
EVALUATE
SUMMARIZECOLUMNS(
    dim_month[calendar_year],
    "Scheduled", [Scheduled Flights],
    "Eligible", [Eligible Arrivals],
    "Late", [Late Arrivals 15+]
)
```

The Import model was compared in its already-refreshed state; a new Power BI refresh was not necessary because the imported totals matched Gold. Keep local credentials and Desktop `.pbi` caches outside version control.