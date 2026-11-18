{{ config(tags=['m35']) }}
-- Sanity rules and exact source-numerator/denominator rate definitions.
with checks as (
    select 'network' as mart, scheduled_flights, completed_flights,
           cancelled_flights, diverted_flights, eligible_arrivals,
           late_arrivals_15, on_time_arrivals, cancellation_rate_pct,
           diversion_rate_pct, arrival_delay_15_rate_pct, arrival_on_time_rate_pct
    from {{ ref('mart_network_monthly') }}
    union all
    select 'airline', scheduled_flights, completed_flights, cancelled_flights,
           diverted_flights, eligible_arrivals, late_arrivals_15, on_time_arrivals,
           cancellation_rate_pct, diversion_rate_pct, arrival_delay_15_rate_pct,
           arrival_on_time_rate_pct
    from {{ ref('mart_airline_monthly') }}
    union all
    select 'airport', scheduled_flights, completed_flights, cancelled_flights,
           diverted_flights, eligible_arrivals, late_arrivals_15, on_time_arrivals,
           cancellation_rate_pct, diversion_rate_pct, arrival_delay_15_rate_pct,
           arrival_on_time_rate_pct
    from {{ ref('mart_airport_daily') }}
    union all
    select 'route', scheduled_flights, completed_flights, cancelled_flights,
           diverted_flights, eligible_arrivals, late_arrivals_15, on_time_arrivals,
           cancellation_rate_pct, diversion_rate_pct, arrival_delay_15_rate_pct,
           arrival_on_time_rate_pct
    from {{ ref('mart_route_monthly') }}
)
select mart, count(*) as invalid_rows from checks
where scheduled_flights <= 0
   or completed_flights + cancelled_flights + diverted_flights > scheduled_flights
   or eligible_arrivals > completed_flights
   or late_arrivals_15 + on_time_arrivals <> eligible_arrivals
   or cancellation_rate_pct is distinct from round(100.0 * cancelled_flights / nullif(scheduled_flights,0),2)
   or diversion_rate_pct is distinct from round(100.0 * diverted_flights / nullif(scheduled_flights,0),2)
   or arrival_delay_15_rate_pct is distinct from round(100.0 * late_arrivals_15 / nullif(eligible_arrivals,0),2)
   or arrival_on_time_rate_pct is distinct from round(100.0 * on_time_arrivals / nullif(eligible_arrivals,0),2)
group by mart
