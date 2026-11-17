-- Every source observation must survive both staging models, month by month.
with silver_counts as (
    select source_month, count(*) as silver_rows
    from {{ source('silver', 'flights') }}
    group by source_month
), staged_counts as (
    select source_month, count(*) as staged_rows
    from {{ ref('stg_flight_outcomes') }}
    group by source_month
)

select
    coalesce(s.source_month, t.source_month) as source_month,
    s.silver_rows,
    t.staged_rows
from silver_counts as s
full outer join staged_counts as t on s.source_month = t.source_month
where s.silver_rows is distinct from t.staged_rows
