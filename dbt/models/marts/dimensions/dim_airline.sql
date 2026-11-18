{{ config(indexes=[{'columns': ['airline_sk'], 'unique': True}]) }}

-- Choose a single observed carrier-code tuple for each stable DOT carrier ID.
-- Most frequent wins; the remaining tie breakers are deterministic.
with observed as (
    select
        reporting_airline_dot_id as airline_dot_id,
        airline_code,
        nullif(upper(btrim(reporting_airline_iata)), '') as airline_iata_code,
        count(*) as flight_observations,
        max(flight_date) as last_observed_date
    from {{ ref('stg_flights') }}
    where reporting_airline_dot_id is not null
    group by 1, 2, 3
), ranked as (
    select
        *,
        row_number() over (
            partition by airline_dot_id
            order by flight_observations desc, last_observed_date desc,
                     airline_code asc nulls last, airline_iata_code asc nulls last
        ) as rank_number
    from observed
)

select
    -1::integer as airline_sk,
    null::integer as airline_dot_id,
    'UNK'::text as airline_code,
    null::text as airline_iata_code,
    true as is_unknown
union all
select
    (1000000 + airline_dot_id)::integer as airline_sk,
    airline_dot_id,
    airline_code,
    airline_iata_code,
    false as is_unknown
from ranked
where rank_number = 1
