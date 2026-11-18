# M3.5 - Gold analytics marts

## Purpose and lineage

Five physical PostgreSQL tables in schema `gold` provide BI-ready aggregates
over the complete BTS 2024-2025 flight population. Every mart reads
`gold.fct_flights` through dbt `ref()`; no source rows are discarded by a
top-N, flight-status, or airline filter. The source-of-truth flight grain
remains `gold.fct_flights` (14,080,680 physical records). The five marts are
rebuildable analytical projections, not replacements for the fact.

| Mart | Grain / composite key | Rows verified | BI use |
| --- | --- | ---: | --- |
| `mart_network_monthly` | `source_month` | 24 | Trend, YoY, executive KPIs |
| `mart_airline_monthly` | `airline_sk, source_month` | 348 | Carrier comparisons |
| `mart_airport_daily` | `airport_sk, airport_role, flight_date` | 481,262 | Origin vs destination; daily and seasonal views |
| `mart_route_monthly` | `origin_airport_sk, dest_airport_sk, source_month` | 139,287 | Directed route comparisons |
| `mart_delay_causes` | `airline_sk, source_month, cause_type` | 1,740 | BTS-reported delay attribution |

The airline and airport surrogate keys reference the M3.4 dimensions.
Airport role is a **mandatory grouping/filter key** in the airport mart.
Each original flight is represented **once for origin and once for
destination**; adding both roles doubles a network count. Directed routes
`A -> B` and `B -> A` remain distinct. Every calendar date is a flight's
reported local date, not a UTC timestamp.

## Materialization and indexes

The models are dbt `table` materializations configured under
`dbt_project.yml -> marts -> analytics`. dbt creates a composite unique
index for each mart's physical grain. The daily airport mart also indexes
`flight_date, airport_role`; the route mart also indexes
`source_month, origin_airport_sk`. Source `NULL` values have not been
converted into invented measurements.

## Rebuild and validate

From the repository root, with Docker Desktop running and the private
`.env` already bootstrapped:

```powershell
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli parse
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli run --select path:models/marts/analytics --threads 2
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli test --select path:models/marts/analytics tag:m35 --threads 2
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

This scoped dbt run reuses the already populated M3.4 fact and dimensions;
it **does not** re-run Silver ingestion or rebuild the 14-million-row fact.
All five mart tables are full-refresh table materializations, not incremental.
On any model or schema change, rerun the models, then the tests. A subsequent
Phase 7 orchestration phase can schedule refreshes and enforce upstream
dependencies.

### Example: top origin airports by flight volume

```sql
select a.airport_code, sum(m.scheduled_flights) as scheduled_flights
from gold.mart_airport_daily m
join gold.dim_airport a on a.airport_sk = m.airport_sk
where m.airport_role = 'origin'
group by a.airport_code
order by scheduled_flights desc
limit 20;
```

### Example: route performance in 2025

```sql
select o.airport_code as origin, d.airport_code as destination,
       sum(r.scheduled_flights) as scheduled,
       round(100.0 * sum(r.late_arrivals_15)
             / nullif(sum(r.eligible_arrivals), 0), 2) as delay_rate_pct
from gold.mart_route_monthly r
join gold.dim_airport o on o.airport_sk = r.origin_airport_sk
join gold.dim_airport d on d.airport_sk = r.dest_airport_sk
where r.source_month >= date '2025-01-01'
  and r.source_month < date '2026-01-01'
group by o.airport_code, d.airport_code
having sum(r.eligible_arrivals) >= 100
order by delay_rate_pct desc;
```

The `having` threshold is a **reporting choice** for ranking stability; it
does not reduce the stored dataset.

Related documents: [KPI mapping](m35_kpi_mapping.md),
[reconciliation](m35_reconciliation.md),
[measured performance](m35_performance.md), and
[verification](m35_validation.md).
