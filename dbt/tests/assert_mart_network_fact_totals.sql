{{ config(tags=['m35']) }}
-- Independent fact-to-network reconciliation, including the complete source grain.
with fact_monthly as (
    select source_month,
           sum(scheduled_flight_count)::bigint as scheduled_flights,
           sum(completed_flight_count)::bigint as completed_flights,
           sum(cancelled_flight_count)::bigint as cancelled_flights,
           sum(diverted_flight_count)::bigint as diverted_flights,
           sum(eligible_arrival_count)::bigint as eligible_arrivals,
           sum(arrival_delayed_15_count)::bigint as late_arrivals_15,
           sum(arrival_on_time_count)::bigint as on_time_arrivals
    from {{ ref('fct_flights') }}
    group by source_month
)
select coalesce(f.source_month, m.source_month) as source_month
from fact_monthly f full join {{ ref('mart_network_monthly') }} m
    on f.source_month = m.source_month
where f.source_month is null or m.source_month is null
   or f.scheduled_flights is distinct from m.scheduled_flights
   or f.completed_flights is distinct from m.completed_flights
   or f.cancelled_flights is distinct from m.cancelled_flights
   or f.diverted_flights is distinct from m.diverted_flights
   or f.eligible_arrivals is distinct from m.eligible_arrivals
   or f.late_arrivals_15 is distinct from m.late_arrivals_15
   or f.on_time_arrivals is distinct from m.on_time_arrivals
