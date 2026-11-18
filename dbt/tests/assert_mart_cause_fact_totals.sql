{{ config(tags=['m35']) }}
-- Compare both non-NULL attribution observations and their minutes with fact.
with fact_causes as (
    select f.airline_sk, f.source_month,
           c.cause_type, count(*)::bigint as reported_observations,
           count(*) filter (where c.cause_minutes > 0)::bigint
               as positive_delay_observations,
           round(sum(c.cause_minutes)::numeric,2) as reported_delay_minutes
    from {{ ref('fct_flights') }} f
    cross join lateral (values
        ('carrier'::text, f.carrier_delay),
        ('weather'::text, f.weather_delay),
        ('nas'::text, f.nas_delay),
        ('security'::text, f.security_delay),
        ('late_aircraft'::text, f.late_aircraft_delay)
    ) c(cause_type, cause_minutes)
    where c.cause_minutes is not null
    group by f.airline_sk, f.source_month, c.cause_type
)
select coalesce(f.airline_sk, m.airline_sk) as airline_sk,
       coalesce(f.source_month, m.source_month) as source_month,
       coalesce(f.cause_type, m.cause_type) as cause_type
from fact_causes f
full join {{ ref('mart_delay_causes') }} m
  on f.airline_sk = m.airline_sk
 and f.source_month = m.source_month
 and f.cause_type = m.cause_type
where f.airline_sk is null or m.airline_sk is null
   or f.reported_observations is distinct from m.reported_observations
   or f.positive_delay_observations is distinct from m.positive_delay_observations
   or f.reported_delay_minutes is distinct from m.reported_delay_minutes
