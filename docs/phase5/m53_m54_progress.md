# Phase 5 / M5.3-M5.4 - Canonical Report (2026-11-21)

## One project

The **only Power BI entry point** is:
D:/Flight_Operations_Intelligence/powerbi/FlightOperations.pbip

The report lives in powerbi/FlightOperations.Report, and the shared semantic
model in powerbi/FlightOperations.SemanticModel.

On 2026-11-21, both original and Atlas Desktop windows were verified saved.
The five-page Atlas report definition (theme, layout and 60 initial visual objects)
was merged into the **original** FlightOperations.Report, retaining its
PBIP manifest, report platform, semantic model binding, and Import model.
The duplicate Atlas PBIP and Atlas Report folder were removed after its
Desktop window was closed.

A recoverable ZIP archive of both pre-merge reports plus the semantic model
is stored outside the repository:
D:/PowerBI_Authoring_Tools/backups/FlightOperations_before_merge_20261121-220920.zip

## Verified data and semantic model

- Both saved Desktop models were queried using Microsoft Modeling MCP 1.0.1:
  each returned 24 monthly rows and 14,080,680 scheduled flights.
- The verified Gold baseline also includes 13,844,731 eligible arrivals,
  2,984,604 arrivals delayed 15+ minutes, 10,860,127 on-time arrivals,
  199,191 cancellations and 36,757 diversions.
- The 43 DAX measures cover network (11), airlines (8), role-safe airports
  (14), directed routes (7) and BTS delay causes (3). Measure snippets
  exported from Modeling MCP are retained under src/phase5/measure_snippets.
- The semantic model has 11 business tables and 11 single-direction star
  relationships. Desktop may omit the explicit oneDirection property
  from saved TMDL because it is the default.
- Source model and Desktop cache are separate. Unit tests generate a new
  sample model in a temporary directory, not over the Desktop-saved TMDL.

## Report content

Five pages, 1280 x 720, **90 visual objects total** (18 per page):
Executive Overview; Airline Performance; Airports & Routes;
Delay Causes; Seasonal Trends.

Theme: powerbi/themes/FlightNetworkRiskIntel.json, registered in the
canonical Report resources. Geographic route maps have not been added
because geocodes have not been validated; the page uses a directed
origin-to-destination flat table instead.

The canonical report generator is src/phase5/build_atlas_report.py.
The initial bootstrap src/phase5/build_report_shell.py refuses to
overwrite a developed report. There is no second PBIP to maintain.

## Rendered-output QA and interaction verification (2026-11-21)

- The original Desktop PBIP was confirmed as the only project, and the
  semantic model remained intact with 11 tables and 43 DAX measures.
- Microsoft PBIR validate --no-schema returned **0 errors, 0 warnings**.
  The Desktop renderer loaded all five pages; all KPI cards and charts
  displayed live Import data after model refresh.
- The Airports & Routes pivotTable originally showed a data-fetch error.
  DAX queries over origin/destination airport fields were verified correct.
  Its two airport_code projections had conflicting nativeQueryRef names
  and a drill-oriented configuration. The visual was replaced with a
  flat tableEx using distinct aliases and four columns: origin airport,
  destination airport, scheduled flights and arrival delay 15+ rate.
  Widening the table to 552 pixels removed horizontal truncation.
- The fixed route table screenshot showed LGA to ORD = 22,516 flights at
  25.02% arrival delay, with a network total of **14,080,680 flights**
  and **21.56%** arrival delay. No data-fetch error was visible.
- A synced Dropdown YEAR slicer bound to dim_month.calendar_year was
  added to each of the five pages with sync group FlightOperationsYear.
  Desktop screenshots confirmed all five dropdowns render correctly.
- In the live Desktop UI, selecting **2024** filtered Executive Overview
  to 12 months and filtered Airports & Routes, including the route table.
  Both showed **7,079,061 scheduled flights** and **20.82%** delayed
  arrivals. Deselecting 2024 restored All; the final Airports & Routes
  screenshot had the same SHA256 as its original All-state capture.
- The final report was saved using the Power BI Desktop UI. Bridge readback
  verified hasUnsavedChanges=false; source readback showed 65 visuals before final navigation authoring and
  five synchronized slicers.
- The targeted repair workflow lives in src/phase5/repair_visuals.py;
  both model and report bootstrap generators protect Desktop-saved files.
  Do not regenerate the full PBIR over the live report.
- Latest final regression (2026-11-22): **91/91 Python tests PASS**, Ruff PASS, PBIR 0 errors/0 warnings.


## Dashboard completion and screenshot acceptance (2026-11-22)

- The sole canonical Power BI Desktop file remains powerbi/FlightOperations.pbip.
  It was saved in Desktop with hasUnsavedChanges=false.
