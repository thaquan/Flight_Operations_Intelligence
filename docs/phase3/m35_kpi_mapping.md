# M3.5 - KPI and dimension mapping

The shared `dbt/macros/flight_kpi_metrics.sql` macro is used without
alteration by the four volume/performance marts. Source contract:
[Phase 1 KPI definitions](../phase1/2024_2025/kpi_definitions.md).

| Published column | Calculation from fact at each mart's group | Important rule |
| --- | --- | --- |
| `scheduled_flights` | `SUM(scheduled_flight_count)` | Every source record |
| `completed_flights` | `SUM(completed_flight_count)` | Completed only |
| `cancelled_flights` | `SUM(cancelled_flight_count)` | Keep cancelled flights |
| `diverted_flights` | `SUM(diverted_flight_count)` | Cancelled = 0 and diverted = 1 |
| `eligible_arrivals` | `SUM(eligible_arrival_count)` | Completed with known `ArrDel15` |
| `late_arrivals_15` | `SUM(arrival_delayed_15_count)` | Eligible and `ArrDel15 = 1` |
| `on_time_arrivals` | `SUM(arrival_on_time_count)` | Eligible and `ArrDel15 = 0` |
| `cancellation_rate_pct` | `100 * cancelled / scheduled` | Scheduled denominator |
| `diversion_rate_pct` | `100 * diverted / scheduled` | Scheduled denominator |
| `arrival_delay_15_rate_pct` | `100 * late / eligible` | **Not** scheduled denominator |
| `arrival_on_time_rate_pct` | `100 * on_time / eligible` | Only valid eligible arrivals |
| `signed_arrival_delay_observations` | `COUNT(arr_delay)` among completed | Non-NULL readings |
| `avg_signed_arrival_delay_minutes` | `AVG(arr_delay)` among completed | Early arrival is negative |
| `avg_positive_arrival_delay_minutes` | `AVG(GREATEST(arr_delay,0))` among completed | Early arrival contributes 0; NULL excluded |

All percentages and averages are rounded to two decimal places for
presentation. For multi-month or multi-carrier rollups, **recalculate
percentage from summed additive numerator and denominator**. Do not average
the stored percentage fields. For signed-delay means across pre-aggregated
groups, use weighted observations or the flight-level fact; never average
group means without their original valid counts.

## Other mart-specific fields

- `mart_airport_daily`: `airport_role` is `origin` or `destination`;
  `avg_taxi_out_minutes` is populated only for origin rows;
  `avg_taxi_in_minutes` only for destination rows. They are unweighted daily
  means, so recompute from raw valid records for longer windows if precise
  volume-weighted averages are required.
- `mart_delay_causes`: `cause_type` is one of `carrier`, `weather`, `nas`,
  `security`, or `late_aircraft`. `reported_observations` counts source
  records where that cause field is **not NULL**, including **zero minutes**.
  `positive_delay_observations` counts records with **strictly positive**
  minutes. `reported_delay_minutes` is the cause minute sum, and
  `avg_reported_cause_minutes` is the mean over non-NULL records.
  `attributed_delay_share_pct` is the share of summed cause minutes
  *within the same airline and month*. A zero total yields NULL, not 0%.
  These categories come from BTS flight reporting, **not** NOAA observations;
  they do not establish weather causality.
- Dimensions: `airline_sk -> dim_airline`,
  `airport_sk / origin_airport_sk / dest_airport_sk -> dim_airport`,
  `flight_date_key -> dim_date`; keep surrogate keys during joins to avoid
  multiplying aggregates.

The cause mart is not additive across cause categories when counting
flights: one flight may have values in multiple cause columns. Its
**cause-minute totals** are additive, but `reported_observations` and
`positive_delay_observations` are category-specific observation counts.
