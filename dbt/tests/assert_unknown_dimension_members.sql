-- Future NULL business IDs must map to exactly one -1 member per dimension.
select 'airline' as dimension_name, count(*) as unknown_rows
from {{ ref('dim_airline') }}
where airline_sk = -1
having count(*) <> 1

union all

select 'airport' as dimension_name, count(*) as unknown_rows
from {{ ref('dim_airport') }}
where airport_sk = -1
having count(*) <> 1
