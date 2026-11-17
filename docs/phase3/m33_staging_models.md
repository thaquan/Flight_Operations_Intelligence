# M3.3: dbt Source and Staging Models

## Purpose and boundary

M3.3 creates the dbt SQL transformation layer on top of the verified M3.2
`silver.flights` PostgreSQL table. It provides a stable, documented input
for the next dimensional-modeling milestone. It does not create Gold facts,
dimensions or report-level KPIs yet.

The grain remains **one original BTS source record**, identified by
`(source_month, source_row_number)`. There are **no WHERE filters, joins,
deduplication or dropped cancellation/diversion records** in either staging
model. Rebuilding a dbt view does not copy the 14-million-row source table.

## Models and dependencies

| dbt resource | PostgreSQL relation | Purpose |
| --- | --- | --- |
| `source('silver', 'flights')` | `silver.flights` | Versioned source declaration and required-field tests |
| `ref('stg_flights')` | `staging.stg_flights` | Explicit Silver columns plus normalized carrier/airport codes |
| `ref('stg_flight_outcomes')` | `staging.stg_flight_outcomes` | Flight status and additive KPI numerators/denominators |

Models are PostgreSQL **views**, so downstream queries observe the latest
committed Silver data. In M3.4, fact and dimension models can choose their
own materialization strategy and business keys.

### Standardization rules

- All typed Silver fields and source lineage columns are passed through.
- `airline_code`, `origin_airport_code` and
  `destination_airport_code` are trimmed/uppercased copies; original BTS
  code fields remain untouched, and blank codes become NULL.
- `CRSDepTime`, `DepTime`, `CRSArrTime` and `ArrTime` remain HHMM
  text. Values such as `0005` and `2400` are **not** interpreted as
  time zones, UTC timestamps or a different flight date.
- No missing delay values are imputed; no natural-key deduplication occurs.

### Flight outcome and arrival KPI contract

| Output | Rule per record |
| --- | --- |
| `flight_status` | `cancelled=1` -> cancelled; otherwise `cancelled=0,diverted=1` -> diverted; `0,0` -> completed; any other combination -> unknown |
| `scheduled_flight_count` | Always 1, including cancelled and diverted records |
| `completed_flight_count` | 1 when status is completed, otherwise 0 |
| `cancelled_flight_count` | 1 when status is cancelled, otherwise 0 |
| `diverted_flight_count` | 1 when status is diverted, otherwise 0 |
| `eligible_arrival_count` | 1 only for completed flights with `ArrDel15 IN (0,1)` |
| `arrival_delayed_15_count` | 1 only for eligible flights with `ArrDel15=1` |
| `arrival_on_time_count` | 1 only for eligible flights with `ArrDel15=0` |

Calculate rates downstream using **SUM(numerator) / NULLIF(SUM(denominator),0)**,
not averages of row or monthly rates. The known September 2025 completed
record with NULL `ArrDel15` is retained but excluded from the eligible
arrival denominator. Departure-delay eligibility and actual timestamp/UTC
construction are deliberately deferred until their business rules are
confirmed.

## Running locally

Requires completed M3.1/M3.2, Docker Desktop and the project virtualenv.
From `D:\Flight_Operations_Intelligence`:

```powershell
docker compose ps
.\.venv\Scripts\python.exe -m src.phase3.check_database
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli debug
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli ls --resource-type model
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli build
.\.venv\Scripts\python.exe -m pytest -q
```

`dbt build` creates/replaces two views and runs source, model and singular
data tests. The tests verify required non-NULL lineage fields, accepted
status values, **monthly source-to-staging row counts**, and arrival
numerator/denominator accounting. Reruns rebuild views without modifying
`silver.flights`.

For a read-only annual KPI sanity check:

```sql
SELECT
    flight_year,
    SUM(scheduled_flight_count) AS scheduled,
    SUM(eligible_arrival_count) AS eligible_arrivals,
    SUM(arrival_delayed_15_count) AS late_arrivals,
    ROUND(
        100.0 * SUM(arrival_delayed_15_count)
        / NULLIF(SUM(eligible_arrival_count), 0), 2
    ) AS late_arrival_pct
FROM staging.stg_flight_outcomes
GROUP BY flight_year
ORDER BY flight_year;
```

Compare those counts and rates to the official full-population Phase 1
`kpi_definitions.md` and `data_quality_assessment.md`, without using
small, non-representative GitHub samples.

## Deferred to later milestones

- M3.4: intermediate models, dimensions, fact grain and surrogate keys.
- Later Phase 3: Gold KPI marts, time-series aggregations, and end-to-end
  source-to-mart reconciliation.
- Phase 4: CI and broader warehouse quality gates.
- Phase 6: weather observations and timezone-aware point-in-time joins.
