{{ config(indexes=[
    {'columns': ['airline_sk', 'source_month', 'cause_type'], 'unique': True}
]) }}

-- BTS-reported attribution categories, not NOAA observed weather.
-- NULL means not reported/applicable and is not silently converted to zero.
with reported as (
    select
        f.airline_sk,
        f.source_month,
        cause.cause_type,
        cause.cause_minutes
    from {{ ref('fct_flights') }} as f
    cross join lateral (values
        ('carrier'::text, f.carrier_delay),
        ('weather'::text, f.weather_delay),
        ('nas'::text, f.nas_delay),
        ('security'::text, f.security_delay),
        ('late_aircraft'::text, f.late_aircraft_delay)
    ) as cause(cause_type, cause_minutes)
    where cause.cause_minutes is not null
), aggregated as (
    select
        airline_sk,
        source_month,
        cause_type,
        count(*)::bigint as reported_observations,
        count(*) filter (where cause_minutes > 0)::bigint
            as positive_delay_observations,
        round(sum(cause_minutes)::numeric, 2) as reported_delay_minutes,
        round(avg(cause_minutes)::numeric, 2) as avg_reported_cause_minutes
    from reported
    group by airline_sk, source_month, cause_type
)

select
    *,
    round(
        100.0 * reported_delay_minutes
        / nullif(
            sum(reported_delay_minutes) over (
                partition by airline_sk, source_month
            ), 0
        ), 2
    ) as attributed_delay_share_pct
from aggregated
