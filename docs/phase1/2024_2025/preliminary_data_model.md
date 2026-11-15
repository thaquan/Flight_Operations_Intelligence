# Preliminary Logical Data Model

This is the target design for Phase 3, not a claim that the PostgreSQL tables already exist.

## Grain and flight identity

**Fact grain:** one BTS-reported scheduled non-stop flight observation.

Candidate natural key:

```text
FlightDate + DOT_ID_Reporting_Airline
+ Flight_Number_Reporting_Airline + OriginAirportID + DestAirportID
+ CRSDepTime
```

The candidate is profiled for collisions across all 24 months. Do not enforce it as a database primary key until collision investigation is complete. A resilient physical model uses a `flight_sk` surrogate key and `source_file` + `source_row_number` for immutable lineage.

## Star-schema proposal

| Entity | Grain / key | Important attributes |
| --- | --- | --- |
| `fct_flight` | One flight source observation; `flight_sk` | Date, reporting airline, origin airport, destination airport FKs; status flags; delays; distance; source lineage. |
| `dim_date` | One calendar date; `date_key` | Full date, weekday, week, month, quarter, year, holiday/season indicators (if sourced). |
| `dim_airline` | One reporting DOT airline ID and effective period if needed; `airline_sk` | DOT carrier ID, reporting code, carrier name if mapped from official lookup. |
| `dim_airport` | One BTS airport ID and effective period if needed; `airport_sk` | Airport ID, code, city, state, region, timezone ID when validated. |
| `dim_cancellation_reason` | One BTS cancellation reason code | Reason label from official field dictionary. |

`dim_airport` is **role-playing**: the fact contains distinct `origin_airport_sk` and `dest_airport_sk` foreign keys.

## Derived marts

| Mart | Grain | Purpose |
| --- | --- | --- |
| `mart_airline_monthly` | Airline x calendar month | YoY reliability, volume and delay causes. |
| `mart_airport_daily` | Origin airport x service date | Airport trends with source-compatible denominators. |
| `mart_route_monthly` | Directed route x month | Volume-filtered delay and cancellation comparisons. |
| `mart_delay_causes` | Carrier/airport/month/attributed cause | Cause contribution with conditionally populated data. |
| `mart_flight_weather` (Phase 6) | One flight x selected weather observation | Point-in-time association; prevent one-to-many row multiplication. |

## Proposed transformations and storage

1. **Raw:** immutable BTS monthly ZIPs and checksums.
2. **Bronze:** typed, month-partitioned Parquet retaining complete source lineage. Proposed: `flight_year=YYYY/flight_month=MM`.
3. **Silver:** PostgreSQL canonical flight rows, normalized flags and timestamps, documented invalid-row handling.
4. **Gold:** dbt dimensions, flight fact and analytical marts.
5. **BI:** Power BI Desktop Import model using Gold tables.

The original calendar-local HHMM clocks must remain traceable. Converting to UTC requires origin/destination airport timezones, DST rules and flight-date rollover. Phase 6 weather joins will use the latest valid observation **at or before** the relevant flight timestamp within an explicit tolerance window.

## Model validation planned for Phase 3

- Reconcile row counts from each source month through Bronze, Silver and fact grain.
- Verify dimensional keys, including unknown members and SCD rules when an airport/carrier code changes.
- Reject one-to-many joins that inflate flight counts.
- Test uniqueness, non-null keys, accepted status values, relationships and temporal consistency.
- Compare calculated marts against independently computed source aggregates.
