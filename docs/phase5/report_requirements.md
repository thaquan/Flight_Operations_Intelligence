# Phase 5 / M5.1 - Report requirements

## Objective and audience

Flight Operations Intelligence is a **historical operational performance**
report for U.S. domestic flights reported to the Bureau of Transportation
Statistics (BTS) during **January 2024 through December 2025**. It serves:

- Airline operations analysts comparing punctuality and reliability.
- Airport and network analysts locating high-volume, high-delay segments.
- Hiring managers reviewing a reproducible Data Engineering + BI portfolio.

This is a **batch historical** dataset. Do not label the report real-time,
predictive, financially oriented, or weather-observation-based.

## Decisions the report must support

| Business question | Report page | Primary evidence |
| --- | --- | --- |
| Is punctuality improving across reporting years and months? | Executive Overview; Seasonal Trends | Delay >=15m rate, on-time rate, month trend |
| Which reporting carriers perform differently at similar volumes? | Airline Performance | Flights, delay rate, cancel/divert rates |
| Which origin airports and directed routes need attention? | Airports & Routes | Airport role-separated and directed-route marts |
| Which BTS-reported categories account for delay minutes? | Delay Causes | Reported delay minutes and within-selection shares |
| Are seasonal patterns stable across years? | Seasonal Trends | Monthly rates, 2024 versus 2025 comparison |

## Pages and interaction contract

1. **Executive Overview** - five headline KPIs, month/year rate trend,
   high-level operational totals, methodology note.
2. **Airline Performance** - reporting-airline ranking with a minimum
   scheduled-flight threshold and optional airline detail drill-through.
3. **Airports & Routes** - explicit Origin/Destination airport role switch,
   two separate airport selectors for directional routes, route ranking.
4. **Delay Causes** - BTS-reported category minute totals, share of all
   selected *reported cause minutes*, airline/month slicers.
5. **Seasonal Trends** - 24-month monthly series, year-over-year comparison
   by calendar month and volume overlay where practical.

An optional **Methodology & Quality** page should show denominators, source
coverage, known source exceptions, and model refresh details.

Common UX:

- A stable 16:9 canvas; dark left navigation and light analytical surface.
- Period selection defaults to all 24 months; show the active period visibly.
- Explicit visual subtitles state the metric and denominator.
- Tooltip displays numerator, denominator, percent, and filter context.
- Clear filters action restores the default selection.
- No hidden page-to-page context carryover that changes a KPI silently.
- Top-N rankings must expose their minimum-volume threshold.
- Metric color is semantic: teal on-time, amber delay, red cancellation,
  slate-blue diversion. Accessibility never depends on color alone.

## Data contract and page-specific filters

All analysis uses existing PostgreSQL `gold` models. These are **separate
grains**, not a single joined fact table.

| Source | Grain | Pages | Constraints |
| --- | --- | --- | --- |
| `gold.mart_network_monthly` | One source month | Executive; Seasonal | Network totals and rates only; no airline slicer |
| `gold.mart_airline_monthly` | Airline x source month | Airline | Airline filter can be applied; ignore network table |
| `gold.mart_airport_daily` | Airport x role x day | Airports | Filter to exactly one `airport_role` for any flight-volume KPI |
| `gold.mart_route_monthly` | Directed origin x destination x month | Routes | No airline field; airline slicer must not claim to filter it |
| `gold.mart_delay_causes` | Airline x month x BTS cause | Delay Causes | Cause observations are not a unique-flight count |
| `gold.dim_airline`, `gold.dim_airport`, `gold.dim_date` | Dimensions | Related pages | Use surrogate keys and role-playing airport/date handling |

For all monthly marts, `source_month` is a real date representing the
reporting month. Define a dedicated month dimension or consistent month-start
key for report-wide time filters; `dim_date` already serves airport daily
dates. Do not make ambiguous many-to-many relationships between marts.

## Out of scope for M5.1

M5.1 delivers design, business logic and acceptance criteria, **not** a live
Power BI report. M5.2 will connect to PostgreSQL and establish a semantic
model. DAX measure implementation follows in M5.3; finished pages follow
in M5.4 and M5.5.

## Acceptance criteria for the finished report

1. Period defaults to Jan 2024-Dec 2025, with correct 24-month coverage.
2. Global totals reconcile to `docs/phase4/quality_report.json`.
3. Numerators and denominators survive year/airline/airport/route filtering
   and are never combined across incompatible grains.
4. Clear visual labels distinguish delay >=15m, cancellation, diversion,
   and BTS-reported delay-cause minutes.
5. All five required pages share the approved theme, page navigation,
   legible text, and consistent date formatting.
6. Quality panel states **6 PASS, 2 REVIEW, 0 FAIL** in the recorded Phase 4
   report, with the review exceptions explained, not hidden.
7. Every screenshot or demo specifies the dataset period and refresh state;
   no claim of live production refresh without proof.