- Added five native PageNavigation action buttons to each of the five pages
  (25 buttons total), with clear active-page teal highlighting and
  configured target page ids. Each link is recognized as a Hyperlink by
  Windows accessibility metadata. Automated Ctrl-click activation in
  Desktop Edit mode could not be completed because Windows blocked
  bringing the host window to the foreground; click-action QA remains
  a minor manual acceptance item (Ctrl+click in Desktop edit mode).
- Corrected the Seasonal Trends main chart: a month-of-year categorical
  axis 1 through 12, with a two-series legend for calendar years 2024 and
  2025 and ratio-based delay-rate Y values. This is distinct from the
  Executive Overview sequential 24-month trend.
- Changed the directed route table headers to Origin, Destination,
  Flights and Delay 15+ %. Other category captions use Month, Year,
  Airline, Origin airport and Delay cause.
- Fresh Desktop screenshots were reviewed for all five pages after
  report reload. All KPIs and graphs rendered live data; no broken
  visual appeared. Re-captured Seasonal Trends after the categorical-axis
  refinement, confirming all 12 months and two visible year series.
- Total visual objects: **90** (18 per page), including five synchronized
  YEAR dropdowns and 25 page-navigation buttons.
- Existing Year filter QA remains valid: selecting 2024 in Executive
  showed 7,079,061 scheduled flights and 20.82% late-arrival rate,
  synchronized with Airports & Routes, then reset back to All.
- Final 2026-11-22 acceptance: **91/91 Python tests**, Ruff PASS,
  PBIR validation (--no-schema) 0 errors/0 warnings. Reapplying the
  idempotent finishing script would change zero files.
- A recoverable snapshot before these UX changes is stored at
  D:/PowerBI_Authoring_Tools/backups/FlightOperations_before_dashboard_finish_20261122-111107.zip.
- No Git commit, push to GitHub or Fabric publication has been performed.


## Flight Deck design review revision (2026-11-22, afternoon)

The user's design review identified four issues: Overview and Seasonal Trends
looked similar; chart selections and palette were generic; page navigation
lacked a Home control; YEAR interrupted the navy header with a white tile.

- **Distinct stories:** Overview now shows a 24-month late-arrival trend
  with year-level cancellation versus diversion rates. Seasonal Trends
  overlays both 2024/2025 late-arrival rates and 2024/2025 monthly traffic
  on two consistent 12-month categorical charts.
- **Chart roles:** Cause minutes use sorted bars plus a composition donut.
  Airline delay rates and airline volumes are separately ranked.
  Airport analysis ranks busy origin airports by scheduled flights,
  with delayed-arrival rate as a tooltip for proper traffic context;
  the old highest-rate-only chart overemphasized small-count airports.
  The route table remains directed and sorted by volume.
- **No duplicated airport KPI:** The four corridor metrics now represent
  route scheduled flights, late-arrival rate, cancelled flights and
  diverted flights rather than repeating the same network total for
  origin and destination roles.
- **Visual styling:** Native navy header (#081B30), YEAR / PERIOD control
  in dark navy (#102B43), electric-blue volume (#1665ED), coral risk
  (#F26852) and brighter cyan navigation. KPI labels and values were
  explicitly corrected to dark ink on light card tiles after screenshots
  identified insufficient contrast.
- **Navigation:** Each page has a native Home icon (Segoe MDL2 Assets)
  linked to Executive Overview and five PageNavigation buttons with
  correct page ids. Each link includes tooltip instructions to use
  Ctrl+click in Power BI Desktop Edit mode; regular clicks work in
  Reading mode. The host exposed the actions as UI hyperlinks; an
  end-to-end click test could not take foreground focus and was not
  claimed as completed.
- **Verification:** Five Desktop screenshots reviewed; follow-up
  screenshots confirmed the icon fully visible, readable KPI figures,
  dark YEAR control, airports by actual high-volume hubs, a cause
  donut and two distinct seasonal charts. No visual data-fetch errors
  were seen. Power BI PBIR validation 0 errors / 0 warnings,
  Python regression 95/95 PASS, Ruff PASS.
- **Safety:** Use src/phase5/redesign_dashboard.py for any scoped repeat
  design edits. Dry run 0 pending changes after application. The sole
  Power BI entrypoint remains powerbi/FlightOperations.pbip.
  Recovery backup outside the repo:
  D:/PowerBI_Authoring_Tools/backups/FlightOperations_before_ux_rework_20261122-150333.zip.
  No Git commit/push, Fabric publication or fabricated geographic data.


## Remaining work

- Airport coordinates and licensing have not been validated; therefore
  a true geospatial route map is not included.
- No Fabric publication or Git commit/push has been performed.
- Further visual polish, UX accessibility review, mobile layout and
  optional airport geocoding can be handled as future enhancements.

## Validate locally

Run from the repository root:
    powerbi-report-author validate powerbi/FlightOperations.pbip --no-schema
    .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider

Do not commit .pbi caches or PostgreSQL credentials.
