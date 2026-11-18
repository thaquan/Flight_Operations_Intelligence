-- Star schema must preserve every physical Silver record in every BTS month.
with silver_counts as (
    select source_month, count(*) as silver_rows
    from {{ source('silver', 'flights') }}
    group by 1
), fact_counts as (
    select source_month, count(*) as fact_rows
    from {{ ref('fct_flights') }}
    group by 1
)
select
    coalesce(s.source_month, f.source_month) as source_month,
    s.silver_rows,
    f.fact_rows
from silver_counts as s
full outer join fact_counts as f on s.source_month = f.source_month
where s.silver_rows is distinct from f.fact_rows
