# M3.5 - Measured Gold marts performance

Environment: Windows workstation, local Docker PostgreSQL 17, dbt Core
1.11.17 / dbt-postgres 1.11.0. The fact contains 14,080,680 records.
These are measurements from the local verification on 2026-11-18,
**not estimates, cloud SLAs or controlled benchmark averages**.

## Build duration

The command
`python -m src.phase3.dbt_cli run --select path:models/marts/analytics --threads 2`
completed all five table materializations:

| Run | Duration | Result |
| --- | ---: | --- |
| First creation | 156.51 s | PASS 5/5 |
| Second unchanged rebuild | 92.51 s | PASS 5/5 |
| Final indexed rebuild | 86.69 s | PASS 5/5 |

All table row counts remained unchanged. Warm data/OS caches, concurrent
database activity and index creation mean these runs are **not directly
comparable** measures of optimization. The full-refresh rebuild still scans
the flight fact.

## Physical storage

`pg_total_relation_size` after the final indexed rebuild:

| PostgreSQL relation | Size including indexes |
| --- | ---: |
| `gold.mart_network_monthly` | 32 kB |
| `gold.mart_airline_monthly` | 88 kB |
| `gold.mart_airport_daily` | 98 MB |
| `gold.mart_route_monthly` | 25 MB |
| `gold.mart_delay_causes` | 272 kB |

The five pre-aggregates together occupy roughly **123 MB**, substantially
less than the previously measured ~6,307 MB materialized flight fact. The
database also stores source/Silver and other tables separately.

## One illustrative BI query

Both versions rank the 20 highest-volume **origin airport keys** by scheduled
flights over all available dates. One uses the pre-aggregated directed route
mart, the other aggregates 14 million fact rows:

```sql
explain (analyze, buffers)
select origin_airport_sk, sum(scheduled_flights) as flights
from gold.mart_route_monthly
group by origin_airport_sk
order by flights desc limit 20;

explain (analyze, buffers)
select origin_airport_sk, sum(scheduled_flight_count) as flights
from gold.fct_flights
group by origin_airport_sk
order by flights desc limit 20;
```

| Query | One observed PostgreSQL execution |
| --- | ---: |
| Route mart | **81.539 ms** |
| Flight fact | **5,913.233 ms** |

The single-sample execution-time ratio is about **72.5x** in this
environment. It is **not** a universal speedup claim: caches, plans and
hardware affect the comparison. A repeatable benchmark should collect
multiple alternating warm/cold runs, inspect the full plans and compare
Power BI Import refresh time in Phase 5.

## Known tradeoffs and next optimization

- The fully rebuilt dbt tables are simple and reproducible; Phase 7 can
  explore partition-aware incremental models after validating equivalence.
- Composite unique indexes enforce physical mart grains; secondary daily
  and route indexes help planned date/airport slices but consume storage.
- The airport mart is 481,262 rows; date/key filtering and choosing one
  `airport_role` are recommended for BI queries.
- Do not compare a month-average of already rounded percentages against a
  weighted multi-month ratio.
