{{ config(indexes=[
    {'columns': ['flight_sk'], 'unique': True},
    {'columns': ['flight_date_key']},
    {'columns': ['origin_airport_sk']}
]) }}

-- One fact row for each physical source observation, never a candidate
-- business-flight key. No dimension joins are needed to assign stable keys.
select
    (
        (extract(year from source_month)::bigint * 100
         + extract(month from source_month)::bigint) * 10000000
        + source_row_number
    ) as flight_sk,
    source_month,
    source_row_number,
    source_file,
    source_sha256,
    flight_date,
    (extract(year from flight_date)::integer * 10000
     + extract(month from flight_date)::integer * 100
     + extract(day from flight_date)::integer) as flight_date_key,
    case
        when reporting_airline_dot_id is null then -1
        else 1000000 + reporting_airline_dot_id
    end as airline_sk,
    case
        when origin_airport_id is null then -1
        else 1000000 + origin_airport_id
    end as origin_airport_sk,
    case
        when dest_airport_id is null then -1
        else 1000000 + dest_airport_id
    end as dest_airport_sk,
    reporting_airline_dot_id,
    origin_airport_id,
    dest_airport_id,
    flight_number,
    tail_number,
    crs_dep_time,
    dep_time,
    crs_arr_time,
    arr_time,
    flight_status,
    cancelled,
    diverted,
    cancellation_code,
    scheduled_flight_count,
    completed_flight_count,
    cancelled_flight_count,
    diverted_flight_count,
    eligible_arrival_count,
    arrival_delayed_15_count,
    arrival_on_time_count,
    dep_del15,
    dep_delay,
    dep_delay_minutes,
    arr_del15,
    arr_delay,
    arr_delay_minutes,
    crs_elapsed_time,
    actual_elapsed_time,
    air_time,
    taxi_out,
    taxi_in,
    distance,
    carrier_delay,
    weather_delay,
    nas_delay,
    security_delay,
    late_aircraft_delay,
    bronze_ingested_at_utc,
    silver_loaded_at_utc
from {{ ref('stg_flight_outcomes') }}
