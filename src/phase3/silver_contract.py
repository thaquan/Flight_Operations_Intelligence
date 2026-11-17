"""Explicit Bronze-to-Silver column contract.

Bronze retains all 109 BTS fields. Silver keeps the attributes needed for
flight, airline, airport, route, delay and diversion analysis.
"""

from __future__ import annotations


SOURCE_TO_TARGET = (
    ("Year", "flight_year"),
    ("Quarter", "quarter"),
    ("Month", "flight_month_number"),
    ("DayofMonth", "day_of_month"),
    ("DayOfWeek", "day_of_week"),
    ("FlightDate", "flight_date"),
    ("Reporting_Airline", "reporting_airline"),
    ("DOT_ID_Reporting_Airline", "reporting_airline_dot_id"),
    ("IATA_CODE_Reporting_Airline", "reporting_airline_iata"),
    ("Tail_Number", "tail_number"),
    ("Flight_Number_Reporting_Airline", "flight_number"),
    ("OriginAirportID", "origin_airport_id"),
    ("OriginAirportSeqID", "origin_airport_seq_id"),
    ("OriginCityMarketID", "origin_city_market_id"),
    ("Origin", "origin"),
    ("OriginCityName", "origin_city_name"),
    ("OriginState", "origin_state"),
    ("DestAirportID", "dest_airport_id"),
    ("DestAirportSeqID", "dest_airport_seq_id"),
    ("DestCityMarketID", "dest_city_market_id"),
    ("Dest", "dest"),
    ("DestCityName", "dest_city_name"),
    ("DestState", "dest_state"),
    ("CRSDepTime", "crs_dep_time"),
    ("DepTime", "dep_time"),
    ("DepDelay", "dep_delay"),
    ("DepDelayMinutes", "dep_delay_minutes"),
    ("DepDel15", "dep_del15"),
    ("DepTimeBlk", "dep_time_block"),
    ("TaxiOut", "taxi_out"),
    ("WheelsOff", "wheels_off"),
    ("WheelsOn", "wheels_on"),
    ("TaxiIn", "taxi_in"),
    ("CRSArrTime", "crs_arr_time"),
    ("ArrTime", "arr_time"),
    ("ArrDelay", "arr_delay"),
    ("ArrDelayMinutes", "arr_delay_minutes"),
    ("ArrDel15", "arr_del15"),
    ("ArrTimeBlk", "arr_time_block"),
    ("Cancelled", "cancelled"),
    ("CancellationCode", "cancellation_code"),
    ("Diverted", "diverted"),
    ("CRSElapsedTime", "crs_elapsed_time"),
    ("ActualElapsedTime", "actual_elapsed_time"),
    ("AirTime", "air_time"),
    ("Flights", "flights"),
    ("Distance", "distance"),
    ("DistanceGroup", "distance_group"),
    ("CarrierDelay", "carrier_delay"),
    ("WeatherDelay", "weather_delay"),
    ("NASDelay", "nas_delay"),
    ("SecurityDelay", "security_delay"),
    ("LateAircraftDelay", "late_aircraft_delay"),
    ("DivAirportLandings", "div_airport_landings"),
    ("DivReachedDest", "div_reached_dest"),
    ("DivArrDelay", "div_arr_delay"),
    ("DivDistance", "div_distance"),
    ("Div1Airport", "div1_airport"),
    ("source_file", "source_file"),
    ("source_sha256", "source_sha256"),
    ("source_row_number", "source_row_number"),
    ("ingested_at_utc", "bronze_ingested_at_utc"),
)

BRONZE_COLUMNS = tuple(source for source, _ in SOURCE_TO_TARGET)
SILVER_COLUMNS = ("source_month",) + tuple(target for _, target in SOURCE_TO_TARGET)

if len(set(BRONZE_COLUMNS)) != len(BRONZE_COLUMNS):
    raise RuntimeError("Duplicate Bronze column in Silver contract")
if len(set(SILVER_COLUMNS)) != len(SILVER_COLUMNS):
    raise RuntimeError("Duplicate Silver column in Silver contract")
