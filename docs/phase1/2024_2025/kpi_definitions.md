# KPI Dictionary and Denominator Rules

All definitions are applied after filtering by the relevant date, carrier, airport or route. Source rows are preserved; no flight outcome is removed during ingestion.

| KPI | Numerator | Denominator | Interpretation |
| --- | --- | --- | --- |
| Scheduled flights | Count of all source flight records | Not applicable | Volume of BTS-reported scheduled flights. |
| Completed flights | `Cancelled = 0 AND Diverted = 0` | Not applicable | Flights eligible for normal arrival outcome analysis. |
| Cancellation rate | `Cancelled = 1` | All scheduled flights | A cancelled flight stays in the dataset. |
| Diversion rate | `Cancelled = 0 AND Diverted = 1` | All scheduled flights | Diversions are reported separately from cancellations. |
| Arrival 15+ minute delay rate | Completed flights with `ArrDel15 = 1` | Completed flights with a valid non-NULL `ArrDel15` | Late threshold is **at least** 15 minutes. |
| Arrival on-time rate | Completed flights with `ArrDel15 = 0` | Same eligible-arrival population | "On time" includes arrivals earlier than scheduled and 0–14 minutes late. |
| Departure 15+ minute delay rate | Eligible flights with `DepDel15 = 1` | Flights with valid `DepDel15`, excluding cancellations | Phase 5 must explicitly confirm the applicable diverted-flight rule. |
| Average signed arrival delay | Sum of non-NULL signed `ArrDelay` | Number of applicable non-NULL `ArrDelay` rows | Negative minutes represent early arrivals. |
| Average positive arrival delay | Sum of `max(ArrDelay, 0)` for eligible records | Count of eligible records with valid `ArrDelay` | A different metric from signed mean delay. |
| Year-over-year flight volume change | 2025 scheduled flights minus 2024 scheduled flights | 2024 scheduled flights | Percentage change; full years only. |
| Year-over-year punctuality change | 2025 arrival on-time rate minus 2024 rate | Not applicable | Expressed in **percentage points**, not percent growth. |

## Important aggregation rules

- Recompute ratios from the **sum of numerators and denominators**, never by averaging monthly percentages.
- The airport-specific departure view uses the origin airport. The arrival view must explicitly use the destination airport; do not mix the two without labeling.
- A route is a **directed** pair `Origin -> Dest`; `LAX -> JFK` and `JFK -> LAX` are different routes.
- Delay-cause fields may be populated only for qualifying delayed flights. A missing cause is not automatically zero minutes.
- When comparing reliability between low- and high-volume routes, show flight counts and use a minimum-volume filter.
- Raw BTS `WeatherDelay` is an **attributed delay category**, not a measurement from NOAA instruments.
- A `NULL` `ArrDelay` on a cancelled or diverted flight is not evidence of an on-time arrival.

## Phase 1 implemented metrics

The Phase 1 profiles calculate scheduled, completed, cancelled and diverted counts; eligible arrival counts; 15+ minute late counts and on-time counts; and weighted yearly rates. Exact full-population segment rates are deferred to the warehouse marts in Phase 3.
