# M3.4: PostgreSQL Star Schema with dbt

## Scope and grain

M3.4 builds a **physical Star Schema** from the verified BTS 2024-2025
staging population. Grain: exactly one official source observation per
fact row. No joins to dimensions or source filters are used to create
`fct_flights`, avoiding silent row multiplication or loss of cancelled
and diverted observations.

See the [Star Schema ERD](m34_erd.md) for the four relationships.

| PostgreSQL relation | Grain | Materialization |
| --- | --- | --- |
| `gold.dim_airline` | One DOT airline ID, plus Unknown | dbt table |
| `gold.dim_airport` | One BTS airport ID, plus Unknown | dbt table |
| `gold.dim_date` | One calendar date from minimum to maximum source date | dbt table |
| `gold.fct_flights` | One BTS source observation | dbt table |

The local project's `generate_schema_name` macro maps explicitly
configured `gold` to PostgreSQL `gold`, while existing staging views
remain in `staging`. Environments sharing one database would need
separate targets/databases before parallel deployments.

## Key design

| Key | Rule | Why |
| --- | --- | --- |
| `flight_sk` | `YYYYMM(source_month) * 10,000,000 + source_row_number` (BIGINT) | Deterministic physical source identity, independent of the non-unique candidate flight business key |
| `airline_sk` | `1,000,000 + DOT airline ID`; NULL maps to -1 | Stable integer lookup without rank changes across reruns |
| `airport_sk` | `1,000,000 + BTS AirportID`; NULL maps to -1 | Stable key shared by origin and destination roles |
| `flight_date_key` | `YYYYMMDD` integer | Standard calendar key, joins local flight date to `dim_date` |

The monthly source-row slot allows positions 1 through 9,999,999.
The current source maximum is 634,613. dbt tests detect future rows
outside the supported range before a key collision can be accepted.

`dim_airline` and `dim_airport` each contain one Unknown row
(`sk=-1`) for future missing business IDs, even though the current
24-month population has **zero** missing carrier/airport IDs.

## Attribute handling

- Airport identifiers are collected from both origin and destination
  observations. `dim_airport` is **role-playing**, with two foreign
  keys in the fact.
- If an ID has multiple observed code/city/state tuples, the most
  frequent tuple is chosen; ties use latest observation date, then
  alphabetical order. This deterministic rule yields one row per ID
  without inventing attributes.
- This is a **current representative-attribute dimension**, not SCD
  Type 2. Historical attribute changes and external official carrier/
  airport reference lookups are deferred until reliable source
  mappings are available.
- No timezone is inferred from airport city/state. Scheduled and
  actual HHMM clocks remain source text; UTC/DST is handled in Phase 6.
- Arrival KPI counters are passed through from M3.3. Ratio denominators
  must be summed from eligible arrivals, not from scheduled flights.

## Materialization and costs

All four Gold models are PostgreSQL tables. Fact is a full-source
snapshot rebuilt by dbt `table` materialization; it is **not yet an
incremental merge**. This avoids stale rows when a monthly source is
reprocessed with a different row count. A later optimization phase can
design month-atomic replacement using source audits and measured
query performance.

The fact has a unique index on `flight_sk` and supporting indexes on
`flight_date_key` and `origin_airport_sk`. The dimensions have unique
indexes on their warehouse keys. Raw ZIPs, Bronze files and local
database storage remain ignored by Git.

## Repeatable local commands

Start Docker Desktop. From the repository root:

```powershell
.\.venv\Scripts\python.exe -m src.phase3.check_database
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli parse
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli run --select path:models/marts
.\.venv\Scripts\python.exe -m src.phase3.dbt_cli test --select path:models/marts
.\.venv\Scripts\python.exe -m pytest -q
```

dbt tests cover:

1. Dimension key uniqueness and non-NULL keys.
2. Distinct source observations in the fact.
3. All four fact-to-dimension relationships (including both airport roles).
4. Monthly Silver-to-Fact row counts and annual KPI sums.
5. Flight source-row position range and Unknown dimension members.

The full Phase 3 validation record is in [M3.4 Validation](m34_validation.md).

## Next work

M3.5 builds Gold aggregate marts for airline/month, airport/day,
directed route/month and reported delay causes using these tables.
They must recompute rates from **summed** numerators and denominators,
and verify source-to-mart business totals before Power BI imports.
