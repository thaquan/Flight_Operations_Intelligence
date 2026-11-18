-- Synthetic BTS-shaped records for isolated CI only; never load into flight_warehouse.
-- Includes completed/on-time, delayed, cancelled, diverted, missing ArrDel15,
-- unknown dimension keys, leap day, NULL versus zero delay attribution.
insert into silver.flights (
    source_month, source_row_number, flight_year, flight_date,
    reporting_airline, reporting_airline_dot_id, reporting_airline_iata,
    origin_airport_id, origin, dest_airport_id, dest,
    cancelled, diverted, arr_del15, arr_delay,
    carrier_delay, weather_delay, nas_delay, security_delay, late_aircraft_delay,
    source_file, source_sha256, bronze_ingested_at_utc
)
select
    date_trunc('month', v.flight_date)::date,
    v.row_no,
    extract(year from v.flight_date)::smallint,
    v.flight_date,
    v.airline_code, v.airline_id, v.airline_code,
    v.origin_id, v.origin_code, v.dest_id, v.dest_code,
    v.cancelled, v.diverted, v.arr_del15, v.arr_delay,
    v.carrier_delay, v.weather_delay, v.nas_delay,
    v.security_delay, v.late_aircraft_delay,
    'ci_fixture.zip', repeat('a', 64), timestamptz '2026-01-01 00:00:00+00'
from (values
    (date '2024-01-03',1,19805,'AA',12478,'JFK',12892,'LAX',0,0,0,-7,null,null,null,null,null),
    (date '2024-01-03',2,19805,'AA',12478,'JFK',12892,'LAX',0,0,1,32,20,0,12,0,0),
    (date '2024-01-04',3,19805,'AA',12892,'LAX',12478,'JFK',1,0,null,null,null,null,null,null,null),
    (date '2024-01-04',4,19805,'AA',12892,'LAX',12478,'JFK',0,1,null,null,null,null,null,null,null),
    (date '2024-01-05',5,20409,'BB',14771,'SFO',12892,'LAX',0,0,1,70,0,50,20,0,0),
    (date '2024-01-05',6,20409,'BB',14771,'SFO',12892,'LAX',0,0,null,null,null,null,null,null,null),
    (date '2024-02-29',1,19805,'AA',12478,'JFK',14771,'SFO',0,0,0,0,null,null,null,null,null),
    (date '2024-02-29',2,null,null,null,null,12478,'JFK',0,0,1,20,10,0,10,0,0),
    (date '2025-01-02',1,19805,'AA',12892,'LAX',12478,'JFK',0,0,0,-2,null,null,null,null,null),
    (date '2025-01-02',2,20409,'BB',14771,'SFO',12478,'JFK',1,0,null,null,null,null,null,null,null)
) as v(
    flight_date, row_no, airline_id, airline_code, origin_id, origin_code,
    dest_id, dest_code, cancelled, diverted, arr_del15, arr_delay,
    carrier_delay, weather_delay, nas_delay, security_delay, late_aircraft_delay
)
on conflict (source_month, source_row_number) do nothing;

insert into audit.silver_loads (
    source_month, source_sha256, parquet_sha256,
    bronze_row_count, silver_row_count
)
select source_month, repeat('a', 64), repeat('b', 64), count(*), count(*)
from silver.flights
group by source_month
on conflict (source_month) do nothing;
