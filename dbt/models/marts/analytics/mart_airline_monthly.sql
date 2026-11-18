{{ config(indexes=[{'columns': ['airline_sk', 'source_month'], 'unique': True}]) }}

-- Airline x source month, including any Unknown dimension member.
select
    airline_sk,
    source_month,
    {{ flight_kpi_metrics() }}
from {{ ref('fct_flights') }}
group by airline_sk, source_month
