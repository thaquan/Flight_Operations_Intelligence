# Business Data Dictionary

The table below covers the attributes required for the initial warehouse and Power BI model. The companion [field catalog](field_catalog.md) inventories **all 109 observed named source columns** and their measured 2024–2025 NULL rates.

All types below are **proposed canonical types**, not values already converted by Phase 1. The original BTS CSV is preserved unchanged.

| Source field | Proposed type | Business meaning | Important handling |
| --- | --- | --- | --- |
| `Year`, `Month`, `DayofMonth` | INTEGER | Calendar components of flight service date | Reconcile with `FlightDate`. |
| `DayOfWeek` | INTEGER | Day of the week as coded by BTS | Validate coding against official definitions. |
| `FlightDate` | DATE | Scheduled service date | Month partition and date dimension key. |
| `Reporting_Airline` | TEXT | BTS reporting carrier code | Display code; not guaranteed globally stable. |
| `DOT_ID_Reporting_Airline` | INTEGER | DOT carrier identifier | Preferred carrier natural key. |
| `Flight_Number_Reporting_Airline` | TEXT NULL | Reported flight number | One observed NULL; not a standalone unique key. |
| `Tail_Number` | TEXT NULL | Aircraft registration | Optional tail-rotation analysis. |
| `OriginAirportID`, `DestAirportID` | INTEGER | DOT identifiers for origin and destination airports | Two foreign-key roles to `dim_airport`. |
| `Origin`, `Dest` | TEXT | Origin and destination airport codes | Labels and directed-route construction. |
| `OriginCityName`, `DestCityName` | TEXT | City labels for origin and destination | Dimension attributes. |
| `OriginState`, `DestState` | TEXT | State abbreviations | U.S. domestic geographic segmentation. |
| `CRSDepTime`, `CRSArrTime` | HHMM TEXT | Scheduled local departure/arrival clock times | Not UTC; handle `2400` and date rollover. |
| `DepTime`, `ArrTime` | HHMM TEXT NULL | Actual local departure/arrival clock times | Missingness depends on flight outcome. |
| `DepDelay`, `ArrDelay` | DECIMAL NULL | Signed departure/arrival delay in minutes | Negative = early; NULL is not zero. |
| `DepDelayMinutes`, `ArrDelayMinutes` | DECIMAL NULL | Nonnegative delay minutes | Distinct from signed delay. |
| `DepDel15`, `ArrDel15` | BOOLEAN NULL | At least 15 minutes late indicator | Core punctuality measures; one completed flight lacks `ArrDel15`. |
| `Cancelled`, `Diverted` | BOOLEAN | Cancellation and diversion indicators | Retain every source row and separate outcomes. |
| `CancellationCode` | TEXT NULL | BTS cancellation cause code | Applicable primarily to cancelled flights. |
| `Distance` | DECIMAL NULL | Reported route distance in statute miles | Clearly label unit; do not assume kilometres. |
| `CRSElapsedTime`, `ActualElapsedTime`, `AirTime` | DECIMAL NULL | Scheduled, actual and airborne duration in minutes | Missing for some irregular operations. |
| `CarrierDelay` | DECIMAL NULL | Airline-attributed delay minutes | Conditional cause field. |
| `WeatherDelay` | DECIMAL NULL | BTS-attributed weather delay minutes | Not equivalent to NOAA measured weather. |
| `NASDelay` | DECIMAL NULL | National Aviation System delay minutes | Conditional cause field. |
| `SecurityDelay` | DECIMAL NULL | Security-attributed delay minutes | Conditional cause field. |
| `LateAircraftDelay` | DECIMAL NULL | Inbound aircraft-attributed delay minutes | Conditional cause field. |
| `DivReachedDest`, `DivArrDelay` | BOOLEAN / DECIMAL NULL | Outcome details for diverted flights | Do not substitute for regular arrival delay. |
| `Flights` | DECIMAL | Observation weight in reporting file | Profile flags values other than 1. |

## Source schema rules

1. All 24 observed files contain 109 named fields and one trailing empty CSV header position. Exclude the unnamed header from the canonical schema, preserving the original bytes.
2. Use the same header validation for each month; the profiling report found no 2024–2025 named-field drift.
3. Keep `source_file`, `source_row_number`, and `source_sha256` as lineage columns in Bronze.
4. Do not enforce the candidate business key as a physical primary key: an August 2024 record lacks its flight number.
5. Preserve source NULLs; design KPI denominators around operational applicability.

## References

- [BTS field definitions](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ)
- [KPI definitions](kpi_definitions.md)
- [Source field catalog and missingness](field_catalog.md)
