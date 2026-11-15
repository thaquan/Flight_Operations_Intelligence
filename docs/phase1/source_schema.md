# Phase 1 — Source schema and planned grain

## Raw source structure

The official January 2025 monthly ZIP contains:

- One CSV: `On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_2025_1.csv`.
- One source-provided `readme.html`.
- **110 CSV header positions**: 109 named source fields and **one final blank header**. The profiler records this irregularity. The Bronze loader must drop the empty header *after* preserving the original ZIP unchanged.
- Fields for dates and time, carrier IDs, airport IDs, flight status, departure/arrival delay, cancellation reasons, distance, causal delay categories and diversion detail.
- Numeric and 0/1 indicator values appear as textual decimals, e.g. `-3.00`, `0.00`, `1.00`.

The canonical source file is stored under `data/raw/bts/2025/` and **not committed to Git**. Every ingest in Phase 2 will record URL, ZIP SHA-256, byte count, reporting year/month, CSV row count and ingest status in a manifest.

## Flight grain / cấp độ bản ghi

Target grain: **one row for one BTS-reported scheduled non-stop domestic flight**. The source contains reporting-carrier records; do not join marketing and reporting carrier datasets as though they represent distinct flights.

The Phase 1 candidate business key is:

`FlightDate + DOT_ID_Reporting_Airline + Flight_Number_Reporting_Airline + OriginAirportID + DestAirportID + CRSDepTime`

An extended candidate adds `CRSArrTime`. Both are empirically checked by the profiler; do **not** declare either a primary key until the collisions have been studied. Phase 2 should retain `source_file` and `source_row_number` even if another surrogate key is chosen.

## Planned normalized model (Phase 3)

| Model | Grain | Role |
| --- | --- | --- |
| `stg_bts_flights` | Raw flight record | Type normalization, transparent status mapping. |
| `dim_date` | Calendar date | Date, month, weekday and season. |
| `dim_airline` | DOT carrier ID / effective period if required | Carrier dimension. |
| `dim_airport` | DOT airport ID / effective period if required | Role-playing origin/destination dimension. |
| `fct_flights` | One scheduled non-stop reported flight | Fact table of flight statuses and delay measures. |
| `fct_airport_daily_performance` | Origin airport × day | Aggregated operational KPI mart. |
| `fct_weather_observations` | NOAA station × observation timestamp × report identifier | Phase 6, hourly/synoptic observations. |
| `mart_flight_weather` | One flight × zero or one selected weather report | Phase 6, point-in-time join without row multiplication. |

## Timestamp modeling risk

`FlightDate` is the flight date, and BTS scheduled departure/arrival clock fields are **local HHMM**, not ready-to-join UTC instants. Transformations must explicitly handle origin/destination IANA time zones, DST, calendar boundaries, `2400` and flights crossing midnight. The NOAA weather join will be evaluated against **scheduled departure UTC** to avoid using future weather measurements.

## Data flow for future phases

1. BTS ZIP → byte-for-byte raw storage + SHA-256 manifest.
2. CSV → Polars/PyArrow typed Bronze Parquet by flight year/month.
3. Bronze → PostgreSQL landing → dbt staging/intermediate → Gold marts.
4. Gold marts → Power BI Desktop Import semantic model.
5. NOAA GHCNh station/year Parquet → normalized weather observations → point-in-time weather mart.
6. Dagster monthly orchestration and GitHub Actions CI for code and small fixture tests.

Source documentation: [BTS monthly downloads](https://transtats.bts.gov/PREZIP/), [BTS fields](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ), [NOAA GHCNh](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly).
