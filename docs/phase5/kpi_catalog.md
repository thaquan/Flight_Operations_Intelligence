# Phase 5 / M5.1 - KPI catalog

## Measurement contract

All counts below are additive **within a compatible mart grain**. Build rates
from summed counts after report filters. In DAX, use `DIVIDE()` to return
BLANK for a zero denominator and format as Percent, not by multiplying by
100 in the measure.

| Display measure | Calculation | Denominator / interpretation | Primary source |
| --- | --- | --- | --- |
| Scheduled Flights | SUM(`scheduled_flights`) | All BTS reporting records | Network / relevant segment mart |
| Completed Flights | SUM(`completed_flights`) | Flights neither cancelled nor diverted | Network / relevant segment mart |
| Eligible Arrivals | SUM(`eligible_arrivals`) | Completed with known ArrDel15 | Network / relevant segment mart |
| Late Arrivals 15+ | SUM(`late_arrivals_15`) | Arrival 15+ min late, among eligible | Network / relevant segment mart |
| On-Time Arrivals | SUM(`on_time_arrivals`) | Arrival delay <15m, among eligible | Network / relevant segment mart |
| Arrival Delay 15+ Rate | Late Arrivals 15+ / Eligible Arrivals | Eligible arrivals, **not** scheduled flights | Network / relevant segment mart |
| Arrival On-Time Rate | On-Time Arrivals / Eligible Arrivals | Eligible arrivals | Network / relevant segment mart |
| Cancellation Rate | SUM(`cancelled_flights`) / Scheduled Flights | Scheduled flights | Network / relevant segment mart |
| Diversion Rate | SUM(`diverted_flights`) / Scheduled Flights | Scheduled flights | Network / relevant segment mart |
| Reported Cause Minutes | SUM(`reported_delay_minutes`) | BTS category minute sum | Delay causes |
| Cause Minute Share | Selected cause minutes / all selected cause minutes | Total across cause categories in current airline/month context | Delay causes |
| Positive Cause Observations | SUM(`positive_delay_observations`) | Counts category-specific nonzero cause entries | Delay causes |

Do **not** sum `mart_delay_causes.reported_observations` and label the
result delayed flights. A flight can appear in several cause categories.
Similarly, do not sum both `origin` and `destination` airport-role rows to
calculate network scheduled flights.

The marts also expose `avg_signed_arrival_delay_minutes` and
`avg_positive_arrival_delay_minutes`. Their values are **not additive**.
For multi-group reporting, rebuild an accurately weighted mean from
underlying delay sums and valid counts or use `gold.fct_flights`; do not
average the mart-level means or multiply rounded values and claim precision.
Keep mean-delay visuals out of the first release unless verified.

## Verified reference snapshot

Source: `docs/phase4/quality_report.json`, validated against BTS for all
24 source months. Numbers here are **QA baselines**, not a hardcoded Power BI
data source.

| Reference measure | Verified value |
| --- | ---: |
| Scheduled flights | 14,080,680 |
| Completed flights | 13,844,732 |
| Eligible arrivals | 13,844,731 |
| Late arrivals 15+ | 2,984,604 |
| On-time arrivals | 10,860,127 |
| Cancelled flights | 199,191 |
| Diverted flights | 36,757 |
| Arrival delay 15+ rate | 21.56% |
| Arrival on-time rate | 78.44% |
| Cancellation rate | 1.41% |
| Diversion rate | 0.26% |

There is one completed flight without a known ArrDel15, so
`completed_flights != eligible_arrivals`. This is an intentional quality
exception, not an arithmetic mistake.

## Acceptance tests for M5.3

- Full-period network totals match every additive value in the table above.
- `late_arrivals_15 + on_time_arrivals = eligible_arrivals` after every
  valid month or airline selection.
- 2024 delay rate = **20.82%** and 2025 = **22.31%** when using the annual
  network aggregate, per Phase 3 reconciliation.
- A multi-month selected rate is a **ratio of sums**, never the arithmetic
  mean of monthly percentages.
- A single airport-role view reconciles with the corresponding airport
  monthly totals. Switching role does not double flight totals.
- Directed route A -> B is different from B -> A.
- Delay Cause percentages sum to 100% only when the denominator includes all
  cause categories and the selected cause-minute total is nonzero.
- An Airline slicer does not alter the route mart unless an airline-resolved
  route source is explicitly added and validated in a future milestone.
