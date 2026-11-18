-- Shared additive denominators, reused by every volume/performance mart.
-- NULL ArrDel15 never counts as an eligible or on-time arrival.
{% macro flight_kpi_metrics() -%}
    sum(scheduled_flight_count)::bigint as scheduled_flights,
    sum(completed_flight_count)::bigint as completed_flights,
    sum(cancelled_flight_count)::bigint as cancelled_flights,
    sum(diverted_flight_count)::bigint as diverted_flights,
    sum(eligible_arrival_count)::bigint as eligible_arrivals,
    sum(arrival_delayed_15_count)::bigint as late_arrivals_15,
    sum(arrival_on_time_count)::bigint as on_time_arrivals,
    round(
        100.0 * sum(cancelled_flight_count)
        / nullif(sum(scheduled_flight_count), 0), 2
    ) as cancellation_rate_pct,
    round(
        100.0 * sum(diverted_flight_count)
        / nullif(sum(scheduled_flight_count), 0), 2
    ) as diversion_rate_pct,
    round(
        100.0 * sum(arrival_delayed_15_count)
        / nullif(sum(eligible_arrival_count), 0), 2
    ) as arrival_delay_15_rate_pct,
    round(
        100.0 * sum(arrival_on_time_count)
        / nullif(sum(eligible_arrival_count), 0), 2
    ) as arrival_on_time_rate_pct,
    count(arr_delay) filter (
        where completed_flight_count = 1
    )::bigint as signed_arrival_delay_observations,
    round(
        (avg(arr_delay) filter (
            where completed_flight_count = 1
        ))::numeric, 2
    ) as avg_signed_arrival_delay_minutes,
    round(
        (avg(greatest(arr_delay, 0)) filter (
            where completed_flight_count = 1
        ))::numeric, 2
    ) as avg_positive_arrival_delay_minutes
{%- endmacro %}
