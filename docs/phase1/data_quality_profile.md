# Phase 1 — Data quality profile / Báo cáo chất lượng dữ liệu

**Profiling method:** Streamed the complete BTS January 2025 CSV inside its official ZIP using `src/phase1/profile_bts.py`; all **539,747 rows** were inspected. The JSON result is available at [profile_2025_01.json](profile_2025_01.json). This is an observed source profile, not an inferred sample or synthetic dataset.

## 1. Structural checks

| Quality rule | January result | Assessment |
| --- | ---: | --- |
| Rows scanned | **539,747** | Full monthly CSV |
| Expected named fields present | 15 / 15 | PASS — all required pilot columns available |
| Named source columns | **109** | PASS — matches BTS field scope |
| Unnamed trailing CSV header | **1** | KNOWN QUIRK — exclude empty header when parsing |
| Distinct flight dates | **31** | PASS — expected calendar coverage |
| Invalid flight dates | **0** | PASS |
| Flights outside January 2025 | **0** | PASS |
| Candidate business-key duplicates | **0** | PASS for this month; not proof of global uniqueness |
| Candidate key with missing component | **0** | PASS |
| Extended-key duplicates | **0** | PASS for this month |
| Exact duplicate source rows | **0** | PASS |
| Cancelled + diverted both set | **0** | PASS |
| `ArrDel15` contradicts numeric `ArrDelay` | **0** | PASS |
| Completed flight with unknown `ArrDel15` | **0** | PASS |
| Cancelled flight with populated `ArrDelay` | **0** | PASS |
| Diverted flight with populated `ArrDelay` | **0** | PASS |
| Invalid HHMM formats in scheduled or actual times | **0** | PASS |
| Actual departure time `2400` | **33** | KNOWN LOCAL-TIME BOUNDARY — handle as next-day midnight |
| Actual arrival time `2400` | **245** | KNOWN LOCAL-TIME BOUNDARY — handle as next-day midnight |

**Important interpretation:** `2400` is an accepted end-of-day boundary value. It must be converted deliberately when creating timestamps, rather than flagged as an invalid time or silently coerced to `00:00` on the same date.

## 2. Missing values: distinguish valid absence from defects

| Field | NULL rows | NULL rate | Interpretation / planned treatment |
| --- | ---: | ---: | --- |
| `FlightDate` | 0 | 0.0000% | Required; reject if absent in future files. |
| `CRSDepTime` | 0 | 0.0000% | Required for scheduled time and flight key. |
| `Cancelled` | 0 | 0.0000% | Status present. |
| `Diverted` | 0 | 0.0000% | Status present. |
| `ArrDelay` | **17,478** | **3.2382%** | Exactly 16,312 cancelled + 1,166 diverted flights; preserve NULL. |
| `ArrDel15` | **17,478** | **3.2382%** | Same operational exclusions; preserve NULL. |
| `DepDelay` | 15,923 | 2.9501% | Gate departure may exist for some subsequently cancelled flights; do not infer status from this column. |
| `Tail_Number` | 2,530 | 0.4687% | Not suitable as mandatory source PK. |
| `CancellationCode` | 523,435 | 96.9778% | Mostly inapplicable to noncancelled flights. |
| `CarrierDelay` | 441,617 | 81.8193% | Conditional reported delay-cause metric; NULL is not necessarily zero. |
| `WeatherDelay` | 441,617 | 81.8193% | BTS cause attribution; **not** NOAA weather readings. |
| `Div1Airport` | 538,495 | 99.7680% | Only applicable to some diverted-flight reporting outcomes. |

**24 columns have 100% NULL** in January: all recorded third, fourth and fifth diversion-airport detail fields (`Div3*`, `Div4*`, `Div5*`). **48 of 109 named columns have at least 95% NULL**. That pattern reflects specialized, conditional diversion/cancellation columns. In Phase 2, preserve them in the raw ZIP; model only useful fields in the initial fact table instead of dropping records based on sparse optional attributes.

## 3. Reconciled business metrics

```text
Scheduled flights:                        539,747
   ├─ Completed:                        522,269
   ├─ Cancelled:                         16,312
   └─ Diverted (not cancelled):           1,166

Eligible for arrival on-time KPI:         522,269
   ├─ On-time arrivals (<15 min late):   424,139
   └─ Late arrivals (>=15 min):          98,130
```

Calculated rates:

- Arrival on-time: `424139 / 522269 × 100 = 81.2108%`.
- Arrival delayed 15+ minutes: `98130 / 522269 × 100 = 18.7892%`.
- Cancelled: `16312 / 539747 × 100 = 3.0222%`.
- Diverted (not cancelled): `1166 / 539747 × 100 = 0.2160%`.

The status categories reconcile to **539,747**; on-time and delayed counts reconcile to **522,269**. These are January operational statistics for reported domestic flights, **not** annual or global performance measurements.

## 4. Uniqueness testing and remaining risk

Both the six-field candidate (`FlightDate`, DOT carrier ID, flight number, origin airport ID, destination airport ID, scheduled departure HHMM) and seven-field candidate (add `CRSArrTime`) produced **539,747 distinct keys**. Exact-row duplicates: **0**.

This supports the proposed grain for January 2025; it **does not establish a guaranteed unique key** for the entire historical dataset. Phase 2 should retain a deterministic lineage key (`source_year_month + source_csv_row_number`) and profile candidate-key collisions in every month, including reprocessed files, before imposing a physical unique constraint.

## 5. Quality gates for Phase 2

1. Ingest the raw bytes unchanged; record ZIP checksum `868387dcedaef1b8d8392e608e642219fde50d594c3cf2094aec858167629ccf` for the pilot.
2. Verify that the parsed January landing contains exactly **539,747 source records** and preserves valid cancellations/diversions.
3. Reject missing `FlightDate`, `OriginAirportID`, `DestAirportID`, `DOT_ID_Reporting_Airline`, flight number or `CRSDepTime`; quarantine and explain key collisions rather than discarding without trace.
4. Parse `0.00` / `1.00` indicators into boolean/integer only after validating the allowed set.
5. Parse HHMM using airport-local time zones later; handle `2400`, daylight saving and midnight rollover.
6. Preserve NULL in `ArrDelay`, `ArrDel15`, conditional delay causes and diversion fields; never fill using blanket zero defaults.
7. Compute KPIs on explicit eligible populations, and reconcile counts after each Bronze → landing → mart load.

## 6. Reproduction

Run the command from repository root after downloading the official ZIP:

```bash
python -m src.phase1.profile_bts --zip data/raw/bts/2025/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_1.zip --expected-month 2025-01 --output docs/phase1/profile_2025_01.json
python -m unittest discover -s tests -v
```

The profiler reads records in a stream without full CSV extraction and is intentionally dependency-light. This profile is **not** a substitute for typed schema, timezone, and station join validation in later phases.
