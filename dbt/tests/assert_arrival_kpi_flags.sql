-- Null ArrDel15 must not be mistaken for on-time; cancelled/diverted
-- flights cannot enter the eligible-arrival denominator.
select source_month, source_row_number
from {{ ref('stg_flight_outcomes') }}
where
    scheduled_flight_count <> 1
    or completed_flight_count <> case when flight_status = 'completed' then 1 else 0 end
    or cancelled_flight_count <> case when flight_status = 'cancelled' then 1 else 0 end
    or diverted_flight_count <> case when flight_status = 'diverted' then 1 else 0 end
    or completed_flight_count + cancelled_flight_count + diverted_flight_count > 1
    or eligible_arrival_count <> case
        when flight_status = 'completed' and arr_del15 in (0, 1) then 1 else 0 end
    or arrival_delayed_15_count <> case
        when flight_status = 'completed' and arr_del15 = 1 then 1 else 0 end
    or arrival_on_time_count <> case
        when flight_status = 'completed' and arr_del15 = 0 then 1 else 0 end
    or arrival_delayed_15_count + arrival_on_time_count <> eligible_arrival_count
