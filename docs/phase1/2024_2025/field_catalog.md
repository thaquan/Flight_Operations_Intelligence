# BTS Source Field Catalog (2024-2025)

All named fields observed in the monthly CSV header. Raw values are text; type names are proposed for Phase 2-3, not transformations performed in Phase 1.
NULL percentages are weighted by actual flight rows across all 24 months.
Consult the [official BTS field definitions](https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=FGJ) for the complete authoritative semantics.

| Field | Proposed type | NULL % | Role / interpretation |
| --- | --- | ---: | --- |
| `Year` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `Quarter` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `Month` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `DayofMonth` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `DayOfWeek` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `FlightDate` | DATE | 0.000000% | Scheduled flight service date |
| `Reporting_Airline` | TEXT | 0.000000% | Reporting carrier code |
| `DOT_ID_Reporting_Airline` | INTEGER | 0.000000% | DOT reporting carrier identifier |
| `IATA_CODE_Reporting_Airline` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `Tail_Number` | TEXT | 0.231899% | Aircraft registration |
| `Flight_Number_Reporting_Airline` | TEXT | 0.000007% | Flight number for reporting carrier |
| `OriginAirportID` | INTEGER | 0.000000% | BTS origin airport identifier |
| `OriginAirportSeqID` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `OriginCityMarketID` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `Origin` | TEXT | 0.000000% | Origin airport code |
| `OriginCityName` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `OriginState` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `OriginStateFips` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `OriginStateName` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `OriginWac` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `DestAirportID` | INTEGER | 0.000000% | BTS destination airport identifier |
| `DestAirportSeqID` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `DestCityMarketID` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `Dest` | TEXT | 0.000000% | Destination airport code |
| `DestCityName` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `DestState` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `DestStateFips` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `DestStateName` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `DestWac` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `CRSDepTime` | HHMM TEXT | 0.000000% | Scheduled local departure time |
| `DepTime` | HHMM TEXT | 1.355254% | Actual local departure time |
| `DepDelay` | DECIMAL | 1.360453% | Signed departure delay in minutes |
| `DepDelayMinutes` | REVIEW | 1.360453% | Additional BTS source attribute; preserve raw value |
| `DepDel15` | BOOLEAN | 1.360453% | Departure at least 15 minutes late |
| `DepartureDelayGroups` | REVIEW | 1.360453% | Additional BTS source attribute; preserve raw value |
| `DepTimeBlk` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `TaxiOut` | REVIEW | 1.405593% | Additional BTS source attribute; preserve raw value |
| `WheelsOff` | REVIEW | 1.405593% | Additional BTS source attribute; preserve raw value |
| `WheelsOn` | REVIEW | 1.437885% | Additional BTS source attribute; preserve raw value |
| `TaxiIn` | REVIEW | 1.437885% | Additional BTS source attribute; preserve raw value |
| `CRSArrTime` | HHMM TEXT | 0.000000% | Scheduled local arrival time |
| `ArrTime` | HHMM TEXT | 1.437871% | Actual local arrival time |
| `ArrDelay` | DECIMAL | 1.675693% | Signed arrival delay in minutes |
| `ArrDelayMinutes` | REVIEW | 1.675693% | Additional BTS source attribute; preserve raw value |
| `ArrDel15` | BOOLEAN | 1.675693% | Arrival at least 15 minutes late |
| `ArrivalDelayGroups` | REVIEW | 1.675693% | Additional BTS source attribute; preserve raw value |
| `ArrTimeBlk` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `Cancelled` | BOOLEAN | 0.000000% | Flight cancelled indicator |
| `CancellationCode` | TEXT | 98.585360% | Reported cancellation cause |
| `Diverted` | BOOLEAN | 0.000000% | Flight diverted indicator |
| `CRSElapsedTime` | REVIEW | 0.000021% | Additional BTS source attribute; preserve raw value |
| `ActualElapsedTime` | REVIEW | 1.675693% | Additional BTS source attribute; preserve raw value |
| `AirTime` | REVIEW | 1.675693% | Additional BTS source attribute; preserve raw value |
| `Flights` | DECIMAL | 0.000000% | Flight observation weight |
| `Distance` | DECIMAL | 0.000000% | Reported route distance in miles |
| `DistanceGroup` | REVIEW | 0.000000% | Additional BTS source attribute; preserve raw value |
| `CarrierDelay` | DECIMAL | 78.803566% | Airline-attributable delay minutes |
| `WeatherDelay` | DECIMAL | 78.803566% | BTS-classified weather delay minutes |
| `NASDelay` | DECIMAL | 78.803566% | National Aviation System delay minutes |
| `SecurityDelay` | DECIMAL | 78.803566% | Security-related delay minutes |
| `LateAircraftDelay` | DECIMAL | 78.803566% | Late-arriving aircraft delay minutes |
| `FirstDepTime` | REVIEW | 99.252153% | Additional BTS source attribute; preserve raw value |
| `TotalAddGTime` | REVIEW | 99.252359% | Additional BTS source attribute; preserve raw value |
| `LongestAddGTime` | REVIEW | 99.252373% | Additional BTS source attribute; preserve raw value |
| `DivAirportLandings` | REVIEW | 0.000021% | Additional BTS source attribute; preserve raw value |
| `DivReachedDest` | REVIEW | 99.738954% | Additional BTS source attribute; preserve raw value |
| `DivActualElapsedTime` | REVIEW | 99.762178% | Additional BTS source attribute; preserve raw value |
| `DivArrDelay` | REVIEW | 99.762178% | Additional BTS source attribute; preserve raw value |
| `DivDistance` | REVIEW | 99.738954% | Additional BTS source attribute; preserve raw value |
| `Div1Airport` | REVIEW | 99.729772% | Additional BTS source attribute; preserve raw value |
| `Div1AirportID` | REVIEW | 99.729772% | Additional BTS source attribute; preserve raw value |
| `Div1AirportSeqID` | REVIEW | 99.729772% | Additional BTS source attribute; preserve raw value |
| `Div1WheelsOn` | REVIEW | 99.729786% | Additional BTS source attribute; preserve raw value |
| `Div1TotalGTime` | REVIEW | 99.729772% | Additional BTS source attribute; preserve raw value |
| `Div1LongestGTime` | REVIEW | 99.729772% | Additional BTS source attribute; preserve raw value |
| `Div1WheelsOff` | REVIEW | 99.760573% | Additional BTS source attribute; preserve raw value |
| `Div1TailNum` | REVIEW | 99.760573% | Additional BTS source attribute; preserve raw value |
| `Div2Airport` | REVIEW | 99.997031% | Additional BTS source attribute; preserve raw value |
| `Div2AirportID` | REVIEW | 99.997024% | Additional BTS source attribute; preserve raw value |
| `Div2AirportSeqID` | REVIEW | 99.997024% | Additional BTS source attribute; preserve raw value |
| `Div2WheelsOn` | REVIEW | 99.997031% | Additional BTS source attribute; preserve raw value |
| `Div2TotalGTime` | REVIEW | 99.997031% | Additional BTS source attribute; preserve raw value |
| `Div2LongestGTime` | REVIEW | 99.997031% | Additional BTS source attribute; preserve raw value |
| `Div2WheelsOff` | REVIEW | 99.998501% | Additional BTS source attribute; preserve raw value |
| `Div2TailNum` | REVIEW | 99.998501% | Additional BTS source attribute; preserve raw value |
| `Div3Airport` | REVIEW | 99.999957% | Additional BTS source attribute; preserve raw value |
| `Div3AirportID` | REVIEW | 99.999957% | Additional BTS source attribute; preserve raw value |
| `Div3AirportSeqID` | REVIEW | 99.999957% | Additional BTS source attribute; preserve raw value |
| `Div3WheelsOn` | REVIEW | 99.999957% | Additional BTS source attribute; preserve raw value |
| `Div3TotalGTime` | REVIEW | 99.999957% | Additional BTS source attribute; preserve raw value |
| `Div3LongestGTime` | REVIEW | 99.999957% | Additional BTS source attribute; preserve raw value |
| `Div3WheelsOff` | REVIEW | 99.999972% | Additional BTS source attribute; preserve raw value |
| `Div3TailNum` | REVIEW | 99.999972% | Additional BTS source attribute; preserve raw value |
| `Div4Airport` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div4AirportID` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div4AirportSeqID` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div4WheelsOn` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div4TotalGTime` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div4LongestGTime` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div4WheelsOff` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div4TailNum` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div5Airport` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div5AirportID` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div5AirportSeqID` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div5WheelsOn` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div5TotalGTime` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div5LongestGTime` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div5WheelsOff` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |
| `Div5TailNum` | REVIEW | 100.000000% | Additional BTS source attribute; preserve raw value |

## Modeling conventions

- Do not assume a source flight-number or airline-code field is globally unique.
- Treat sparse cancellation, diversion and delay-cause fields as conditional attributes.
- Preserve source values until transformations, numeric casts and timestamp rules have been tested.
- Phase 2 should explicitly type the remaining `REVIEW` fields that will enter the curated schema; not every raw column belongs in the star schema.
