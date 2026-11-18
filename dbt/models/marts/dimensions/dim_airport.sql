{{ config(indexes=[{'columns': ['airport_sk'], 'unique': True}]) }}

-- Build a role-playing airport dimension from BOTH origin and destination.
-- Group before ranking so attribute variants do not multiply fact rows.
with airport_observations as (
    select
        origin_airport_id as airport_id,
        origin_airport_code as airport_code,
        nullif(btrim(origin_city_name), '') as city_name,
        nullif(upper(btrim(origin_state)), '') as state_code,
        count(*) as flight_observations,
        max(flight_date) as last_observed_date
    from {{ ref('stg_flights') }}
    where origin_airport_id is not null
    group by 1, 2, 3, 4

    union all

    select
        dest_airport_id as airport_id,
        destination_airport_code as airport_code,
        nullif(btrim(dest_city_name), '') as city_name,
        nullif(upper(btrim(dest_state)), '') as state_code,
        count(*) as flight_observations,
        max(flight_date) as last_observed_date
    from {{ ref('stg_flights') }}
    where dest_airport_id is not null
    group by 1, 2, 3, 4
), merged as (
    select
        airport_id,
        airport_code,
        city_name,
        state_code,
        sum(flight_observations) as total_observations,
        max(last_observed_date) as last_observed_date
    from airport_observations
    group by 1, 2, 3, 4
), ranked as (
    select
        *,
        row_number() over (
            partition by airport_id
            order by total_observations desc, last_observed_date desc,
                     airport_code asc nulls last, city_name asc nulls last,
                     state_code asc nulls last
        ) as rank_number
    from merged
)

select
    -1::integer as airport_sk,
    null::integer as airport_id,
    'UNK'::text as airport_code,
    'Unknown'::text as city_name,
    null::text as state_code,
    true as is_unknown
union all
select
    (1000000 + airport_id)::integer as airport_sk,
    airport_id,
    airport_code,
    city_name,
    state_code,
    false as is_unknown
from ranked
where rank_number = 1
