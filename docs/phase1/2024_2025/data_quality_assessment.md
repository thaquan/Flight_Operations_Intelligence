# BTS 2024-2025: Full-Scope Data Quality Assessment

**Validation status:** PASS. Source manifest timestamp: 2026-11-15T02:57:02+00:00.

**Coverage:** 24/24 months.
**Flight records:** 14,080,680 (all reporting airlines and airports).
**Source columns:** 109.
**Compressed ZIP storage:** 709,735,704 bytes.
**Uncompressed CSV storage:** 6,370,981,019 bytes.
**Distinct origin airports / reporting airlines / directed routes:** 358 / 15 / 7,328.

## Year-by-year measured KPIs

| Year | Scheduled flights | Eligible arrivals | Arrival >=15 min late | Cancellation rate |
| --- | ---: | ---: | ---: | ---: |
| 2024 | 7,079,061 | 6,965,247 | 20.82% | 1.36% |
| 2025 | 7,001,619 | 6,879,484 | 22.31% | 1.47% |

Rates are recomputed from total counts, not averaged from monthly percentages.

## 2025 versus 2024

- Scheduled flight volume: -1.09%.
- Arrival delay >=15 minutes: +1.49 percentage points.
- Cancellation: +0.11 percentage points.

## Monthly source coverage

| Month | Rows | First flight date | Last flight date | Delay >=15 min |
| --- | ---: | --- | --- | ---: |
| 2024-01 | 547,271 | 2024-01-01 | 2024-01-31 | 24.06% |
| 2024-02 | 519,221 | 2024-02-01 | 2024-02-29 | 15.92% |
| 2024-03 | 591,767 | 2024-03-01 | 2024-03-31 | 20.85% |
| 2024-04 | 582,185 | 2024-04-01 | 2024-04-30 | 19.06% |
| 2024-05 | 609,743 | 2024-05-01 | 2024-05-31 | 26.41% |
| 2024-06 | 611,132 | 2024-06-01 | 2024-06-30 | 24.94% |
| 2024-07 | 634,613 | 2024-07-01 | 2024-07-31 | 29.62% |
| 2024-08 | 619,025 | 2024-08-01 | 2024-08-31 | 23.47% |
| 2024-09 | 582,622 | 2024-09-01 | 2024-09-30 | 15.51% |
| 2024-10 | 615,497 | 2024-10-01 | 2024-10-31 | 13.20% |
| 2024-11 | 575,404 | 2024-11-01 | 2024-11-30 | 14.67% |
| 2024-12 | 590,581 | 2024-12-01 | 2024-12-31 | 21.16% |
| 2025-01 | 539,747 | 2025-01-01 | 2025-01-31 | 18.79% |
| 2025-02 | 504,884 | 2025-02-01 | 2025-02-28 | 20.77% |
| 2025-03 | 600,872 | 2025-03-01 | 2025-03-31 | 19.59% |
| 2025-04 | 583,950 | 2025-04-01 | 2025-04-30 | 19.66% |
| 2025-05 | 605,648 | 2025-05-01 | 2025-05-31 | 23.60% |
| 2025-06 | 611,575 | 2025-06-01 | 2025-06-30 | 28.26% |
| 2025-07 | 631,428 | 2025-07-01 | 2025-07-31 | 28.89% |
| 2025-08 | 602,378 | 2025-08-01 | 2025-08-31 | 22.56% |
| 2025-09 | 562,439 | 2025-09-01 | 2025-09-30 | 16.63% |
| 2025-10 | 605,844 | 2025-10-01 | 2025-10-31 | 20.32% |
| 2025-11 | 570,550 | 2025-11-01 | 2025-11-30 | 20.56% |
| 2025-12 | 582,304 | 2025-12-01 | 2025-12-31 | 26.77% |

## Top 20 origin airports by reported flight count

| Rank | Airport | Flights |
| ---: | --- | ---: |
| 1 | ATL | 656,343 |
| 2 | DFW | 629,436 |
| 3 | DEN | 626,331 |
| 4 | ORD | 607,080 |
| 5 | CLT | 412,980 |
| 6 | PHX | 390,307 |
| 7 | LAX | 384,525 |
| 8 | LAS | 373,055 |
| 9 | SEA | 328,559 |
| 10 | MCO | 319,601 |
| 11 | LGA | 298,157 |
| 12 | BOS | 286,349 |
| 13 | DCA | 282,522 |
| 14 | SFO | 279,473 |
| 15 | DTW | 253,900 |
| 16 | EWR | 249,265 |
| 17 | MSP | 239,710 |
| 18 | IAH | 233,199 |
| 19 | SLC | 229,545 |
| 20 | JFK | 228,108 |

## Source anomalies

| Anomaly | Records |
| --- | ---: |
| ArrTime_2400_boundary | 7,486 |
| CRSArrTime_2400_boundary | 2 |
| CRSDepTime_2400_boundary | 2 |
| DepTime_2400_boundary | 1,468 |
| completed_missing_arrdel15 | 1 |
| missing_business_key_component | 1 |
| missing_extended_key_component | 1 |

## Validation errors

- None.

## Review warnings

- 2024-08: flight record missing a candidate business-key component; preserve source-row lineage
- 2025-09: completed flight missing ArrDel15; excluded from arrival punctuality denominator

## Methodology and interpretation

- Every record comes from a verified monthly ZIP published by BTS; the manifest stores SHA-256 hashes and ZIP CRC checks.
- Missing numeric delay values are preserved, not imputed. Cancelled and diverted flights are excluded from the arrival-delay denominator.
- Arrival delay >=15 minutes is computed from BTS `ArrDel15` for non-cancelled, non-diverted flights with a populated indicator.
- Year-over-year comparisons describe reported flights, not every U.S. flight or all global aviation activity.
- Candidate-key collisions and other anomalies are retained for investigation; this assessment does not silently deduplicate.
- See `aggregate_profile.json` and all 24 month-level JSON profiles for exact machine-readable measures.
