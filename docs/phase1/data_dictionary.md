# Phase 1 — Data dictionary / Từ điển dữ liệu

**Source:** U.S. DOT / BTS — Reporting Carrier On-Time Performance (1987–present). This is a curated subset of fields necessary for the MVP, **not a claim that the source contains only these fields**. All source columns are listed in the machine-readable profile JSON.

The types below are **proposed warehouse types**. Values in the source CSV arrive as text; type casting belongs in Phase 2–3.

| Source field | Planned logical type | Meaning / Vietnamese | Key handling rule |
| --- | --- | --- | --- |
| `Year`, `Month`, `DayofMonth` | integer | Year, month, day / năm, tháng, ngày | Reconcile against `FlightDate`. |
| `FlightDate` | date | Scheduled flight date / ngày bay | Must be valid and within source month. |
| `Reporting_Airline` | string | Reporting (operating) carrier code / mã hãng vận hành báo cáo | Use for display, stable uniqueness is **not** assumed over long history. |
| `DOT_ID_Reporting_Airline` | integer | U.S. DOT carrier identifier / mã định danh hãng | Preferred dimension natural ID across years. |
| `Flight_Number_Reporting_Airline` | string | Reported flight number / số hiệu chuyến | Not unique by itself. |
| `Tail_Number` | string, nullable | Aircraft registration / số đăng ký tàu bay | Often unavailable; future rotation analysis only. |
| `OriginAirportID`, `DestAirportID` | integer | Stable DOT airport IDs / mã định danh sân bay | Prefer for dimensional keys across years. |
| `Origin`, `Dest` | string | Origin and destination airport codes / mã sân bay đi/đến | Display; code reuse possible over time. |
| `OriginCityName`, `DestCityName` | string | Airport city / thành phố | Dimension attributes. |
| `OriginState`, `DestState` | string | U.S. state abbreviations / bang | Dimension attributes. |
| `CRSDepTime` | HHMM local-time string | Scheduled departure / giờ xuất phát theo lịch | **Not UTC**; preserve leading zero and handle `2400`/date rollover explicitly. |
| `CRSArrTime` | HHMM local-time string | Scheduled arrival / giờ đến theo lịch | Use **destination** airport time zone if converting; date rollover matters. |
| `DepTime`, `ArrTime` | HHMM local-time string, nullable | Actual gate times / giờ rời/đến cổng thực tế | Missing for some cancelled/diverted flights. |
| `DepDelay`, `ArrDelay` | numeric minutes, nullable | Signed departure/arrival delay / phút trễ có dấu | Negative = early; NULL for cancellations/diversions where not applicable. |
| `DepDelayMinutes`, `ArrDelayMinutes` | numeric minutes, nullable | Nonnegative delay minutes / số phút trễ không âm | Early arrivals/departures set to zero. |
| `DepDel15`, `ArrDel15` | 0/1, nullable | 15+ minutes late / trễ từ 15 phút | Source CSV uses `0.00` / `1.00`. |
| `Cancelled`, `Diverted` | 0/1 | Flight cancellation/diversion / hủy/chuyển hướng | Distinct operational outcomes; do not coerce NULL ArrDelay to zero. |
| `CancellationCode` | string, nullable | Cancellation reason code / mã lý do hủy | Primarily populated when `Cancelled = 1`. |
| `Distance` | numeric miles | Great-circle-ish route distance from BTS / khoảng cách tuyến bay | Use BTS value and label miles. |
| `CRSElapsedTime`, `ActualElapsedTime`, `AirTime` | numeric minutes, nullable | Scheduled/actual duration/airborne time / thời lượng | Handle cancelled and diverted separately. |
| `CarrierDelay` | numeric minutes, nullable | Delay attributable to carrier / trễ do hãng | Optional cause field; missing does not mean zero. |
| `WeatherDelay` | numeric minutes, nullable | BTS-classified weather delay / trễ do thời tiết | **Different** from NOAA measured weather conditions. |
| `NASDelay` | numeric minutes, nullable | National Aviation System delay / trễ hệ thống hàng không | Cause field. |
| `SecurityDelay` | numeric minutes, nullable | Security delay / trễ an ninh | Cause field. |
| `LateAircraftDelay` | numeric minutes, nullable | Late inbound aircraft delay / tàu bay đến trễ | Important for future rotation analysis. |
| `DivArrDelay`, `DivReachedDest` | numeric/binary, nullable | Diverted-flight arrival outcome / kết quả chuyến chuyển hướng | Do not substitute for standard `ArrDelay`. |

## KPI definitions agreed for Phase 5

1. **Scheduled flights:** Count of all BTS flight records in the chosen scope; confirm grain/uniqueness before this becomes `COUNTROWS(fct_flights)`.
2. **Completed flights:** `Cancelled = 0 AND Diverted = 0`.
3. **Arrival eligible flights:** Completed flights with known `ArrDel15` (denominator for arrival punctuality).
4. **Arrival on-time rate:** Arrival eligible flights with `ArrDel15 = 0` / all arrival eligible flights. **On-time means less than 15 minutes late.**
5. **15+ minute arrival delay rate:** Arrival eligible flights with `ArrDel15 = 1` / all arrival eligible flights.
6. **Cancellation rate:** `Cancelled = 1` / all scheduled flights.
7. **Diversion rate:** `Cancelled = 0 AND Diverted = 1` / all scheduled flights.
8. **Average arrival delay:** Mean of available signed `ArrDelay` on applicable flights, explicitly document denominator and negative values.

No revenue, ticket pricing, passenger counts, profitability, or aircraft capacity is available in this dataset. Do not create KPIs for those measures.

## NOAA extension (Phase 6 only)

Proposed extra fields: `weather_station_id`, observation time in UTC, temperature, precipitation, wind, visibility and weather QC flags (depending on station's actual available variables). Mapping airport → weather station and local scheduled departure → UTC **must be validated** before joining.

References: [BTS fields](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ), [BTS data-table definitions](https://transtats.bts.gov/TableInfo.asp?QO_fu146_anzr=b0-gvzr&V0s1_b0yB=D&gnoyr_VQ=FGJ), [NOAA GHCNh](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly).
