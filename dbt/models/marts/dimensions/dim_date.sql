{{ config(indexes=[{'columns': ['date_key'], 'unique': True}]) }}

-- One calendar row per date in the actual source range, including leap days.
with bounds as (
    select min(flight_date) as first_date, max(flight_date) as last_date
    from {{ ref('stg_flights') }}
), calendar as (
    select days.day_value::date as flight_date
    from bounds
    cross join lateral generate_series(
        bounds.first_date, bounds.last_date, interval '1 day'
    ) as days(day_value)
)

select
    (extract(year from flight_date)::integer * 10000
     + extract(month from flight_date)::integer * 100
     + extract(day from flight_date)::integer) as date_key,
    flight_date,
    extract(year from flight_date)::smallint as calendar_year,
    extract(quarter from flight_date)::smallint as calendar_quarter,
    extract(month from flight_date)::smallint as calendar_month,
    extract(day from flight_date)::smallint as day_of_month,
    extract(isodow from flight_date)::smallint as iso_day_of_week,
    extract(week from flight_date)::smallint as iso_week_of_year,
    to_char(flight_date, 'IYYY')::smallint as iso_week_year,
    (extract(isodow from flight_date) in (6, 7)) as is_weekend
from calendar
