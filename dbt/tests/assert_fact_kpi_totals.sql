-- Additive KPI components must not change when moving from staging to Fact.
with staging_years as (
    select
        extract(year from flight_date)::integer as calendar_year,
        sum(scheduled_flight_count) as scheduled,
        sum(completed_flight_count) as completed,
        sum(cancelled_flight_count) as cancelled,
        sum(diverted_flight_count) as diverted,
        sum(eligible_arrival_count) as eligible_arrivals,
        sum(arrival_delayed_15_count) as late_arrivals,
        sum(arrival_on_time_count) as on_time_arrivals
    from {{ ref('stg_flight_outcomes') }}
    group by 1
), fact_years as (
    select
        extract(year from flight_date)::integer as calendar_year,
        sum(scheduled_flight_count) as scheduled,
        sum(completed_flight_count) as completed,
        sum(cancelled_flight_count) as cancelled,
        sum(diverted_flight_count) as diverted,
        sum(eligible_arrival_count) as eligible_arrivals,
        sum(arrival_delayed_15_count) as late_arrivals,
        sum(arrival_on_time_count) as on_time_arrivals
    from {{ ref('fct_flights') }}
    group by 1
)
select
    coalesce(s.calendar_year, f.calendar_year) as calendar_year,
    s.scheduled as staging_scheduled,
    f.scheduled as fact_scheduled
from staging_years as s
full outer join fact_years as f on s.calendar_year = f.calendar_year
where
    s.scheduled is distinct from f.scheduled
    or s.completed is distinct from f.completed
    or s.cancelled is distinct from f.cancelled
    or s.diverted is distinct from f.diverted
    or s.eligible_arrivals is distinct from f.eligible_arrivals
    or s.late_arrivals is distinct from f.late_arrivals
    or s.on_time_arrivals is distinct from f.on_time_arrivals
