# M3.3 Staging Validation Record

## Local execution on 2026-11-17

| Verification | Observed result | Status |
| --- | --- | --- |
| dbt Core / PostgreSQL adapter | 1.11.17 / 1.11.0 | Pass |
| dbt project parse | Parsed without errors | Pass |
| dbt Source | `silver.flights` | Pass |
| dbt models created | `staging.stg_flights`, `staging.stg_flight_outcomes` | Pass |
| dbt generic and singular data tests | 9 passed | Pass |
| Complete `dbt build` | PASS=11, WARN=0, ERROR=0, SKIP=0 | Pass |
| dbt build wall time | 119 seconds (two concurrent threads) | Measured |
| Monthly Silver-to-staging row reconciliation | Every source month matched | Pass |
| Arrival status and eligibility logic | Singular test found no violations | Pass |
| Python regression suite | 48 passed | Pass |

The local database retains **24 source months and 14,080,680 flight
observations**. Both staging models are views over the complete Silver
population; no physical flight rows are copied into the staging schema.
The monthly row-count test runs against live PostgreSQL relations, not
the stored M3.2 reconciliation JSON.

## Independently queried annual KPI sanity check

The following values were queried from `staging.stg_flight_outcomes`,
grouped by `flight_year`, and compared against the Phase 1
full-population data-quality assessment:

| Year | Scheduled | Eligible arrivals | Arrivals >=15 min late | Late arrival % | Cancelled |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2024 | 7,079,061 | 6,965,247 | 1,449,966 | 20.82% | 96,315 |
| 2025 | 7,001,619 | 6,879,484 | 1,534,638 | 22.31% | 102,876 |

These totals match the published Phase 1 annual counts and rate
definitions. In particular, the known completed flight with NULL
`ArrDel15` remains in staging but is not included in the arrival
punctuality denominator.

## Scope limitations

- Staging views do not provide independent persisted snapshots; they
  reflect the current committed `silver.flights` data.
- dbt view creation and test success do not yet validate future
  fact/dimension joins or Gold marts.
- Timestamp normalization, departure-delay eligibility and weather
  joins are intentionally deferred until their rules are finalized.
- The dbt State extension printed an optional authentication notice;
  local PostgreSQL dbt execution completed without cloud credentials.
