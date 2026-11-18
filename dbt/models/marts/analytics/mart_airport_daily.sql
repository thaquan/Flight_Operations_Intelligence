{{ config(indexes=[
    {'columns': ['airport_sk', 'airport_role', 'flight_date'], 'unique': True},
    {'columns': ['flight_date', 'airport_role']}
]) }}

-- Each flight contributes one origin and one destination row BEFORE
-- aggregation. Keep airport_role when consuming this mart: never add
-- origin and destination network totals together.
with airport_roles as (
    select
        origin_airport_sk as airport_sk,
        'origin'::text as airport_role,
        flight_date,
        flight_date_key,
        scheduled_flight_count,
        completed_flight_count,
        cancelled_flight_count,
        diverted_flight_count,
        eligible_arrival_count,
        arrival_delayed_15_count,
        arrival_on_time_count,
        arr_delay,
        taxi_out,
        taxi_in
    from {{ ref('fct_flights') }}

    union all

    select
        dest_airport_sk as airport_sk,
        'destination'::text as airport_role,
        flight_date,
        flight_date_key,
        scheduled_flight_count,
        completed_flight_count,
        cancelled_flight_count,
        diverted_flight_count,
        eligible_arrival_count,
        arrival_delayed_15_count,
        arrival_on_time_count,
        arr_delay,
        taxi_out,
        taxi_in
    from {{ ref('fct_flights') }}
)

select
    airport_sk,
    airport_role,
    flight_date,
    flight_date_key,
    {{ flight_kpi_metrics() }},
    case when airport_role = 'origin' then
        round(avg(taxi_out)::numeric, 2)
    end as avg_taxi_out_minutes,
    case when airport_role = 'destination' then
        round(avg(taxi_in)::numeric, 2)
    end as avg_taxi_in_minutes
from airport_roles
group by airport_sk, airport_role, flight_date, flight_date_key
