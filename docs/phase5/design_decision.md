# Phase 5 - Approved dashboard design direction

**Decision on 2026-11-21:** Flight Network Atlas x Ops Risk Intel.
This replaces Aviation Command as the selected style for the five-page
Power BI report. The earlier M5.1 preview/theme remain in the repository
as historical design alternatives and are not deleted.

## Design language

- Light analytical canvas (#F3F7FB), dark navy navigation (#0B1F33),
  primary ink (#15283A), white cards and compact, high-contrast KPI panels.
- Teal (#0A98A4) denotes on-time/success; amber (#E7A545) delay of at
  least 15 minutes; rose (#D95F65) cancelled; slate blue (#677FB2)
  diverted; network blue (#3C7BB6) neutral traffic volumes.
- 16:9, 1280 x 720 page; 3-5 KPIs across the top, one major analytic
  story, and 2-3 supporting visuals. Never rely only on color.
- Source-controlled theme: powerbi/themes/FlightNetworkRiskIntel.json.
  The JSON configures defaults only; layouts and visual formats still
  need to be authored and verified in Power BI Desktop.

## Approved page direction

| Page | Main visual | Data source |
| --- | --- | --- |
| Executive Overview | Operational KPI strip plus 24-month delay trend | mart_network_monthly |
| Airline Performance | Airline rank and volume-versus-delay comparison | mart_airline_monthly |
| Airports & Routes | Airport geography and directed route rankings | mart_airport_daily, mart_route_monthly |
| Delay Causes | Cause-minute breakdown and shares | mart_delay_causes |
| Seasonal Trends | Year-on-year month overlay and volume comparison | mart_network_monthly |

## Accuracy guardrails

- Jan 2024-Dec 2025 BTS records only. This is a historical BI report,
  not real-time aircraft tracking.
- Airport markers and route arcs require a licensed, validated coordinate
  lookup joined consistently to the BTS airport keys. Until those
  coordinates are validated, use route/airport rank visuals rather than
  fabricated geography.
- A carrier slicer cannot legitimately filter the route mart, because
  that mart has no airline key.
- Use a single explicit origin/destination role when aggregating airport
  daily facts. Directed route A-to-B differs from B-to-A.
- Compute delay percentages by dividing summed late counts by summed
  eligible counts; cancellation/diversion use scheduled flights.
- BTS reported weather delay categories are not NOAA weather observations.

## Handoff

1. Complete a real Desktop import and refresh of existing PBIP/TMDL.
2. Add validated DAX measures and role-safe filters.
3. Use Report Authoring skill/PBIR tooling if accessible to build the five
   pages, beginning with Executive Overview and Airports & Routes.
4. Test navigation, map data coverage, chart labels and KPI reconciliation.
5. Capture screenshots before claiming a finished dashboard.

**Implementation status (2026-11-22):** The approved five-page
Power BI Desktop report is implemented locally in FlightOperations.pbip.
The revised Flight Deck edition has 95 visual objects, 43 DAX
measures, synchronized YEAR filters, native Home/PageNavigation and
distinct network-reliability versus calendar-seasonality stories. All five
pages were rendered and reviewed in Desktop. Geospatial route mapping
remains outside scope until a validated licensed airport-coordinate lookup
exists; the report uses a directed-route table in its place. No Fabric
publication or Git push has been made.
