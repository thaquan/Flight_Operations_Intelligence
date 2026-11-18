{{ config(tags=['m35']) }}
-- Composite-key uniqueness for all Gold aggregates; a test returns zero rows.
with violations as (
    select 'airline_month' as mart, count(*) as duplicate_rows
    from (
        select airline_sk, source_month
        from {{ ref('mart_airline_monthly') }}
        group by 1, 2 having count(*) > 1
    ) d
    union all
    select 'airport_role_day', count(*)
    from (
        select airport_sk, airport_role, flight_date
        from {{ ref('mart_airport_daily') }}
        group by 1, 2, 3 having count(*) > 1
    ) d
    union all
    select 'directed_route_month', count(*)
    from (
        select origin_airport_sk, dest_airport_sk, source_month
        from {{ ref('mart_route_monthly') }}
        group by 1, 2, 3 having count(*) > 1
    ) d
    union all
    select 'airline_cause_month', count(*)
    from (
        select airline_sk, source_month, cause_type
        from {{ ref('mart_delay_causes') }}
        group by 1, 2, 3 having count(*) > 1
    ) d
)
select * from violations where duplicate_rows <> 0
