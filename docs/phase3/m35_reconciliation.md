# M3.5 - Gold mart reconciliation

Verified against the local PostgreSQL warehouse on 2026-11-18 after
materializing and rebuilding all five marts. The original source population
has **24 monthly BTS files and 14,080,680 physical flight records**.

## Materialized rows

| Mart | First build | Repeat build | Result |
| --- | ---: | ---: | --- |
| `mart_network_monthly` | 24 | 24 | Match |
| `mart_airline_monthly` | 348 | 348 | Match |
| `mart_airport_daily` | 481,262 | 481,262 | Match |
| `mart_route_monthly` | 139,287 | 139,287 | Match |
| `mart_delay_causes` | 1,740 | 1,740 | Match |

Rebuilding creates a new version of each **table**, so these counts are
evidence of repeatable results, not evidence of incremental merge support.
No mart filters top airports, carriers, months or flight statuses.

## Annual network KPIs

Re-aggregated from the materialized `mart_network_monthly`, with
`arrival_delay_15_rate_pct = 100 * SUM(late_arrivals_15) /
SUM(eligible_arrivals)`.

| Year | Scheduled | Eligible arrivals | Arrivals late 15+ | Delay rate |
| --- | ---: | ---: | ---: | ---: |
| 2024 | 7,079,061 | 6,965,247 | 1,449,966 | 20.82% |
| 2025 | 7,001,619 | 6,879,484 | 1,534,638 | 22.31% |
| **Total** | **14,080,680** | **13,844,731** | **2,984,604** | Calculated from totals |

These figures agree with previously verified M3.3/M3.4 KPI baselines.
The fact-to-network dbt test compares **all seven additive counters per
month**; no monthly count or numerator/denominator drift was observed.

## Independent reconciliation checks

The five singular dbt tests in `dbt/tests/assert_mart_*.sql` confirm:

1. No duplicate composite grains for airline, airport-role/day, directed
   route, or airline/month/cause.
2. Every month and additive counter in the network mart matches
   `gold.fct_flights` exactly.
3. Aggregating airline, route, origin-airport and destination-airport
   mart rows **independently** reproduces each network month's counters.
4. Percentage fields agree with their stored additive numerators and
   eligible denominators (to the documented two-decimal precision).
5. The cause mart matches the source fact independently for reported
   non-NULL observations, positive observations, and total minutes.

There is intentionally **no cross-role sum** for the airport mart. It
would count each flight twice. Combining the five BTS cause categories
is valid for **minutes** but not for counts of unique flights.

## Source cause attribution snapshot

For each cause field, 2,984,602 source records had a non-NULL value;
many of those values are zero and do not mean a positive contribution.

| Cause | Strictly positive records | Reported minutes |
| --- | ---: | ---: |
| Carrier | 1,594,275 | 72,149,640 |
| Late aircraft | 1,517,615 | 85,836,655 |
| NAS | 1,518,942 | 44,105,725 |
| Security | 12,506 | 332,730 |
| Weather (BTS category) | 189,008 | 13,304,587 |

An explicit `NULL` remains excluded from both the observation count and
the minute sum; no source `NULL` was silently replaced with zero.
The fact-versus-cause reconciliation passed after the final rebuild.
