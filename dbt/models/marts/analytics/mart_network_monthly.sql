{{ config(indexes=[{'columns': ['source_month'], 'unique': True}]) }}

-- Network-wide month grain; no source outcome filtering.
select
    source_month,
    extract(year from source_month)::smallint as calendar_year,
    extract(month from source_month)::smallint as calendar_month,
    {{ flight_kpi_metrics() }}
from {{ ref('fct_flights') }}
group by source_month
