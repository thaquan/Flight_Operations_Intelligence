{{ config(tags=['m35']) }}
-- All five additive KPI families must reconcile at the monthly grain.
with network as (
    select source_month, scheduled_flights, completed_flights,
           cancelled_flights, diverted_flights, eligible_arrivals,
           late_arrivals_15, on_time_arrivals
    from {{ ref('mart_network_monthly') }}
), segments as (
    select 'airline' as segment, source_month, sum(scheduled_flights) as scheduled_flights,
           sum(completed_flights) as completed_flights, sum(cancelled_flights) as cancelled_flights,
           sum(diverted_flights) as diverted_flights, sum(eligible_arrivals) as eligible_arrivals,
           sum(late_arrivals_15) as late_arrivals_15, sum(on_time_arrivals) as on_time_arrivals
    from {{ ref('mart_airline_monthly') }} group by source_month
    union all
    select 'route', source_month, sum(scheduled_flights), sum(completed_flights),
           sum(cancelled_flights), sum(diverted_flights), sum(eligible_arrivals),
           sum(late_arrivals_15), sum(on_time_arrivals)
    from {{ ref('mart_route_monthly') }} group by source_month
    union all
    select airport_role, date_trunc('month', flight_date)::date,
           sum(scheduled_flights), sum(completed_flights), sum(cancelled_flights),
           sum(diverted_flights), sum(eligible_arrivals), sum(late_arrivals_15),
           sum(on_time_arrivals)
    from {{ ref('mart_airport_daily') }}
    group by airport_role, date_trunc('month', flight_date)
)
select segments.segment, segments.source_month
from segments full join network using (source_month)
where network.source_month is null
   or segments.source_month is null
   or segments.scheduled_flights is distinct from network.scheduled_flights
   or segments.completed_flights is distinct from network.completed_flights
   or segments.cancelled_flights is distinct from network.cancelled_flights
   or segments.diverted_flights is distinct from network.diverted_flights
   or segments.eligible_arrivals is distinct from network.eligible_arrivals
   or segments.late_arrivals_15 is distinct from network.late_arrivals_15
   or segments.on_time_arrivals is distinct from network.on_time_arrivals
