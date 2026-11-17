-- Add additive KPI components without discarding cancelled/diverted observations.
-- Rates are calculated later as SUM(numerator) / SUM(denominator).
with classified as (
    select
        f.*,
        case
            when cancelled = 1 then 'cancelled'
            when cancelled = 0 and diverted = 1 then 'diverted'
            when cancelled = 0 and diverted = 0 then 'completed'
            else 'unknown'
        end as flight_status
    from {{ ref('stg_flights') }} as f
)

select
    c.*,
    1 as scheduled_flight_count,
    case when flight_status = 'completed' then 1 else 0 end as completed_flight_count,
    case when flight_status = 'cancelled' then 1 else 0 end as cancelled_flight_count,
    case when flight_status = 'diverted' then 1 else 0 end as diverted_flight_count,
    case
        when flight_status = 'completed' and arr_del15 in (0, 1) then 1
        else 0
    end as eligible_arrival_count,
    case
        when flight_status = 'completed' and arr_del15 = 1 then 1
        else 0
    end as arrival_delayed_15_count,
    case
        when flight_status = 'completed' and arr_del15 = 0 then 1
        else 0
    end as arrival_on_time_count
from classified as c
