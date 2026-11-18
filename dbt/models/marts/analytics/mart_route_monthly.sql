{{ config(indexes=[
    {'columns': ['origin_airport_sk', 'dest_airport_sk', 'source_month'], 'unique': True},
    {'columns': ['source_month', 'origin_airport_sk']}
]) }}

-- Directed routes: origin -> destination is NOT interchangeable with reverse.
-- Keep all traffic; the minimum-volume threshold is a report-level choice.
select
    origin_airport_sk,
    dest_airport_sk,
    source_month,
    {{ flight_kpi_metrics() }}
from {{ ref('fct_flights') }}
group by origin_airport_sk, dest_airport_sk, source_month
